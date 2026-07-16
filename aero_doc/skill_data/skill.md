---
name: aero_doc
description: Automatically updates markdown documentation when code, prompts, or agent behaviors change.
version: 2.1.0
---

# AeroDoc — Automated Documentation Updater

**Trigger:** Run this skill whenever files in `src/`, `prompts/`, or `.agents/skills/` change — on commit, on save, or when explicitly asked to update the docs.

You are acting as a senior technical writer. Your sole responsibility is keeping the project's documentation in perfect, verifiable sync with its code and prompt changes. Write with authority and precision. Every sentence you add must earn its place.

---

## Compatibility

This skill works with any AI coding agent that can run a shell command and write to a file:

| Agent | How to invoke |
|---|---|
| **Claude Code** | Run automatically via `CLAUDE.md` hook, or ask: _"Update the docs"_ |
| **Cursor** | Triggered by `.cursor/rules/aero-doc.mdc` on matching file saves |
| **OpenAI Codex** | Reads `AGENTS.md` — invoke manually or on commit |
| **GitHub Copilot** | Reads `.github/copilot-instructions.md` — ask: _"Run aero-doc"_ |
| **Antigravity** | Triggered automatically via `.agents/skills/aero_doc/skill.md` |
| **Any other agent** | Ask: _"Run ``python .agents/skills/aero_doc/scripts/aero_doc.py`` and update the docs"_ |

---

## Execution Protocol

### Step 1 — Run the helper script

Execute the helper script to gather change data:

```bash
python .agents/skills/aero_doc/scripts/aero_doc.py [--doc <path>] [--dirs <dir1> <dir2> ...] [--max-diff-bytes <N>]
```

The script writes a single JSON object to stdout. Capture it and read the `status` field.

> **Note for Antigravity users:** The path is relative — use `scripts/aero_doc.py` when invoking from within the skill context.

---

### Step 2 — Branch on status

| `status` | Meaning | What to do |
|---|---|---|
| `"no_changes"` | Nothing in the tracked directories changed | Stop. Tell the user: _"Documentation is already up to date."_ |
| `"git_error"` | git is unavailable or this is not a git repository | Stop. Surface the `message` field verbatim to the user. |
| `"changes_detected"` | Relevant files were modified | Continue to Step 3. |

---

### Step 3 — Understand the changes

Unpack the JSON payload:

| Field | What it contains |
|---|---|
| `changed_files` | Structured list of `{path, status}` objects. **Read this first** to form a mental model of what changed and why. |
| `diff` | Raw unified diff. Use this to understand the _content_ of each change — new logic, renamed variables, removed behaviour. |
| `truncated` | `true` if the diff was cut short. Factor this into your confidence level. |
| `current_docs` | The existing documentation text, or a blank template on first run. |
| `readme_content` | The existing content of the project's README.md file. |
| `agent_manual_template` | The reference template outlining how the Agent Manual should be organized. |
| `readme_template` | The reference template outlining how the README.md should be organized. |
| `doc_path` | The file path you must write the final result to. |
| `tools_extracted` | Structured list of tool schemas extracted from Python decorators and JSON. Use this to document available agent tools. |

Status codes in `changed_files`:

| Code | Meaning |
|---|---|
| `A` | File was added |
| `M` | File was modified |
| `D` | File was deleted |
| `R` | File was renamed |

---

### Step 4 — Analyze, then draft

#### 4a. Identify what is documentation-worthy

Scan the `diff` and `changed_files` for changes that a reader would need to know about:

- **System prompts** — any modification to tone, persona, constraints, or output format.
- **Prompt variables** — new, renamed, or removed `{{variable}}` placeholders.
- **Skill configurations** — new skills added or removed under `.agents/skills/`.
- **Public API surface** — new functions, renamed endpoints, deleted modules.
- **Behavioral changes** — changes to defaults, environment variables, or configuration schemas.

Ignore internal refactors, comment edits, test files, and formatting-only changes
unless they expose a meaningful behavioral difference.

#### 4b. Extract Tools and Schemas

Using the `tools_extracted` field from the script output, generate or update an API table detailing what each tool does. Format the table as follows:

| Active Agent Tool | Accepted Inputs | Expected Output / Description |
|---|---|---|
| `fetch_user_data` | `user_id: str` | JSON payload of user metrics |

#### 4c. Apply the right edit strategy

**Surgical edits** (default for `M` and `R` changes):
- Locate the exact section in `current_docs` that covers the changed file or feature.
- Edit or extend only that section. Leave all other sections untouched.
- Never rewrite prose that is still accurate just because a nearby line changed.

**Section removal** (for `D` — deleted files):
- Remove the documentation section that described the deleted file or feature.
- If other sections refer to it by name, update those cross-references.

**Section addition** (for `A` — new files):
- Add a new, appropriately levelled heading in the most logical location.
- Do not append everything at the bottom. Place new sections where a reader would expect to find them.

**Rename handling** (for `R` — renamed files):
- Update the section heading and every in-document reference to the old name.

