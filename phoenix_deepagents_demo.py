#!/usr/bin/env python3
"""
Phoenix + DeepAgents Agent 监控 Demo (本地模式 + GLM-5)

演示如何使用 Arize Phoenix 监控 LangChain DeepAgents 的调用节点。
使用本地 Phoenix 实例和 GLM-5 模型。

功能：
- 使用 Phoenix 自动追踪 DeepAgents 的每个节点调用
- 可视化 agent 的思考过程、工具调用和响应
- 本地 Phoenix UI: http://localhost:6006
"""

import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# =============================================================================
# LLM 服务选择配置
# =============================================================================
# 设置 USE_LOCAL_LLM=True 使用本地 LLM 服务
# 设置 USE_LOCAL_LLM=False 使用 GLM-5 (智谱云 API)
USE_LOCAL_LLM = os.getenv("USE_LOCAL_LLM", "false").lower() in ("true", "1", "yes")

# 本地 LLM 服务配置 (当 USE_LOCAL_LLM=True 时使用)
LOCAL_LLM_CONFIG = {
    "api_url": os.getenv("LOCAL_LLM_URL", "http://localhost:8000/v1/chat/completions"),
    "model_name": os.getenv("LOCAL_LLM_MODEL", "local-model"),
    "temperature": float(os.getenv("LOCAL_LLM_TEMPERATURE", "0.1")),
    "max_tokens": int(os.getenv("LOCAL_LLM_MAX_TOKENS", "1024")),
}

# =============================================================================
# 本地 LLM 模型服务接入类
# =============================================================================

from typing import List, Optional

import requests
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field


class LocalLLM(BaseChatModel):
    """
    本地大模型服务接入类

    适配本地部署的 LLM 服务，如：
    - vLLM (https://github.com/vllm-project/vllm)
    - Text Generation Inference (TGI)
    - llama.cpp server
    - Ollama
    - 或其他兼容 OpenAI API 格式的本地服务

    示例：
        llm = LocalLLM(
            api_url="http://localhost:8000/v1/chat/completions",
            model_name="llama2-7b",
            temperature=0.1,
            max_tokens=1024,
        )
    """

    # 必填参数
    api_url: str = Field(default="http://localhost:8000/v1/chat/completions")
    """本地模型服务的 API 地址"""

    model_name: str = Field(default="local-model")
    """模型名称（用于标识）"""

    # 可选参数
    temperature: float = Field(default=0.1)
    """采样温度"""

    max_tokens: int = Field(default=1024)
    """最大生成 token 数"""

    api_key: Optional[str] = Field(default=None)
    """API Key（如果服务需要认证）"""

    timeout: int = Field(default=120)
    """请求超时时间（秒）"""

    @property
    def _llm_type(self) -> str:
        """返回 LLM 类型标识"""
        return "local-llm"

    def _convert_messages(self, messages: List[BaseMessage]) -> List[dict]:
        """
        将 LangChain 消息格式转换为 OpenAI API 格式

        Args:
            messages: LangChain 消息列表

        Returns:
            OpenAI API 格式的消息列表
        """
        converted = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                converted.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                converted.append({"role": "assistant", "content": msg.content})
            elif isinstance(msg, SystemMessage):
                converted.append({"role": "system", "content": msg.content})
            else:
                # 默认当作 user 消息
                converted.append({"role": "user", "content": str(msg.content)})
        return converted

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """
        调用本地模型服务生成回复

        这是必须实现的核心方法，会被 LangChain 自动调用。

        Args:
            messages: 对话历史消息
            stop: 停止词列表
            run_manager: 回调管理器（Phoenix 追踪会用到这里）
            **kwargs: 额外参数

        Returns:
            ChatResult: 包含生成结果的对象
        """
        # 转换消息格式
        api_messages = self._convert_messages(messages)

        # 构建请求体
        payload = {
            "model": self.model_name,
            "messages": api_messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": False,  # 非流式请求
        }

        # 添加 stop 参数（如果有）
        if stop:
            payload["stop"] = stop

        # 构建请求头
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            # 发送请求到本地服务
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()

            # 解析响应
            result = response.json()

            # 提取生成的文本
            # 注意：不同服务的响应格式可能略有不同，这里以 OpenAI 格式为例
            generated_text = result["choices"][0]["message"]["content"]

            # 创建 LangChain 消息对象
            message = AIMessage(content=generated_text)

            # 构建 ChatGeneration
            generation = ChatGeneration(
                message=message,
                generation_info={
                    "finish_reason": result["choices"][0].get("finish_reason"),
                    "model": result.get("model"),
                    "usage": result.get("usage", {}),
                },
            )

            # 返回 ChatResult
            return ChatResult(generations=[generation], llm_output=result)

        except requests.exceptions.ConnectionError:
            raise RuntimeError(
                f"无法连接到本地模型服务: {self.api_url}\n"
                "请确认服务已启动，例如运行:\n"
                "  vllm: python -m vllm.entrypoints.openai.api_server --model ...\n"
                "  ollama: ollama serve"
            )
        except requests.exceptions.Timeout:
            raise RuntimeError(f"请求超时（{self.timeout}秒）")
        except KeyError as e:
            raise RuntimeError(f"响应格式错误，缺少字段: {e}")
        except Exception as e:
            raise RuntimeError(f"调用本地模型失败: {e}")

    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """
        异步调用本地模型服务（可选实现）

        如果不实现，LangChain 会自动使用 _generate 的同步版本
        """
        import aiohttp

        api_messages = self._convert_messages(messages)
        payload = {
            "model": self.model_name,
            "messages": api_messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": False,
        }
        if stop:
            payload["stop"] = stop

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=self.timeout),
            ) as response:
                response.raise_for_status()
                result = await response.json()

                generated_text = result["choices"][0]["message"]["content"]
                message = AIMessage(content=generated_text)
                generation = ChatGeneration(
                    message=message,
                    generation_info={
                        "finish_reason": result["choices"][0].get("finish_reason"),
                        "model": result.get("model"),
                        "usage": result.get("usage", {}),
                    },
                )
                return ChatResult(generations=[generation], llm_output=result)


