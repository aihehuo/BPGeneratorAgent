"""
BP结构评估节点
负责评估BP结构段落是否与用户商业创意相关
"""

import json
from typing import Dict, Any, List
from json.decoder import JSONDecodeError

from .base_node import BaseNode
from ..prompts import SYSTEM_PROMPT_BP_EVALUATION
from ..utils.text_processing import (
    remove_reasoning_from_output,
    clean_json_tags,
    extract_clean_response
)


class BPEvaluationNode(BaseNode):
    """评估BP结构的节点"""
    
    def __init__(self, llm_client):
        """
        初始化BP评估节点
        
        Args:
            llm_client: LLM客户端
        """
        super().__init__(llm_client, "BPEvaluationNode")
    
    def validate_input(self, input_data: Any) -> bool:
        """验证输入数据"""
        if isinstance(input_data, dict):
            required_fields = ["business_idea", "paragraphs"]
            if not all(field in input_data for field in required_fields):
                return False
            if not isinstance(input_data["paragraphs"], list):
                return False
            if len(input_data["paragraphs"]) == 0:
                return False
            return True
        return False
    
    def run(self, input_data: Any, **kwargs) -> Dict[str, Any]:
        """
        调用LLM评估BP结构
        
        Args:
            input_data: 包含business_idea和paragraphs的字典
            **kwargs: 额外参数
            
        Returns:
            评估结果字典，包含：
            - passed: bool, 是否通过
            - failed_paragraph_index: int, 不通过段落的索引（如果有）
            - failed_paragraph_title: str, 不通过段落的标题（如果有）
            - evaluation_result: str, 评估结果说明
            - suggestions: str, 修改建议（如果有）
        """
        try:
            if not self.validate_input(input_data):
                raise ValueError("输入数据格式错误，需要包含business_idea和paragraphs字段")
            
            business_idea = input_data["business_idea"]
            paragraphs = input_data["paragraphs"]
            
            self.log_info(f"正在评估BP结构，共 {len(paragraphs)} 个段落...")
            
            # 准备输入数据
            formatted_input = {
                "business_idea": business_idea,
                "paragraphs": paragraphs
            }
            
            # 将输入转换为JSON字符串
            message = json.dumps(formatted_input, ensure_ascii=False)
            
            # 调用LLM
            response = self.llm_client.invoke(SYSTEM_PROMPT_BP_EVALUATION, message)
            
            # 处理响应
            processed_response = self.process_output(response)
            
            # 验证输出格式
            if "passed" not in processed_response:
                raise ValueError("评估结果缺少passed字段")
            
            if processed_response.get("passed"):
                self.log_info("BP结构评估通过")
            else:
                failed_index = processed_response.get("failed_paragraph_index", -1)
                failed_title = processed_response.get("failed_paragraph_title", "未知")
                self.log_info(f"BP结构评估不通过，失败段落索引: {failed_index}, 标题: {failed_title}")
            
            return processed_response
            
        except Exception as e:
            self.log_error(f"BP结构评估失败: {str(e)}")
            raise e
    
    def process_output(self, output: str) -> Dict[str, Any]:
        """
        处理LLM输出，提取评估结果
        
        Args:
            output: LLM原始输出
            
        Returns:
            处理后的评估结果
        """
        try:
            # 清理响应文本
            cleaned_output = remove_reasoning_from_output(output)
            cleaned_output = clean_json_tags(cleaned_output)
            
            # 解析JSON
            try:
                evaluation_result = json.loads(cleaned_output)
            except JSONDecodeError:
                # 使用更强大的提取方法
                evaluation_result = extract_clean_response(cleaned_output)
                if not isinstance(evaluation_result, dict):
                    raise ValueError("评估结果格式错误")
            
            # 验证必需字段
            if "passed" not in evaluation_result:
                raise ValueError("评估结果缺少passed字段")
            if "evaluation_result" not in evaluation_result:
                raise ValueError("评估结果缺少evaluation_result字段")
            
            # 确保passed是布尔值
            if isinstance(evaluation_result["passed"], str):
                evaluation_result["passed"] = evaluation_result["passed"].lower() in ("true", "1", "yes")
            elif not isinstance(evaluation_result["passed"], bool):
                evaluation_result["passed"] = bool(evaluation_result["passed"])
            
            return evaluation_result
            
        except Exception as e:
            self.log_error(f"处理输出失败: {str(e)}")
            raise e
    
    def evaluate_paragraphs(self, business_idea: str, paragraphs: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        评估段落列表的便捷方法
        
        Args:
            business_idea: 商业创意
            paragraphs: 段落列表，每个段落包含title和content
            
        Returns:
            评估结果字典
        """
        input_data = {
            "business_idea": business_idea,
            "paragraphs": paragraphs
        }
        return self.run(input_data)

