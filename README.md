# AeroDoc

**AeroDoc** is an agent skill that keeps your markdown documentation in perfect sync with your code, prompts, and agent configurations — automatically, on every commit.

No more stale docs. No more manual copy-paste. AeroDoc reads your git diff, understands what changed, and makes the smallest possible edit to your documentation to reflect it.

---

## How it works

```
git commit  →  AeroDoc detects changes  →  Agent reads diff  →  Docs updated in place
```

1. **`scripts/aero_doc.py`** — a Python helper that queries git and returns a structured JSON payload: which files changed, the unified diff, and the current docs content.
2. **`skill.md`** — instructions for the Antigravity agent that turns the diff into precise, well-written documentation updates.

The agent follows strict writing standards: present tense, direct voice, surgical edits only, and a length discipline rule that removes any sentence a reader would not miss.

---

## Features

- **Surgical edits** — only the section that covers the changed file is touched; everything else is left alone.
- **Bootstrap mode** — on first run, writes a complete initial document from scratch.
- **Structured change metadata** — knows whether each file was added, modified, deleted, or renamed, and applies the right edit strategy for each.
- **Diff truncation** — caps the diff at a configurable byte limit to avoid overwhelming the agent's context window.
- **Clean error handling** — surfaces git errors as structured JSON instead of silently treating them as "no changes".

---

## Requirements

- Python 3.8 or later
- Git (the project must be a git repository)
- [Antigravity IDE](https://antigravity.dev) with skill support
- Node.js 16+ *(only if installing via npm)*

---

## Quick start

### 1. Install

> **Installing from source** (before publishing):
> ```bash
> git clone https://github.com/ItzKyudo/aero-doc-skill.git
> pip install ./aero-doc-skill      # Python
> npm install -g ./aero-doc-skill   # Node.js
> ```

### 2. Add the skill to your project

Run this inside your project's root directory:

```bash
aero-doc install
```

That's it. The command copies the skill files into `.agents/skills/aero_doc/` — no manual file management needed.

```
your-project/
└── .agents/
    └── skills/
        └── aero_doc/          ← created by aero-doc install
            ├── skill.md
            └── scripts/
                └── aero_doc.py
```

### 3. Verify the helper runs

```bash
aero-doc run
```

On a repo with no tracked changes you'll see:

```json
{"status": "no_changes", "message": "No prompt or code changes detected in the tracked directories.", "doc_path": "docs/AGENT_MANUAL.md"}
```

On a repo with changes you'll see:

```json
{
  "status": "changes_detected",
  "doc_path": "docs/AGENT_MANUAL.md",
  "changed_files": [{"path": "src/loader.py", "status": "M"}],
  "truncated": false,
  "diff": "...",
  "current_docs": "..."
}
```

### 4. Commit and let Antigravity take over

Commit the new `.agents/` files. From here, the Antigravity agent fires automatically
on every relevant commit and writes the updated docs to `docs/AGENT_MANUAL.md`.

### 5. Uninstall the skill

To remove the skill from your project, simply delete the skill directory:

```bash
rm -rf .agents/skills/aero_doc/
```
If you had platform files generated (e.g., `CLAUDE.md`, `AGENTS.md`, `.cursor/rules/aero-doc.mdc`), you should also remove the injected `<!-- aero-doc -->` configuration blocks from them.

To remove the `aero-doc` CLI package itself from your system:

```bash
pip uninstall aero-doc      # If installed via Python
npm uninstall -g aero-doc   # If installed via Node.js
```

---

## Configuration

Pass flags to `aero_doc.py` to target a different doc file or watch different directories:

| Flag | Default | Description |
|---|---|---|
| `--doc` | `docs/AGENT_MANUAL.md` | Path to the markdown file to update |
| `--dirs` | `src/ prompts/ .agents/skills/` | One or more directories to watch for changes |
| `--max-diff-bytes` | `40000` | Truncate the diff at this many bytes (`0` = unlimited) |

**Example — custom paths:**

```bash
python scripts/aero_doc.py --doc wiki/AGENT_GUIDE.md --dirs agents/ configs/
```

---

## Output format

AeroDoc writes to the doc file in place. After each run, the agent reports its changes in a structured format:

> - **Added:** `## aero_doc Skill` — documents the new AeroDoc skill configuration.
> - **Updated:** `### Configuration / --dirs` — reflects the new default value.
> - **Removed:** `## Legacy Prompt Loader` — section deleted because `src/loader.py` was removed.

---

## License

MIT — see [LICENSE](LICENSE).
