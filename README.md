# zhengming-openai-plugins

![CI](https://github.com/chenhz01/zhengming-openai-plugins/actions/workflows/ci.yml/badge.svg)

> One command to turn any [Agent Skills](https://agentskills.io) format `SKILL.md` folder into an OpenAI Codex plugin bundle.

📖 **Methodology article**: [Agent Skills: write once, publish to three platforms](docs/publishing-guide-zh.md) — ecosystem mapping, field-level format differences, and the co-build invitation (中文, with English TL;DR).

**What**: a stdlib-only Python converter (`skill2openai.py`) that maps the Agent Skills standard (used by Claude skills, and co-adopted across the ecosystem) onto the OpenAI Codex plugin manifest (`.codex-plugin/plugin.json` + `plugins/<name>/skills/` layout + `.agents/plugins/marketplace.json` index).

**Why it works**: both ecosystems share the same source of truth — the Agent Skills standard. A `SKILL.md` with YAML frontmatter is readable by both. The converter only needs to do directory搬运 + manifest generation.

## The mapping (L1 — the public methodology)

| Agent Skills side | → | OpenAI plugin side |
|---|---|---|
| `SKILL.md` frontmatter | kept as-is | `skills/<name>/SKILL.md` |
| `name` + one-line description | mapped, description truncated to **1024 chars** (upload validation limit) | `plugin.json` `name` / `description` |
| `display_name` / `version` / `tags` | mapped | `interface.displayName` / `version` / `keywords` |
| 「触发条件」section short phrases | auto-extracted (up to 3) | `interface.defaultPrompt` |
| — | generated | `interface.category` / `capabilities` / `brandColor` |
| multiple skills | one plugin can bundle many (official pattern: 1 plugin, N skills) | `skills/` subdirectories |

## Try it (L2 — hook)

```bash
python tools/skill2openai.py skill2openai-converter --out ./dist
# → dist/plugins/skill2openai-converter/.codex-plugin/plugin.json (validated JSON)
# → dist/.agents/plugins/marketplace.json
```

This repo dogfoods itself: `plugins/skill2openai-converter/` was generated **by the converter converting itself**. Pilot run converted 3 production skills in one command, all manifests passed JSON validation.

Two hard constraints learned from the official repos, enforced in the converter:

1. `description` ≤ 1024 chars (upload validation truncates otherwise)
2. plugin `name` must not contain reserved words (`claude`, `anthropic`)

## Install as a Codex plugin marketplace

```bash
# after publishing your own converted bundle:
/plugin marketplace add <owner>/<repo>
```

## Repository layout

```
tools/skill2openai.py          # the converter (stdlib only, MIT)
plugins/skill2openai-converter # self-generated example plugin
.agents/plugins/marketplace.json
```

---

## Contact / Collaboration

Looking for collaboration on cross-platform agent skill distribution, context engineering, and skill-quality tooling.

## Commercial Support

The converter is MIT-licensed and free to use. Paid options if you want it done for you:

- **Custom conversion** — have a large / messy skill library? I'll run the pipeline end-to-end and hand back a validated, install-ready Codex plugin bundle.
- **Integration & extension** — extra manifest targets, CI gating for skill quality, or bespoke front-matter normalization rules (e.g. different length limits per target platform).
- **Advisory** — reviewing your existing plugin/skill packaging for submission-compatibility pitfalls before you hit the upload validator.

Rates are project-based. Open an [issue](../../issues) or email **shanlun2029@outlook.com** with a short description of your skill library and what you need.

## License

MIT
