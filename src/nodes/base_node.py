"""
节点基类
定义所有处理节点的基础接口
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Union
from ..llms.base import BaseLLM
from ..state.state import State

try:
    from langchain_core.language_models.chat_models import BaseChatModel
    from langchain_core.messages import HumanMessage, SystemMessage
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    BaseChatModel = Any
    HumanMessage = Any
    SystemMessage = Any


class BaseNode(ABC):
    """节点基类"""
    
    def __init__(self, llm_client: Union[BaseLLM, BaseChatModel], node_name: str = ""):
        """
        初始化节点
        
        Args:
            llm_client: LLM客户端 (BaseLLM 或 BaseChatModel)
            node_name: 节点名称
        """
        self.llm_client = llm_client
        self.node_name = node_name or self.__class__.__name__
        self.is_langchain_model = LANGCHAIN_AVAILABLE and isinstance(llm_client, BaseChatModel)
    
    def invoke_llm(self, system_prompt: str, user_prompt: str) -> str:
        """
        统一调用LLM的方法
        
        Args:
            system_prompt: 系统提示词
            user_prompt: 用户输入
            
        Returns:
            LLM响应文本
        """
        if self.is_langchain_model:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            response = self.llm_client.invoke(messages)
            return response.content
        else:
            # 假设是传统的 BaseLLM
            return self.llm_client.invoke(system_prompt, user_prompt)
    
    @abstractmethod
    def run(self, input_data: Any, **kwargs) -> Any:

        """
        执行节点处理逻辑
        
        Args:
            input_data: 输入数据
            **kwargs: 额外参数
            
        Returns:
            处理结果
        """
        pass
    
    def validate_input(self, input_data: Any) -> bool:
        """
        验证输入数据
        
        Args:
            input_data: 输入数据
            
        Returns:
            验证是否通过
        """
        return True
    
    def process_output(self, output: Any) -> Any:
        """
        处理输出数据
        
        Args:
            output: 原始输出
            
        Returns:
            处理后的输出
        """
        return output
    
    def log_info(self, message: str):
        """记录信息日志"""
        print(f"[{self.node_name}] {message}")
    
    def log_error(self, message: str):
        """记录错误日志"""
        print(f"[{self.node_name}] 错误: {message}")


class StateMutationNode(BaseNode):
    """带状态修改功能的节点基类"""
    
    @abstractmethod
    def mutate_state(self, input_data: Any, state: State, **kwargs) -> State:
        """
        修改状态
        
        Args:
            input_data: 输入数据
            state: 当前状态
            **kwargs: 额外参数
            
        Returns:
            修改后的状态
        """
        pass
