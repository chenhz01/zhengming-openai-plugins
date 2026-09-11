
## TL;DR

**English**: The Agent Skills ecosystem has quietly split into three layers — Anthropic's official SKILL.md format (175k★), OpenAI's Codex plugin bundles (6.4k★), and Vercel's `npx skills` distribution layer that already supports 75+ agents (31k★). The formats share a common core, but publishing to each still means re-describing your skill three times. We open-sourced a stdlib-only converter that turns any SKILL.md folder into a compliant OpenAI plugin bundle — and it ships with the CI proof that it can convert itself. This article is the methodology behind it, and an invitation to co-build the missing piece: a multi-platform publish index with behavior regression.

**中文一句话**：Agent Skills 的"编写标准"已经统一（SKILL.md），但"发布"还停留在手工搬运——我们把三平台的格式差异摸清后开源了一个转换器，本文是方法论文档 + 合作邀请。

---

## 一、生态现状：三层已经形成（2026-09-11 API 实测）

| 层 | 项目 | 星数 | 最近提交 | 角色 |
|---|---|---|---|---|
| 编写标准 | anthropics/skills | 175,757 | 09-10 | SKILL.md 格式的官方源头（agentskills.io 规范） |
| 分发层 | vercel-labs/skills | 31,369 | 09-08 | `npx skills add <repo>`——一个命令装进 75+ 个 agent |
| 发布格式 | openai/plugins | 6,414 | 09-08 | Codex plugin 打包格式（plugin.json + skills/ 布局） |
| 方法论 | obra/superpowers | 285,028 | 09-11 | 怎么写出"会被真正触发"的 skill |

**关键观察**：编写和分发都标准化了，唯独"发布到多平台"这一步没人做——每个平台一个格式，skill 作者要么三处手工维护，要么放弃其他平台。这就是窗口。

## 二、方法论：三平台差异到底在哪

以一个标准 SKILL.md 文件夹为输入，三个出口的差异收敛为一张映射表：

| 关注点 | Agent Skills（Anthropic） | OpenAI Codex plugin | 共同核心 |
|---|---|---|---|
| 入口文件 | SKILL.md（frontmatter） | plugin.json + 捆绑的 skills/ | SKILL.md 本体 |
| 身份字段 | name / description | name / version / interface | description |
| 交互入口 | 靠 description 触发 | interface.defaultPrompt（默认指令） | 触发语义 |
| 硬约束 | description ≤1024 字符；name 禁含 `claude`/`anthropic` | 同源规范（agentskills.io） | 一套约束管两头 |
| 目录契约 | skills/ 扁平命名空间 | .codex-plugin/ + skills/ 捆绑布局 | 兼容 |

**三条实战教训**（每条都踩过）：

1. **description 不是简介，是触发器**。它必须回答"什么时候该加载我"，写成功能总结是 skill 触发率低的头号根因。
2. **能用代码强制的约束，不要写进文档**。1024 上限、保留字检查这类规则应该进校验脚本，每次构建机器把关——文档只留需要判断力的内容。
3. **`>-` 折叠语法是坑**。行式 frontmatter 解析器不认 YAML 折叠块，字段一律写行内格式（我们为此修过一次回归）。

## 三、L2 钩子：转换器已开源，带自证

[chenhz01/zhengming-openai-plugins](https://github.com/chenhz01/zhengming-openai-plugins)（MIT）：

- **纯 stdlib 零依赖**：`python skill2openai.py <skill> --out <dir>` 一条命令，SKILL.md 文件夹 → 合规 plugin 包（plugin.json + skills/ 布局 + marketplace.json 索引）
- **吃狗粮示范**：仓里的示例 plugin 是转换器转换它自己生成的——工具和产物同源，CI 字节级一致性检查防漂移
- **CI 回归**：3 个测试夹具（最小件 / 触发词提取 / 1200 字符截断到 1024）+ 19 项断言，push 即自动验证官方硬约束
- **interface.defaultPrompt 自动提取**：从 skill 正文触发词节抽取，抽不到回退安全默认值

**使用分层说明**（读到这里的都值得知道）：转换器本身零门槛——零依赖、一条命令、输入任意标准 SKILL.md 即可，仓内 CI 就是它的使用示范。但它只负责**格式翻译**，不提升内容：转换产物的触发质量取决于你源 SKILL.md 写得好不好（description 是功能总结还是触发器、触发词是否闭合）。写好后可用仓内 `tests/behavior_regression.py` 自测回环与串触发。至于"怎么从零写出高触发率 SKILL.md"的方法论（失败基线、常见漏洞模式），不在本仓范围内——它属于我们与共建伙伴的深度协作部分。

## 四、缺的最后一块（已实现 v0 · 合作邀请）

转换器解决了"格式翻译"。多平台发布的另外两件，现已实现 v0 并进 CI（读者可当场复现）：

1. **发布索引**：`python tools/publish_index.py --check` — 扫描全部 skill，产出 `PUBLISH-INDEX.json`（每个 skill 的三平台状态：agent-skills 版本 / openai-plugin 版本 / registry 安装通道），版本漂移即 CI 失败。当前覆盖已发布插件 + 生成态校验，跨平台远端同步为下一步。
2. **行为回归**：`python tests/behavior_regression.py` — 关键词级触发回归：每条 defaultPrompt 必须能"回环"到自己 skill 的描述词汇（round-trip），且对自己的匹配不得弱于任何兄弟 skill（防串触发）。它在第一次运行就抓到了一个真实断点（夹具的触发说法与描述词汇不衔接，已修复）。**诚实边界**：这是启发式层——平台真实触发是语义匹配，LLM 端到端触发实测是下一层，需要模型调用，不在零依赖 CI 范围内。

我们正在寻找**首批共建伙伴**：agent 框架作者、skill 市场运营方、或有多平台分发需求的 skill 重度作者——共建方向：语义级行为回归（LLM 触发实测）、跨平台远端同步、多平台 marketplace 索引。首批伙伴获得完整引擎访问权与联合发布位。

**回信即可获取完整技术方案（邀请制）。**
联系：hcac4735@agent.qq.com（注明 "skills-publish"）

---

*本文基于 2026-09-11 GitHub API 实测数据撰写。文中工具为独立开源项目，与所列平台无隶属关系。*
