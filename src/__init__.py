"""
Deep Search Agent
一个无框架的深度搜索AI代理实现
"""

# 延迟导入，避免循环依赖
try:
    from .ds_agent import DeepSearchAgent
except ImportError:
    DeepSearchAgent = None

try:
    from .utils.config import Config, load_config
except ImportError:
    Config = None
    load_config = None

__version__ = "1.0.0"
__author__ = "Deep Search Agent Team"

__all__ = ["DeepSearchAgent", "Config", "load_config"]
