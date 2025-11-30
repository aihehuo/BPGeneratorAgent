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
from ..prompts.ppt_generation import SYSTEM_PROMPT_PPT_GENERATION
from ..utils.text_processing import (
    remove_reasoning_from_output,
    clean_json_tags,
    extract_clean_response,
    detect_language
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
            
            # 检测语言
            detected_lang = detect_language(business_idea)
            # 如果bp_structure有内容，也检查其语言
            if bp_structure and len(bp_structure) > 0:
                first_title = bp_structure[0].get('title', '')
                if first_title:
                    # 如果标题是英文，强制使用英文
                    if re.search(r'[a-zA-Z]', first_title) and not re.search(r'[\u4e00-\u9fff]', first_title):
                        detected_lang = 'en'
                    # 如果标题是中文，强制使用中文
                    elif re.search(r'[\u4e00-\u9fff]', first_title):
                        detected_lang = 'zh'
            
            lang_instruction = ""
            if detected_lang == 'en':
                lang_instruction = "\n\n**CRITICAL LANGUAGE REQUIREMENT: The business_idea and bp_structure are in ENGLISH. You MUST generate ALL output (including all slide titles, points, lines, reserved hooks, etc.) in ENGLISH ONLY. DO NOT use Chinese characters anywhere in your output.**\n\n"
            else:
                lang_instruction = "\n\n**CRITICAL LANGUAGE REQUIREMENT: The business_idea and bp_structure are in CHINESE. You MUST generate ALL output (including all slide titles, points, lines, reserved hooks, etc.) in CHINESE ONLY. DO NOT use English in your output.**\n\n"
            
            # 准备输入数据
            formatted_input = {
                "business_idea": business_idea,
                "bp_structure": bp_structure
            }
            
            # 将输入转换为JSON字符串，并在前面添加语言指令
            message = lang_instruction + json.dumps(formatted_input, ensure_ascii=False)
            
            # 调用LLM (使用新的 invoke_llm 方法)
            response = self.invoke_llm(SYSTEM_PROMPT_PPT_GENERATION, message)
            
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
            
            # 首先尝试直接解析JSON（可能已经是纯JSON）
            parsed_output = None
            try:
                if isinstance(output, str):
                    parsed_output = json.loads(output)
                    self.log_info("从原始输出成功解析JSON")
                elif isinstance(output, dict):
                    parsed_output = output
            except (JSONDecodeError, TypeError):
                # 如果直接解析失败，进行清理后重试
                if isinstance(cleaned_output, str):
                    try:
                        parsed_output = json.loads(cleaned_output)
                        self.log_info("从清理后的输出成功解析JSON")
                    except (JSONDecodeError, TypeError):
                        # 策略2: 尝试从original_output解析（可能更完整）
                        if isinstance(original_output, str):
                            original_cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', original_output)
                            try:
                                parsed_output = json.loads(original_cleaned)
                                self.log_info("从清理后的原始输出成功解析JSON")
                            except (JSONDecodeError, TypeError):
                                # 策略3: 使用extract_clean_response提取JSON
                                extracted = extract_clean_response(original_output)
                                if isinstance(extracted, dict) and "error" not in extracted:
                                    parsed_output = extracted
                                elif isinstance(extracted, str):
                                    try:
                                        parsed_output = json.loads(extracted)
                                    except (JSONDecodeError, TypeError):
                                        raise ValueError("无法从输出中提取有效的JSON")
                                else:
                                    raise ValueError("无法从输出中提取有效的JSON")
                elif isinstance(cleaned_output, dict):
                    parsed_output = cleaned_output
                else:
                    raise ValueError("无法解析输出")
            
            # 检查是否是新格式（包含data和markdown_summary）
            markdown_summary = None
            if isinstance(parsed_output, dict):
                if "data" in parsed_output and "markdown_summary" in parsed_output:
                    # 新格式：包含data和markdown_summary
                    ppt_result = parsed_output["data"]
                    markdown_summary = parsed_output.get("markdown_summary")
                    self.log_info("检测到新格式输出（包含data和markdown_summary）")
                else:
                    # 旧格式：直接是PPT结果
                    ppt_result = parsed_output
            else:
                raise ValueError(f"解析后的输出不是字典格式，而是 {type(parsed_output)}")
            
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
            
            # 验证每页幻灯片的必需字段，并在验证前设置默认值
            for i, slide in enumerate(slides):
                if not isinstance(slide, dict):
                    debug_file = self._save_debug_output(original_output, cleaned_output if 'cleaned_output' in locals() else str(output))
                    error_msg = f"PPT第 {i+1} 页不是字典格式。调试文件已保存到: {debug_file}"
                    self.log_error(error_msg)
                    raise ValueError(error_msg)
                
                # 先设置slide_number的默认值（如果缺失）
                if "slide_number" not in slide or slide.get("slide_number") is None:
                    slide["slide_number"] = i + 1
                
                # 然后验证必需字段
                required_fields = ["slide_number", "slide_title", "point", "line", "reserved"]
                missing_fields = [field for field in required_fields if field not in slide]
                if missing_fields:
                    debug_file = self._save_debug_output(original_output, cleaned_output if 'cleaned_output' in locals() else str(output))
                    error_msg = f"PPT第 {i+1} 页缺少字段: {', '.join(missing_fields)}。调试文件已保存到: {debug_file}"
                    self.log_error(error_msg)
                    raise ValueError(error_msg)
            
            # 如果提取到了markdown_summary，添加到结果中
            if markdown_summary:
                ppt_result["markdown_summary"] = markdown_summary
            
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

