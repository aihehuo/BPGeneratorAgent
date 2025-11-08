"""
Qwen LLM实现
使用Qwen API进行文本生成
"""

import os
from typing import Optional, Dict, Any
from openai import OpenAI
from .base import BaseLLM


class QwenLLM(BaseLLM):
    """Qwen LLM实现类"""
    
    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        """
        初始化Qwen客户端
        
        Args:
            api_key: Qwen API密钥，如果不提供则从环境变量读取
            model_name: 模型名称，默认使用qwen-turbo
        """
        if api_key is None:
            api_key = os.getenv("QWEN_API_KEY")
            if not api_key:
                raise ValueError("Qwen API Key未找到！请设置QWEN_API_KEY环境变量或在初始化时提供")
        
        super().__init__(api_key, model_name)
        
        # 初始化OpenAI客户端，使用Qwen的endpoint
        # OpenAI client appends /chat/completions to base_url
        # Since base_url already has a path (/compatible-mode), we need to include /v1
        # So base_url should be: https://dashscope.aliyuncs.com/compatible-mode/v1
        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        
        self.default_model = model_name or self.get_default_model()
    
    def get_default_model(self) -> str:
        """获取默认模型名称"""
        return "qwen-turbo"
    
    def invoke(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        """
        调用Qwen API生成回复
        
        Args:
            system_prompt: 系统提示词
            user_prompt: 用户输入
            **kwargs: 其他参数，如temperature、max_tokens等
            
        Returns:
            Qwen生成的回复文本
        """
        try:
            # 构建消息
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            # 设置默认参数
            params = {
                "model": self.default_model,
                "messages": messages,
                "temperature": kwargs.get("temperature", 0.7),
                "max_tokens": kwargs.get("max_tokens", 4000),
                "stream": False
            }
            
            # 调用API
            response = self.client.chat.completions.create(**params)
            
            # 提取回复内容
            if response.choices and response.choices[0].message:
                content = response.choices[0].message.content
                return self.validate_response(content)
            else:
                return ""
                
        except Exception as e:
            error_msg = str(e)
            # Try to extract more details from the error
            if hasattr(e, 'response') and hasattr(e.response, 'request'):
                if hasattr(e.response.request, 'url'):
                    print(f"Qwen API调用URL: {e.response.request.url}")
            print(f"Qwen API调用错误: {error_msg}")
            # If it's a 404, provide helpful debugging info
            if "404" in error_msg or "Not Found" in error_msg:
                print(f"调试信息: base_url={self.client.base_url}, model={self.default_model}")
                print(f"预期URL应该是: https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions")
                print(f"提示: 如果base_url不包含/v1，OpenAI客户端可能不会自动添加/v1路径")
            raise e
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        获取当前模型信息
        
        Returns:
            模型信息字典
        """
        return {
            "provider": "Qwen",
            "model": self.default_model,
            "api_base": "https://dashscope.aliyuncs.com/compatible-mode/v1"
        }

