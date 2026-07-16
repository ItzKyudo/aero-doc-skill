#!/usr/bin/env node
/**
 * aero-doc CLI shim for npm
 *
 * Delegates to the bundled Python helper scripts. Requires Python 3.8+.
 */

"use strict";

const { execFileSync, spawnSync } = require("child_process");
const path = require("path");
const fs = require("fs");

// ─── ANSI helpers ─────────────────────────────────────────────────────────────
const isTTY = process.stdout.isTTY;
const green  = (s) => isTTY ? `\x1b[32m${s}\x1b[0m` : s;
const yellow = (s) => isTTY ? `\x1b[33m${s}\x1b[0m` : s;
const red    = (s) => isTTY ? `\x1b[31m${s}\x1b[0m` : s;
const bold   = (s) => isTTY ? `\x1b[1m${s}\x1b[0m`  : s;

function ok(msg)   { console.log(`  ${green("ok")}  ${msg}`); }
function warn(msg) { console.log(`  ${yellow("!")}   ${msg}`); }
function err(msg)  { console.error(`  ${red("err")} ${msg}`); }

// ─── Find Python ──────────────────────────────────────────────────────────────
function findPython() {
  const candidates = process.platform === "win32"
    ? ["python", "python3", "py"]
    : ["python3", "python"];

  for (const bin of candidates) {
    try {
      const result = spawnSync(bin, ["--version"], { encoding: "utf8" });
      if (result.status === 0) {
        const match = (result.stdout || result.stderr || "").match(/(\d+)\.(\d+)/);
        if (match) {
          const [, major, minor] = match.map(Number);
          if (major > 3 || (major === 3 && minor >= 8)) return bin;
        }
      }
    } catch (_) { /* not found */ }
  }
  return null;
}

// ─── Paths ────────────────────────────────────────────────────────────────────
const PKG_ROOT    = path.join(__dirname, "..");
const SKILL_DEST  = path.join(".agents", "skills", "aero_doc");
const BUNDLED_PY  = path.join(PKG_ROOT, "aero_doc", "skill_data", "scripts", "aero_doc.py");
const INSTALLED_PY = path.join(SKILL_DEST, "scripts", "aero_doc.py");

// ─── Commands ─────────────────────────────────────────────────────────────────
const VERSION = require("../package.json").version;

// ─── Platform config snippets ─────────────────────────────────────────────────
const MARKER = "<!-- aero-doc -->";

const CLAUDE_SNIPPET = `
## AeroDoc — Automated Documentation

After every change to \`src/\`, \`prompts/\`, or \`.agents/skills/\`, run:

\`\`\`bash
python .agents/skills/aero_doc/scripts/aero_doc.py
\`\`\`

Then follow the instructions in \`.agents/skills/aero_doc/skill.md\` to update \`docs/AGENT_MANUAL.md\`.
`;

const AGENTS_SNIPPET = `
## AeroDoc — Documentation Sync

This project uses AeroDoc to keep \`docs/AGENT_MANUAL.md\` in sync with the codebase.

Whenever you modify files under \`src/\`, \`prompts/\`, or \`.agents/skills/\`, run:

\`\`\`bash
python .agents/skills/aero_doc/scripts/aero_doc.py
\`\`\`

Follow the output instructions to update the documentation. Full protocol: \`.agents/skills/aero_doc/skill.md\`.
`;

const CURSOR_MDC = `---
description: Run AeroDoc to update docs/AGENT_MANUAL.md whenever src/, prompts/, or .agents/skills/ files change.
globs:
  - "src/**/*"
  - "prompts/**/*"
  - ".agents/skills/**/*"
alwaysApply: false
---

# AeroDoc — Documentation Sync

When files matching the globs above are saved or modified, run:

\`\`\`bash
python .agents/skills/aero_doc/scripts/aero_doc.py
\`\`\`

Then follow the instructions in \`.agents/skills/aero_doc/skill.md\` to update \`docs/AGENT_MANUAL.md\`.
`;

const COPILOT_SNIPPET = `
## AeroDoc — Documentation Sync

This project uses AeroDoc. When \`src/\`, \`prompts/\`, or \`.agents/skills/\` files change, run:

\`\`\`bash
python .agents/skills/aero_doc/scripts/aero_doc.py
\`\`\`

Follow \`.agents/skills/aero_doc/skill.md\` to update \`docs/AGENT_MANUAL.md\`.
`;

function cmdVersion() {
  console.log(`aero-doc ${VERSION}`);
}

