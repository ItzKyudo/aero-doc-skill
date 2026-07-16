---
name: aero_doc
description: Automatically updates markdown documentation when code, prompts, or agent behaviors change.
version: 2.1.0
---

# AeroDoc — Automated Documentation Updater

**Trigger:** Run this skill whenever files in `src/`, `prompts/`, or `.agents/skills/` change. This can be on commit, on save, or when requested.

Act as a technical writer. Keep the project's documentation in sync with its code and prompt changes. Write clearly and concisely.

---

## Compatibility

This skill works with AI coding agents that can run a shell command and write files:

| Agent | How to invoke |
|---|---|
| **Claude Code** | Runs via `CLAUDE.md` hook, or ask: *"Update the docs"* |
| **Cursor** | Triggered by `.cursor/rules/aero-doc.mdc` on file saves |
| **OpenAI Codex** | Reads `AGENTS.md` — run manually or on commit |
| **GitHub Copilot** | Reads `.github/copilot-instructions.md` — ask: *"Run aero-doc"* |
| **Antigravity** | Runs automatically via `.agents/skills/aero_doc/skill.md` |
| **Other agents** | Ask: *"Run `python .agents/skills/aero_doc/scripts/aero_doc.py` and update the docs"* |

---

## Execution Protocol

### Step 1 — Run the helper script

Run the helper script to gather changes:

```bash
python .agents/skills/aero_doc/scripts/aero_doc.py [--doc <path>] [--dirs <dir1> <dir2> ...] [--max-diff-bytes <N>]
```

The script outputs a JSON object. Read the `status` field.

> **Note for Antigravity users:** The path is relative — use `scripts/aero_doc.py` when running from the skill context.

---

### Step 2 — Check status

| `status` | Meaning | Action |
|---|---|---|
| `"no_changes"` | No tracked files changed | Stop and tell the user: *"Documentation is already up to date."* |
| `"git_error"` | Git isn't available or it's not a repo | Stop and show the user the `message` field. |
| `"changes_detected"` | Files changed | Move to Step 3. |

---

### Step 3 — Understand the changes

Read the JSON payload:

| Field | Description |
|---|---|
| `changed_files` | List of `{path, status}` objects. Read this first to understand what changed. |
| `diff` | Raw unified diff. Read this to see the actual code changes. |
| `truncated` | `true` if the diff was cut short. Keep this in mind when writing. |
| `current_docs` | The existing docs, or a blank template if it's the first run. |
| `readme_content` | The existing README.md content. |
| `agent_manual_template` | Template showing how the Agent Manual should be organized. |
| `readme_template` | Template showing how the README.md should be organized. |
| `doc_path` | The file you need to write the final docs to. |
| `tools_extracted` | List of tool schemas extracted from code. Use this to document agent tools. |

File status codes:

| Code | Meaning |
|---|---|
| `A` | Added |
| `M` | Modified |
| `D` | Deleted |
| `R` | Renamed |

---

### Step 4 — Analyze and draft

#### 4a. Find documentation-worthy changes

Check the `diff` and `changed_files` for things the reader actually needs to know:

- **System prompts:** changes to tone, constraints, or format.
- **Prompt variables:** new, renamed, or removed `{{variable}}`s.
- **Skill configurations:** new or removed skills in `.agents/skills/`.
- **Public API:** new functions, renamed endpoints, deleted modules.
- **Behavior:** changes to defaults, env vars, or configs.

Ignore internal refactors, minor comment edits, test files, and formatting unless they change behavior.

#### 4b. Extract tools and schemas

Use `tools_extracted` to create or update an API table showing what each tool does:

| Active Agent Tool | Accepted Inputs | Expected Output / Description |
|---|---|---|
| `fetch_user_data` | `user_id: str` | JSON payload of user metrics |

#### 4c. Edit strategy

**Surgical edits** (`M` and `R`):
- Find the exact section in `current_docs` that covers the change.
- Edit only that section. Don't touch the rest.
- Don't rewrite accurate text just because a nearby line changed.

**Section removal** (`D`):
- Delete the section describing the removed file or feature.
- Update any other sections that reference it.

**Section addition** (`A`):
- Add a new heading in a logical spot.
- Don't just dump it at the bottom. Put it where readers expect it.

