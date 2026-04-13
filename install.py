#!/usr/bin/env python3
"""
install.py — symlinks Claude Code skills and installs Python dependencies.

Supports Linux, macOS, and Windows. Safe to re-run.

Usage:
  python install.py          # or ./install.py on Unix
"""

import os
import platform
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

SKILLS = [
    "onboard", "readme", "commit", "blitzy-pr", "test",
    "aap", "dev-doc", "z", "tech-spec", "chuck", "logger", "use-case",
]


def claude_skills_dir() -> Path:
    return Path.home() / ".claude" / "skills"


def link_skills(skills_dir: Path) -> list[str]:
    skills_dir.mkdir(parents=True, exist_ok=True)
    linked = []

    for name in SKILLS:
        src = HERE / "skills" / name
        dst = skills_dir / name

        if not src.is_dir():
            print(f"  skip    {name} (not found in skills/)")
            continue

        if dst.is_symlink():
            dst.unlink()
        elif dst.is_dir():
            print(f"  replace {name} (was a directory)")
            import shutil
            shutil.rmtree(dst)

        os.symlink(src, dst)
        linked.append(name)
        print(f"  link    {dst} -> {src}")

    return linked


def install_deps() -> None:
    req = HERE / "requirements.txt"
    if not req.exists():
        return

    print("\nInstalling Python dependencies...")
    pip = "pip3" if platform.system() != "Windows" else "pip"

    # Try standard install first; fall back to --break-system-packages on
    # Debian/Ubuntu systems that block global pip installs.
    for extra in ([], ["--break-system-packages"]):
        result = subprocess.run(
            [pip, "install", "-r", str(req), "--quiet", *extra],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            break
        if "externally-managed-environment" not in result.stderr:
            print(f"  warning: pip failed — install manually:")
            print(f"    pip install -r {req}")
            return

    if result.returncode != 0:
        print(f"  warning: pip failed — install manually:")
        print(f"    pip install -r {req}")
        return

    # Verify tree-sitter
    check = subprocess.run(
        [sys.executable, "-c", "import tree_sitter"],
        capture_output=True,
    )
    if check.returncode == 0:
        print("  tree-sitter: OK")
    else:
        print("  warning: tree-sitter not importable after install")


def main() -> None:
    claude_dir = Path.home() / ".claude"
    if not claude_dir.exists():
        sys.exit(
            f"Error: {claude_dir} does not exist.\n"
            "Install Claude Code first: https://docs.anthropic.com/en/docs/claude-code"
        )

    skills_dir = claude_skills_dir()
    print(f"Skills dir: {skills_dir}")
    print("Linking skills...")
    linked = link_skills(skills_dir)

    install_deps()

    print(f"\n=== claude-config installed ({len(linked)} skills) ===")
    for name in linked:
        print(f"  /{name}")
    print("\nSkills are ready. Start a new Claude Code session to use them.")


if __name__ == "__main__":
    main()
