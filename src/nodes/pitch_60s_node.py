"""
黄金60秒Pitch节点
根据完整的BP结构生成黄金60秒pitch
"""

import json
import os
import re
from datetime import datetime
from typing import Dict, Any, List
from json.decoder import JSONDecodeError

from .base_node import BaseNode
from ..prompts.pitch_60s import SYSTEM_PROMPT_60S_PITCH
from ..utils.text_processing import (
    remove_reasoning_from_output,
    clean_json_tags,
    extract_clean_response,
    detect_language
)


class Pitch60sNode(BaseNode):
    """黄金60秒Pitch节点"""
    
    def __init__(self, llm_client):
        """
        初始化黄金60秒Pitch节点
        
        Args:
            llm_client: LLM客户端
        """
        super().__init__(llm_client, "Pitch60sNode")
    
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
    
    def generate_pitch(self, business_idea: str, bp_structure: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        生成黄金60秒pitch
        
        Args:
            business_idea: 商业创意
            bp_structure: BP结构列表，每个元素包含title和content
            
        Returns:
            Pitch结果字典，包含：
            - painpoint_resonance: 痛点共鸣部分
            - team_advantages: 团队优势部分
            - call_to_action: 召唤行动部分
            - full_pitch: 完整的60秒pitch文本
        """
        input_data = {
            "business_idea": business_idea,
            "bp_structure": bp_structure
        }
        return self.run(input_data)
    
    def run(self, input_data: Any, **kwargs) -> Dict[str, Any]:
        """
        调用LLM生成黄金60秒pitch
        
        Args:
            input_data: 包含business_idea和bp_structure的字典
            **kwargs: 额外参数
            
        Returns:
            Pitch结果字典
        """
        try:
            if not self.validate_input(input_data):
                raise ValueError("输入数据格式错误，需要包含business_idea和bp_structure字段")
            
            business_idea = input_data["business_idea"]
            bp_structure = input_data["bp_structure"]
            
            self.log_info(f"正在生成黄金60秒pitch，BP结构包含 {len(bp_structure)} 个段落")
            
            # 检测语言
            import re
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
                lang_instruction = "\n\n**CRITICAL LANGUAGE REQUIREMENT: The business_idea and bp_structure are in ENGLISH. You MUST generate ALL output (including painpoint_resonance, team_advantages, call_to_action, full_pitch, etc.) in ENGLISH ONLY. DO NOT use Chinese characters anywhere in your output.**\n\n"
            else:
                lang_instruction = "\n\n**CRITICAL LANGUAGE REQUIREMENT: The business_idea and bp_structure are in CHINESE. You MUST generate ALL output (including painpoint_resonance, team_advantages, call_to_action, full_pitch, etc.) in CHINESE ONLY. DO NOT use English in your output.**\n\n"
            
            # 准备输入数据
            formatted_input = {
                "business_idea": business_idea,
                "bp_structure": bp_structure
            }
            
            # 将输入转换为JSON字符串，并在前面添加语言指令
            message = lang_instruction + json.dumps(formatted_input, ensure_ascii=False)
            
            # 调用LLM (使用新的 invoke_llm 方法)
            response = self.invoke_llm(SYSTEM_PROMPT_60S_PITCH, message)
            
            if not response:
                raise ValueError("LLM返回空响应")
            
            # 处理输出
            pitch_result = self.process_output(response)
            
            self.log_info("黄金60秒pitch生成成功")
            return pitch_result
            
        except Exception as e:
            self.log_error(f"生成黄金60秒pitch失败: {str(e)}")
            raise
    
    def process_output(self, output: Any) -> Dict[str, Any]:
        """
        处理LLM输出，解析JSON并验证
        
        Args:
            output: LLM原始输出
            
        Returns:
            解析后的pitch结果字典
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
                    pitch_result = parsed_output["data"]
                    markdown_summary = parsed_output.get("markdown_summary")
                    self.log_info("检测到新格式输出（包含data和markdown_summary）")
                else:
                    # 旧格式：直接是pitch结果
                    pitch_result = parsed_output
            else:
                raise ValueError(f"解析后的输出不是字典格式，而是 {type(parsed_output)}")
            
            # 验证必需字段
            if not isinstance(pitch_result, dict):
                debug_file = self._save_debug_output(original_output, cleaned_output)
                error_msg = f"Pitch结果不是字典格式，而是 {type(pitch_result)}。调试文件已保存到: {debug_file}"
                self.log_error(error_msg)
                raise ValueError(error_msg)
            
            # 验证必需字段
            required_fields = ["painpoint_resonance", "team_advantages", "call_to_action", "full_pitch"]
            missing_fields = [field for field in required_fields if field not in pitch_result]
            if missing_fields:
                debug_file = self._save_debug_output(original_output, cleaned_output)
                error_msg = f"Pitch结果缺少必需字段: {', '.join(missing_fields)}。调试文件已保存到: {debug_file}"
                self.log_error(error_msg)
                raise ValueError(error_msg)
            
            # 验证painpoint_resonance结构
            painpoint_resonance = pitch_result.get("painpoint_resonance", {})
            if not isinstance(painpoint_resonance, dict):
                pitch_result["painpoint_resonance"] = {"selected_dimensions": [], "content": ""}
            else:
                if "selected_dimensions" not in painpoint_resonance:
                    pitch_result["painpoint_resonance"]["selected_dimensions"] = []
                if "content" not in painpoint_resonance:
                    pitch_result["painpoint_resonance"]["content"] = ""
            
            # 验证team_advantages结构
            team_advantages = pitch_result.get("team_advantages", {})
            if not isinstance(team_advantages, dict):
                pitch_result["team_advantages"] = {"selected_advantages": [], "content": ""}
            else:
                if "selected_advantages" not in team_advantages:
                    pitch_result["team_advantages"]["selected_advantages"] = []
                if "content" not in team_advantages:
                    pitch_result["team_advantages"]["content"] = ""
            
            # 验证call_to_action结构
            call_to_action = pitch_result.get("call_to_action", {})
            if not isinstance(call_to_action, dict):
                pitch_result["call_to_action"] = {"target_audience": "", "action": "", "content": ""}
            else:
                if "target_audience" not in call_to_action:
                    pitch_result["call_to_action"]["target_audience"] = ""
                if "action" not in call_to_action:
                    pitch_result["call_to_action"]["action"] = ""
                if "content" not in call_to_action:
                    pitch_result["call_to_action"]["content"] = ""
            
            # 设置默认值
            if "full_pitch" not in pitch_result or not pitch_result["full_pitch"]:
                # 如果没有full_pitch，尝试组合生成
                parts = []
                if painpoint_resonance.get("content"):
                    parts.append(painpoint_resonance["content"])
                if team_advantages.get("content"):
                    parts.append(team_advantages["content"])
                if call_to_action.get("content"):
                    parts.append(call_to_action["content"])
                pitch_result["full_pitch"] = " ".join(parts)
            
            # 如果提取到了markdown_summary，添加到结果中
            if markdown_summary:
                pitch_result["markdown_summary"] = markdown_summary
            
            return pitch_result
            
        except ValueError:
            # 重新抛出ValueError
            raise
        except Exception as e:
            debug_file = self._save_debug_output(original_output, cleaned_output if 'cleaned_output' in locals() else None)
            error_msg = f"处理Pitch输出时发生错误: {str(e)}。调试文件已保存到: {debug_file}"
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
            filename = f"60s_pitch_debug_{timestamp}.txt"
            filepath = os.path.join("/tmp", filename)
            
            # 确保 /tmp 目录存在
            os.makedirs("/tmp", exist_ok=True)
            
            # 写入文件
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write("60s Pitch Node - 输出处理失败调试信息\n")
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
            return "/tmp/60s_pitch_debug_error.txt"