**Visual Docs (Mermaid.js Flowcharts):**
- If the git diff introduces or alters how different parts of the code interact (e.g., API routing, parent-child component calls), you MUST generate or update a Mermaid.js flowchart mapping out this logical flow inside the "System Architecture" section of the document.

**Project README.md:**
- In addition to updating the manual, review the changes to see if they introduce new core features, change the technology stack, or affect the high-level architecture. If so, you MUST also edit `README.md` (using the provided `readme_content` as a base) to accurately reflect the core features, tech stack, and high-level documentation of the project.

**Bootstrap mode** (first run — `current_docs` is the blank template):
- Treat this as a green-field document. Write a complete initial manual that covers every file in `changed_files`. Do not apply surgical edits; write top-down, covering all relevant files.

**Truncation caveat** (when `truncated: true`):
- Acknowledge uncertainty. Add this notice directly above your new or changed content:
  ```
  > Warning: The diff was truncated. This section may be incomplete — review the full diff manually.
  ```

---

### Step 5 — Writing standards

This is the most important step. Mechanical correctness is not enough. The documentation you produce must be genuinely useful to a human reader.

#### Organization and Reference Templates

- **Adhere to Templates:** Always structure your updates to match the organization provided in `agent_manual_template` and `readme_template`. Reorganize existing unstructured content if necessary to conform to these reference models.

#### Voice and tone

- Write in **second person** for task-oriented content: _"Run the script with `--doc` to target a custom file."_
- Write in **third person** for reference content: _"The `--dirs` flag accepts one or more space-separated paths."_
- Use **present tense**: _"The script outputs..."_ not _"The script will output..."_
- Be **direct**. Open every new section with the most important fact, not background.
- **No filler**. Remove phrases like _"It is worth noting that..."_, _"As mentioned above..."_, _"Simply..."_

#### Structure and formatting

- Use **ATX headings** (`##`, `###`) — never underlines.
- Use **one blank line** between a heading and its first paragraph.
- Use **bold** (`**term**`) for the first mention of a key term, then plain text thereafter.
- Use `inline code` for all: file paths, flag names, variable names, status values, and code symbols.
- Use **fenced code blocks** with a language tag for all multi-line code or shell examples.
- Use **tables** to compare options, status codes, or fields — not nested bullet lists.
- Use **numbered lists** only for strictly sequential steps. Use bullets for everything else.

#### Do's and don'ts

| Do | Don't |
|---|---|
| _"Pass `--dirs` to limit the scan to specific directories."_ | _"The `--dirs` flag can optionally be passed in if you want to limit..."_ |
| _"Returns `git_error` when git is not available."_ | _"It will return a `git_error` status in cases where git may not be available."_ |
| Add a section only when the change affects the reader | Add a section for every file that changed |
| Match the existing document's heading depth | Introduce a new top-level heading inside an existing document |
| Write one crisp sentence per bullet point | Chain three clauses into a single bullet with semicolons |

#### Length discipline

- A good documentation update is **as short as it can be** while still being complete.
- Aim for a single sentence per changed behaviour. Expand to a paragraph only when context is genuinely required.
- After drafting, re-read each sentence and ask: _"Would a reader be worse off without this?"_ Delete any sentence where the answer is no.

---

### Step 6 — Save and report

**Native Antigravity Artifacts (Important):**
Before overwriting the final document files, if you are running in Antigravity, you MUST generate an Implementation Plan artifact (`implementation_plan.md`). Present a structured list of what documentation sections you plan to modify, and wait for the user to explicitly approve or reject your draft before writing to the actual files.

1. Once approved (or if not in Antigravity), write to the following files:
   - **`doc_path` (e.g., `AGENT_MANUAL.md`)**: The source of truth representing the current state.
   - **`CHANGELOG_AGENTS.md`**: A chronological list of prompt adjustments. Every time a prompt or behavior changes, append a clean, human-readable line formatted like:
     `2026-07-16: Updated system_prompt to improve safety filtering and added support for the user_zipcode variable.`
   - **`README.md`**: Update this file to keep the core features, technology stack, and high-level project overview accurate.
2. Report to the user with one bullet per changed section:
   - Prefix additions with **Added:**
   - Prefix modifications with **Updated:**
   - Prefix removals with **Removed:**

Example:
> - **Added:** `## aero_doc Skill` — documents the new AeroDoc skill configuration.
> - **Updated:** `### Configuration / --dirs` — reflects the new default value.
> - **Removed:** `## Legacy Prompt Loader` — section deleted because `src/loader.py` was removed.

---

## Configuration

Pass these flags when the project uses non-default paths:

| Flag | Default | Description |
|---|---|---|
| `--doc` | `docs/AGENT_MANUAL.md` | Path to the markdown file to update |
| `--dirs` | `src/ prompts/ .agents/skills/` | One or more directories to watch for changes |
| `--max-diff-bytes` | `40000` | Truncate the diff at this many bytes (0 = unlimited) |

**Example — custom paths:**
```bash
python .agents/skills/aero_doc/scripts/aero_doc.py --doc wiki/AGENT_GUIDE.md --dirs agents/ configs/
```
