"""
aero-doc CLI

Commands:
  aero-doc install   — copy the aero_doc skill into the current project
  aero-doc run       — run the helper script directly (wrapper around aero_doc.py)
  aero-doc version   — print the installed version
"""

from __future__ import annotations

import argparse
import importlib.resources
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SKILL_DEST = Path(".agents") / "skills" / "aero_doc"
_GREEN = "\033[32m"
_YELLOW = "\033[33m"
_RED = "\033[31m"
_RESET = "\033[0m"
_BOLD = "\033[1m"

# Platform config snippets injected by `aero-doc install`
_AERO_DOC_MARKER = "<!-- aero-doc -->"

_CLAUDE_MD_SNIPPET = """
## AeroDoc — Automated Documentation

After every change to `src/`, `prompts/`, or `.agents/skills/`, run:

```bash
python .agents/skills/aero_doc/scripts/aero_doc.py
```

Then follow the instructions in `.agents/skills/aero_doc/skill.md` to update `docs/AGENT_MANUAL.md`.
"""

_AGENTS_MD_SNIPPET = """
## AeroDoc — Documentation Sync

This project uses AeroDoc to keep `docs/AGENT_MANUAL.md` in sync with the codebase.

Whenever you modify files under `src/`, `prompts/`, or `.agents/skills/`, run:

```bash
python .agents/skills/aero_doc/scripts/aero_doc.py
```

Follow the output instructions to update the documentation. Full protocol: `.agents/skills/aero_doc/skill.md`.
"""

_CURSOR_MDC = """---
description: Run AeroDoc to update docs/AGENT_MANUAL.md whenever src/, prompts/, or .agents/skills/ files change.
globs:
  - "src/**/*"
  - "prompts/**/*"
  - ".agents/skills/**/*"
alwaysApply: false
---

# AeroDoc — Documentation Sync

When files matching the globs above are saved or modified, run:

```bash
python .agents/skills/aero_doc/scripts/aero_doc.py
```

Then follow the instructions in `.agents/skills/aero_doc/skill.md` to update `docs/AGENT_MANUAL.md`.
"""

_COPILOT_SNIPPET = """
## AeroDoc — Documentation Sync

This project uses AeroDoc. When `src/`, `prompts/`, or `.agents/skills/` files change, run:

```bash
python .agents/skills/aero_doc/scripts/aero_doc.py
```

Follow `.agents/skills/aero_doc/skill.md` to update `docs/AGENT_MANUAL.md`.
"""


def _ok(msg: str) -> None:
    print(f"  {_GREEN}ok{_RESET}  {msg}")


def _warn(msg: str) -> None:
    print(f"  {_YELLOW}!{_RESET}   {msg}")


def _err(msg: str) -> None:
    print(f"  {_RED}err{_RESET} {msg}", file=sys.stderr)


def _section(title: str) -> None:
    print(f"\n{_BOLD}{title}{_RESET}")


def _skill_data_dir() -> Path:
    """Return the path to the bundled skill_data directory."""
    # Works both as an installed package and from source.
    pkg_root = Path(__file__).parent
    data_dir = pkg_root / "skill_data"
    if data_dir.exists():
        return data_dir
    raise FileNotFoundError(
        f"Bundled skill data not found at {data_dir}. "
        "Try reinstalling: pip install --force-reinstall aero-doc"
    )


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_install(args: argparse.Namespace) -> int:
    """Copy the aero_doc skill into the current project and generate platform config files."""
    target = Path(args.target) if args.target else SKILL_DEST
    src = _skill_data_dir()

    _section(f"Installing AeroDoc skill -> {target}")

    if target.exists() and not args.force:
        _warn(f"{target} already exists. Use --force to overwrite.")
        return 1

    try:
        if target.exists() and args.force:
            shutil.rmtree(target)
        shutil.copytree(src, target)
    except Exception as exc:
        _err(f"Copy failed: {exc}")
        return 1

    _ok(f"Skill files copied to {target}/")
    _ok("skill.md            - agent instructions (universal)")
    _ok("scripts/aero_doc.py - helper script")

    if not args.no_platform_files:
        _section("Generating platform config files")
        _write_platform_files(args.force)

    print(
        f"\n{_BOLD}Next step:{_RESET} commit these files and let your agent do the rest.\n"
        f"  Run manually:  python {target / 'scripts' / 'aero_doc.py'} --help\n"
        f"  Works with:    Claude Code, Cursor, Codex, Copilot, Antigravity\n"
    )
    return 0


