"""
配置管理模块
处理环境变量和配置参数
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class Config:
    """配置类"""
    # API密钥
    deepseek_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    qwen_api_key: Optional[str] = None
    tavily_api_key: Optional[str] = None
    aihehuo_api_key: Optional[str] = None
    aihehuo_api_base: Optional[str] = None
    
    # 模型配置
    default_llm_provider: str = "deepseek"  # deepseek, openai, 或 qwen
    deepseek_model: str = "deepseek-chat"
    openai_model: str = "gpt-4o-mini"
    qwen_model: str = "qwen-turbo"
    
    # 搜索配置
    max_search_results: int = 3
    search_timeout: int = 240
    max_content_length: int = 20000
    
    # Agent配置
    max_reflections: int = 2
    max_paragraphs: int = 5
    
    # 输出配置
    output_dir: str = "reports"
    save_intermediate_states: bool = True
    
    def validate(self) -> bool:
        """验证配置"""
        # 检查必需的API密钥
        if self.default_llm_provider == "deepseek" and not self.deepseek_api_key:
            print("错误: DeepSeek API Key未设置")
            return False
        
        if self.default_llm_provider == "openai" and not self.openai_api_key:
            print("错误: OpenAI API Key未设置")
            return False
        
        if self.default_llm_provider == "qwen" and not self.qwen_api_key:
            print("错误: Qwen API Key未设置")
            return False
        
        if not self.tavily_api_key:
            print("错误: Tavily API Key未设置")
            return False
        
        return True
    
    @classmethod
    def from_file(cls, config_file: str) -> "Config":
        """从配置文件创建配置"""
        if config_file.endswith('.py'):
            # Python配置文件
            import importlib.util
            
            # 动态导入配置文件
            spec = importlib.util.spec_from_file_location("config", config_file)
            config_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(config_module)
            
            return cls(
                deepseek_api_key=getattr(config_module, "DEEPSEEK_API_KEY", None),
                openai_api_key=getattr(config_module, "OPENAI_API_KEY", None),
                qwen_api_key=getattr(config_module, "QWEN_API_KEY", None),
                tavily_api_key=getattr(config_module, "TAVILY_API_KEY", None),
                aihehuo_api_key=getattr(config_module, "AIHEHUO_API_KEY", None),
                aihehuo_api_base=getattr(config_module, "AIHEHUO_API_BASE", None),
                default_llm_provider=getattr(config_module, "DEFAULT_LLM_PROVIDER", "deepseek"),
                deepseek_model=getattr(config_module, "DEEPSEEK_MODEL", "deepseek-chat"),
                openai_model=getattr(config_module, "OPENAI_MODEL", "gpt-4o-mini"),
                qwen_model=getattr(config_module, "QWEN_MODEL", "qwen-turbo"),
                max_search_results=getattr(config_module, "SEARCH_RESULTS_PER_QUERY", 3),
                search_timeout=getattr(config_module, "SEARCH_TIMEOUT", 240),
                max_content_length=getattr(config_module, "SEARCH_CONTENT_MAX_LENGTH", 20000),
                max_reflections=getattr(config_module, "MAX_REFLECTIONS", 2),
                max_paragraphs=getattr(config_module, "MAX_PARAGRAPHS", 5),
                output_dir=getattr(config_module, "OUTPUT_DIR", "reports"),
                save_intermediate_states=getattr(config_module, "SAVE_INTERMEDIATE_STATES", True)
            )
        else:
            # .env格式配置文件
            config_dict = {}
            
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            config_dict[key.strip()] = value.strip()
            
            return cls(
                deepseek_api_key=config_dict.get("DEEPSEEK_API_KEY"),
                openai_api_key=config_dict.get("OPENAI_API_KEY"),
                qwen_api_key=config_dict.get("QWEN_API_KEY"),
                tavily_api_key=config_dict.get("TAVILY_API_KEY"),
                aihehuo_api_key=config_dict.get("AIHEHUO_API_KEY"),
                aihehuo_api_base=config_dict.get("AIHEHUO_API_BASE"),
                default_llm_provider=config_dict.get("DEFAULT_LLM_PROVIDER", "deepseek"),
                deepseek_model=config_dict.get("DEEPSEEK_MODEL", "deepseek-chat"),
                openai_model=config_dict.get("OPENAI_MODEL", "gpt-4o-mini"),
                qwen_model=config_dict.get("QWEN_MODEL", "qwen-turbo"),
                max_search_results=int(config_dict.get("SEARCH_RESULTS_PER_QUERY", "3")),
                search_timeout=int(config_dict.get("SEARCH_TIMEOUT", "240")),
                max_content_length=int(config_dict.get("SEARCH_CONTENT_MAX_LENGTH", "20000")),
                max_reflections=int(config_dict.get("MAX_REFLECTIONS", "2")),
                max_paragraphs=int(config_dict.get("MAX_PARAGRAPHS", "5")),
                output_dir=config_dict.get("OUTPUT_DIR", "reports"),
                save_intermediate_states=config_dict.get("SAVE_INTERMEDIATE_STATES", "true").lower() == "true"
            )


def load_config(config_file: Optional[str] = None) -> Config:
    """
    加载配置
    优先级：环境变量 > 配置文件
    
    Args:
        config_file: 配置文件路径，如果不指定则使用默认路径
        
    Returns:
        配置对象
    """
    # 首先检查环境变量中是否有API密钥配置（Docker友好）
    # 去除空字符串和None值
    env_keys = [
        os.getenv("DEEPSEEK_API_KEY"),
        os.getenv("OPENAI_API_KEY"),
        os.getenv("QWEN_API_KEY"),
        os.getenv("TAVILY_API_KEY")
    ]
    has_env_api_keys = any(key and key.strip() for key in env_keys)
    
    # Debug: 打印环境变量状态（仅显示是否设置，不显示值）
    if has_env_api_keys:
        print(f"[DEBUG] 检测到环境变量中的API密钥")
    else:
        print(f"[DEBUG] 未检测到环境变量中的API密钥，将尝试从配置文件加载")
    
    # 如果环境变量中有API密钥，优先使用环境变量
    if has_env_api_keys:
        print("从环境变量加载配置")
        config = Config(
            deepseek_api_key=os.getenv("DEEPSEEK_API_KEY"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            qwen_api_key=os.getenv("QWEN_API_KEY"),
            tavily_api_key=os.getenv("TAVILY_API_KEY"),
            aihehuo_api_key=os.getenv("AIHEHUO_API_KEY"),
            aihehuo_api_base=os.getenv("AIHEHUO_API_BASE"),
            default_llm_provider=os.getenv("DEFAULT_LLM_PROVIDER", "deepseek"),
            deepseek_model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            qwen_model=os.getenv("QWEN_MODEL", "qwen-turbo"),
            max_search_results=int(os.getenv("MAX_SEARCH_RESULTS", os.getenv("SEARCH_RESULTS_PER_QUERY", "3"))),
            search_timeout=int(os.getenv("SEARCH_TIMEOUT", "240")),
            max_content_length=int(os.getenv("MAX_CONTENT_LENGTH", os.getenv("SEARCH_CONTENT_MAX_LENGTH", "20000"))),
            max_reflections=int(os.getenv("MAX_REFLECTIONS", "2")),
            max_paragraphs=int(os.getenv("MAX_PARAGRAPHS", "5")),
            output_dir=os.getenv("OUTPUT_DIR", "reports"),
            save_intermediate_states=os.getenv("SAVE_INTERMEDIATE_STATES", "true").lower() == "true"
        )
    else:
        # 从配置文件加载
        if config_file:
            if not os.path.exists(config_file):
                raise FileNotFoundError(f"配置文件不存在: {config_file}")
            file_to_load = config_file
        else:
            # 尝试加载常见的配置文件
            for config_path in ["config.py", "config.env", ".env"]:
                if os.path.exists(config_path):
                    file_to_load = config_path
                    print(f"已找到配置文件: {config_path}")
                    break
            else:
                raise FileNotFoundError("未找到配置文件，请创建 config.py 文件或设置环境变量（DEEPSEEK_API_KEY, OPENAI_API_KEY, QWEN_API_KEY, TAVILY_API_KEY等）")
        
        # 创建配置对象
        config = Config.from_file(file_to_load)
        
        # 环境变量覆盖配置文件中的值（允许部分配置通过环境变量覆盖）
        if os.getenv("DEEPSEEK_API_KEY"):
            config.deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
        if os.getenv("OPENAI_API_KEY"):
            config.openai_api_key = os.getenv("OPENAI_API_KEY")
        if os.getenv("QWEN_API_KEY"):
            config.qwen_api_key = os.getenv("QWEN_API_KEY")
        if os.getenv("TAVILY_API_KEY"):
            config.tavily_api_key = os.getenv("TAVILY_API_KEY")
        if os.getenv("AIHEHUO_API_KEY"):
            config.aihehuo_api_key = os.getenv("AIHEHUO_API_KEY")
        if os.getenv("AIHEHUO_API_BASE"):
            config.aihehuo_api_base = os.getenv("AIHEHUO_API_BASE")
        if os.getenv("DEFAULT_LLM_PROVIDER"):
            config.default_llm_provider = os.getenv("DEFAULT_LLM_PROVIDER")
        if os.getenv("OUTPUT_DIR"):
            config.output_dir = os.getenv("OUTPUT_DIR")
    
    # 验证配置
    if not config.validate():
        raise ValueError("配置验证失败，请检查配置文件中的API密钥或环境变量")
    
    return config


def print_config(config: Config):
    """打印配置信息（隐藏敏感信息）"""
    print("\n=== 当前配置 ===")
    print(f"LLM提供商: {config.default_llm_provider}")
    print(f"DeepSeek模型: {config.deepseek_model}")
    print(f"OpenAI模型: {config.openai_model}")
    print(f"Qwen模型: {config.qwen_model}")
    print(f"最大搜索结果数: {config.max_search_results}")
    print(f"搜索超时: {config.search_timeout}秒")
    print(f"最大内容长度: {config.max_content_length}")
    print(f"最大反思次数: {config.max_reflections}")
    print(f"最大段落数: {config.max_paragraphs}")
    print(f"输出目录: {config.output_dir}")
    print(f"保存中间状态: {config.save_intermediate_states}")
    
    # 显示API密钥状态（不显示实际密钥）
    print(f"DeepSeek API Key: {'已设置' if config.deepseek_api_key else '未设置'}")
    print(f"OpenAI API Key: {'已设置' if config.openai_api_key else '未设置'}")
    print(f"Qwen API Key: {'已设置' if config.qwen_api_key else '未设置'}")
    print(f"Tavily API Key: {'已设置' if config.tavily_api_key else '未设置'}")
    print(f"AIHehuo API Key: {'已设置' if config.aihehuo_api_key else '未设置'}")
    if config.aihehuo_api_base:
        print(f"AIHehuo API Base: {config.aihehuo_api_base}")
    print("==================\n")
