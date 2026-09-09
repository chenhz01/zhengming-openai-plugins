#!/usr/bin/env python3
"""CI regression for skill2openai converter.
Runs the converter on 3 fixtures + self-hosting consistency check.
Exit 0 = all green."""
import filecmp
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONVERTER = ROOT / "tools" / "skill2openai.py"
FIXTURES = ROOT / "tests" / "fixtures"
DEFAULT_PROMPTS = ["Use this skill on my current task",
                   "Explain what this skill does, then apply it"]

fails = []

def check(cond, msg):
    print(("  PASS  " if cond else "  FAIL  ") + msg)
    if not cond:
        fails.append(msg)

def convert(name, out):
    r = subprocess.run([sys.executable, str(CONVERTER), name, "--out", str(out),
                        "--root", str(FIXTURES)],
                       capture_output=True, text=True)
    check(r.returncode == 0, f"convert {name}: exit 0")
    return out / "plugins" / name / ".codex-plugin" / "plugin.json"

def load(p):
    return json.loads(p.read_text(encoding="utf-8"))

def main():
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "dist"

        # --- fixture 1: minimal -> fallback defaultPrompt ---
        pj = load(convert("demo-minimal", out))
        check(pj["name"] == "demo-minimal", "minimal: name correct")
        check(pj["interface"]["defaultPrompt"] == DEFAULT_PROMPTS,
              "minimal: defaultPrompt falls back to defaults")

        # --- fixture 2: triggers -> extracted prompts ---
        pj = load(convert("demo-triggers", out))
        dp = pj["interface"]["defaultPrompt"]
        check(dp != DEFAULT_PROMPTS and len(dp) >= 2,
              f"triggers: prompts extracted ({len(dp)} items)")
        check(any("fixture" in p.lower() for p in dp),
              "triggers: extracted text comes from the trigger section")

        # --- fixture 3: longdesc -> truncated to 1024 ---
        pj = load(convert("demo-longdesc", out))
        d = pj["description"]
        check(len(d) == 1024 and d.endswith("..."),
              f"longdesc: truncated to 1024 with '...' (got {len(d)})")

        # --- official hard constraints hold for every fixture ---
        for name in ("demo-minimal", "demo-triggers", "demo-longdesc"):
            pj = load(out / "plugins" / name / ".codex-plugin" / "plugin.json")
            check(len(pj["description"]) <= 1024, f"{name}: description <=1024")
            check(not any(w in pj["name"].lower() for w in ("claude", "anthropic")),
                  f"{name}: no reserved words in name")
            skills_dir = out / "plugins" / name / "skills" / name
            check(skills_dir.is_dir() and (skills_dir / "SKILL.md").exists(),
                  f"{name}: skills/<name>/SKILL.md bundled")

        # --- self-hosting: converter output must equal committed plugin ---
        self_out = Path(td) / "self"
        r = subprocess.run([sys.executable, str(CONVERTER), "skill2openai-converter",
                            "--out", str(self_out), "--root", str(ROOT / "plugins" / "skill2openai-converter" / "skills")],
                           capture_output=True, text=True)
        check(r.returncode == 0, "self-host: convert committed skill source, exit 0")
        generated = self_out / "plugins" / "skill2openai-converter"
        committed = ROOT / "plugins" / "skill2openai-converter"
        same = filecmp.dircmp(generated, committed)
        diff_ok = compare_dirs(generated, committed)
        check(diff_ok, "self-host: regenerated output identical to committed plugin")

    print(f"\n{'='*50}\n  RESULT: {'ALL GREEN' if not fails else f'{len(fails)} FAILURES'}\n{'='*50}")
    sys.exit(0 if not fails else 1)

def compare_dirs(a: Path, b: Path) -> bool:
    ok = True
    for p in sorted(a.rglob("*")):
        if p.is_file():
            rel = p.relative_to(a)
            q = b / rel
            if not q.exists() or q.read_bytes() != p.read_bytes():
                print(f"        diff: {rel}")
                ok = False
    for q in sorted(b.rglob("*")):
        if q.is_file() and not (a / q.relative_to(b)).exists():
            print(f"        missing in generated: {q.relative_to(b)}")
            ok = False
    return ok

if __name__ == "__main__":
    main()
