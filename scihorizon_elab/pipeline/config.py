"""
scihorizon_elab Agent 统一配置模块

集中管理 LLM API 配置,修改此文件即可全局生效。

所有配置通过环境变量控制(支持 .env 文件),仓库内不包含任何密钥,且不预设任何模型:
    LLM_API_KEY           API Key(必填)
    LLM_BASE_URL          OpenAI 兼容端点(可选,留空则用 openai SDK 默认端点)
    LLM_MODEL_NAME        文本模型(必填)
    LLM_VISION_MODEL_NAME 视觉模型(reviewer 审核视频帧时需要)
"""

import os
from typing import Optional

try:
    from dotenv import load_dotenv
except ImportError:  # python-dotenv 未安装时跳过,仅依赖真实环境变量
    load_dotenv = None

# 加载 .env(已存在的环境变量优先;先找项目根,再找当前工作目录)
if load_dotenv is not None:
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
    load_dotenv()


class AgentConfig:
    """
    Agent 配置类

    通过环境变量配置 Agent 的行为,支持任何 OpenAI 兼容 API
    """

    # ==================== LLM 模型配置 ====================

    # 文本模型名称(无默认值,由使用者按所选 API 自行配置)
    MODEL_NAME: str = os.getenv("LLM_MODEL_NAME", "")

    # 视觉模型名称(无默认值,由使用者按所选 API 自行配置)
    VISION_MODEL_NAME: str = os.getenv("LLM_VISION_MODEL_NAME", "")

    # 温度参数 (0-1 控制输出随机性, 0=确定性, 1=创造性)
    TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.7"))

    # 最大输出 token 数
    MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "4096"))

    # 请求超时时间 (秒)
    TIMEOUT: float = float(os.getenv("LLM_TIMEOUT", "300.0"))

    # 失败重试次数
    MAX_RETRIES: int = int(os.getenv("LLM_MAX_RETRIES", "2"))

    # ==================== API 配置 ====================

    # API Key(从环境变量读取,仓库内零密钥)
    API_KEY: Optional[str] = os.getenv("LLM_API_KEY")

    # OpenAI 兼容端点(无默认值;留空时使用 openai SDK 默认端点)
    BASE_URL: Optional[str] = os.getenv("LLM_BASE_URL")

    # ==================== 其他配置 ====================

    # 是否启用调试模式
    DEBUG: bool = os.getenv("LLM_DEBUG", "0") == "1"

    # ==================== 工厂方法 ====================

    @classmethod
    def create_llm(cls, vision: bool = False):
        """
        统一 LLM 工厂,返回配置好的 ChatOpenAI 实例

        Args:
            vision: True 使用视觉模型(qwen-vl-max),False 使用文本模型(qwen-plus)

        Returns:
            langchain_openai.ChatOpenAI 实例

        Raises:
            RuntimeError: 必填项未设置时抛出
        """
        if not cls.API_KEY:
            raise RuntimeError(
                "LLM_API_KEY 未设置,请设置环境变量或在 .env 文件中配置"
            )

        model = cls.VISION_MODEL_NAME if vision else cls.MODEL_NAME
        if not model:
            env_var = "LLM_VISION_MODEL_NAME" if vision else "LLM_MODEL_NAME"
            raise RuntimeError(
                f"{env_var} 未设置,请设置环境变量或在 .env 文件中配置"
            )

        from langchain_openai import ChatOpenAI

        kwargs = dict(
            model=model,
            api_key=cls.API_KEY,
            temperature=cls.TEMPERATURE,
            max_tokens=cls.MAX_TOKENS,
            timeout=cls.TIMEOUT,
            max_retries=cls.MAX_RETRIES,
        )
        # 端点留空时交给 openai SDK 默认行为
        if cls.BASE_URL:
            kwargs["base_url"] = cls.BASE_URL

        return ChatOpenAI(**kwargs)

    @classmethod
    def validate(cls) -> tuple[bool, str]:
        """
        验证配置是否正确

        Returns:
            (是否有效, 错误信息)
        """
        if not cls.API_KEY:
            return False, "LLM_API_KEY 未设置,请设置环境变量或在 .env 文件中配置"

        if len(cls.API_KEY) < 10:
            return False, "LLM_API_KEY 格式不正确"

        if not cls.MODEL_NAME:
            return False, "LLM_MODEL_NAME 未设置,请设置环境变量或在 .env 文件中配置"

        return True, ""


if __name__ == "__main__":
    import sys

    is_valid, error_msg = AgentConfig.validate()
    if is_valid:
        print("配置有效")
        print(f"  文本模型: {AgentConfig.MODEL_NAME}")
        if AgentConfig.VISION_MODEL_NAME:
            print(f"  视觉模型: {AgentConfig.VISION_MODEL_NAME}")
        else:
            print("  视觉模型: 未设置(reviewer 视频审核将不可用)")
        print(f"  端点: {AgentConfig.BASE_URL or '(openai SDK 默认端点)'}")
        sys.exit(0)
    else:
        print(f"配置错误: {error_msg}", file=sys.stderr)
        sys.exit(1)