function cmdInstall(argv) {
  const forceIdx = argv.indexOf("--force");
  const force = forceIdx !== -1;
  if (force) argv.splice(forceIdx, 1);

  const noPlatformIdx = argv.indexOf("--no-platform-files");
  const noPlatformFiles = noPlatformIdx !== -1;
  if (noPlatformFiles) argv.splice(noPlatformIdx, 1);

  const targetIdx = argv.indexOf("--target");
  const target = targetIdx !== -1 ? argv[targetIdx + 1] : SKILL_DEST;

  const src = path.join(PKG_ROOT, "aero_doc", "skill_data");
  if (!fs.existsSync(src)) {
    err(`Bundled skill data not found at ${src}.`);
    err("Try reinstalling: npm install -g aero-doc");
    process.exit(1);
  }

  console.log(`\n${bold(`Installing AeroDoc skill -> ${target}`)}`);

  if (fs.existsSync(target) && !force) {
    warn(`${target} already exists. Use --force to overwrite.`);
    process.exit(1);
  }

  if (fs.existsSync(target) && force) fs.rmSync(target, { recursive: true });

  copyDirSync(src, target);
  ok(`Skill files copied to ${target}/`);
  ok("skill.md            - agent instructions (universal)");
  ok("scripts/aero_doc.py - helper script");

  if (!noPlatformFiles) {
    console.log(`\n${bold("Generating platform config files")}`);
    writePlatformFiles(force);
  }

  console.log(`\n${bold("Next step:")} commit these files and let your agent do the rest.`);
  console.log(`  Run manually:  python ${path.join(target, "scripts", "aero_doc.py")} --help`);
  console.log(`  Works with:    Claude Code, Cursor, Codex, Copilot, Antigravity\n`);
}

function cmdRun(argv) {
  const python = findPython();
  if (!python) {
    err("Python 3.8+ is required but was not found on your PATH.");
    err("Install Python from https://python.org and try again.");
    process.exit(1);
  }

  const script = fs.existsSync(INSTALLED_PY) ? INSTALLED_PY : null;
  if (!script) {
    err(`Helper script not found at ${INSTALLED_PY}.`);
    err("Run 'aero-doc install' first to set up the skill.");
    process.exit(1);
  }

  const result = spawnSync(python, [script, ...argv], { stdio: "inherit" });
  process.exit(result.status ?? 1);
}

// ─── Platform files ───────────────────────────────────────────────────────────
function appendOrCreate(filePath, snippet, label, force) {
  if (fs.existsSync(filePath)) {
    const existing = fs.readFileSync(filePath, "utf8");
    if (existing.includes(MARKER)) {
      warn(`${filePath} — already configured, skipping.`);
      return;
    }
    fs.appendFileSync(filePath, `\n${MARKER}\n${snippet}`, "utf8");
    ok(`${filePath} — appended ${label} block`);
  } else {
    fs.mkdirSync(path.dirname(filePath), { recursive: true });
    fs.writeFileSync(filePath, `${MARKER}\n${snippet}`, "utf8");
    ok(`${filePath} — created (${label})`);
  }
}

function writeNew(filePath, content, label, force) {
  if (fs.existsSync(filePath) && !force) {
    warn(`${filePath} — already exists, skipping. Use --force to overwrite.`);
    return;
  }
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, content, "utf8");
  ok(`${filePath} — created (${label})`);
}

function writePlatformFiles(force) {
  appendOrCreate("CLAUDE.md",                               CLAUDE_SNIPPET,  "Claude Code",      force);
  appendOrCreate("AGENTS.md",                               AGENTS_SNIPPET,  "Codex / AGENTS.md",force);
  writeNew(path.join(".cursor","rules","aero-doc.mdc"),      CURSOR_MDC,      "Cursor",           force);
  appendOrCreate(path.join(".github","copilot-instructions.md"), COPILOT_SNIPPET, "GitHub Copilot", force);
}

// ─── Utility ──────────────────────────────────────────────────────────────────
function copyDirSync(src, dest) {
  fs.mkdirSync(dest, { recursive: true });
  for (const entry of fs.readdirSync(src, { withFileTypes: true })) {
    const srcPath  = path.join(src, entry.name);
    const destPath = path.join(dest, entry.name);
    if (entry.isDirectory()) copyDirSync(srcPath, destPath);
    else fs.copyFileSync(srcPath, destPath);
  }
}

// ─── Dispatch ─────────────────────────────────────────────────────────────────
const [,, command, ...rest] = process.argv;

switch (command) {
  case "version":
    cmdVersion();
    break;
  case "install":
    cmdInstall(rest);
    break;
  case "run":
    cmdRun(rest.filter(a => a !== "--")); // strip bare --
    break;
  default:
    console.log(`\n${bold("aero-doc")} — Antigravity skill that keeps docs in sync with code.\n`);
  console.log("Usage:");
  console.log("  aero-doc install [--force] [--no-platform-files] [--target PATH]  Copy skill into current project");
  console.log("  aero-doc run [-- ARGS]                                            Run the aero_doc helper script");
  console.log("  aero-doc version                                                  Print version\n");
  console.log("Examples:");
  console.log("  aero-doc install                    # copies skill + generates CLAUDE.md, AGENTS.md, Cursor rules");
  console.log("  aero-doc install --force");
  console.log("  aero-doc install --no-platform-files  # skip platform config files");
  console.log("  aero-doc run -- --doc wiki/GUIDE.md\n");
  console.log("Compatible with: Claude Code, Cursor, OpenAI Codex, GitHub Copilot, Antigravity\n");
    if (command && command !== "--help" && command !== "-h") {
      err(`Unknown command: ${command}`);
      process.exit(1);
    }
}