# =============================================================================
# 1. 配置 Phoenix 监控 (仅本地模式)
# =============================================================================


def setup_phoenix_tracing():
    """
    配置 Phoenix 本地追踪系统

    本地 Phoenix: 启动本地服务器，访问 http://localhost:6006
    """
    from openinference.instrumentation.langchain import LangChainInstrumentor
    from openinference.instrumentation.openai import OpenAIInstrumentor
    from phoenix.otel import register

    print("📊 配置本地 Phoenix 追踪...")

    # 注册 OpenTelemetry tracer provider
    tracer_provider = register(
        project_name="deepagents-demo",
    )

    # 自动为 LangChain 和 OpenAI 启用追踪
    LangChainInstrumentor().instrument(tracer_provider=tracer_provider)
    OpenAIInstrumentor().instrument(tracer_provider=tracer_provider)

    print("✅ Phoenix 追踪已启用")
    return tracer_provider


# =============================================================================
# 2. 创建带监控的 DeepAgent (支持 GLM-5 或本地 LLM)
# =============================================================================


def create_monitored_agent():
    """
    创建一个带有 Phoenix 监控的 DeepAgent

    根据 USE_LOCAL_LLM 环境变量选择使用：
    - True: 本地 LLM 服务 (LocalLLM)
    - False: GLM-5 (智谱云 API)

    所有节点调用（planning, execution, observation, final_answer 等）
    都会被自动追踪并在 Phoenix UI 中可视化
    """
    from deepagents import create_deep_agent
    from deepagents.backends import FilesystemBackend
    from langchain_core.tools import Tool
    from langchain_openai import ChatOpenAI
    from langgraph.store.memory import InMemoryStore

    if USE_LOCAL_LLM:
        # 使用本地 LLM 服务
        print("🤖 使用本地 LLM 服务")
        print(f"   API URL: {LOCAL_LLM_CONFIG['api_url']}")
        print(f"   模型名称: {LOCAL_LLM_CONFIG['model_name']}")

        llm = LocalLLM(
            api_url=LOCAL_LLM_CONFIG["api_url"],
            model_name=LOCAL_LLM_CONFIG["model_name"],
            temperature=LOCAL_LLM_CONFIG["temperature"],
            max_tokens=LOCAL_LLM_CONFIG["max_tokens"],
        )
    else:
        # 使用 GLM-5 (智谱云 API)
        api_key = os.getenv("GLM_API_KEY")
        if not api_key:
            raise RuntimeError("GLM_API_KEY is missing. Please set it in .env")

        # 设置 OpenAI API Key (GLM API 兼容 OpenAI 格式)
        os.environ["OPENAI_API_KEY"] = api_key

        # 配置 LLM - 使用 GLM-5
        model_name = os.getenv("Z_MODEL", "glm-5")

        llm = ChatOpenAI(
            model=model_name,
            base_url="https://open.bigmodel.cn/api/paas/v4",
            temperature=0.1,
        )

        print(f"🤖 使用 GLM-5 模型: {model_name}")

    # 定义示例工具
    def search_knowledge(query: str) -> str:
        """搜索知识库"""
        return f"找到关于 '{query}' 的信息: 这是一个示例搜索结果。"

    def calculate(expression: str) -> str:
        """计算数学表达式"""
        try:
            # 安全计算
            allowed_chars = set("0123456789+-*/.() ")
            if not all(c in allowed_chars for c in expression):
                return "表达式包含非法字符"
            result = eval(expression)
            return f"计算结果: {result}"
        except Exception as e:
            return f"计算失败: {e}"

    def get_current_time(_input: str = "") -> str:
        """获取当前时间（_input 参数由 LangChain 工具调用传入，但不使用）"""
        """获取当前时间"""
        from datetime import datetime

        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 创建工具列表
    tools = [
        Tool(
            name="search_knowledge",
            func=search_knowledge,
            description="搜索知识库获取信息。输入: 搜索关键词",
        ),
        Tool(
            name="calculate",
            func=calculate,
            description="计算数学表达式。输入: 数学表达式如 '2 + 3 * 4'",
        ),
        Tool(
            name="get_current_time", func=get_current_time, description="获取当前时间"
        ),
    ]

    # 创建本地 backend
    project_root = Path(__file__).resolve().parent
    backend = FilesystemBackend(root_dir=str(project_root))

    # 创建 DeepAgent - 使用与 main.py 相同的参数结构
    agent = create_deep_agent(
        model=llm,
        store=InMemoryStore(),
        backend=backend,
        tools=tools,
        system_prompt="""你是一个智能助手，可以帮助用户完成各种任务。

你可以使用以下工具:
1. search_knowledge: 搜索知识库
2. calculate: 计算数学表达式  
3. get_current_time: 获取当前时间

请根据用户的需求选择合适的工具，并以友好、专业的方式回复。""",
    )

    return agent, tools


