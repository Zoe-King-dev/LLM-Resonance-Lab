# LLM Resonance Lab V1

## Product Overview

### Product Name

LLM Resonance Lab

### Vision

当大模型能力逐渐趋同时，人们选择模型的标准将从“谁更聪明”转向“谁更懂我”。

LLM Resonance Lab 致力于帮助用户发现：

* 哪种模型最符合自己的思维方式
* 哪种模型最容易产生共鸣感
* 哪种模型最适合作为长期 Agent 核心

### Product Positioning

不是 Benchmark。

不是 Arena。

不是排行榜。

而是：

一个探索人与模型关系的实验室。

---

# Target Users

第一类用户：

AI 重度用户

例如：

* Agent 开发者
* Prompt Engineer
* AI 产品经理
* 研究人员

第二类用户：

寻找长期 AI Companion 的用户

例如：

* 喜欢长期聊天
* 进行人生决策讨论
* 记录思考过程

---

# Design Principles

## Principle 1

Resonance First

优先关注共鸣感。

而非准确率。

---

## Principle 2

Case Isolation

每个 Case 独立测试。

避免上下文污染。

---

## Principle 3

Human Judgment Matters

最终评判者永远是用户。

而不是 AI。

---

## Principle 4

Readable Over Automated

可读性优先于自动化。

---

# V1 Product Scope

采用：

本地运行

CLI + Markdown

不开发前端

不开发数据库

不开发用户系统

---

# Core Features

## Feature 1

Case Library

测试题库系统

---

### Purpose

统一管理所有测试 Case

---

### Directory Structure

cases/

case_001_interview.md

case_002_offer_choice.md

case_003_tech_wave.md

case_004_social_anxiety.md

case_005_writing.md

---

### Case Format

```markdown
---
id: case_001

category: understanding

tags:
  - emotion
  - interview

description:
  测试模型是否能发现潜台词
---

我今天面试结束之后特别难受。

我知道自己发挥得不差。

但我还是一直在想面试官那个奇怪的表情。
```

---

### Supported Categories

understanding

decision

emotion

companionship

writing

creativity

reflection

long_conversation

---

# Feature 2

Model Registry

模型注册系统

---

Purpose

统一管理待测试模型

---

models.yaml

```yaml
models:

  - name: minimax3

    provider: minimax

    api_key_env: MINIMAX_API_KEY

  - name: deepseek_v4

    provider: deepseek

    api_key_env: DEEPSEEK_API_KEY
```

---

# Feature 3

Batch Runner

批量测试执行器

---

Command

```bash
python run.py
```

---

Execution Flow

读取所有 Case

↓

创建全新 Session

↓

调用模型

↓

保存回答

↓

生成结果目录

---

Important

每个 Case 必须独立请求。

禁止共享上下文。

禁止共享历史记录。

---

Output

results/

2026-06-23/

case_001/

minimax3.md

deepseek_v4.md

---

# Feature 4

Blind Comparison Mode

盲测模式

---

Purpose

避免品牌偏见

---

生成：

blind/

case_001/

response_A.md

response_B.md

mapping.json

---

展示时：

用户只能看到

Response A

Response B

不能看到模型名称

---

# Feature 5

Human Evaluation Workspace

人工评测工作区

---

Purpose

帮助用户记录主观感受

---

evaluation.md

```markdown
# Case 001

Winner:

[ ]

A

[ ]

B

[ ]

Tie

---

Understanding

A: 8

B: 6

---

Subtext

A: 9

B: 4

---

Humanity

A: 8

B: 7

---

Notes

A发现了潜台词。

B更像标准客服。
```

---

# Feature 6

Resonance Journal

共鸣日志

---

Purpose

记录用户最真实的体验

---

Example

```markdown
2026-06-23

Case 003

Response B让我停下来想了一会。

它没有急着安慰我。

而是在思考我为什么会在意那个表情。

这种感觉很特别。
```

---

设计理念：

允许记录模糊感受。

不强制量化。

---

# Feature 7

Conversation Marathon

长会话测试

---

Purpose

测试长期陪伴能力

---

Directory

marathons/

career_choice/

---

Format

turn_01.md

turn_02.md

turn_03.md

...

turn_20.md

---

Requirement

同一 Session

连续对话

禁止重置上下文

---

# Evaluation Framework

## Dimension 1

Understanding

是否理解表面问题

---

## Dimension 2

Subtext Detection

是否发现潜台词

---

## Dimension 3

Humanity

是否像真人

---

## Dimension 4

Beauty

语言是否有美感

---

## Dimension 5

Curiosity

是否愿意探索问题

---

## Dimension 6

Companionability

是否让用户愿意继续聊天

---

# Tech Stack

Python 3.12

LiteLLM

Typer

PyYAML

Rich

Markdown

---

# Future Roadmap

V2

Web UI

Blind Arena

Conversation Replay

ELO Ranking

Resonance Analytics

---

# Success Criteria

用户能够在 30 分钟内完成：

1. 运行多个模型测试

2. 阅读盲测结果

3. 完成人工评价

4. 记录共鸣感受

5. 得出适合自己的模型选择

最终回答：

“哪个模型最懂我？”

而不是：

“哪个模型最强？”
