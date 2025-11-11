"""
痛点加强节点
根据"用户痛点的六个切入维度"理论加强痛点陈述
"""

import json
import os
import re
from datetime import datetime
from typing import Dict, Any, List
from json.decoder import JSONDecodeError

from .base_node import BaseNode
from ..prompts import SYSTEM_PROMPT_PAINPOINT_ENHANCEMENT
from ..utils.text_processing import (
    remove_reasoning_from_output,
    clean_json_tags,
    extract_clean_response
)


class PainpointEnhancementNode(BaseNode):
    """痛点加强节点"""
    
    def __init__(self, llm_client):
        """
        初始化痛点加强节点
        
        Args:
            llm_client: LLM客户端
        """
        super().__init__(llm_client, "PainpointEnhancementNode")
    
    def validate_input(self, input_data: Any) -> bool:
        """验证输入数据"""
        if isinstance(input_data, dict):
            required_fields = ["business_idea", "painpoint_paragraph"]
            if not all(field in input_data for field in required_fields):
                return False
            painpoint_para = input_data.get("painpoint_paragraph", {})
            if not isinstance(painpoint_para, dict):
                return False
            if "title" not in painpoint_para or "content" not in painpoint_para:
                return False
            return True
        return False
    
    def enhance(self, business_idea: str, painpoint_paragraph: Dict[str, str]) -> Dict[str, Any]:
        """
        加强痛点段落
        
        Args:
            business_idea: 商业创意
            painpoint_paragraph: 痛点段落字典，包含title和content
            
        Returns:
            加强结果字典，包含：
            - enhanced_content: 加强后的内容
            - dimensions_used: 已使用的维度列表
            - dimensions_missing: 缺失的维度列表
            - enhancement_explanation: 加强说明
        """
        input_data = {
            "business_idea": business_idea,
            "painpoint_paragraph": painpoint_paragraph
        }
        return self.run(input_data)
    
    def run(self, input_data: Any, **kwargs) -> Dict[str, Any]:
        """
        调用LLM加强痛点陈述
        
        Args:
            input_data: 包含business_idea和painpoint_paragraph的字典
            **kwargs: 额外参数
            
        Returns:
            加强结果字典
        """
        try:
            if not self.validate_input(input_data):
                raise ValueError("输入数据格式错误，需要包含business_idea和painpoint_paragraph字段")
            
            business_idea = input_data["business_idea"]
            painpoint_paragraph = input_data["painpoint_paragraph"]
            
            para_title = painpoint_paragraph.get("title", "用户画像与痛点")
            self.log_info(f"正在加强痛点段落: {para_title}")
            
            # 准备输入数据
            formatted_input = {
                "business_idea": business_idea,
                "painpoint_paragraph": painpoint_paragraph
            }
            
            # 将输入转换为JSON字符串
            message = json.dumps(formatted_input, ensure_ascii=False)
            
            # 调用LLM
            response = self.llm_client.invoke(SYSTEM_PROMPT_PAINPOINT_ENHANCEMENT, message)
            
            # 处理响应
            processed_response = self.process_output(response)
            
            self.log_info(f"痛点加强完成: {para_title}")
            return processed_response
            
        except Exception as e:
            self.log_error(f"痛点加强失败: {str(e)}")
            raise e
    
    def process_output(self, output: str) -> Dict[str, Any]:
        """
        处理LLM输出，提取加强结果
        
        Args:
            output: LLM原始输出
            
        Returns:
            处理后的加强结果
        """
        original_output = output
        cleaned_output = None
        
        try:
            # 清理响应文本
            cleaned_output = remove_reasoning_from_output(output)
            cleaned_output = clean_json_tags(cleaned_output)
            
            # 修复可能的 JSON 数组格式问题
            if isinstance(cleaned_output, str):
                cleaned_output = cleaned_output.strip()
                # 清理控制字符
                cleaned_output = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', cleaned_output)
            
            # 检查输出是否已经是字典
            if isinstance(cleaned_output, dict):
                enhancement_result = cleaned_output
            elif isinstance(cleaned_output, list) and len(cleaned_output) > 0:
                # 如果是数组，取第一个元素
                enhancement_result = cleaned_output[0]
                if not isinstance(enhancement_result, dict):
                    raise ValueError("加强结果数组中的元素不是字典格式")
            else:
                # 解析JSON字符串
                enhancement_result = None
                
                # 首先尝试解析原始输出
                try:
                    if isinstance(original_output, str):
                        cleaned_original = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', original_output)
                        enhancement_result = json.loads(cleaned_original)
                        self.log_info("从原始输出成功解析JSON")
                except (JSONDecodeError, TypeError):
                    # 如果原始输出解析失败，尝试清理后的输出
                    try:
                        enhancement_result = json.loads(cleaned_output)
                    except (JSONDecodeError, TypeError) as e:
                        # 使用更强大的提取方法
                        extracted = extract_clean_response(cleaned_output)
                        if isinstance(extracted, dict) and "error" not in extracted:
                            enhancement_result = extracted
                        elif isinstance(extracted, list) and len(extracted) > 0:
                            enhancement_result = extracted[0]
                        else:
                            # 最后尝试从原始输出提取
                            extracted_original = extract_clean_response(original_output)
                            if isinstance(extracted_original, dict) and "error" not in extracted_original:
                                enhancement_result = extracted_original
                            elif isinstance(extracted_original, list) and len(extracted_original) > 0:
                                enhancement_result = extracted_original[0]
                            else:
                                # 保存调试信息
                                debug_file = self._save_debug_output(original_output, cleaned_output)
                                error_msg = f"加强结果格式错误。调试文件已保存到: {debug_file}"
                                self.log_error(error_msg)
                                raise ValueError(error_msg)
                
                # 如果仍然无法解析
                if enhancement_result is None:
                    debug_file = self._save_debug_output(original_output, cleaned_output)
                    error_msg = f"无法解析加强结果。调试文件已保存到: {debug_file}"
                    self.log_error(error_msg)
                    raise ValueError(error_msg)
            
            # 确保是字典格式
            if not isinstance(enhancement_result, dict):
                debug_file = self._save_debug_output(original_output, cleaned_output)
                error_msg = f"加强结果不是字典格式，而是 {type(enhancement_result)}。调试文件已保存到: {debug_file}"
                self.log_error(error_msg)
                raise ValueError(error_msg)
            
            # 验证必需字段
            if "enhanced_content" not in enhancement_result:
                debug_file = self._save_debug_output(original_output, cleaned_output)
                error_msg = f"加强结果缺少enhanced_content字段。调试文件已保存到: {debug_file}"
                self.log_error(error_msg)
                raise ValueError(error_msg)
            
            # 验证必需字段
            if "selected_dimensions" not in enhancement_result:
                debug_file = self._save_debug_output(original_output, cleaned_output)
                error_msg = f"加强结果缺少selected_dimensions字段。调试文件已保存到: {debug_file}"
                self.log_error(error_msg)
                raise ValueError(error_msg)
            
            # 验证维度数量
            selected_dimensions = enhancement_result.get("selected_dimensions", [])
            if len(selected_dimensions) != 3:
                self.log_info(f"警告: selected_dimensions包含{len(selected_dimensions)}个维度，期望3个")
            
            # 验证dimension_descriptions
            if "dimension_descriptions" not in enhancement_result:
                debug_file = self._save_debug_output(original_output, cleaned_output)
                error_msg = f"加强结果缺少dimension_descriptions字段。调试文件已保存到: {debug_file}"
                self.log_error(error_msg)
                raise ValueError(error_msg)
            
            # 设置默认值
            if "enhancement_explanation" not in enhancement_result:
                enhancement_result["enhancement_explanation"] = ""
            
            # 确保dimension_descriptions是数组
            if not isinstance(enhancement_result.get("dimension_descriptions"), list):
                enhancement_result["dimension_descriptions"] = []
            
            return enhancement_result
            
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
            filename = f"painpoint_enhancement_debug_{timestamp}.txt"
            filepath = os.path.join("/tmp", filename)
            
            # 确保 /tmp 目录存在
            os.makedirs("/tmp", exist_ok=True)
            
            # 写入文件
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write("Painpoint Enhancement Node - 输出处理失败调试信息\n")
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
            return "/tmp/painpoint_enhancement_debug_failed.txt"

