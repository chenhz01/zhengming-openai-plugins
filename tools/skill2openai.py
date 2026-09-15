#!/usr/bin/env python3
"""skill2openai.py — zhengming skill → OpenAI Codex plugin 转换器 MVP
用法: python skill2openai.py <skill名...> [--all] --out <输出目录>
产物: <out>/plugins/<name>/{.codex-plugin/plugin.json, skills/<name>/...} + marketplace.json
"""
import argparse, json, os, re, shutil, sys
from pathlib import Path

DESCRIPTION_MAX = 1024
RESERVED = ("claude", "anthropic")
BRAND_COLOR = "#4F8CFF"  # 正明蓝
DEFAULT_CATEGORY = "Productivity"
DEFAULT_PROMPTS = [
    "Use this skill on my current task",
    "Explain what this skill does, then apply it",
]

def parse_frontmatter(text: str) -> dict:
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    fm = {}
    if not m:
        return fm
    for line in m.group(1).splitlines():
        if ":" in line and not line.startswith((" ", "-", "#")):
            k, _, v = line.partition(":")
            v = v.strip().strip('"').strip("'")
            if v.startswith("[") and v.endswith("]"):
                v = [x.strip().strip('"').strip("'") for x in v[1:-1].split(",")]
            fm[k.strip()] = v
    return fm

def extract_default_prompts(body: str) -> list:
    # 优先从「触发条件/触发场景/触发词」节取 2-3 条真实触发说法作为 defaultPrompt
    m = re.search(r"##\s*触发[^\n]*\n(.*?)(?=\n##\s|\Z)", body, re.DOTALL)
    if m:
        lines = [l.strip(" -`*") for l in m.group(1).splitlines() if l.strip()]
        picks = []
        for l in lines:
            for piece in re.split(r"[·/｜]", l):
                p = piece.strip(" -`*\"“”")
                if 4 <= len(p) <= 60:
                    picks.append(p)
        if len(picks) >= 2:
            return picks[:3]
    return DEFAULT_PROMPTS

def normalize_bundled_frontmatter(sk_md_path: Path, max_len: int) -> bool:
    """把打包副本 SKILL.md front matter 里的 description 截断到 max_len。

    OpenAI 提交校验对 SKILL 描述单独执行 skill_description_too_long（1024 上限，
    见 developers.openai.com/plugins/deploy/submission-errors#skill-errors），
    因此打包副本必须与 plugin.json 同步归一化。只改产物副本，源文件不动。
    返回是否做了归一化。"""
    text = sk_md_path.read_text(encoding="utf-8")
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not m:
        return False
    desc = str(parse_frontmatter(text).get("description") or "")
    if len(desc) <= max_len:
        return False
    new_desc = desc[:max_len - 3] + "..."
    new_block = re.sub(r"(?m)^description:[^\n]*$",
                       lambda _: "description: " + new_desc, m.group(1), count=1)
    sk_md_path.write_text("---\n" + new_block + "\n---\n" + text[m.end():],
                          encoding="utf-8")
    return True

