---
name: skill2openai-converter
skill_name: skill2openai-converter
display_name: OpenAI Plugin 转换器
version: 0.1.0
author: 正明系统
agent_created: true
created: 2026-09-09
description: 把 zhengming/Agent-Skills 格式 skill（SKILL.md 文件夹）转换为 OpenAI Codex plugin 包（.codex-plugin/plugin.json + skills/ 布局 + marketplace.json 索引）。适用于: 要把 skill 发布到 OpenAI 生态 / 跨平台分发 / OpenAI plugin 打包 / skill 转换器 / skill2openai。纯 Python 标准库零依赖，只生成到本地输出目录，不自动对外发布。
allowed-tools: Bash, Read, Write, Glob
capsule: Capsule-021
tags: [skill-engineering, cross-platform, openai-plugin, converter]
---

# skill2openai-converter（正明→OpenAI Plugin 转换器 MVP）

> 触发词：`/skill2openai` 或提及“转换器”、“OpenAI plugin 打包”、“跨平台分发”、“skill 发布”等关键词。

> 依据 openai/plugins 官方 manifest 结构（figma 实例字段全解，2026-09-09 实抓）。
> SKILL.md 两边同源 agentskills.io 标准，本转换器只做「目录搬运 + plugin.json 生成」。

## 核心规则

### ✅ 必须遵守 (MUST)

1. description 生成时截断至 1024 字符（官方上限），并保留触发场景词
2. plugin name = skill 目录名（kebab-case），自动检查 claude/anthropic 保留字并告警
3. 整个 skill 文件夹原样拷入 `plugins/<name>/skills/<name>/`（SKILL.md + references/ + scripts/）
4. defaultPrompt 从 skill 触发条件节自动提取，提不到用安全默认值
5. 输出 `marketplace.json` 索引所有已转换插件
6. 生成后自检：每个 plugin.json 必须 json.loads 通过 + skills 目录非空

### 🚫 禁止行为 (FORBIDDEN)

1. 禁止上传/发布——只生成到本地输出目录，对外发布须走 GitHub 发表两原则 + 人工确认
2. 禁止改动源 skill 目录（只读）
3. 禁止在 manifest 中写入密钥/邮箱等敏感信息

## 用法

```bash
python scripts/skill2openai.py <skill名1> <skill名2> ... --out <输出目录>
python scripts/skill2openai.py --all --out <输出目录>          # 全量
python scripts/skill2openai.py zhengming-skillforge --out ./dist
```

## 工作流

### Step 1: 解析源 skill

读 frontmatter（name/description/version/tags/display_name）+ 触发条件节正文。

### Step 2: 拷贝 skill 目录

整个目录原样拷入 `<out>/plugins/<name>/skills/<name>/`（忽略 __pycache__/.git）。

### Step 3: 生成 plugin.json

`<out>/plugins/<name>/.codex-plugin/plugin.json`，interface 块含 displayName/shortDescription/longDescription/category/capabilities/defaultPrompt/brandColor（正明蓝 #4F8CFF）。

### Step 4: 生成 marketplace.json

`<out>/.agents/plugins/marketplace.json` 索引全部已转换插件。

### Step 5: 自检与验证报告

json.loads 每个 manifest + 统计文件数 + 保留字告警 + 打印汇总，退出码 0/1。

## 首次实战记录（2026-09-09）

试点 3 个生产 skill（内部技能，未随包发布）→
输出到本地输出目录（示例仓库即由其生成），3 plugin.json 全部 JSON 校验通过，marketplace 索引 3 条。

## Gotchas

- frontmatter 解析是行式的：description 若用 `>-` 折叠语法，validator 读不到全文——**description 写单行**
- 正明四层 frontmatter（skill_name/display_name/version/...）与 Agent Skills 官方（name/description）字段**同时保留**，两套工具链都兼容
- defaultPrompt 提取依赖「触发条件」节用 `·`/`/` 分隔的短句格式
