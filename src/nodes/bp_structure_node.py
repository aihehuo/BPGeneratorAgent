"""
BP结构生成节点
负责根据商业创意生成商业计划书的整体结构
"""

import json
import os
import re
from datetime import datetime
from typing import Dict, Any, List
from json.decoder import JSONDecodeError

from .base_node import StateMutationNode
from ..state.state import State
from ..prompts.bp_structure import SYSTEM_PROMPT_BP_STRUCTURE, SYSTEM_PROMPT_BP_STRUCTURE_REGENERATE
from ..utils.text_processing import (
    remove_reasoning_from_output,
    clean_json_tags,
    extract_clean_response,
    detect_language
)


class BPStructureNode(StateMutationNode):
    """生成BP结构的节点"""
    
    def __init__(self, llm_client, business_idea: str):
        """
        初始化BP结构节点
        
        Args:
            llm_client: LLM客户端
            business_idea: 商业创意
        """
        super().__init__(llm_client, "BPStructureNode")
        self.business_idea = business_idea
    
    def validate_input(self, input_data: Any) -> bool:
        """验证输入数据"""
        return isinstance(self.business_idea, str) and len(self.business_idea.strip()) > 0
    
    def run(self, input_data: Any = None, **kwargs) -> Dict[str, Any]:
        """
        调用LLM生成BP结构
        
        Args:
            input_data: 输入数据（这里不使用，使用初始化时的business_idea）
            **kwargs: 额外参数
            
        Returns:
            包含bp_structure和markdown_summary的字典
        """
        try:
            self.log_info(f"正在为商业创意生成BP结构: {self.business_idea[:50]}...")
            
            # 检测语言
            detected_lang = detect_language(self.business_idea)
            lang_instruction = ""
            if detected_lang == 'en':
                lang_instruction = "\n\n**CRITICAL LANGUAGE REQUIREMENT: The business_idea is in ENGLISH. You MUST generate ALL output (including title, content fields, and markdown_summary) in ENGLISH ONLY. Use English titles like 'User Persona & Pain Points', 'Solution', 'Minimum Viable Product (MVP)', etc. DO NOT use Chinese characters anywhere in your output.**\n\n"
            else:
                lang_instruction = "\n\n**CRITICAL LANGUAGE REQUIREMENT: The business_idea is in CHINESE. You MUST generate ALL output (including title, content fields, and markdown_summary) in CHINESE ONLY. Use Chinese titles like '用户画像与痛点', '解决方案', '最小可行产品（MVP）', etc. DO NOT use English titles or content.**\n\n"
            
            # 准备输入数据，按照input_schema_bp_structure格式
            formatted_input = {
                "business_idea": self.business_idea
            }
            
            # 将输入转换为JSON字符串，并在前面添加语言指令
            message = lang_instruction + json.dumps(formatted_input, ensure_ascii=False)
            
            # 调用LLM (使用新的 invoke_llm 方法)
            response = self.invoke_llm(SYSTEM_PROMPT_BP_STRUCTURE, message)
            
            # 处理响应
            processed_response = self.process_output(response)
            
            bp_structure = processed_response.get("bp_structure", [])
            self.log_info(f"成功生成 {len(bp_structure)} 个段落结构")
            return processed_response
            
        except Exception as e:
            self.log_error(f"生成BP结构失败: {str(e)}")
            raise e
    
    def regenerate(self, evaluation_result: str, suggestions: str, current_structure: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """
        根据评估反馈重新生成BP结构
        
        Args:
            evaluation_result: 评估结果说明
            suggestions: 修改建议
            current_structure: 当前BP结构
            **kwargs: 额外参数
        
        Returns:
            包含bp_structure和markdown_summary的字典
        """
        try:
            self.log_info(f"正在根据反馈重新生成BP结构...")
            
            # 检测语言（从business_idea和current_structure）
            detected_lang = detect_language(self.business_idea)
            # 如果current_structure有内容，也检查其语言
            if current_structure and len(current_structure) > 0:
                first_title = current_structure[0].get('title', '')
                if first_title:
                    # 如果标题是英文，强制使用英文
                    if re.search(r'[a-zA-Z]', first_title) and not re.search(r'[\u4e00-\u9fff]', first_title):
                        detected_lang = 'en'
                    # 如果标题是中文，强制使用中文
                    elif re.search(r'[\u4e00-\u9fff]', first_title):
                        detected_lang = 'zh'
            
            lang_instruction = ""
            if detected_lang == 'en':
                lang_instruction = "\n\n**CRITICAL LANGUAGE REQUIREMENT: The business_idea and current_structure are in ENGLISH. You MUST generate ALL output (including title, content fields, and markdown_summary) in ENGLISH ONLY. Keep the same English titles from current_structure. DO NOT use Chinese characters anywhere in your output.**\n\n"
            else:
                lang_instruction = "\n\n**CRITICAL LANGUAGE REQUIREMENT: The business_idea and current_structure are in CHINESE. You MUST generate ALL output (including title, content fields, and markdown_summary) in CHINESE ONLY. Keep the same Chinese titles from current_structure. DO NOT use English titles or content.**\n\n"
            
            # 准备输入数据，按照input_schema_bp_structure_regenerate格式
            formatted_input = {
                "business_idea": self.business_idea,
                "evaluation_result": evaluation_result,
                "suggestions": suggestions,
                "current_structure": current_structure
            }
            
            # 将输入转换为JSON字符串，并在前面添加语言指令
            message = lang_instruction + json.dumps(formatted_input, ensure_ascii=False)
            
            # 调用LLM (使用新的 invoke_llm 方法)
            response = self.invoke_llm(SYSTEM_PROMPT_BP_STRUCTURE_REGENERATE, message)
            
            # 处理响应
            processed_response = self.process_output(response)
            
            bp_structure = processed_response.get("bp_structure", [])
            self.log_info(f"成功重新生成 {len(bp_structure)} 个段落结构")
            return processed_response
            
        except Exception as e:
            self.log_error(f"重新生成BP结构失败: {str(e)}")
            raise e
    
    def process_output(self, output: str) -> Dict[str, Any]:
        """
        处理LLM输出，提取BP结构和Markdown摘要
        
        Args:
            output: LLM原始输出
            
        Returns:
            包含bp_structure和markdown_summary的字典
            
        Raises:
            ValueError: 如果JSON解析失败或格式不正确
        """
        # 保存原始输出和清理后的输出，用于调试
        original_output = output
        cleaned_output = None
        markdown_summary = None
        
        # 检查输出是否已经是数组或字典（已解析的JSON）
        if isinstance(output, (list, dict)):
            # 如果已经是数组，说明是旧格式（向后兼容）
            if isinstance(output, list):
                bp_structure = output
            # 如果是字典，检查是否是新格式（包含data和markdown_summary）
            elif isinstance(output, dict):
                if "data" in output and "markdown_summary" in output:
                    # 新格式：包含data和markdown_summary
                    bp_structure = output["data"]
                    markdown_summary = output.get("markdown_summary")
                elif "title" in output and "content" in output:
                    # 单个段落对象（旧格式）
                    bp_structure = [output]
                else:
                    # 可能是其他格式，尝试查找数组字段
                    bp_structure = output
            else:
                bp_structure = output
        else:
            # 清理响应文本
            cleaned_output = remove_reasoning_from_output(output)
            cleaned_output = clean_json_tags(cleaned_output)
            
            # 修复可能的 JSON 数组格式问题：如果结尾有 ] 但开头没有 [
            if isinstance(cleaned_output, str):
                cleaned_output = cleaned_output.strip()
                # 检查是否缺少开头的 [ 但结尾有 ]
                if cleaned_output.endswith(']') and not cleaned_output.startswith('['):
                    # 检查是否以 { 开头（可能是数组的第一个元素）
                    if cleaned_output.startswith('{'):
                        # 添加缺失的 [
                        cleaned_output = '[' + cleaned_output
                        self.log_info("检测到缺失的开头 [，已修复")
                
                # 清理控制字符（除了合法的换行符和制表符）
                # JSON 标准允许 \n, \r, \t，但不允许其他控制字符
                # 移除除 \n, \r, \t 之外的控制字符
                cleaned_output = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', cleaned_output)
            
            # 检查清理后的输出是否已经是数组或字典
            if isinstance(cleaned_output, (list, dict)):
                parsed_output = cleaned_output
            else:
                # 解析JSON字符串
                parsed_output = None
                json_error = None
                
                # 首先尝试解析原始输出（通常更完整）
                try:
                    if isinstance(original_output, str):
                        # 清理原始输出的控制字符
                        cleaned_original = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', original_output)
                        parsed_output = json.loads(cleaned_original)
                        self.log_info("从原始输出成功解析JSON")
                except (JSONDecodeError, TypeError):
                    # 如果原始输出解析失败，尝试清理后的输出
                    try:
                        parsed_output = json.loads(cleaned_output)
                    except (JSONDecodeError, TypeError) as e:
                        json_error = e
                        # 使用更强大的提取方法
                        extracted = extract_clean_response(cleaned_output)
                        if "error" in extracted:
                            # 最后尝试从原始输出提取
                            extracted_original = extract_clean_response(original_output)
                            if isinstance(extracted_original, dict) and "error" not in extracted_original:
                                parsed_output = extracted_original
                            elif isinstance(extracted_original, list) and len(extracted_original) > 0:
                                parsed_output = extracted_original
                            else:
                                # 保存原始输出到临时文件
                                debug_file = self._save_debug_output(original_output, cleaned_output)
                                error_msg = f"JSON解析失败。调试文件已保存到: {debug_file}"
                                self.log_error(error_msg)
                                raise ValueError(error_msg) from json_error
                        else:
                            parsed_output = extracted
                
                # 如果仍然无法解析，抛出异常
                if parsed_output is None:
                    # 保存原始输出到临时文件
                    debug_file = self._save_debug_output(original_output, cleaned_output)
                    error_msg = f"无法解析JSON响应。调试文件已保存到: {debug_file}"
                    self.log_error(error_msg)
                    raise ValueError(error_msg)
            
            # 处理解析后的输出：检查是否是新格式（包含data和markdown_summary）
            if isinstance(parsed_output, dict):
                if "data" in parsed_output and "markdown_summary" in parsed_output:
                    # 新格式：包含data和markdown_summary
                    bp_structure = parsed_output["data"]
                    markdown_summary = parsed_output.get("markdown_summary")
                    self.log_info("检测到新格式输出（包含data和markdown_summary）")
                elif "title" in parsed_output and "content" in parsed_output:
                    # 单个段落对象（旧格式）
                    bp_structure = [parsed_output]
                else:
                    # 可能是其他格式，尝试查找数组字段
                    bp_structure = parsed_output
            elif isinstance(parsed_output, list):
                # 旧格式：直接是数组
                bp_structure = parsed_output
            else:
                bp_structure = parsed_output
        
        # 验证结构 - 如果返回的是单个对象，尝试转换为数组
        if isinstance(bp_structure, dict):
            # 检查是否是单个段落对象
            if "title" in bp_structure and "content" in bp_structure:
                self.log_info("检测到单个对象格式，转换为数组")
                bp_structure = [bp_structure]
            else:
                # 尝试查找数组字段
                found_array = False
                for key in bp_structure:
                    if isinstance(bp_structure[key], list):
                        bp_structure = bp_structure[key]
                        found_array = True
                        break
                
                if not found_array:
                    # 保存调试信息
                    if cleaned_output is not None:
                        debug_file = self._save_debug_output(original_output, cleaned_output)
                        error_msg = f"BP结构应该是一个列表，但收到的是对象。调试文件已保存到: {debug_file}"
                    else:
                        error_msg = f"BP结构应该是一个列表，但收到的是对象"
                    self.log_error(error_msg)
                    raise ValueError(error_msg)
        
        # 验证结构
        if not isinstance(bp_structure, list):
            # 保存调试信息
            if cleaned_output is not None:
                debug_file = self._save_debug_output(original_output, cleaned_output)
                error_msg = f"BP结构应该是一个列表，但收到的是 {type(bp_structure)}。调试文件已保存到: {debug_file}"
            else:
                error_msg = f"BP结构应该是一个列表，但收到的是 {type(bp_structure)}"
            self.log_error(error_msg)
            raise ValueError(error_msg)
        
        # 验证数组不为空
        if len(bp_structure) == 0:
            # 保存调试信息
            if cleaned_output is not None:
                debug_file = self._save_debug_output(original_output, cleaned_output)
                error_msg = f"BP结构数组为空。调试文件已保存到: {debug_file}"
            else:
                error_msg = "BP结构数组为空"
            self.log_error(error_msg)
            raise ValueError(error_msg)
        
        # 验证每个段落
        validated_structure = []
        for i, paragraph in enumerate(bp_structure):
            if not isinstance(paragraph, dict):
                error_msg = f"段落 {i+1} 不是字典格式: {type(paragraph)}"
                self.log_error(error_msg)
                raise ValueError(error_msg)
            
            title = paragraph.get("title", f"段落 {i+1}")
            content = paragraph.get("content", "")
            
            # 验证必需字段
            if not title or not isinstance(title, str):
                error_msg = f"段落 {i+1} 的title字段无效: {title}"
                self.log_error(error_msg)
                raise ValueError(error_msg)
            
            if not isinstance(content, str):
                error_msg = f"段落 {i+1} 的content字段不是字符串: {type(content)}"
                self.log_error(error_msg)
                raise ValueError(error_msg)
            
            validated_structure.append({
                "title": title,
                "content": content
            })
        
        # 验证至少有一个段落
        if len(validated_structure) == 0:
            error_msg = "验证后没有有效的段落"
            self.log_error(error_msg)
            raise ValueError(error_msg)
        
        # 返回包含bp_structure和markdown_summary的字典
        result = {
            "bp_structure": validated_structure
        }
        
        # 如果提取到了markdown_summary，添加到结果中
        if markdown_summary:
            result["markdown_summary"] = markdown_summary
        else:
            # 如果没有markdown_summary，生成一个默认的
            result["markdown_summary"] = f"已生成包含 {len(validated_structure)} 个段落的BP结构。"
        
        return result
    
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
            filename = f"bp_structure_debug_{timestamp}.txt"
            filepath = os.path.join("/tmp", filename)
            
            # 确保 /tmp 目录存在
            os.makedirs("/tmp", exist_ok=True)
            
            # 写入文件
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write("BP Structure Node - JSON 解析失败调试信息\n")
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
            return "/tmp/bp_structure_debug_failed.txt"
    
    def mutate_state(self, input_data: Any = None, state: State = None, **kwargs) -> State:
        """
        将BP结构写入状态
        
        Args:
            input_data: 输入数据
            state: 当前状态，如果为None则创建新状态
            **kwargs: 额外参数
            
        Returns:
            更新后的状态
        """
        if state is None:
            state = State()
        
        try:
            # 生成BP结构
            bp_structure = self.run(input_data, **kwargs)
            
            # 设置查询和报告标题
            state.query = self.business_idea
            if not state.report_title:
                state.report_title = f"商业计划书 - {self.business_idea[:30]}..."
            
            # 添加段落到状态
            for paragraph_data in bp_structure:
                state.add_paragraph(
                    title=paragraph_data["title"],
                    content=paragraph_data["content"]
                )
            
            self.log_info(f"已将 {len(bp_structure)} 个段落添加到状态中")
            return state
            
        except Exception as e:
            self.log_error(f"状态更新失败: {str(e)}")
            raise e

