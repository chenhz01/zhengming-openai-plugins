#!/usr/bin/env python3
"""Multi-platform publish index for Agent Skills.

Scans skill sources and derives per-platform release state:
  - agent-skills  : SKILL.md itself (source of truth; version from frontmatter)
  - openai-plugin : committed plugin under plugins/<name>/.codex-plugin/plugin.json
                    (or generated on the fly for uncommitted skills; version must
                    match the source, else version drift -> exit 1 with --check)
  - registry      : `npx skills add <git-repo>` installability (repo path recorded)

Writes PUBLISH-INDEX.json next to this script's repo root (unless --stdout).
Exit codes: 0 = in sync, 1 = version drift / check failed, 2 = usage error.
"""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from skill2openai import convert, parse_frontmatter  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def fm_version(skill_md: Path):
    """skill_md 是 SKILL.md 文件本身，返回 (version, name)。"""
    fm = parse_frontmatter(skill_md.read_text(encoding="utf-8"))
    return str(fm.get("version") or "?"), str(fm.get("name") or skill_md.parent.name)


def build_entries(fixtures_dir: Path, plugins_dir: Path) -> list:
    entries = []

    # committed plugins: source skill lives inside the plugin bundle
    for pd in sorted(plugins_dir.iterdir()) if plugins_dir.exists() else []:
        src = pd / "skills" / pd.name / "SKILL.md"
        pj = pd / ".codex-plugin" / "plugin.json"
        if not (src.exists() and pj.exists()):
            continue
        v_src, _ = fm_version(src)
        manifest = json.loads(pj.read_text(encoding="utf-8"))
        v_pub = str(manifest.get("version") or "?")
        entries.append({
            "skill": pd.name,
            "agent-skills": {"version": v_src, "state": "released"},
            "openai-plugin": {"version": v_pub, "state": "released",
                              "in_sync": v_src == v_pub},
            "registry": {"state": "installable",
                         "source": "github:chenhz01/zhengming-openai-plugins"},
        })

    # uncommitted skills (e.g. CI fixtures): generate on the fly, compare versions
    for sd in sorted(fixtures_dir.iterdir()) if fixtures_dir.exists() else []:
        if not (sd / "SKILL.md").exists() or any(e["skill"] == sd.name for e in entries):
            continue
        v_src, _ = fm_version(sd / "SKILL.md")
        with tempfile.TemporaryDirectory() as td:
            convert(sd, Path(td), fixtures_dir)
            pj = next(Path(td).rglob(".codex-plugin/plugin.json"), None)
            v_gen = str(json.loads(pj.read_text(encoding="utf-8")).get("version")) if pj else "?"
        entries.append({
            "skill": sd.name,
            "agent-skills": {"version": v_src, "state": "source-only"},
            "openai-plugin": {"version": v_gen, "state": "generated-on-check",
                              "in_sync": v_src == v_gen},
            "registry": {"state": "installable",
                         "source": "github:chenhz01/zhengming-openai-plugins"},
        })
    return entries


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    check = "--check" in sys.argv
    to_stdout = "--stdout" in sys.argv
    fixtures = Path(args[0]) if args else ROOT / "tests" / "fixtures"

    entries = build_entries(fixtures, ROOT / "plugins")
    drift = [e["skill"] for e in entries if not e["openai-plugin"]["in_sync"]]

    index = {
        "generated_by": "tools/publish_index.py",
        "repo": "github:chenhz01/zhengming-openai-plugins",
        "platforms": ["agent-skills (SKILL.md)", "openai-codex-plugin (.codex-plugin)",
                      "registry (npx skills add <repo>)"],
        "skills": entries,
        "in_sync": not drift,
    }
    text = json.dumps(index, ensure_ascii=False, indent=2)
    if to_stdout:
        print(text)
    else:
        (ROOT / "PUBLISH-INDEX.json").write_text(text + "\n", encoding="utf-8")
        print(f"PUBLISH-INDEX.json written: {len(entries)} skills, drift={drift or 'none'}")
    if check and drift:
        print("VERSION DRIFT:", drift)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
