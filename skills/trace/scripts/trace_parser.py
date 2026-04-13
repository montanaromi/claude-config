#!/usr/bin/env python3
"""
LangSmith trace parser for Blitzy agentic coding pipeline traces.

Parses trace JSON files exported via archie-tracing.py and extracts
the agent's reasoning: decisions, task breakdowns, strategy shifts,
and problem-solving narrative.

Usage:
    python3 trace_parser.py <trace.json> [--verbose] [--focus AREA]
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
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Parse LangSmith trace JSON files and extract agent reasoning.",
    )
    parser.add_argument(
        "file", type=str,
        help="path to the trace JSON file",
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

    file_path = Path(args.file)
    if not file_path.exists():
        print(f"Error: {file_path} not found.", file=sys.stderr)
        sys.exit(1)

    config = TraceConfig(
        file_path=str(file_path),
        verbose=args.verbose,
        focus=args.focus,
    )

    # Load JSON
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