def _write_platform_files(force: bool) -> None:
    """Write platform-specific agent config files."""

    def _append_or_create(path: Path, snippet: str, label: str) -> None:
        """Append snippet to file if marker absent, or create the file."""
        if path.exists():
            existing = path.read_text(encoding="utf-8")
            if _AERO_DOC_MARKER in existing:
                _warn(f"{path} — already configured, skipping.")
                return
            if not force:
                with open(path, "a", encoding="utf-8") as f:
                    f.write(f"\n{_AERO_DOC_MARKER}\n{snippet}")
                _ok(f"{path} — appended {label} block")
            else:
                with open(path, "a", encoding="utf-8") as f:
                    f.write(f"\n{_AERO_DOC_MARKER}\n{snippet}")
                _ok(f"{path} — appended {label} block (force)")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"{_AERO_DOC_MARKER}\n{snippet}", encoding="utf-8")
            _ok(f"{path} — created ({label})")

    def _write_new(path: Path, content: str, label: str) -> None:
        """Write file only if it doesn't exist (or force)."""
        if path.exists() and not force:
            _warn(f"{path} — already exists, skipping. Use --force to overwrite.")
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        _ok(f"{path} — created ({label})")

    # Claude Code
    _append_or_create(Path("CLAUDE.md"), _CLAUDE_MD_SNIPPET, "Claude Code")

    # OpenAI Codex / universal AGENTS.md
    _append_or_create(Path("AGENTS.md"), _AGENTS_MD_SNIPPET, "Codex / AGENTS.md")

    # Cursor
    _write_new(Path(".cursor") / "rules" / "aero-doc.mdc", _CURSOR_MDC, "Cursor")

    # GitHub Copilot
    _append_or_create(
        Path(".github") / "copilot-instructions.md",
        _COPILOT_SNIPPET,
        "GitHub Copilot",
    )


def cmd_run(args: argparse.Namespace) -> int:
    """Run the aero_doc helper script directly."""
    script = SKILL_DEST / "scripts" / "aero_doc.py"

    if not script.exists():
        _err(
            f"Helper script not found at {script}.\n"
            "  Run 'aero-doc install' first to set up the skill."
        )
        return 1

    extra = args.script_args or []
    result = subprocess.run([sys.executable, str(script), *extra])
    return result.returncode


def cmd_version(_args: argparse.Namespace) -> int:
    """Print the installed version."""
    from aero_doc import __version__
    print(f"aero-doc {__version__}")
    return 0


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="aero-doc",
        description="AeroDoc — Antigravity skill that keeps docs in sync with code.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  aero-doc install                   # install skill into current project\n"
            "  aero-doc install --force            # overwrite existing skill files\n"
            "  aero-doc install --target my/path  # install to a custom location\n"
            "  aero-doc run -- --doc wiki/GUIDE.md  # run helper with custom flags\n"
            "  aero-doc version                   # print version\n"
        ),
    )
    sub = parser.add_subparsers(dest="command", metavar="<command>")

    # install
    p_install = sub.add_parser("install", help="Copy the skill into the current project.")
    p_install.add_argument(
        "--target",
        metavar="PATH",
        default=None,
        help=f"Destination directory (default: {SKILL_DEST})",
    )
    p_install.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing skill files.",
    )
    p_install.add_argument(
        "--no-platform-files",
        action="store_true",
        dest="no_platform_files",
        help="Skip generating CLAUDE.md, AGENTS.md, .cursor/rules/, and .github/copilot-instructions.md.",
    )
    p_install.set_defaults(func=cmd_install)

    # run
    p_run = sub.add_parser("run", help="Run the aero_doc helper script.")
    p_run.add_argument(
        "script_args",
        nargs=argparse.REMAINDER,
        help="Arguments forwarded to aero_doc.py (e.g. -- --doc wiki/GUIDE.md).",
    )
    p_run.set_defaults(func=cmd_run)

    # version
    p_ver = sub.add_parser("version", help="Print the installed version.")
    p_ver.set_defaults(func=cmd_version)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)

    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