def convert(skill_dir: Path, out_dir: Path, skills_root: Path) -> dict:
    name = skill_dir.name
    report = {"skill": name, "ok": False, "warnings": []}
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        report["error"] = "SKILL.md 不存在"
        return report
    text = skill_md.read_text(encoding="utf-8")
    fm = parse_frontmatter(text)
    body = text[m.end():] if (m := re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)) else text

    if any(r in name.lower() for r in RESERVED):
        report["warnings"].append(f"name 含官方保留字 {RESERVED}，发布前须改名")

    # 1. 拷贝整个 skill 目录（只读源）
    dest = out_dir / "plugins" / name / "skills" / name
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(skill_dir, dest,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".git"))

    # 1.5 打包副本 front matter description 同步归一化（源文件保持不动）
    #     修复 openai/codex#44843 审查指出的 skill_description_too_long 缺口
    if normalize_bundled_frontmatter(dest / "SKILL.md", DESCRIPTION_MAX):
        report["warnings"].append(
            f"bundled SKILL.md description 归一化到 {DESCRIPTION_MAX}（源文件未改动）")

    # 2. description：frontmatter description 优先，截断 1024
    desc = str(fm.get("description") or f"{name} skill for Agent workflows.")
    if len(desc) > DESCRIPTION_MAX:
        desc = desc[:DESCRIPTION_MAX - 3] + "..."

    # 3. plugin.json（对齐 openai/plugins figma 实例字段结构）
    display = str(fm.get("display_name") or name)
    version = str(fm.get("version") or "0.1.0")
    tags = fm.get("tags") or []
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.strip("[]").split(",") if t.strip()]
    manifest = {
        "name": name,
        "version": version,
        "description": desc,
        "author": {"name": str(fm.get("author") or "zhengming")},
        "homepage": "https://github.com/chenhz01",
        "license": "MIT",
        "keywords": (tags + ["zhengming", "agent-skills"])[:10],
        "skills": f"./skills/{name}/",
        "interface": {
            "displayName": display,
            "shortDescription": desc.split("。")[0][:100],
            "longDescription": desc,
            "developerName": "zhengming",
            "category": DEFAULT_CATEGORY,
            "capabilities": ["Read", "Write"],
            "defaultPrompt": extract_default_prompts(body),
            "brandColor": BRAND_COLOR,
        },
    }
    pj_dir = out_dir / "plugins" / name / ".codex-plugin"
    pj_dir.mkdir(parents=True, exist_ok=True)
    (pj_dir / "plugin.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    # 4. 自检：JSON 可解析 + skills 目录非空
    json.loads((pj_dir / "plugin.json").read_text(encoding="utf-8"))
    n_files = sum(1 for _ in dest.rglob("*") if _.is_file())
    report["ok"] = n_files > 0
    report["files"] = n_files
    report["prompts"] = manifest["interface"]["defaultPrompt"]
    return report

def main():
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("skills", nargs="*")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--root", default=os.path.expanduser("~/.workbuddy/skills"))
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    root = Path(args.root)
    names = sorted(d.name for d in root.iterdir()
                   if d.is_dir() and not d.name.startswith((".", "_"))) \
            if args.all else args.skills
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    def resolve(name_or_path: str) -> Path:
        # 独立路径（相对或绝对）优先；否则回退到 root 下的名字（--all 兼容内部用法）
        p = Path(name_or_path)
        return p if (p / "SKILL.md").exists() else root / name_or_path

    results = [convert(resolve(n), out_dir, root) for n in names]

    # 5. marketplace.json 索引
    ok = [r for r in results if r["ok"]]
    marketplace = {
        "name": "zhengming-skills",
        "owner": "chenhz01",
        "plugins": [
            {"name": r["skill"],
             "source": f"./plugins/{r['skill']}",
             "description": json.loads(
                 (out_dir / "plugins" / r["skill"] / ".codex-plugin" / "plugin.json")
                 .read_text(encoding="utf-8"))["description"]}
            for r in ok
        ],
    }
    mp = out_dir / ".agents" / "plugins"
    mp.mkdir(parents=True, exist_ok=True)
    (mp / "marketplace.json").write_text(
        json.dumps(marketplace, ensure_ascii=False, indent=2), encoding="utf-8")

    # 验证报告
    print(f"\n{'='*56}\n  skill2openai 转换报告 → {out_dir}\n{'='*56}")
    for r in results:
        if r["ok"]:
            w = f"  ⚠️ {'; '.join(r['warnings'])}" if r["warnings"] else ""
            print(f"  ✅ {r['skill']}: plugin.json OK, {r['files']} files{w}")
        else:
            print(f"  ❌ {r['skill']}: {r.get('error')}")
    print(f"\n  marketplace.json: {len(ok)} plugins")
    sys.exit(0 if len(ok) == len(results) else 1)

if __name__ == "__main__":
    main()
