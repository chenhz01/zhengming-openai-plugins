---
name: demo-triggers
skill_name: demo-triggers
display_name: Demo Triggers
version: 0.1.0
author: zhengming
agent_created: true
created: 2026-09-09
description: Fixture skill with a trigger section, used to verify defaultPrompt auto-extraction. 触发场景: CI 回归 / defaultPrompt 提取测试。
tags: [ci-fixture, demo]
---

# Demo Triggers

Fixture skill for CI regression. Has a 「触发条件」section with distinctive
phrases; the converter must extract them into `interface.defaultPrompt`.

## 触发条件

- "run the fixture check" / "extract defaultPrompt prompts" · "fixture mode on"
- `/demo-triggers`
