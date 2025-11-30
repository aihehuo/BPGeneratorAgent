import json
from typing import Dict, Any, List
from json.decoder import JSONDecodeError

from .base_node import StateMutationNode
from ..state.state import State
from ..prompts.bp_completion_guide import SYSTEM_PROMPT_BP_COMPLETION_GUIDE  # 确保导入BP完整性引导prompt
from ..utils.text_processing import (
    remove_reasoning_from_output,
    clean_json_tags,
    extract_clean_response
)


class BPCompletionGuideNode(StateMutationNode):
    """BP完整性引导节点 - 调用BP完整性引导prompt"""
    
    def __init__(self, llm_client):
        """
        初始化BP完整性引导节点
        
        Args:
            llm_client: LLM客户端
        """
        super().__init__(llm_client, "BPCompletionGuideNode")
    
    def validate_input(self, input_data: Any) -> bool:
        """
        验证输入数据是否符合要求
        
        Args:
            input_data: 输入数据
            
        Returns:
            bool: 验证结果
        """
        if isinstance(input_data, str):
            return True  # 接受任何字符串输入
        elif isinstance(input_data, dict):
            # 检查是否包含raw_text字段
            return "raw_text" in input_data and isinstance(input_data["raw_text"], str)
        return False
    
    def run(self, input_data: Any = None, **kwargs) -> Dict[str, Any]:
        """
        调用LLM执行BP完整性引导
        
        Args:
            input_data: 包含raw_text的数据
            **kwargs: 额外参数
            
        Returns:
            Dict[str, Any]: BP完整性引导结果
        """
        try:
            self.log_info("正在执行BP完整性引导...")
            
            # 准备输入数据
            if isinstance(input_data, dict) and "raw_text" in input_data:
                formatted_input = input_data["raw_text"]
            else:
                formatted_input = str(input_data)
            
            # 调用LLM
            response = self.llm_client.invoke(SYSTEM_PROMPT_BP_COMPLETION_GUIDE, formatted_input)
            
            # 处理响应
            processed_response = self.process_output(response)
            
            self.log_info("BP完整性引导完成")
            return processed_response
            
        except Exception as e:
            self.log_error(f"BP完整性引导失败: {str(e)}")
            raise e
    
    def process_output(self, output: str) -> Dict[str, Any]:
        """
        处理LLM输出，提取BP完整性引导结果
        
        Args:
            output: LLM原始输出
            
        Returns:
            Dict[str, Any]: 处理后的BP完整性引导结果
        """
        try:
            # 清理响应文本
            cleaned_output = remove_reasoning_from_output(output)
            cleaned_output = clean_json_tags(cleaned_output)
            
            # 解析JSON
            try:
                bp_completion_result = json.loads(cleaned_output)
            except JSONDecodeError:
                # 使用更强大的提取方法
                bp_completion_result = extract_clean_response(cleaned_output)
                if not isinstance(bp_completion_result, dict):
                    raise ValueError("BP完整性引导结果格式错误")
            
            return bp_completion_result
            
        except Exception as e:
            self.log_error(f"处理输出失败: {str(e)}")
            raise e
    
    def mutate_state(self, input_data: Any, state: State, **kwargs) -> State:
        """
        将BP完整性引导结果更新到状态
        
        Args:
            input_data: 输入数据
            state: 当前状态
            **kwargs: 额外参数
            
        Returns:
            State: 更新后的状态
        """
        try:
            # 执行BP完整性引导
            bp_completion_result = self.run(input_data, **kwargs)
            
            # 更新状态
            state.bp_completion_guide = {
                "result": bp_completion_result,
                "timestamp": kwargs.get("timestamp", None)
            }
            
            self.log_info("已将BP完整性引导结果更新到状态")
            state.update_timestamp()
            return state
            
        except Exception as e:
            self.log_error(f"状态更新失败: {str(e)}")
            raise e