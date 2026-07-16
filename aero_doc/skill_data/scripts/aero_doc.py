#!/usr/bin/env python3
"""
areo_doc.py — AeroDoc helper script.

Gathers git diff information and current documentation so the AeroDoc
agent can decide whether documentation needs to be updated.

Outputs a single JSON object to stdout:
  - status: "no_changes" | "changes_detected" | "git_error"
  - message: human-readable summary
  - changed_files: list of {path, status} dicts  (only on changes_detected)
  - diff: raw unified diff string               (only on changes_detected)
  - truncated: true if diff was cut short       (only on changes_detected)
  - current_docs: content of the docs file      (only on changes_detected)
  - doc_path: resolved path of the docs file    (always)
"""

import argparse
import json
import os
import subprocess
import sys


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="aero_doc.py",
        description="AeroDoc helper — surfaces git changes for documentation updates.",
    )
    parser.add_argument(
        "--doc",
        default="docs/AGENT_MANUAL.md",
        metavar="PATH",
        help="Path to the markdown doc file to read/update. (default: docs/AGENT_MANUAL.md)",
    )
    parser.add_argument(
        "--dirs",
        nargs="+",
        default=["src/", "prompts/", ".agents/skills/"],
        metavar="DIR",
        help="Directories to watch for changes. (default: src/ prompts/ .agents/skills/)",
    )
    parser.add_argument(
        "--max-diff-bytes",
        type=int,
        default=40_000,
        metavar="N",
        help="Truncate diff output to at most N bytes to avoid overwhelming the agent. "
             "0 = unlimited. (default: 40000)",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------

def _git(*args: str) -> tuple[str, bool]:
    """Run a git command. Returns (stdout, success)."""
    try:
        out = subprocess.check_output(
            ["git", *args],
            text=True,
            stderr=subprocess.DEVNULL,
        )
        return out, True
    except subprocess.CalledProcessError:
        return "", False
    except FileNotFoundError:
        return "", False


def _commit_count() -> int:
    """Return the number of commits reachable from HEAD (0 on error)."""
    out, ok = _git("rev-list", "--count", "HEAD")
    if ok and out.strip().isdigit():
        return int(out.strip())
    return 0


def get_git_diff(dirs: list[str]) -> tuple[str, str]:
    """
    Collect the most relevant diff for the watched directories.

    Strategy:
      1. Staged changes  (git diff --cached HEAD -- <dirs>)
      2. Unstaged changes (git diff HEAD -- <dirs>)
      3. If both empty, last commit's changes (git diff HEAD~1 HEAD -- <dirs>)
         (skipped on repos with only 1 commit)

    Returns (diff_text, error_message).
    error_message is empty string on success.
    """
    # Staged changes
    staged, ok = _git("diff", "--cached", "HEAD", "--", *dirs)
    if not ok:
        # git itself failed (e.g., not a git repo)
        _, second_ok = _git("rev-parse", "--is-inside-work-tree")
        if not second_ok:
            return "", "Not inside a git repository."
        return "", "git diff failed for an unknown reason."

    # Unstaged changes
    unstaged, _ = _git("diff", "HEAD", "--", *dirs)

    combined = "\n".join(filter(None, [staged.strip(), unstaged.strip()]))

    if combined.strip():
        return combined, ""

    # Fallback: diff of the last commit (if there's at least 2 commits)
    if _commit_count() >= 2:
        last_commit, _ = _git("diff", "HEAD~1", "HEAD", "--", *dirs)
        return last_commit, ""

    return "", ""


def get_changed_files(dirs: list[str]) -> list[dict]:
    """
    Return a structured list of files that changed, with their git status letter.

    Each entry: {"path": str, "status": str}  where status is one of:
      A=added, M=modified, D=deleted, R=renamed, C=copied, U=unmerged
    """
    entries: list[dict] = []

    for flag in ("--cached", ""):
        args = ["diff", "--name-status"]
        if flag:
            args.append(flag)
        args += ["HEAD", "--"]
        args += dirs

        out, ok = _git(*args)
        if not ok or not out.strip():
            continue

        for line in out.splitlines():
            parts = line.split("\t", maxsplit=2)
            if len(parts) < 2:
                continue
            status_code = parts[0][0]  # first char: A, M, D, R, C …
            path = parts[-1]           # last part is the destination path
            # Deduplicate: same path might appear in staged + unstaged
            if not any(e["path"] == path for e in entries):
                entries.append({"path": path, "status": status_code})

    # If nothing staged/unstaged, check last commit
    if not entries and _commit_count() >= 2:
        out, ok = _git("diff", "--name-status", "HEAD~1", "HEAD", "--", *dirs)
        if ok and out.strip():
            for line in out.splitlines():
                parts = line.split("\t", maxsplit=2)
                if len(parts) >= 2:
                    entries.append({"path": parts[-1], "status": parts[0][0]})

    return entries


# ---------------------------------------------------------------------------
# Docs helpers
# ---------------------------------------------------------------------------

DOCS_TEMPLATE = """\
# Agent System Manual

Welcome to your AI Agent documentation. This file is automatically maintained by AeroDoc.

## Agent System Prompts
*No system prompts documented yet.*

## Configured Behaviors
*No custom behaviors tracked yet.*
"""


def read_existing_docs(path: str) -> str:
    """Read the current docs file, or return the starter template."""
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except OSError as exc:
            return f"# Agent System Manual\n\n_Error reading file: {exc}_\n"
    return DOCS_TEMPLATE


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    args = parse_args()

    diff, error = get_git_diff(args.dirs)

    if error:
        result = {
            "status": "git_error",
            "message": error,
            "doc_path": args.doc,
        }
        print(json.dumps(result, ensure_ascii=False))
        sys.exit(1)

    if not diff.strip():
        result = {
            "status": "no_changes",
            "message": "No prompt or code changes detected in the tracked directories.",
            "doc_path": args.doc,
        }
        print(json.dumps(result, ensure_ascii=False))
        sys.exit(0)

    # Apply diff size limit
    truncated = False
    if args.max_diff_bytes and len(diff.encode()) > args.max_diff_bytes:
        diff = diff.encode()[:args.max_diff_bytes].decode(errors="replace")
        diff += "\n\n[... diff truncated — use --max-diff-bytes to increase the limit ...]"
        truncated = True

    changed_files = get_changed_files(args.dirs)
    current_docs = read_existing_docs(args.doc)

    result = {
        "status": "changes_detected",
        "doc_path": args.doc,
        "changed_files": changed_files,
        "truncated": truncated,
        "diff": diff,
        "current_docs": current_docs,
    }

    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()