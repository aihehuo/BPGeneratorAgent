"""
PPT生成节点
将完整的BP结构转换为10页PPT格式
"""

import json
import os
import re
from datetime import datetime
from typing import Dict, Any, List
from json.decoder import JSONDecodeError

from .base_node import BaseNode
from ..prompts import SYSTEM_PROMPT_PPT_GENERATION
from ..utils.text_processing import (
    remove_reasoning_from_output,
    clean_json_tags,
    extract_clean_response
)


class PPTGenerationNode(BaseNode):
    """PPT生成节点"""
    
    def __init__(self, llm_client):
        """
        初始化PPT生成节点
        
        Args:
            llm_client: LLM客户端
        """
        super().__init__(llm_client, "PPTGenerationNode")
    
    def validate_input(self, input_data: Any) -> bool:
        """验证输入数据"""
        if isinstance(input_data, dict):
            required_fields = ["business_idea", "bp_structure"]
            if not all(field in input_data for field in required_fields):
                return False
            bp_structure = input_data.get("bp_structure", [])
            if not isinstance(bp_structure, list):
                return False
            # 验证每个段落都有title和content
            for para in bp_structure:
                if not isinstance(para, dict):
                    return False
                if "title" not in para or "content" not in para:
                    return False
            return True
        return False
    
    def generate_ppt(self, business_idea: str, bp_structure: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        生成10页PPT
        
        Args:
            business_idea: 商业创意
            bp_structure: BP结构列表，每个元素包含title和content
            
        Returns:
            PPT结果字典，包含：
            - slides: 10页PPT的数组，每页包含slide_number、slide_title、point、line、reserved
        """
        input_data = {
            "business_idea": business_idea,
            "bp_structure": bp_structure
        }
        return self.run(input_data)
    
    def run(self, input_data: Any, **kwargs) -> Dict[str, Any]:
        """
        调用LLM生成10页PPT
        
        Args:
            input_data: 包含business_idea和bp_structure的字典
            **kwargs: 额外参数
            
        Returns:
            PPT结果字典
        """
        try:
            if not self.validate_input(input_data):
                raise ValueError("输入数据格式错误，需要包含business_idea和bp_structure字段")
            
            business_idea = input_data["business_idea"]
            bp_structure = input_data["bp_structure"]
            
            self.log_info(f"正在生成10页PPT，BP结构包含 {len(bp_structure)} 个段落")
            
            # 准备输入数据
            formatted_input = {
                "business_idea": business_idea,
                "bp_structure": bp_structure
            }
            
            # 将输入转换为JSON字符串
            message = json.dumps(formatted_input, ensure_ascii=False)
            
            # 调用LLM
            response = self.llm_client.invoke(SYSTEM_PROMPT_PPT_GENERATION, message)
            
            if not response:
                raise ValueError("LLM返回空响应")
            
            # 处理输出
            ppt_result = self.process_output(response)
            
            self.log_info("10页PPT生成成功")
            return ppt_result
            
        except Exception as e:
            self.log_error(f"生成10页PPT失败: {str(e)}")
            raise
    
    def process_output(self, output: Any) -> Dict[str, Any]:
        """
        处理LLM输出，解析JSON并验证
        
        Args:
            output: LLM原始输出
            
        Returns:
            解析后的PPT结果字典
        """
        original_output = output
        
        try:
            # 如果输出已经是字典，直接使用
            if isinstance(output, dict):
                cleaned_output = output
            else:
                # 转换为字符串
                if not isinstance(output, str):
                    output = str(output)
                
                # 清理输出
                cleaned_output = remove_reasoning_from_output(output)
                cleaned_output = clean_json_tags(cleaned_output)
                
                # 移除控制字符（除了换行、回车、制表符）
                cleaned_output = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', cleaned_output)
            
            # 尝试解析JSON
            ppt_result = None
            
            # 策略1: 如果cleaned_output是字符串，尝试直接解析
            if isinstance(cleaned_output, str):
                try:
                    ppt_result = json.loads(cleaned_output)
                except JSONDecodeError:
                    # 策略2: 尝试从original_output解析（可能更完整）
                    if isinstance(original_output, str):
                        original_cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', original_output)
                        try:
                            ppt_result = json.loads(original_cleaned)
                        except JSONDecodeError:
                            # 策略3: 使用extract_clean_response提取JSON
                            extracted = extract_clean_response(original_output)
                            if extracted:
                                ppt_result = json.loads(extracted)
                            else:
                                raise ValueError("无法从输出中提取有效的JSON")
            else:
                # cleaned_output已经是字典
                ppt_result = cleaned_output
            
            # 验证必需字段
            if not isinstance(ppt_result, dict):
                debug_file = self._save_debug_output(original_output, cleaned_output)
                error_msg = f"PPT结果不是字典格式，而是 {type(ppt_result)}。调试文件已保存到: {debug_file}"
                self.log_error(error_msg)
                raise ValueError(error_msg)
            
            # 验证必需字段
            if "slides" not in ppt_result:
                debug_file = self._save_debug_output(original_output, cleaned_output)
                error_msg = f"PPT结果缺少slides字段。调试文件已保存到: {debug_file}"
                self.log_error(error_msg)
                raise ValueError(error_msg)
            
            slides = ppt_result.get("slides", [])
            if not isinstance(slides, list):
                debug_file = self._save_debug_output(original_output, cleaned_output)
                error_msg = f"PPT结果中slides不是数组格式。调试文件已保存到: {debug_file}"
                self.log_error(error_msg)
                raise ValueError(error_msg)
            
            # 验证幻灯片数量
            if len(slides) != 10:
                self.log_info(f"警告: PPT包含 {len(slides)} 页，期望10页")
            
            # 验证每页幻灯片的必需字段
            for i, slide in enumerate(slides):
                if not isinstance(slide, dict):
                    debug_file = self._save_debug_output(original_output, cleaned_output)
                    error_msg = f"PPT第 {i+1} 页不是字典格式。调试文件已保存到: {debug_file}"
                    self.log_error(error_msg)
                    raise ValueError(error_msg)
                
                required_fields = ["slide_number", "slide_title", "point", "line", "reserved"]
                missing_fields = [field for field in required_fields if field not in slide]
                if missing_fields:
                    debug_file = self._save_debug_output(original_output, cleaned_output)
                    error_msg = f"PPT第 {i+1} 页缺少字段: {', '.join(missing_fields)}。调试文件已保存到: {debug_file}"
                    self.log_error(error_msg)
                    raise ValueError(error_msg)
                
                # 设置默认值
                if "slide_number" not in slide or slide.get("slide_number") is None:
                    slide["slide_number"] = i + 1
            
            return ppt_result
            
        except ValueError:
            # 重新抛出ValueError
            raise
        except Exception as e:
            debug_file = self._save_debug_output(original_output, cleaned_output if 'cleaned_output' in locals() else None)
            error_msg = f"处理PPT输出时发生错误: {str(e)}。调试文件已保存到: {debug_file}"
            self.log_error(error_msg)
            raise ValueError(error_msg)
    
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
            filename = f"ppt_generation_debug_{timestamp}.txt"
            filepath = os.path.join("/tmp", filename)
            
            # 确保 /tmp 目录存在
            os.makedirs("/tmp", exist_ok=True)
            
            # 写入文件
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write("PPT Generation Node - 输出处理失败调试信息\n")
                f.write("=" * 80 + "\n\n")
                
                f.write("时间: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\n\n")
                
                f.write("-" * 80 + "\n")
                f.write("原始输出 (original_output):\n")
                f.write("-" * 80 + "\n")
                f.write(str(original_output))
                f.write("\n\n")
                
                if cleaned_output is not None:
                    f.write("-" * 80 + "\n")
                    f.write("清理后输出 (cleaned_output):\n")
                    f.write("-" * 80 + "\n")
                    f.write(str(cleaned_output))
                    f.write("\n\n")
            
            return filepath
        except Exception as e:
            self.log_error(f"保存调试文件失败: {str(e)}")
            return "/tmp/ppt_generation_debug_error.txt"

