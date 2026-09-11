#!/usr/bin/env python3
"""Behavior regression for Agent Skills (heuristic layer).

WHAT THIS IS: keyword-level trigger regression that runs in CI with no LLM:
  1. Round-trip: every extracted (non-fallback) defaultPrompt must reference at
     least one salient token of its own skill (description + name), i.e. a naive
     keyword matcher would route the prompt to THIS skill.
  2. Interference: a skill's own prompts must score >= on its own description
     than on any sibling's description (no cross-trigger ambiguity; ties allowed).
  3. Fallback honesty: skills whose prompts are the converter's generic fallback
     get a WARNING (ambiguous routing by design), not a hard failure.

WHAT THIS IS NOT: an end-to-end LLM trigger test. Platform matching is semantic;
that layer requires live model calls and stays out of scope for zero-dependency CI.

Exit codes: 0 = pass (warnings allowed), 1 = regression, 2 = usage error.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from skill2openai import parse_frontmatter, extract_default_prompts, DEFAULT_PROMPTS  # noqa: E402

STOP = {"the", "a", "an", "and", "or", "for", "with", "this", "that", "these",
        "used", "use", "verify", "verified", "must", "its", "into", "from",
        "when", "has", "have", "so", "none", "not", "real", "skill", "skills",
        "test", "tests", "my", "me", "then"}


def load_skill(path: Path):
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    fm = parse_frontmatter(text)
    body = text[m.end():] if m else text
    return fm, body


def salient_tokens(text: str) -> set:
    text = text.lower()
    words = {w for w in re.findall(r"[a-z0-9][a-z0-9\-]+", text)
             if len(w) >= 3 and w not in STOP}
    cjk = re.sub(r"[^\u4e00-\u9fff]+", " ", text).split()
    bigrams = set()
    for seg in cjk:
        if len(seg) >= 2:
            bigrams |= {seg[i:i + 2] for i in range(len(seg) - 1)}
    return words | bigrams


def score(prompt_tokens: set, target_tokens: set) -> float:
    return len(prompt_tokens & target_tokens) / max(len(prompt_tokens), 1)


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    roots = [Path(a) for a in args] or [Path(__file__).resolve().parents[1] / "tests" / "fixtures"]

    skills = {}
    for root in roots:
        for d in sorted(root.iterdir()) if root.exists() else []:
            if d.is_dir() and (d / "SKILL.md").exists():
                fm, body = load_skill(d / "SKILL.md")
                name = str(fm.get("name") or d.name)
                skills[d.name] = {
                    "own": salient_tokens(str(fm.get("description") or ""))
                           | salient_tokens(name),
                    "prompts": extract_default_prompts(body),
                }
    if not skills:
        print("no skills found under:", [str(r) for r in roots])
        return 2

    failures, warnings = [], []
    for name, info in skills.items():
        is_fallback = all(p in DEFAULT_PROMPTS for p in info["prompts"])
        if is_fallback:
            warnings.append(f"{name}: fallback-only prompts (ambiguous routing by design)")
        for p in info["prompts"]:
            pt = salient_tokens(p)
            if not pt:
                continue
            self_score = score(pt, info["own"])
            if self_score <= 0 and not is_fallback:
                failures.append(f"{name}: round-trip fail, prompt routes nowhere: {p[:50]!r}")
            for sib, sib_info in skills.items():
                if sib == name:
                    continue
                s = score(pt, sib_info["own"])
                if s > self_score:
                    failures.append(
                        f"{name}: interference, prompt {p[:40]!r} matches {sib} "
                        f"({s:.2f}) stronger than itself ({self_score:.2f})")
        print(f"  [{'WARN' if is_fallback else 'PASS'}] {name}")

    print(f"behavior regression: {len(skills)} skills, "
          f"{len(failures)} failure(s), {len(warnings)} warning(s)")
    for f in failures + warnings:
        print("  -", f)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
