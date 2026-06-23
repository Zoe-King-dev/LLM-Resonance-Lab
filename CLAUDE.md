# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 仓库性质

这是一个**纯文档仓库**，当前只包含产品规格文档，**尚未编写任何代码**。V1 的实现完全依据 `LLM Resonance Lab PRD_V1.0.md` 展开。背景讨论与设计动机见 `LLM Resonance Lab项目诞生的背景.md`。两份文档合在一起才构成完整的"项目意图 + 设计约束"。

- `README.md` 仅一行标题（实现开始时应予扩展）
- `LICENSE` 为 Apache License 2.0

## V1 范围（硬约束）

- 本地运行 / CLI + Markdown
- **不**开发前端 / 数据库 / 用户系统

## V1 技术栈

Python 3.12 / LiteLLM / Typer / PyYAML / Rich

规划入口：`python run.py`

## V1 设计原则（任何功能都必须遵循）

1. **Resonance First** — 优先关注共鸣感，而非准确率
2. **Case Isolation** — 每个 Case 必须独立测试，**禁止**共享上下文与历史
3. **Human Judgment Matters** — 最终评判者是用户，不是 AI
4. **Readable Over Automated** — 可读性优先于自动化

## 测试框架：两阶段结构（关键约束）

测试污染是本项目最强调的反模式。任何 runner 设计都必须支持两种互斥的会话策略，**不可混用**：

- **A 组：隔离测试** — 每题一个全新 Session，测首轮理解能力
- **B 组：长会话测试（Marathon）** — 同一 Session 连续 20 轮，测记忆、人格一致性、抗重复能力

**绝对禁止**：把多个 Case 拼成一个 Prompt 一次性喂给模型 —— 背景文档已说明这会让模型进入"考试模式"并形成统一叙事，测不出真实水平。

## 评测维度（6 项）

`Understanding` / `Subtext Detection` / `Humanity` / `Beauty` / `Curiosity` / `Companionability`

其中**潜台词理解（Subtext Detection）是核心差异化指标**，背景文档给出的权重建议：潜台词 30% / 长对话 25% / 中文美感 20% / 分析能力 15% / 指令遵循 10%。任何"重要性排序"或权重表的设计都应保留这个优先级。

## 规划目录结构

```
cases/                  # Case 题库（Markdown + YAML frontmatter，含 id/category/tags/description）
models.yaml             # 模型注册表（name / provider / api_key_env）
results/YYYY-MM-DD/     # 每次跑测的输出（按 case_id 和 model_name 分文件）
  case_001/<model>.md
blind/                  # 盲测目录（response_A.md / response_B.md / mapping.json）
marathons/<scenario>/   # 长会话测试（turn_01.md ~ turn_20.md，同一 Session）
```

Case 的 `category` 取值固定为：`understanding` / `decision` / `emotion` / `companionship` / `writing` / `creativity` / `reflection` / `long_conversation`。

## 文件命名与文档约定

- 产品文档统一使用**中文**，技术标识符、命令、库名保持原文
- 中文文件名（如 `LLM Resonance Lab项目诞生的背景.md`）是有意保留的，**不要**迁改为英文
- 修改 PRD 或背景文档时，commit 信息保持 `docs:` 前缀

## 仓库维护

- `.history/` 是编辑器自动生成的备份目录，目前**未跟踪**，也不应被加入版本控制
- 当前工作区有两份 Markdown 处于已修改未提交状态（PRD 与背景文档），在开始新工作前请确认这些改动是否需要先提交或暂存