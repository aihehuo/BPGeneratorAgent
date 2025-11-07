import json
from typing import Dict, Any, List
from json.decoder import JSONDecodeError

from .base_node import StateMutationNode
from ..state.state import State
from ..prompts import SYSTEM_PROMPT_BP_ANALYSIS  # 确保导入BP分析prompt
from ..utils.text_processing import (
    remove_reasoning_from_output,
    clean_json_tags,
    extract_clean_response
)


class BPAnalysisNode(StateMutationNode):
    """BP分析节点 - 调用BP分析prompt"""
    
    def __init__(self, llm_client):
        """
        初始化BP分析节点
        
        Args:
            llm_client: LLM客户端
        """
        super().__init__(llm_client, "BPAnalysisNode")
    
    def validate_input(self, input_data: Any) -> bool:
        """验证输入数据"""
        if isinstance(input_data, str):
            try:
                data = json.loads(input_data)
                required_fields = ["business_plan"]  # 根据BP分析prompt需要的字段调整
                return all(field in data for field in required_fields)
            except JSONDecodeError:
                return False
        elif isinstance(input_data, dict):
            required_fields = ["business_plan"]
            return all(field in input_data for field in required_fields)
        return False
    
    def run(self, input_data: Any = None, **kwargs) -> Dict[str, Any]:
        """
        调用LLM执行BP分析
        
        Args:
            input_data: 包含business_plan的数据
            **kwargs: 额外参数
            
        Returns:
            BP分析结果
        """
        try:
            self.log_info("正在执行BP分析...")
            
            # 调用LLM
            response = self.llm_client.invoke(SYSTEM_PROMPT_BP_ANALYSIS, input_data)
            
            # 处理响应
            processed_response = self.process_output(response)
            
            self.log_info("BP分析完成")
            return processed_response
            
        except Exception as e:
            self.log_error(f"BP分析失败: {str(e)}")
            raise e
    
    def process_output(self, output: str) -> Dict[str, Any]:
        """
        处理LLM输出，提取BP分析结果
        
        Args:
            output: LLM原始输出
            
        Returns:
            处理后的BP分析结果
        """
        try:
            # 清理响应文本
            cleaned_output = remove_reasoning_from_output(output)
            cleaned_output = clean_json_tags(cleaned_output)
            
            # 解析JSON
            try:
                bp_analysis_result = json.loads(cleaned_output)
            except JSONDecodeError:
                # 使用更强大的提取方法
                bp_analysis_result = extract_clean_response(cleaned_output)
                if not isinstance(bp_analysis_result, dict):
                    raise ValueError("BP分析结果格式错误")
            
            return bp_analysis_result
            
        except Exception as e:
            self.log_error(f"处理输出失败: {str(e)}")
            raise e
    
    def mutate_state(self, input_data: Any, state: State, **kwargs) -> State:
        """
        将BP分析结果更新到状态
        
        Args:
            input_data: 输入数据
            state: 当前状态
            **kwargs: 额外参数
            
        Returns:
            更新后的状态
        """
        try:
            # 执行BP分析
            bp_analysis_result = self.run(input_data, **kwargs)
            
            # 更新状态
            state.bp_analysis = {
                "result": bp_analysis_result,
                "timestamp": kwargs.get("timestamp", None)
            }
            
            self.log_info("已将BP分析结果更新到状态")
            state.update_timestamp()
            return state
            
        except Exception as e:
            self.log_error(f"状态更新失败: {str(e)}")
            raise e