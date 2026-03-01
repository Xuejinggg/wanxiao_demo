# Phoenix + DeepAgents Agent 监控 Demo

使用 [Arize Phoenix](https://phoenix.arize.com) 监控 LangChain DeepAgents 调用节点的完整演示。

## 🌟 功能特性

- 🔍 **自动追踪**: 所有 DeepAgent 节点调用（planning、execution、observation、final_answer）
- 📊 **可视化**: 在 Phoenix UI 中查看完整的 agent 执行流程
- 🛠️ **工具监控**: 追踪每个工具调用的输入/输出和执行时间
- 💬 **LLM 追踪**: 监控所有 LLM 调用的参数和响应
- 🤖 **GLM-5 支持**: 使用智谱 GLM-5 模型进行推理

## 📦 安装

依赖已添加到 `pyproject.toml`，运行:

```bash
uv sync
```

### 必需依赖包

确保以下包已正确安装：

```bash
# Phoenix 监控库（必须指定版本）
uv pip install arize-phoenix==12.29.0

# 时区库（Phoenix 的依赖）
uv pip install pytz
```

或使用 pip：

```bash
pip install arize-phoenix==12.29.0 pytz
```

在 `.env` 文件中添加以下配置:

```bash
# 必需: GLM API Key (从 https://open.bigmodel.cn 获取)
GLM_API_KEY="your_glm_api_key_here"

# 可选: 模型名称 (默认 glm-5)
Z_MODEL="glm-5"
```

## 🚀 快速开始

```bash
# 运行 demo
uv run python phoenix_deepagents_demo.py
```

然后访问: http://localhost:6006

## 📊 查看监控数据

运行 demo 后，agent 的每一步执行都会被自动追踪。

1. 打开浏览器访问: http://localhost:6006
2. 点击 **Traces** 标签页
3. 查看 agent 执行的每个步骤:
   - **Trace**: 完整的任务执行流程
   - **Spans**: 单个操作（如工具调用、LLM 调用）
   - **Attributes**: 输入、输出、参数等元数据
   - **Timeline**: 执行时间线

## 🔧 核心代码说明

### 1. 设置 Phoenix 追踪

```python
from phoenix.otel import register
from openinference.instrumentation.langchain import LangChainInstrumentor

# 注册 tracer provider
tracer_provider = register(
    project_name="deepagents-demo",
    endpoint="http://127.0.0.1:4317",
)

# 自动为 LangChain 启用追踪
LangChainInstrumentor().instrument(tracer_provider=tracer_provider)
```

### 2. 创建 Agent (使用 GLM-5)

```python
from langchain_openai import ChatOpenAI
from deepagents import create_deep_agent

# 配置 GLM-5
llm = ChatOpenAI(
    model="glm-5",
    base_url="https://open.bigmodel.cn/api/paas/v4",
    temperature=0.1,
)

# 创建 DeepAgent
agent = create_deep_agent(
    model=llm,
    store=InMemoryStore(),
    backend=backend,
    tools=tools,
    system_prompt="...",
)

# 所有调用都会被自动追踪
result = agent.invoke({"messages": [{"role": "user", "content": "查询"}]})
```

## 🤔 深入理解

### `setup_phoenix_tracing()` 做了什么？

这个函数是 **Phoenix 追踪系统的入口**，完成三件核心事情：

#### 1. 初始化 OpenTelemetry 追踪器

```python
tracer_provider = register(
    project_name="deepagents-demo",
    endpoint="http://127.0.0.1:4317",
)
```

| 参数 | 作用 |
|------|------|
| `project_name` | 在 Phoenix UI 中显示的项目名称，用于分类管理 traces |
| `endpoint` | **OTLP 接收端点**，Phoenix 服务器监听这个地址接收追踪数据 |

#### 2. 自动为 LangChain 注入追踪代码

```python
LangChainInstrumentor().instrument(tracer_provider=tracer_provider)
```

这行代码会**自动拦截** LangChain/DeepAgents 的所有操作：
- Agent 节点的进入/退出（planning → execution → observation → final_answer）
- 工具调用的输入/输出
- LLM 调用的参数和响应
- 执行时间和错误信息

#### 3. 为 GLM API 调用添加追踪

```python
OpenAIInstrumentor().instrument(tracer_provider=tracer_provider)
```

追踪每次 GLM API 调用的：
- 请求内容（prompt）
- 响应内容
- token 使用量
- 延迟时间

### `endpoint` 详解

```python
endpoint="http://127.0.0.1:4317"
```

这是 **OTLP (OpenTelemetry Protocol) gRPC 端点**，数据流向如下：

```
┌─────────────────┐     OTLP/gRPC      ┌─────────────────┐
│  DeepAgent      │  ───────────────►  │  Phoenix Server │
│  (你的代码)      │   traces/spans     │   :6006 (UI)    │
│                 │                    │   :4317 (gRPC)  │
└─────────────────┘                    └─────────────────┘
                              ▲
                              │
                         存储 + 可视化
```

**端口说明**：
- **6006** - Phoenix Web UI（浏览器访问）
- **4317** - OTLP gRPC 接收端口（程序发送追踪数据到这里）

这是 OpenTelemetry 的标准端口，Phoenix 同时监听这两个端口。

### 工作流程

当你运行 agent 时：

```python
result = agent.invoke({"messages": [...]})
```

实际发生的追踪过程：

1. **Planning 节点开始** → 发送 span 到 `:4317`
2. **调用 search_knowledge 工具** → 记录工具输入/输出
3. **调用 GLM API** → 记录 LLM 调用详情
4. **Execution 节点完成** → 更新 span 时间戳
5. **Final answer 生成** → 完成整个 trace

所有数据通过 gRPC 实时发送到本地 Phoenix 服务器，你可以在 `http://localhost:6006` 实时查看完整的执行链路。

> 💡 **一句话总结**: `setup_phoenix_tracing()` = **给 DeepAgent 装上监控摄像头**，`endpoint` 就是**监控数据传回监控室的通道**。


## 📁 文件结构

```
phoenix_deepagents_demo.py  # 主 demo 脚本
.env.example                # 环境变量示例
```

## 🔍 监控内容

## 🔧 最近修复与改进

### 2025-03-01 修复

#### 1. 工具函数参数错误修复

**问题**: `get_current_time()` 函数报错 `takes 0 positional arguments but 1 was given`

**原因**: LangChain 调用工具时会自动传入输入参数，即使工具不需要输入

**修复**: 添加可选参数 `_input`:
```python
# 修复前
def get_current_time() -> str:

# 修复后
def get_current_time(_input: str = "") -> str:
    """获取当前时间（_input 参数由 LangChain 工具调用传入，但不使用）"""
```

#### 2. Phoenix 启动逻辑增强

**新增功能**:
- ✅ **端口冲突检测** - 启动前检查 6006 和 4317 端口是否被占用
- ✅ **服务复用** - 如果 Phoenix 已在运行，自动复用现有服务
- ✅ **进程健康检查** - 实时监控 Phoenix 进程状态，崩溃立即发现
- ✅ **超时保护** - 最多等待 30 秒，避免无限等待
- ✅ **详细错误输出** - 显示 Phoenix 启动失败的详细原因

**使用体验改进**:
```bash
# 场景 1: Phoenix 未运行
$ uv run python phoenix_deepagents_demo.py
🌐 正在启动 Phoenix UI...
   等待 Phoenix 启动...
✅ Phoenix UI 已启动!
   访问: http://localhost:6006

# 场景 2: Phoenix 已在运行
$ uv run python phoenix_deepagents_demo.py
⚠️  端口 6006 已被占用，检查是否为已运行的 Phoenix 服务...
✅ 检测到 Phoenix 已在运行，将复用现有服务
   访问: http://localhost:6006

# 场景 3: 启动失败
$ uv run python phoenix_deepagents_demo.py
🌐 正在启动 Phoenix UI...
❌ Phoenix 进程已退出 (退出码: 1)
错误信息:
   ModuleNotFoundError: No module named 'phoenix'
可能的原因:
  1. 依赖未正确安装: uv sync
  2. 端口冲突
  3. 尝试手动启动查看详细错误:
     python -m phoenix.server.main --port 6006
```

#### 3. Phoenix 启动方式修正

**问题**: 之前使用 `subprocess.Popen()` 直接启动 `phoenix.server.main` 模块，导致 Phoenix 服务无法正常启动和访问。

**正确方式**: 使用官方推荐的 `phoenix.launch_app()` API：

```python
import phoenix as px

# 官方推荐的启动方式
session = px.launch_app(
    host="127.0.0.1",
    port=6006,
)

# 关闭时使用
px.close_app()
```

**为什么不推荐用 subprocess？**

| 方式 | 问题 | 正确性 |
|------|------|--------|
| ❌ `subprocess.Popen(["python", "-m", "phoenix.server.main", ...])` | Phoenix 无法正确初始化，端口可能无法绑定，服务不稳定 | **不推荐** |
| ✅ `px.launch_app()` | 官方 API，自动处理初始化、数据库、端口绑定、gRPC 接收器 | **推荐** |

`px.launch_app()` 会自动处理：
- SQLite 数据库初始化
- gRPC 追踪接收器启动 (:4317)
- Web UI 服务启动 (:6006)
- 端口冲突检测和处理
- 优雅关闭资源

**参考**: [Arize Phoenix 官方教程](https://github.com/Arize-ai/phoenix/blob/main/tutorials/tracing/langchain_agent_tracing_tutorial.ipynb)

### 本地 LLM 支持

新增 `LocalLLM` 类，支持通过环境变量切换:

```bash
# 使用 GLM-5 (默认)
uv run python phoenix_deepagents_demo.py

# 使用本地 LLM
USE_LOCAL_LLM=true LOCAL_LLM_URL=http://localhost:8000/v1/chat/completions uv run python phoenix_deepagents_demo.py
```


Demo 会自动追踪以下内容:

1. **Planning 阶段**: Agent 的思考过程
2. **工具调用**: 每次工具执行的输入/输出
3. **LLM 调用**: 模型调用的参数和响应
4. **执行时间**: 每个步骤的耗时
5. **错误追踪**: 异常和错误信息

## 🐛 故障排除

### Phoenix UI 无法访问

```bash
# 检查端口是否被占用
lsof -i :6006

# 手动启动 Phoenix 服务器
python -m phoenix.server.main --port 6006
```

### 追踪数据未显示

1. 检查 Phoenix 服务器是否已启动
2. 查看日志中的错误信息
3. 确认 GLM_API_KEY 已正确设置

### 依赖问题

```bash
# 重新安装依赖
uv sync --reinstall
```

### 404 Not Found 错误

**问题**: 访问 `http://localhost:6006/` 出现 **404 Not Found** 错误。

**原因**: 
- `px.launch_app()` 主要是为 **notebook 环境**（Jupyter/Colab）设计的
- 在普通 Python 脚本中使用会导致 Web UI 无法正常初始化

**解决方案**: 使用 **`phoenix serve`** 启动：

```bash
# 在终端启动（推荐）
phoenix serve --port 6006

# 或在代码中使用 subprocess
subprocess.Popen([sys.executable, "-m", "phoenix.server.main", "serve", "--port", "6006"])
```

**启动方式对比**：

| 方式 | 适用场景 | 说明 |
|------|---------|------|
| ❌ `px.launch_app()` | 仅 notebook | 在脚本中会导致 404 Not Found |
| ✅ `phoenix serve` | 脚本/终端 | 正确初始化所有服务 |

**参考**: [Arize Community Discussion](https://community.arize.com/x/phoenix-support/1d744x7r3162)

---

**重要提示**:
1. 等待 Phoenix 完全启动（约 5-10 秒）
2. 访问的 URL 应该是 `http://localhost:6006/`（注意最后的斜杠）
3. 如果仍然无法访问，尝试清除浏览器缓存或使用无痕模式

## 📚 相关链接

- [Arize Phoenix 文档](https://docs.arize.com/phoenix)
- [OpenInference 规范](https://github.com/Arize-ai/openinference)
- [LangChain DeepAgents](https://github.com/langchain-ai/deepagents)
- [智谱 AI (GLM)](https://open.bigmodel.cn)

## 📄 许可证

MIT License
