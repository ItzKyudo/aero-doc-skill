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

import ast
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
# Tool Extraction helpers
# ---------------------------------------------------------------------------

def extract_tools_from_python(filepath: str) -> list[dict]:
    """Scan a Python file for @tool decorators and extract their schemas."""
    tools = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=filepath)
    except Exception:
        return tools

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            is_tool = any(
                (isinstance(dec, ast.Name) and dec.id == "tool") or
                (isinstance(dec, ast.Call) and getattr(dec.func, "id", "") == "tool")
                for dec in node.decorator_list
            )
            if is_tool:
                args = [arg.arg for arg in node.args.args if arg.arg != "self"]
                docstring = ast.get_docstring(node) or ""
                description = docstring.strip().split("\n")[0] if docstring else "No description"
                tools.append({
                    "name": node.name,
                    "inputs": args,
                    "description": description,
                    "source": filepath
                })
    return tools


def extract_tools_from_json(filepath: str) -> list[dict]:
    """Scan a JSON file heuristically for tool schemas."""
    tools = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return tools

    # Heuristically check if this json looks like a tool schema
    if isinstance(data, dict) and "name" in data and "description" in data:
        inputs = []
        if "parameters" in data and "properties" in data["parameters"]:
            inputs = list(data["parameters"]["properties"].keys())
        tools.append({
            "name": data.get("name"),
            "inputs": inputs,
            "description": data.get("description", ""),
            "source": filepath
        })
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and "name" in item and "description" in item:
                inputs = []
                if "parameters" in item and "properties" in item["parameters"]:
                    inputs = list(item["parameters"]["properties"].keys())
                tools.append({
                    "name": item.get("name"),
                    "inputs": inputs,
                    "description": item.get("description", ""),
                    "source": filepath
                })
    return tools


def gather_tools(dirs: list[str]) -> list[dict]:
    """Gather all tools from python and json files in the tracked directories."""
    all_tools = []
    for d in dirs:
        if not os.path.isdir(d):
            continue
        for root, _, files in os.walk(d):
            for file in files:
                filepath = os.path.join(root, file)
                if file.endswith(".py"):
                    all_tools.extend(extract_tools_from_python(filepath))
                elif file.endswith(".json"):
                    all_tools.extend(extract_tools_from_json(filepath))
    return all_tools


# ---------------------------------------------------------------------------
# Docs helpers
# ---------------------------------------------------------------------------

def get_template(name: str) -> str:
    """Load a reference template from the resources directory."""
    template_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "resources", name)
    try:
        with open(template_path, "r", encoding="utf-8") as f:
            return f.read()
    except OSError:
        return f"# Template not found: {name}\n"


def read_existing_docs(path: str) -> str:
    """Read the current docs file, or return the starter template."""
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except OSError as exc:
            return f"# Agent System Manual\n\n_Error reading file: {exc}_\n"
    return get_template("AGENT_MANUAL_TEMPLATE.md")


def read_readme() -> str:
    """Read the existing README.md or return a template."""
    path = "README.md"
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except OSError:
            pass
    return get_template("README_TEMPLATE.md")


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
    readme_content = read_readme()
    tools_extracted = gather_tools(args.dirs)
    
    agent_manual_template = get_template("AGENT_MANUAL_TEMPLATE.md")
    readme_template = get_template("README_TEMPLATE.md")

    result = {
        "status": "changes_detected",
        "doc_path": args.doc,
        "changed_files": changed_files,
        "truncated": truncated,
        "diff": diff,
        "current_docs": current_docs,
        "readme_content": readme_content,
        "tools_extracted": tools_extracted,
        "agent_manual_template": agent_manual_template,
        "readme_template": readme_template,
    }

    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()