**Renames** (`R`):
- Update the heading and any references to the old name.

**Visual docs (Mermaid.js):**
- If the diff changes how code components interact, update or create a Mermaid.js flowchart in the "System Architecture" section.

**Project README.md:**
- If changes affect core features, the tech stack, or high-level architecture, update `README.md` (using `readme_content` as a base).

**Bootstrap mode** (first run, blank `current_docs`):
- Write a complete manual covering all `changed_files`. Don't use surgical edits; write the whole document.

**Truncation** (`truncated: true`):
- If the diff was cut short, add this warning above your changes:
  ```
  > Warning: The diff was truncated. This section may be incomplete — review the full diff manually.
  ```

---

### Step 5 — Writing standards

Write like a human engineer. Be clear, direct, and concise. Avoid AI-sounding fluff.

#### Anti-slop rules

- **No buzzwords:** Do not use words like *delve, testament, comprehensive, navigating, robust, seamless, crucial, elevate, utilize, landscape, paradigm, synergy*.
- **No dramatic intros:** Avoid *"In the ever-evolving world of..."* or *"Welcome to the guide for..."*.
- **No filler conclusions:** Skip *"In conclusion..."*, *"Ultimately..."*, or *"By following these steps..."*.
- **Be direct:** State what the code does and how to use it. Skip the marketing fluff.

#### Organization

- **Use the templates:** Structure your updates to match `agent_manual_template` and `readme_template`. Reorganize existing content if it doesn't fit.

#### Voice and tone

- Use **second person** for instructions: *"Run the script with `--doc`."*
- Use **third person** for references: *"The `--dirs` flag accepts multiple paths."*
- Use **active voice** and **present tense**: *"The script outputs..."* (not *"will output"*).
- Start sections with the most important fact.
- Remove filler like *"It is worth noting that..."* or *"Simply..."*

#### Formatting

- Use **ATX headings** (`##`, `###`).
- Leave **one blank line** below headings.
- Use **bold** (`**term**`) for the first mention of a key term, then plain text.
- Use `inline code` for paths, flags, variables, and code.
- Use **fenced code blocks** for examples.
- Use **tables** for comparing options.
- Use **numbered lists** only for steps. Use bullets for everything else.

#### Examples

| Do | Don't |
|---|---|
| *"Pass `--dirs` to limit the scan."* | *"The `--dirs` flag can optionally be utilized to seamlessly limit..."* |
| *"Returns `git_error` when git is not available."* | *"Crucially, it will robustly return a `git_error` status when..."* |

#### Keep it short

- Make it as short as possible while staying complete.
- Aim for one sentence per change. Add a paragraph only if needed.
- Delete any sentence that doesn't add value.

---

### Step 6 — Save and report

**Antigravity users:**
If you're running in Antigravity, create an `implementation_plan.md` artifact first. List the sections you plan to change and wait for user approval before writing to files.

1. Once approved (or if not using Antigravity), update these files:
   - **`doc_path`** (e.g., `AGENT_MANUAL.md`): The main documentation file.
   - **`CHANGELOG_AGENTS.md`**: Add a clean, readable line for any prompt or behavior changes, like:
     `2026-07-16: Updated system_prompt to improve safety filtering and added support for the user_zipcode variable.`
   - **`README.md`**: Keep the core features and tech stack accurate.
2. Tell the user what changed, bullet by bullet:
   - Use **Added:** for new sections.
   - Use **Updated:** for changed sections.
   - Use **Removed:** for deleted sections.

Example:
> - **Added:** `## aero_doc Skill` — documents the new AeroDoc skill.
> - **Updated:** `### Configuration / --dirs` — reflects the new default value.
> - **Removed:** `## Legacy Prompt Loader` — section deleted because `src/loader.py` was removed.

---

## Configuration

Use these flags for custom paths:

| Flag | Default | Description |
|---|---|---|
| `--doc` | `docs/AGENT_MANUAL.md` | Path to the markdown file to update |
| `--dirs` | `src/ prompts/ .agents/skills/` | Directories to watch |
| `--max-diff-bytes` | `40000` | Truncate the diff at this many bytes (0 = unlimited) |

**Example:**
```bash
python .agents/skills/aero_doc/scripts/aero_doc.py --doc wiki/AGENT_GUIDE.md --dirs agents/ configs/
```
