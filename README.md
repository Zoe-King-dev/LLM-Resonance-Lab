# LLM Resonance Lab

> 当大模型能力逐渐趋同时，人们选择模型的标准将从"谁更聪明"转向"谁更懂我"。

LLM Resonance Lab 是一个本地运行的 CLI 工具，帮助你通过**主观共鸣度**而非 Benchmark 分数，挑选出最适合作为长期 Agent 核心的 LLM。

它**不是** Benchmark / Arena / 排行榜。
它是**一个探索人与模型关系的实验室**。

详细产品需求见 [`LLM Resonance Lab PRD_V1.0.md`](LLM%20Resonance%20Lab%20PRD_V1.0.md)，背景与设计动机见 [`LLM Resonance Lab项目诞生的背景.md`](LLM%20Resonance%20Lab%E9%A1%B9%E7%9B%AE%E8%AF%9E%E7%94%9F%E7%9A%84%E8%83%8C%E6%99%AF.md)。

---

## 快速开始（无需 API Key，使用 mock 模式）

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 浏览 Case 与模型
python run.py cases
python run.py models

# 3. 用 mock 跑一遍全流程
python run.py run --mock --model minimax3     # A 组：每个 Case 一个独立 Session
python run.py blind case_001 --seed 1         # 盲测：生成 A/B 包
python run.py eval case_001                   # 评估：生成人工评分模板
python run.py marathon career_choice --model minimax3 --mock   # B 组：长会话

# 4. 记录感受
python run.py journal new
python run.py journal note "Response B 让我停下来想了一会。"
```

## 使用真实模型

### 1. 创建你的本地 `models.yaml`

仓库里只有 `models.yaml.example` 模板（可入库）。把你的真实配置放到 `models.yaml`（已在 `.gitignore` 中）：

```bash
cp models.yaml.example models.yaml
# 然后编辑 models.yaml，修改 name / provider / model_name 字段
```

`models.yaml` 字段说明：

| 字段 | 必填 | 说明 |
|------|------|------|
| `name` | ✅ | 人类可读 ID，CLI / 文件名 / 日志都用它 |
| `provider` | ✅ | LiteLLM provider 前缀（`openai` / `deepseek` / `anthropic` / ...） |
| `api_key_env` | ✅ | **环境变量名**（如 `MINIMAX_API_KEY`），不是 key 本身 |
| `model_name` | ❌ | 厂商 API 实际期望的模型名。**默认用 `name`**。当你的 `name` 是别名（如 `minimax3`）但厂商要 `MiniMax-M3` 时设这个 |
| `api_base_env` | ❌ | 自定义 API 端点 URL 所在的环境变量名。**默认用 LiteLLM provider 内置端点**。OpenAI 兼容厂商接非默认域名时设这个。注意：`platform.minimaxi.com` 是登录拿 key 的网页，**API 端点是 `api.minimax.chat`**。同理 `platform.deepseek.com` 是平台，API 端点是 `api.deepseek.com` |

> ⚠️ **绝对不要** 把 API Key / URL 直接写在 `models.yaml` 里。`api_key_env` 和 `api_base_env` 字段都是环境变量的**名字**，真实值通过 shell 注入。模型注册加载器会做硬性检查 —— 如果检测到字段值看起来像真实 Key（`sk-...`、过长、含小写或连字符），会直接拒绝启动。

### 2. 设置环境变量

把 API Key、API 端点 URL 都放到 shell（推荐：`.env` + `set -a && source .env && set +a`）：

```bash
# 必填：API Key
export MINIMAX_API_KEY=...
export DEEPSEEK_API_KEY=...

# 可选：当厂商不是 LiteLLM 内置 provider，或要覆盖默认端点时
export MINIMAX_API_BASE=https://api.minimax.chat/v1
export DEEPSEEK_API_BASE=https://api.deepseek.com/v1
```

> 💡 **注意区分"平台 URL"和"API 端点 URL"**：
> - 平台 URL（`https://platform.deepseek.com`）是你登录、拿 key 的网页
> - API 端点 URL（`https://api.deepseek.com/v1`）是你实际发请求的地址
>
> `api_base_env` 必须是后者。填错就会出现"SSL 握手失败"或"404 Not Found"。

### 3. 验证配置

```bash
python run.py models
```

会显示每个模型的：`Name` / `Provider` / `API Model`（实际发给厂商的模型名） / `API Key` 状态 / `API Base` 状态。如果 Key 显示 `missing` 或 Base 显示 `missing`，回去查 `.env` / shell 注入。

### 4. 运行（不加 `--mock`）

```bash
python run.py run --model minimax3
python run.py marathon career_choice --model minimax3
```

## 命令清单

| 命令 | 说明 |
| --- | --- |
| `python run.py` | 默认执行 batch runner（等价于 `run`） |
| `python run.py run` | A 组：每个 Case 一个独立 Session |
| `python run.py blind <case_id>` | 盲测：随机 A/B 分配两个模型的回答 |
| `python run.py eval <case_id>` | 生成人工评估模板（6 维度 + 胜者） |
| `python run.py journal new` | 创建当天的共鸣日志 |
| `python run.py journal note "..."` | 追加一条感受 |
| `python run.py marathon <scenario> --model <name>` | B 组：同一 Session 跨 N 轮 |
| `python run.py models` | 列出已注册模型 + API Key 状态 |
| `python run.py cases` | 列出所有 Case |

### 公共参数

| 参数 | 作用 |
| --- | --- |
| `--mock` | 使用内置 / 指定的 mock 响应，不调用任何真实 API |
| `--mock-file PATH` | YAML 文件，提供 `{model_name: response_text}` 覆盖 |
| `--date YYYY-MM-DD` | 指定 results 子目录日期（默认今天） |
| `--model NAME` | 限制为指定模型（可重复） |
| `--cases ID` | 限制为指定 Case（可重复） |

## 输出目录

```
results/                              # 由 batch / marathon runner 生成
  YYYY-MM-DD/
    case_001/<model>.md               # A 组：每个 (case, model) 一个文件
    marathon_<scenario>_<model>/
      turn_NN.md                      # B 组：每轮一个完整对话快照
blind/<case_id>/                      # 盲测包
  response_A.md
  response_B.md
  mapping.json                        # 模型到 A/B 的映射
evaluation/                           # 人工评估模板
  YYYY-MM-DD_<case_id>_evaluation.md
journal/                              # 共鸣日志
  YYYY-MM-DD.md
```

## 目录结构

```
.
├── cases/                 # Case 题库（Markdown + YAML frontmatter）
├── marathons/             # 长会话场景（每轮一个 turn_NN.md）
├── models.yaml            # 模型注册表
├── results/, blind/,
│   evaluation/, journal/  # 由 CLI 生成的输出（已 .gitignore）
├── lab/                   # Python 实现包
├── tests/                 # pytest 套件
├── run.py                 # 入口
├── requirements.txt
└── pyproject.toml
```

## 开发

```bash
# 运行测试套件
pytest -q

# 类型检查
mypy lab run.py
```

## 设计原则

任何修改都必须遵循：

1. **Resonance First** — 优先关注共鸣感，而非准确率
2. **Case Isolation** — 每个 Case 必须独立测试，禁止共享上下文与历史
3. **Human Judgment Matters** — 最终评判者是用户，不是 AI
4. **Readable Over Automated** — 可读性优先于自动化

## 许可证

Apache License 2.0 — 详见 [`LICENSE`](LICENSE)。
