"""
LLM调用模块
支持多种大语言模型的统一接口
"""

from .base import BaseLLM
from .deepseek import DeepSeekLLM
from .openai_llm import OpenAILLM
from .qwen import QwenLLM

__all__ = ["BaseLLM", "DeepSeekLLM", "OpenAILLM", "QwenLLM"]
