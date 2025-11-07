"""
本地LLM实现
使用本地API进行文本生成
"""

import requests
from typing import Optional, Dict, Any
from .base import BaseLLM


class LocalLLM(BaseLLM):
    """本地LLM实现类"""
    
    def __init__(self, model_name: Optional[str] = None):
        """
        初始化本地LLM客户端
        
        Args:
            model_name: 模型名称，默认使用gemma3:4b
        """
        super().__init__(None, model_name)  # 使用None作为API密钥
        
        # 设置默认模型
        self.default_model = model_name or self.get_default_model()
    
    def get_default_model(self) -> str:
        """获取默认模型名称"""
        return "gemma3:4b"
    
    def invoke(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        """
        调用本地LLM API生成回复
        
        Args:
            system_prompt: 系统提示词
            user_prompt: 用户输入
            **kwargs: 其他参数，如temperature、max_tokens等
            
        Returns:
            本地LLM生成的回复文本
        """
        try:
            # 构建消息
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            # 设置请求参数
            params = {
                "model": self.default_model,
                "messages": messages,
                "temperature": kwargs.get("temperature", 0.7),
                "max_tokens": kwargs.get("max_tokens", 4000),
                "stream": False
            }
            
            # 发送请求到本地API
            response = requests.post(
                "http://localhost:11434/api/chat",
                json=params
            )
            
            # 检查请求是否成功
            if response.status_code != 200:
                raise ConnectionError(f"本地API连接失败: {response.status_code}")
            
            # 解析响应
            response_data = response.json()
            
            # 提取回复内容
            if response_data.get("response"):
                return response_data["response"]
            else:
                return ""
                
        except Exception as e:
            print(f"本地LLM API调用错误: {str(e)}")
            raise e
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        获取当前模型信息
        
        Returns:
            模型信息字典
        """
        return {
            "provider": "本地",
            "model": self.default_model,
            "api_base": "http://localhost:11434/api"
        }

    def validate_response(self, response: str) -> str:
        """
        验证响应内容
        
        Args:
            response: 原始响应内容
            
        Returns:
            验证后的响应内容
        """
        return response