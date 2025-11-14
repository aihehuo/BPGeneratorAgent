"""
投资者评估节点
从投资者的角度评估BP结构段落
"""

import json
import os
import re
from datetime import datetime
from typing import Dict, Any, List
from json.decoder import JSONDecodeError

from .base_node import BaseNode
from ..prompts import SYSTEM_PROMPT_INVESTOR_EVALUATION
from ..utils.text_processing import (
    remove_reasoning_from_output,
    clean_json_tags,
    extract_clean_response,
    detect_language
)


class InvestorEvaluationNode(BaseNode):
    """投资者评估节点"""
    
    def __init__(self, llm_client):
        """
        初始化投资者评估节点
        
        Args:
            llm_client: LLM客户端
        """
        super().__init__(llm_client, "InvestorEvaluationNode")
    
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
    
    def evaluate_paragraph(self, business_idea: str, paragraph: Dict[str, str], paragraph_index: int) -> Dict[str, Any]:
        """
        评估单个段落
        
        Args:
            business_idea: 商业创意
            paragraph: 段落字典，包含title和content
            paragraph_index: 段落索引（在原始列表中的索引）
            
        Returns:
            评估结果字典
        """
        paragraphs = [paragraph]
        input_data = {
            "business_idea": business_idea,
            "paragraphs": paragraphs
        }
        # 传递原始索引，但告诉run方法使用列表中的第一个元素（索引0）
        result = self.run(input_data, paragraph_index=0, original_index=paragraph_index)
        # 确保结果中使用原始索引
        result["paragraph_index"] = paragraph_index
        return result
    
    def evaluate_full_bp(self, business_idea: str, paragraphs: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        评估整篇BP
        
        Args:
            business_idea: 商业创意
            paragraphs: 段落列表
            
        Returns:
            评估结果字典，包含整篇BP的评估和每个段落的反馈
        """
        input_data = {
            "business_idea": business_idea,
            "paragraphs": paragraphs
        }
        return self.run(input_data)
    
    def run(self, input_data: Any, **kwargs) -> Dict[str, Any]:
        """
        调用LLM进行投资者评估（整篇BP）
        
        Args:
            input_data: 包含business_idea和paragraphs的字典
            **kwargs: 额外参数（保留兼容性）
            
        Returns:
            评估结果字典，包含：
            - market_size: 市场大小评估
            - replicability: 可复制性评估
            - competitive_barriers: 竞争壁垒评估
            - unique_competitive_advantage: 独特竞争力评估
            - revenue_model: 盈利模型评估
            - overall_assessment: 整体评估
            - concerns: 投资关注点和潜在风险
            - suggestions: 整体改进建议
            - paragraph_specific_feedback: 每个段落的具体反馈数组
        """
        try:
            if not self.validate_input(input_data):
                raise ValueError("输入数据格式错误，需要包含business_idea和paragraphs字段")
            
            business_idea = input_data["business_idea"]
            paragraphs = input_data["paragraphs"]
            
            self.log_info(f"正在从投资者角度评估整篇BP，共 {len(paragraphs)} 个段落...")
            
            # 检测语言
            detected_lang = detect_language(business_idea)
            # 如果paragraphs有内容，也检查其语言
            if paragraphs and len(paragraphs) > 0:
                first_title = paragraphs[0].get('title', '')
                if first_title:
                    # 如果标题是英文，强制使用英文
                    if re.search(r'[a-zA-Z]', first_title) and not re.search(r'[\u4e00-\u9fff]', first_title):
                        detected_lang = 'en'
                    # 如果标题是中文，强制使用中文
                    elif re.search(r'[\u4e00-\u9fff]', first_title):
                        detected_lang = 'zh'
            
            lang_instruction = ""
            if detected_lang == 'en':
                lang_instruction = "\n\n**CRITICAL LANGUAGE REQUIREMENT: The business_idea and paragraphs are in ENGLISH. You MUST generate ALL output (including all evaluation fields like market_size, replicability, competitive_barriers, unique_competitive_advantage, revenue_model, overall_assessment, concerns, suggestions, paragraph_specific_feedback, etc.) in ENGLISH ONLY. DO NOT use Chinese characters anywhere in your output.**\n\n"
            else:
                lang_instruction = "\n\n**CRITICAL LANGUAGE REQUIREMENT: The business_idea and paragraphs are in CHINESE. You MUST generate ALL output (including all evaluation fields) in CHINESE ONLY. DO NOT use English in your output.**\n\n"
            
            # 准备输入数据（整篇BP）
            formatted_input = {
                "business_idea": business_idea,
                "paragraphs": paragraphs
            }
            
            # 将输入转换为JSON字符串，并在前面添加语言指令
            message = lang_instruction + json.dumps(formatted_input, ensure_ascii=False)
            
            # 调用LLM
            response = self.llm_client.invoke(SYSTEM_PROMPT_INVESTOR_EVALUATION, message)
            
            # 处理响应
            processed_response = self.process_output(response)
            
            self.log_info(f"投资者评估完成，共 {len(processed_response.get('paragraph_specific_feedback', []))} 个段落反馈")
            return processed_response
            
        except Exception as e:
            self.log_error(f"投资者评估失败: {str(e)}")
            raise e
    
    def process_output(self, output: str) -> Dict[str, Any]:
        """
        处理LLM输出，提取评估结果
        
        Args:
            output: LLM原始输出
            
        Returns:
            处理后的评估结果
        """
        original_output = output
        cleaned_output = None
        
        try:
            # 清理响应文本
            cleaned_output = remove_reasoning_from_output(output)
            cleaned_output = clean_json_tags(cleaned_output)
            
            # 修复可能的 JSON 数组格式问题：如果结尾有 ] 但开头没有 [
            if isinstance(cleaned_output, str):
                cleaned_output = cleaned_output.strip()
                if cleaned_output.endswith(']') and not cleaned_output.startswith('['):
                    if cleaned_output.startswith('{'):
                        cleaned_output = '[' + cleaned_output
                        self.log_info("检测到缺失的开头 [，已修复")
            
            # 检查输出是否已经是字典
            if isinstance(cleaned_output, dict):
                evaluation_result = cleaned_output
            elif isinstance(cleaned_output, list) and len(cleaned_output) > 0:
                # 如果是数组，取第一个元素
                evaluation_result = cleaned_output[0]
                if not isinstance(evaluation_result, dict):
                    raise ValueError("评估结果数组中的元素不是字典格式")
            else:
                # 解析JSON字符串
                evaluation_result = None
                json_error = None
                
                try:
                    evaluation_result = json.loads(cleaned_output)
                except (JSONDecodeError, TypeError) as e:
                    json_error = e
                    # 如果清理后的输出解析失败，尝试从原始输出解析
                    try:
                        # 尝试直接解析原始输出
                        evaluation_result = json.loads(original_output)
                        self.log_info("从原始输出成功解析JSON")
                    except (JSONDecodeError, TypeError):
                        # 使用更强大的提取方法
                        extracted = extract_clean_response(cleaned_output)
                        if isinstance(extracted, dict) and "error" not in extracted:
                            evaluation_result = extracted
                        elif isinstance(extracted, list) and len(extracted) > 0:
                            evaluation_result = extracted[0]
                        elif isinstance(extracted, str):
                            # 如果提取的是字符串，尝试再次解析
                            try:
                                evaluation_result = json.loads(extracted)
                            except (JSONDecodeError, TypeError):
                                # 最后尝试从原始输出提取
                                extracted_original = extract_clean_response(original_output)
                                if isinstance(extracted_original, dict) and "error" not in extracted_original:
                                    evaluation_result = extracted_original
                                elif isinstance(extracted_original, list) and len(extracted_original) > 0:
                                    evaluation_result = extracted_original[0]
                
                # 如果仍然无法解析
                if evaluation_result is None:
                    # 保存调试信息
                    debug_file = self._save_debug_output(original_output, cleaned_output)
                    error_msg = f"评估结果格式错误。调试文件已保存到: {debug_file}"
                    self.log_error(error_msg)
                    raise ValueError(error_msg)
            
            # 确保是字典格式
            if not isinstance(evaluation_result, dict):
                debug_file = self._save_debug_output(original_output, cleaned_output)
                error_msg = f"评估结果不是字典格式，而是 {type(evaluation_result)}。调试文件已保存到: {debug_file}"
                self.log_error(error_msg)
                raise ValueError(error_msg)
            
            # 验证必需字段（整篇BP评估格式）
            if "overall_assessment" not in evaluation_result:
                debug_file = self._save_debug_output(original_output, cleaned_output)
                error_msg = f"评估结果缺少overall_assessment字段。调试文件已保存到: {debug_file}"
                self.log_error(error_msg)
                raise ValueError(error_msg)
            if "suggestions" not in evaluation_result:
                evaluation_result["suggestions"] = ""
            if "paragraph_specific_feedback" not in evaluation_result:
                evaluation_result["paragraph_specific_feedback"] = []
            
            return evaluation_result
            
        except ValueError:
            # 重新抛出ValueError
            raise
        except Exception as e:
            # 保存调试信息
            debug_file = self._save_debug_output(original_output, cleaned_output if cleaned_output is not None else str(output))
            error_msg = f"处理输出失败: {str(e)}。调试文件已保存到: {debug_file}"
            self.log_error(error_msg)
            raise ValueError(error_msg) from e
    
    def _save_debug_output(self, original_output: Any, cleaned_output: Any) -> str:
        """
        保存调试输出到临时文件
        
        Args:
            original_output: 原始输出
            cleaned_output: 清理后的输出
            
        Returns:
            保存的文件路径
        """
        try:
            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            filename = f"investor_evaluation_debug_{timestamp}.txt"
            filepath = os.path.join("/tmp", filename)
            
            # 确保 /tmp 目录存在
            os.makedirs("/tmp", exist_ok=True)
            
            # 写入文件
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write("Investor Evaluation Node - 输出处理失败调试信息\n")
                f.write("=" * 80 + "\n\n")
                
                f.write("时间: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\n\n")
                
                f.write("-" * 80 + "\n")
                f.write("原始输出 (original_output):\n")
                f.write("-" * 80 + "\n")
                f.write(f"类型: {type(original_output)}\n")
                f.write(f"内容:\n{str(original_output)}\n\n")
                
                f.write("-" * 80 + "\n")
                f.write("清理后的输出 (cleaned_output):\n")
                f.write("-" * 80 + "\n")
                f.write(f"类型: {type(cleaned_output)}\n")
                f.write(f"内容:\n{str(cleaned_output)}\n\n")
                
                # 如果是字符串，尝试显示长度和字符编码信息
                if isinstance(cleaned_output, str):
                    f.write(f"长度: {len(cleaned_output)} 字符\n")
                    f.write(f"前1000字符:\n{cleaned_output[:1000]}\n\n")
                    f.write(f"后1000字符:\n{cleaned_output[-1000:]}\n\n")
            
            return filepath
        except Exception as e:
            self.log_error(f"保存调试文件失败: {str(e)}")
            return "/tmp/investor_evaluation_debug_failed.txt"
    
    def evaluate_all_paragraphs(self, business_idea: str, paragraphs: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """
        评估所有段落
        
        Args:
            business_idea: 商业创意
            paragraphs: 段落列表
            
        Returns:
            评估结果列表，每个元素是一个段落的评估结果
        """
        results = []
        for i, paragraph in enumerate(paragraphs):
            try:
                result = self.evaluate_paragraph(business_idea, paragraph, i)
                results.append(result)
            except Exception as e:
                self.log_error(f"评估段落 {i} 失败: {str(e)}")
                # 继续评估下一个段落
                continue
        return results

