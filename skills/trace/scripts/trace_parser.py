#!/usr/bin/env python3
"""
Trace parser for Blitzy agentic coding pipeline traces.

Supports two formats:
  - LangSmith JSON: exported via archie-tracing.py
  - Plain text: exported to ~/.traces/ with ====/---- delimiters and [ROLE] markers

Auto-detects format based on file content.

Usage:
    python3 trace_parser.py <trace-file> [--verbose] [--focus AREA]
    python3 trace_parser.py --latest [--verbose] [--focus AREA]
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass
class TraceConfig:
    """Configuration for trace parsing."""
    file_path: str = ""
    verbose: bool = False
    focus: str = ""  # decisions, todos, errors


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class RunSummary:
    """Summary of a single LLM run in the trace."""
    run_id: str
    run_name: str
    run_type: str
    message_count: int
    has_todo_list: bool = False
    has_code_blocks: bool = False
    error_count: int = 0


@dataclass
class ErrorEvent:
    """An error detected in the trace."""
    run_index: int
    message_index: int
    error_type: str  # stderr, exception, test_failure, syntax_error, validation_error
    content_preview: str


@dataclass
class TodoProgress:
    """To-do list progression tracking."""
    total_items: int = 0
    completed_items: int = 0
    phases: list[str] = field(default_factory=list)


@dataclass
class TodoSnapshot:
    """A snapshot of the to-do list at a point in time."""
    run_index: int
    total: int
    completed: int
    text: str  # the actual to-do list text


@dataclass
class ReasoningMessage:
    """An assistant text message representing agent reasoning."""
    run_index: int
    msg_index: int
    text: str           # full assistant text
    has_todo: bool
    has_code: bool
    follows_error: bool  # previous message was a tool error
    is_decision: bool    # contains strategy-shift language


@dataclass
class TraceDocument:
    """Aggregated data extracted from a trace."""
    trace_id: str = ""
    total_runs: int = 0
    total_messages: int = 0
    runs: list[RunSummary] = field(default_factory=list)
    errors: list[ErrorEvent] = field(default_factory=list)
    todo_progress: TodoProgress | None = None
    todo_snapshots: list[TodoSnapshot] = field(default_factory=list)
    reasoning_messages: list[ReasoningMessage] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Message classification patterns
# ---------------------------------------------------------------------------

_SIGNATURE_RE = re.compile(r"^\s*\{['\"]signature['\"]\s*:")
_EXIT_CODE_RE = re.compile(r"EXIT_CODE=(\d+)")
_TRACEBACK_RE = re.compile(r"Traceback \(most recent call last\)")
_TEST_FAIL_RE = re.compile(r"(FAILED|FAIL|AssertionError|assert .+ ==|test.*failed)", re.IGNORECASE)
_SYNTAX_ERR_RE = re.compile(r"(SyntaxError|IndentationError|TabError|unexpected token)", re.IGNORECASE)
_TODO_RE = re.compile(r"\[[ xX]\]")
_CODE_BLOCK_RE = re.compile(r"```")
_SUMMARY_RE = re.compile(r"^\s*\{['\"]summary['\"]\s*:")
_VALIDATION_ERR_RE = re.compile(
    r"(ValidationError|TypeError: .+ expected|ModuleNotFoundError|ImportError|NameError|AttributeError)",
    re.IGNORECASE,
)

# Strategy-shift language patterns
_DECISION_RE = re.compile(
    r"\b(instead|let me try|actually|the issue is|I need to|different approach|"
    r"let me reconsider|I('ll| will) switch|on second thought|that didn't work|"
    r"the problem is|the root cause|I realize|let me change|won't work|"
    r"better approach|rethink|pivot|going back to)\b",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

class TraceParser:
    """Parses a LangSmith trace JSON file and extracts reasoning data."""

    def __init__(self, config: TraceConfig | None = None):
        self.config = config or TraceConfig()

    def parse(self, data: dict) -> TraceDocument:
        """Parse trace data dict and return a TraceDocument."""
        doc = TraceDocument()
        doc.trace_id = data.get("trace_id", "unknown")
        runs_data = data.get("runs", [])
        doc.total_runs = len(runs_data)

        # Track whether the previous message was an error (across runs)
        last_was_error = False

        for run_index, run_data in enumerate(runs_data):
            messages = run_data.get("messages", [])
            summary = RunSummary(
                run_id=run_data.get("run_id", ""),
                run_name=run_data.get("run_name", "unknown"),
                run_type=run_data.get("run_type", "unknown"),
                message_count=len(messages),
            )

            for msg_index, msg in enumerate(messages):
                role = msg.get("role", "")
                content = msg.get("content", "")

                if role == "assistant":
                    if isinstance(content, str) and _SIGNATURE_RE.match(content):
                        # Tool call — skip
                        pass
                    elif isinstance(content, str) and content.strip():
                        # Text response — this is reasoning
                        has_todo = bool(_TODO_RE.search(content))
                        has_code = bool(_CODE_BLOCK_RE.search(content))
                        is_decision = bool(_DECISION_RE.search(content))

                        if has_todo:
                            summary.has_todo_list = True
                        if has_code:
                            summary.has_code_blocks = True

                        doc.reasoning_messages.append(ReasoningMessage(
                            run_index=run_index,
                            msg_index=msg_index,
                            text=content,
                            has_todo=has_todo,
                            has_code=has_code,
                            follows_error=last_was_error,
                            is_decision=is_decision,
                        ))

                        # Track to-do snapshots
                        if has_todo:
                            unchecked = len(re.findall(r"\[ \]", content))
                            checked = len(re.findall(r"\[[xX]\]", content))
                            if unchecked + checked > 0:
                                doc.todo_snapshots.append(TodoSnapshot(
                                    run_index=run_index,
                                    total=unchecked + checked,
                                    completed=checked,
                                    text=content,
                                ))

                        last_was_error = False

                elif role == "tool" and isinstance(content, str):
                    # Check for errors in tool results
                    is_error = self._is_error_result(content)
                    if is_error:
                        error_type = self._classify_error_type(content)
                        summary.error_count += 1
                        doc.errors.append(ErrorEvent(
                            run_index=run_index,
                            message_index=msg_index,
                            error_type=error_type,
                            content_preview=content[:300],
                        ))
                        last_was_error = True
                    else:
                        last_was_error = False
                else:
                    last_was_error = False

            doc.runs.append(summary)
            doc.total_messages += summary.message_count

        # Build to-do progress from snapshots
        if doc.todo_snapshots:
            last = doc.todo_snapshots[-1]
            phases = []
            prev_completed = 0
            for snap in doc.todo_snapshots:
                if snap.completed > prev_completed:
                    phases.append(f"Run {snap.run_index}: {snap.completed}/{snap.total} done")
                prev_completed = snap.completed
            doc.todo_progress = TodoProgress(
                total_items=last.total,
                completed_items=last.completed,
                phases=phases,
            )

        return doc

    def _is_error_result(self, content: str) -> bool:
        """Check if a tool result contains an error."""
        exit_codes = _EXIT_CODE_RE.findall(content)
        if any(code != "0" for code in exit_codes):
            return True
        if _TRACEBACK_RE.search(content):
            return True
        return False

    def _classify_error_type(self, content: str) -> str:
        """Classify the type of error in a tool result."""
        if _SYNTAX_ERR_RE.search(content):
            return "syntax_error"
        if _TEST_FAIL_RE.search(content):
            return "test_failure"
        if _VALIDATION_ERR_RE.search(content):
            return "validation_error"
        if _TRACEBACK_RE.search(content):
            return "exception"
        return "stderr"

    # -------------------------------------------------------------------
    # Output formatting
    # -------------------------------------------------------------------

    def format_output(self, doc: TraceDocument) -> str:
        """Format the extracted trace data as a reasoning-focused narrative."""
        focus = self.config.focus
        verbose = self.config.verbose

        if focus == "decisions":
            return self._format_decisions(doc, verbose)
        elif focus == "todos":
            return self._format_todos(doc, verbose)
        elif focus == "errors":
            return self._format_errors(doc, verbose)
        else:
            return self._format_full(doc, verbose)

    def _format_full(self, doc: TraceDocument, verbose: bool) -> str:
        """Full reasoning-focused output."""
        lines: list[str] = []

        # --- Header (3 lines max) ---
        lines.append(f"# Trace: `{doc.trace_id}`")
        todo_str = ""
        if doc.todo_progress:
            tp = doc.todo_progress
            pct = (tp.completed_items / tp.total_items * 100) if tp.total_items else 0
            todo_str = f" | To-do: {tp.completed_items}/{tp.total_items} ({pct:.0f}%)"
        lines.append(
            f"**{doc.total_runs} runs** | "
            f"{len(doc.reasoning_messages)} reasoning messages | "
            f"{len(doc.errors)} errors{todo_str}"
        )
        lines.append("")

        # --- Agent Reasoning Timeline ---
        lines.append("## Agent Reasoning Timeline")
        lines.append("")

        if not doc.reasoning_messages:
            lines.append("*No text reasoning messages found in this trace.*")
            lines.append("")
        else:
            for msg in doc.reasoning_messages:
                label = self._message_label(msg)
                text = msg.text if verbose else self._truncate(msg.text, 2000)
                lines.append(f"### Run {msg.run_index}{label}")
                lines.append("")
                lines.append(text)
                lines.append("")

        # --- To-Do Snapshots ---
        if doc.todo_snapshots:
            lines.append("## To-Do Snapshots")
            lines.append("")
            snapshots = self._pick_todo_snapshots(doc.todo_snapshots)
            for label, snap in snapshots:
                pct = (snap.completed / snap.total * 100) if snap.total else 0
                lines.append(f"### {label} (Run {snap.run_index}) — {snap.completed}/{snap.total} ({pct:.0f}%)")
                lines.append("")
                text = snap.text if verbose else self._truncate(snap.text, 1500)
                lines.append(text)
                lines.append("")

        # --- Key Decisions ---
        decisions = [m for m in doc.reasoning_messages if m.is_decision]
        if decisions:
            lines.append("## Key Decisions")
            lines.append("")
            lines.append(f"*{len(decisions)} messages contain strategy-shift language.*")
            lines.append("")
            for msg in decisions:
                label = self._message_label(msg)
                text = msg.text if verbose else self._truncate(msg.text, 1000)
                lines.append(f"### Run {msg.run_index}{label}")
                lines.append("")
                lines.append(text)
                lines.append("")

        return "\n".join(lines)

    def _format_decisions(self, doc: TraceDocument, verbose: bool) -> str:
        """Focus: only strategy-shift messages."""
        lines: list[str] = []
        decisions = [m for m in doc.reasoning_messages if m.is_decision]

        lines.append(f"# Trace: `{doc.trace_id}` — Decisions Focus")
        lines.append(f"**{len(decisions)} decision messages** out of {len(doc.reasoning_messages)} total reasoning messages")
        lines.append("")

        if not decisions:
            lines.append("*No strategy-shift language detected.*")
        else:
            for msg in decisions:
                label = self._message_label(msg)
                text = msg.text if verbose else self._truncate(msg.text, 2000)
                lines.append(f"## Run {msg.run_index}{label}")
                lines.append("")
                lines.append(text)
                lines.append("")

        return "\n".join(lines)

    def _format_todos(self, doc: TraceDocument, verbose: bool) -> str:
        """Focus: to-do list snapshots and progression."""
        lines: list[str] = []

        lines.append(f"# Trace: `{doc.trace_id}` — To-Do Focus")
        if doc.todo_progress:
            tp = doc.todo_progress
            pct = (tp.completed_items / tp.total_items * 100) if tp.total_items else 0
            lines.append(f"**{tp.completed_items}/{tp.total_items} items completed ({pct:.0f}%)**")
        else:
            lines.append("*No to-do lists found in this trace.*")
        lines.append("")

        if doc.todo_progress and doc.todo_progress.phases:
            lines.append("## Progression")
            lines.append("")
            for phase_desc in doc.todo_progress.phases:
                lines.append(f"- {phase_desc}")
            lines.append("")

        if doc.todo_snapshots:
            lines.append("## Snapshots")
            lines.append("")
            snapshots = self._pick_todo_snapshots(doc.todo_snapshots)
            for label, snap in snapshots:
                pct = (snap.completed / snap.total * 100) if snap.total else 0
                lines.append(f"### {label} (Run {snap.run_index}) — {snap.completed}/{snap.total} ({pct:.0f}%)")
                lines.append("")
                text = snap.text if verbose else self._truncate(snap.text, 2000)
                lines.append(text)
                lines.append("")

        return "\n".join(lines)

    def _format_errors(self, doc: TraceDocument, verbose: bool) -> str:
        """Focus: error→response pairs."""
        lines: list[str] = []

        lines.append(f"# Trace: `{doc.trace_id}` — Errors Focus")
        lines.append(f"**{len(doc.errors)} errors detected**")
        lines.append("")

        if not doc.errors:
            lines.append("*No errors found in this trace.*")
            return "\n".join(lines)

        # Group errors with the agent's response that follows
        error_responses = [m for m in doc.reasoning_messages if m.follows_error]

        lines.append("## Error → Response Pairs")
        lines.append("")

        # For each error, find the next reasoning message
        for err in doc.errors:
            lines.append(f"### Error at Run {err.run_index}, msg {err.message_index} [{err.error_type}]")
            lines.append("")
            preview = err.content_preview.replace("\n", "\n> ")
            lines.append(f"> {preview}")
            lines.append("")

            # Find the next reasoning message after this error
            response = None
            for msg in doc.reasoning_messages:
                if msg.run_index > err.run_index or (
                    msg.run_index == err.run_index and msg.msg_index > err.message_index
                ):
                    response = msg
                    break

            if response:
                text = response.text if verbose else self._truncate(response.text, 1000)
                lines.append(f"**Agent response (Run {response.run_index}):**")
                lines.append("")
                lines.append(text)
            else:
                lines.append("*No reasoning response found after this error.*")
            lines.append("")

        # Summary
        lines.append("## Error Summary")
        lines.append("")
        error_types: dict[str, int] = {}
        for err in doc.errors:
            error_types[err.error_type] = error_types.get(err.error_type, 0) + 1
        for etype, count in sorted(error_types.items(), key=lambda x: -x[1]):
            lines.append(f"- **{etype}**: {count}")
        lines.append("")
        lines.append(f"- **Errors with agent follow-up**: {len(error_responses)}/{len(doc.errors)}")
        lines.append("")

        return "\n".join(lines)

    # -------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------

    @staticmethod
    def _message_label(msg: ReasoningMessage) -> str:
        """Build a label suffix for a reasoning message."""
        tags = []
        if msg.has_todo:
            tags.append("TODO")
        if msg.has_code:
            tags.append("CODE")
        if msg.follows_error:
            tags.append("AFTER-ERROR")
        if msg.is_decision:
            tags.append("DECISION")
        return f" [{', '.join(tags)}]" if tags else ""

    @staticmethod
    def _truncate(text: str, max_len: int) -> str:
        """Truncate text to max_len characters."""
        if len(text) <= max_len:
            return text
        return text[:max_len] + "\n\n*... truncated ...*"

    @staticmethod
    def _pick_todo_snapshots(snapshots: list[TodoSnapshot]) -> list[tuple[str, TodoSnapshot]]:
        """Pick first, midpoint, and final to-do snapshots."""
        if not snapshots:
            return []
        result = [("First appearance", snapshots[0])]
        if len(snapshots) > 2:
            mid = snapshots[len(snapshots) // 2]
            result.append(("Midpoint", mid))
        if len(snapshots) > 1:
            result.append(("Final state", snapshots[-1]))
        return result


# ---------------------------------------------------------------------------
# Text format parser
# ---------------------------------------------------------------------------

_RUN_HEADER_RE = re.compile(
    r"^RUN\s+(\d+)/(\d+):\s+(.+?)\s+\((\w+)\)$"
)
_RUN_ID_RE = re.compile(r"^Run ID:\s+(.+)$")
_TRACE_HEADER_RE = re.compile(r"^TRACE:\s+(.+)$")
_RUNS_COUNT_RE = re.compile(r"^RUNS WITH MESSAGES:\s+(\d+)$")
_ROLE_RE = re.compile(r"^\[(SYSTEM|USER|ASSISTANT|TOOL)\]\s*$")


class TextTraceParser:
    """Parses plain-text trace files from ~/.traces/ directory."""

    def __init__(self, config: TraceConfig | None = None):
        self.config = config or TraceConfig()

    def parse(self, text: str) -> TraceDocument:
        """Parse a plain-text trace and return a TraceDocument."""
        lines = text.split("\n")
        doc = TraceDocument()

        # Parse header
        for line in lines[:10]:
            m = _TRACE_HEADER_RE.match(line.strip())
            if m:
                doc.trace_id = m.group(1)
            m = _RUNS_COUNT_RE.match(line.strip())
            if m:
                doc.total_runs = int(m.group(1))

        # Split into runs
        runs_raw = self._split_runs(lines)

        last_was_error = False

        for run_index, (run_header_lines, run_body_lines) in enumerate(runs_raw):
            # Parse run header
            run_name = "unknown"
            run_type = "unknown"
            run_id = ""
            for hl in run_header_lines:
                m = _RUN_HEADER_RE.match(hl.strip())
                if m:
                    run_name = m.group(3)
                    run_type = m.group(4)
                m = _RUN_ID_RE.match(hl.strip())
                if m:
                    run_id = m.group(1)

            # Parse messages within the run
            messages = self._split_messages(run_body_lines)

            summary = RunSummary(
                run_id=run_id,
                run_name=run_name,
                run_type=run_type,
                message_count=len(messages),
            )

            for msg_index, (role, content) in enumerate(messages):
                if role == "ASSISTANT":
                    # Extract text reasoning (skip tool-call JSON blobs and signatures)
                    reasoning_text = self._extract_reasoning_text(content)
                    if reasoning_text.strip():
                        has_todo = bool(_TODO_RE.search(reasoning_text))
                        has_code = bool(_CODE_BLOCK_RE.search(reasoning_text))
                        is_decision = bool(_DECISION_RE.search(reasoning_text))

                        if has_todo:
                            summary.has_todo_list = True
                        if has_code:
                            summary.has_code_blocks = True

                        doc.reasoning_messages.append(ReasoningMessage(
                            run_index=run_index,
                            msg_index=msg_index,
                            text=reasoning_text,
                            has_todo=has_todo,
                            has_code=has_code,
                            follows_error=last_was_error,
                            is_decision=is_decision,
                        ))

                        if has_todo:
                            unchecked = len(re.findall(r"\[ \]", reasoning_text))
                            checked = len(re.findall(r"\[[xX]\]", reasoning_text))
                            if unchecked + checked > 0:
                                doc.todo_snapshots.append(TodoSnapshot(
                                    run_index=run_index,
                                    total=unchecked + checked,
                                    completed=checked,
                                    text=reasoning_text,
                                ))

                        last_was_error = False

                elif role == "TOOL":
                    is_error = self._is_error_result(content)
                    if is_error:
                        error_type = self._classify_error_type(content)
                        summary.error_count += 1
                        doc.errors.append(ErrorEvent(
                            run_index=run_index,
                            message_index=msg_index,
                            error_type=error_type,
                            content_preview=content[:300],
                        ))
                        last_was_error = True
                    else:
                        last_was_error = False
                else:
                    last_was_error = False

            doc.runs.append(summary)
            doc.total_messages += summary.message_count

        # Build to-do progress from snapshots
        if doc.todo_snapshots:
            last = doc.todo_snapshots[-1]
            phases = []
            prev_completed = 0
            for snap in doc.todo_snapshots:
                if snap.completed > prev_completed:
                    phases.append(f"Run {snap.run_index}: {snap.completed}/{snap.total} done")
                prev_completed = snap.completed
            doc.todo_progress = TodoProgress(
                total_items=last.total,
                completed_items=last.completed,
                phases=phases,
            )

        return doc

    def _split_runs(self, lines: list[str]) -> list[tuple[list[str], list[str]]]:
        """Split text into (header_lines, body_lines) per run."""
        runs: list[tuple[list[str], list[str]]] = []
        separator = "-" * 80
        i = 0
        while i < len(lines):
            if lines[i].strip() == separator:
                # Collect header lines until next separator
                header_start = i + 1
                i = header_start
                while i < len(lines) and lines[i].strip() != separator:
                    i += 1
                header_lines = lines[header_start:i]
                i += 1  # skip closing separator

                # Collect body lines until next run separator or EOF
                body_start = i
                while i < len(lines):
                    if lines[i].strip() == separator:
                        # Check if next line looks like a run header
                        peek = i + 1
                        while peek < len(lines) and not lines[peek].strip():
                            peek += 1
                        if peek < len(lines) and _RUN_HEADER_RE.match(lines[peek].strip()):
                            break
                        # Also break on the separator itself if it's followed by another separator
                        if peek < len(lines) and lines[peek].strip() == separator:
                            break
                    i += 1
                body_lines = lines[body_start:i]
                runs.append((header_lines, body_lines))
            else:
                i += 1
        return runs

    def _split_messages(self, lines: list[str]) -> list[tuple[str, str]]:
        """Split run body into (role, content) messages."""
        messages: list[tuple[str, str]] = []
        current_role: str | None = None
        current_lines: list[str] = []

        for line in lines:
            m = _ROLE_RE.match(line.strip())
            if m:
                if current_role is not None:
                    messages.append((current_role, "\n".join(current_lines).strip()))
                current_role = m.group(1)
                current_lines = []
            elif current_role is not None:
                current_lines.append(line)

        if current_role is not None:
            messages.append((current_role, "\n".join(current_lines).strip()))

        return messages

    def _extract_reasoning_text(self, content: str) -> str:
        """Extract human-readable reasoning from assistant content.

        Strips tool-call JSON, signature blobs, and extracts thinking text.
        """
        parts: list[str] = []

        # Extract thinking content from inline JSON-like blocks
        thinking_re = re.compile(r"'thinking':\s*['\"](.+?)['\"]", re.DOTALL)
        for m in thinking_re.finditer(content):
            thinking = m.group(1).strip()
            if thinking:
                parts.append(thinking)

        # Extract plain text that isn't a signature blob or tool_use JSON
        # Split on tool_use markers
        segments = re.split(r"\{['\"]id['\"]\s*:\s*['\"]toolu_", content)
        if segments:
            first = segments[0]
            # Remove signature blobs
            first = re.sub(r"\{['\"]signature['\"].*?\}", "", first, flags=re.DOTALL)
            # Remove thinking JSON blocks (already extracted above)
            first = re.sub(r"\{['\"].*?['\"]thinking['\"].*?\}", "", first, flags=re.DOTALL)
            # Remove type markers
            first = re.sub(r"\{['\"]type['\"]\s*:\s*['\"]thinking['\"]\}", "", first)
            text = first.strip()
            if text and not _SIGNATURE_RE.match(text):
                parts.append(text)

        return "\n\n".join(parts) if parts else ""

    @staticmethod
    def _is_error_result(content: str) -> bool:
        """Check if a tool result contains an error."""
        exit_codes = _EXIT_CODE_RE.findall(content)
        if any(code != "0" for code in exit_codes):
            return True
        if _TRACEBACK_RE.search(content):
            return True
        return False

    @staticmethod
    def _classify_error_type(content: str) -> str:
        """Classify the type of error in a tool result."""
        if _SYNTAX_ERR_RE.search(content):
            return "syntax_error"
        if _TEST_FAIL_RE.search(content):
            return "test_failure"
        if _VALIDATION_ERR_RE.search(content):
            return "validation_error"
        if _TRACEBACK_RE.search(content):
            return "exception"
        return "stderr"


# ---------------------------------------------------------------------------
# Format detection
# ---------------------------------------------------------------------------

def detect_format(file_path: Path) -> str:
    """Detect whether a trace file is JSON or plain text."""
    with open(file_path) as f:
        first_lines = f.read(500)
    # Text format starts with ===== header
    if first_lines.strip().startswith("=" * 20):
        return "text"
    # Try JSON
    if first_lines.strip().startswith("{") or first_lines.strip().startswith("["):
        return "json"
    # Default to text for .txt files
    if file_path.suffix == ".txt":
        return "text"
    return "json"


def find_latest_trace() -> Path | None:
    """Find the most recently modified trace file in ~/.traces/."""
    traces_dir = Path.home() / ".traces"
    if not traces_dir.exists():
        return None
    trace_files = sorted(traces_dir.glob("*.txt"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not trace_files:
        # Also check for JSON files
        trace_files = sorted(traces_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    return trace_files[0] if trace_files else None


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Parse trace files (JSON or plain text) and extract agent reasoning.",
    )
    parser.add_argument(
        "file", type=str, nargs="?", default="",
        help="path to the trace file (JSON or text). Omit to use --latest.",
    )
    parser.add_argument(
        "--latest", action="store_true",
        help="use the most recently modified trace from ~/.traces/",
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="show full untruncated text for all messages",
    )
    parser.add_argument(
        "--focus", type=str, default="", metavar="AREA",
        help="focus output on a specific area (decisions, todos, errors)",
    )

    args = parser.parse_args()

    # Resolve file path
    if args.latest or not args.file:
        file_path = find_latest_trace()
        if file_path is None:
            print("Error: No trace files found in ~/.traces/", file=sys.stderr)
            sys.exit(1)
        print(f"Using latest trace: {file_path}", file=sys.stderr)
    else:
        file_path = Path(args.file)

    if not file_path.exists():
        print(f"Error: {file_path} not found.", file=sys.stderr)
        sys.exit(1)

    config = TraceConfig(
        file_path=str(file_path),
        verbose=args.verbose,
        focus=args.focus,
    )

    fmt = detect_format(file_path)

    if fmt == "text":
        with open(file_path) as f:
            text = f.read()
        text_parser = TextTraceParser(config)
        doc = text_parser.parse(text)
        # Reuse TraceParser for output formatting
        formatter = TraceParser(config)
        print(formatter.format_output(doc))
    else:
        try:
            with open(file_path) as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"Error: Failed to parse JSON: {e}", file=sys.stderr)
            sys.exit(1)
        trace_parser = TraceParser(config)
        doc = trace_parser.parse(data)
        print(trace_parser.format_output(doc))


if __name__ == "__main__":
    main()