# =============================================================================
# 3. 运行示例任务
# =============================================================================


def run_demo_tasks(agent):
    """
    运行一些示例任务来演示 Phoenix 监控

    每个任务都会在 Phoenix UI 中显示为一条 trace，
    包含完整的节点执行流程
    """
    print("\n" + "=" * 60)
    print("🚀 开始运行监控演示任务")
    print("=" * 60)

    demo_tasks = [
        {
            "name": "多步推理任务",
            "query": "先搜索 'Python 编程' 的相关知识，然后计算 100 除以 4 的结果，最后告诉我现在几点了",
        },
        {
            "name": "工具组合任务",
            "query": "计算 (25 * 4) + (100 / 5) 的结果，并搜索 '机器学习' 的相关信息",
        },
        {
            "name": "知识查询任务",
            "query": "搜索 'LangChain' 和 'DeepAgents' 的相关信息",
        },
    ]

    for i, task in enumerate(demo_tasks, 1):
        print(f"\n{'─'*60}")
        print(f"📋 任务 {i}/{len(demo_tasks)}: {task['name']}")
        print(f"📝 输入: {task['query']}")
        print("─" * 60)

        try:
            # 运行 agent - 所有步骤都会被 Phoenix 追踪
            result = agent.invoke(
                {"messages": [{"role": "user", "content": task["query"]}]}
            )

            # 提取助手回复
            assistant_text = ""
            for msg in reversed(result.get("messages", [])):
                if hasattr(msg, "type") and msg.type == "ai":
                    assistant_text = str(getattr(msg, "content", ""))
                    break
                elif isinstance(msg, dict) and msg.get("type") == "ai":
                    assistant_text = str(msg.get("content", ""))
                    break

            print(f"✅ 完成!")
            print(
                f"💬 输出: {assistant_text[:200]}..."
                if len(assistant_text) > 200
                else f"💬 输出: {assistant_text}"
            )

        except Exception as e:
            print(f"❌ 错误: {e}")
            import traceback

            traceback.print_exc()

    print(f"\n{'='*60}")
    print("🎉 所有演示任务已完成!")
    print("=" * 60)


# =============================================================================
# 4. 启动本地 Phoenix UI
# =============================================================================


def launch_phoenix_ui():
    """
    启动本地 Phoenix UI 服务器

    使用官方推荐的 phoenix.launch_app() 方法启动，
    而不是直接通过 subprocess 启动模块。
    """
    import phoenix as px

    print("🌐 正在启动 Phoenix UI...")

    try:
        # 使用官方推荐的 API 启动 Phoenix
        # 这会自动处理：
        # - 端口检测和冲突处理
        # - 数据库初始化 (SQLite)
        # - gRPC 追踪接收器 (:4317)
        # - Web UI 服务 (:6006)
        session = px.launch_app()

        print(f"✅ Phoenix UI 已启动!")
        print(f"   访问: {session.url}")
        print(f"   点击 'Traces' 标签页查看 agent 调用追踪\n")

        return session

    except Exception as e:
        error_msg = str(e)

        # 检查是否是端口占用错误
        if "address already in use" in error_msg.lower() or "port" in error_msg.lower():
            print("⚠️  端口 6006 已被占用，检查是否为已运行的 Phoenix 服务...")
            try:
                import urllib.request

                urllib.request.urlopen("http://127.0.0.1:6006", timeout=2)
                print("✅ 检测到 Phoenix 已在运行，将复用现有服务")
                print("   访问: http://localhost:6006\n")
                return None
            except:
                print("❌ 端口 6006 被其他程序占用，请关闭后重试")
                print(f"   错误信息: {error_msg}")
                sys.exit(1)

        # 其他错误
        print(f"❌ 启动 Phoenix 失败: {e}")
        print("\n可能的原因:")
        print("  1. 依赖未正确安装: uv sync")
        print("  2. 请确认已安装 phoenix: pip install arize-phoenix")
        print("\n尝试手动启动查看详细错误:")
        print('   python -c "import phoenix as px; px.launch_app()"')
        sys.exit(1)


# =============================================================================
# 5. 主函数
# =============================================================================


def main():
    """
    主函数：设置 Phoenix 监控并运行 DeepAgent 演示
    """
    print("=" * 60)
    print("🔍 Phoenix + DeepAgents Agent 监控 Demo")
    print("=" * 60)

    # 检查必要的环境变量
    if USE_LOCAL_LLM:
        print("\n📍 当前模式: 本地 LLM 服务")
        print(f"   服务地址: {LOCAL_LLM_CONFIG['api_url']}")
    else:
        print("\n📍 当前模式: GLM-5 (智谱云)")
        if not os.getenv("GLM_API_KEY"):
            print("\n⚠️  错误: GLM_API_KEY 未设置")
            print("   请在 .env 文件中添加: GLM_API_KEY=your_key_here")
            print("   或运行: export GLM_API_KEY=your_key_here")
            print("\n   如需使用本地 LLM，请设置: USE_LOCAL_LLM=true")
            sys.exit(1)

    phoenix_session = None

    try:
        # 步骤 1: 启动本地 Phoenix UI
        phoenix_session = launch_phoenix_ui()

        # 步骤 2: 设置 Phoenix 追踪
        tracer_provider = setup_phoenix_tracing()

        # 步骤 3: 创建监控的 agent
        agent, tools = create_monitored_agent()

        # 步骤 4: 运行演示任务
        run_demo_tasks(agent)

        print("\n" + "=" * 60)
        print("📊 监控数据查看方式:")
        print("=" * 60)
        print("1. 打开浏览器访问: http://localhost:6006")
        print("2. 点击 'Traces' 标签页")
        print("3. 查看 agent 执行的每一步详情:")
        print("   - 输入/输出")
        print("   - 工具调用")
        print("   - LLM 调用详情")
        print("   - 执行时间线")

        print("\n按 Ctrl+C 停止程序...")

        # 保持程序运行
        import signal

        signal.pause()

    except KeyboardInterrupt:
        print("\n\n👋 程序已停止")

    finally:
        # 清理资源
        if phoenix_session:
            import phoenix as px

            px.close_app()
            print("✅ Phoenix 服务器已关闭")


if __name__ == "__main__":
    main()
