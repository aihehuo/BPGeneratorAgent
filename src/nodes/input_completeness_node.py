"""
输入完整性检查节点
检查用户输入是否至少从一个视角做了完整描述
"""

import json
from typing import Dict, Any, Tuple, Optional
from json.decoder import JSONDecodeError


from .base_node import BaseNode
from ..prompts.input_completeness import (
    output_schema_input_completeness,
    get_input_completeness_prompt
)
from ..utils.text_processing import (
    remove_reasoning_from_output,
    clean_json_tags,
    extract_clean_response,
    detect_language
)




class InputCompletenessNode(BaseNode):
    """输入完整性检查节点"""
    
    def __init__(self, llm_client):
        """
        初始化输入完整性检查节点
        
        Args:
            llm_client: LLM客户端
        """
        super().__init__(llm_client, "InputCompletenessNode")
    
    
    def _get_checkpoint_names(self, perspective: str) -> Dict[str, str]:
        """
        获取检查点的中文名称映射
        
        Args:
            perspective: 视角名称
            
        Returns:
            检查点名称映射字典
        """
        checkpoint_names = {
            "technical": {
                "technology_mention": "技术提及",
                "solution_approach": "解决方案方法",
                # 保留旧字段以兼容可能的历史数据
                "technology_stack": "技术栈",
                "technical_architecture": "技术架构",
                "implementation_method": "实现方法",
                "technical_advantages": "技术优势",
                "development_approach": "开发方式"
            },
            "user_painpoint": {
                "problem_need_mention": "问题/需求提及",
                "target_users": "目标用户",
                # 保留旧字段以兼容可能的历史数据
                "specific_pain_points": "具体痛点",
                "target_user_groups": "目标用户群体",
                "problem_scenarios": "问题场景",
                "user_needs": "用户需求",
                "use_cases": "使用场景"
            },
            "market": {
                "market_mention": "市场提及",
                "opportunity_mention": "机会提及",
                # 保留旧字段以兼容可能的历史数据
                "market_size": "市场规模",
                "market_trends": "市场趋势",
                "competitive_analysis": "竞争分析",
                "market_opportunities": "市场机会",
                "target_market_segments": "目标市场细分",
                "market_positioning": "市场定位"
            }
        }
        return checkpoint_names.get(perspective, {})
    
    def _format_checklist(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        格式化检查清单信息，供外部显示使用
        
        Args:
            result: 检查结果
            
        Returns:
            格式化的检查清单信息
        """
        formatted = {}
        perspective_details = result.get("perspective_details", {})
        
        for perspective, details in perspective_details.items():
            checklist = details.get("checklist", {})
            missing_checkpoints = details.get("missing_checkpoints", [])
            checkpoint_names = self._get_checkpoint_names(perspective)
            
            # 格式化检查清单状态
            checklist_status = []
            for key, value in checklist.items():
                status = "✓" if value else "✗"
                checkpoint_name = checkpoint_names.get(key, key)
                checklist_status.append({
                    "key": key,
                    "name": checkpoint_name,
                    "status": status,
                    "checked": value
                })
            
            formatted[perspective] = {
                "checklist_status": checklist_status,
                "missing_checkpoints": missing_checkpoints,
                "checkpoint_names": checkpoint_names
            }
        
        return formatted
    
    def _build_prompt(self, business_idea: str, is_english: bool) -> Tuple[str, str]:
        """
        构建系统提示词和用户提示词
        
        Args:
            business_idea: 商业创意
            is_english: 是否为英文
            
        Returns:
            (system_prompt, user_prompt) 元组
        """
        return get_input_completeness_prompt(business_idea, is_english)
    
    def run(self, business_idea: str, previous_inputs: Optional[str] = None, session_id: Optional[str] = None, session_dir: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        执行输入完整性检查
        
        Args:
            business_idea: 商业创意
            previous_inputs: 之前的用户输入（可选），如果提供则与当前输入合并检查
            session_id: Session ID（可选），用于向后兼容的文件系统保存
            session_dir: Session目录路径（可选，向后兼容），用于文件系统保存
            **kwargs: 额外参数（保留用于向后兼容）
            
        Returns:
            Dict[str, Any]: 检查结果，包含：
                - is_complete: bool, 是否完整
                - current_perspective: str, 当前视角
                - perspective_details: dict, 各视角的详细信息
                - suggestions: list, 改进建议
        
        Note:
            Chat history persistence is now handled at the wrapper level (InputNode).
            This method focuses only on the core completeness checking logic.
            session_id/session_dir are kept for backward compatibility when used outside the graph.
        """
        try:
            self.log_info("正在检查输入完整性...")
            
            # Note: previous_inputs should be provided by the wrapper (InputNode)
            # Chat history management is now handled at the workflow level
            
            # 合并之前的输入和当前输入（如果提供了previous_inputs且不为空）
            if previous_inputs:
                combined_input = f"{previous_inputs}\n\n---\n\n当前输入:\n{business_idea}"
                self.log_info("已合并之前的输入和当前输入一起检查")
                # 记录合并后的输入（截断过长的内容）
                input_preview = combined_input[:500] + "..." if len(combined_input) > 500 else combined_input
                self.log_info(f"合并后的输入预览（总长度: {len(combined_input)} 字符）:\n{input_preview}")
            else:
                combined_input = business_idea
                self.log_info(f"当前输入（无历史记录，长度: {len(combined_input)} 字符）:\n{combined_input[:500] + '...' if len(combined_input) > 500 else combined_input}")
            
            # 检测语言（使用合并后的输入）
            is_english = detect_language(combined_input) == 'en'
            
            # 构建提示词（使用合并后的输入）
            system_prompt, user_prompt = self._build_prompt(combined_input, is_english)
            
            # 调用LLM (使用新的 invoke_llm 方法)
            response = self.invoke_llm(system_prompt, user_prompt)
            
            # 处理响应
            result = self.process_output(response)
            
            # Note: Chat history persistence is now handled at the wrapper level
            # Add session_id to result if available
            if session_id:
                result["session_id"] = session_id
            
            self.log_info(f"输入完整性检查完成: is_complete={result.get('is_complete')}, perspective={result.get('current_perspective')}")
            return result
            
        except Exception as e:
            self.log_error(f"输入完整性检查失败: {str(e)}")
            raise e
    
    def process_output(self, output: str) -> Dict[str, Any]:
        """
        处理LLM输出，提取检查结果
        
        Args:
            output: LLM原始输出
            
        Returns:
            Dict[str, Any]: 处理后的检查结果
        """
        try:
            # 记录原始响应（用于调试）
            self.log_info(f"LLM原始响应长度: {len(output)} 字符")
            if len(output) > 100000:
                self.log_info(f"LLM原始响应前500字符: {output[:500]}...")
            else:
                self.log_info(f"LLM原始响应: {output}")
            
            # 清理响应文本
            # cleaned_output = remove_reasoning_from_output(output)
            cleaned_output = clean_json_tags(output)
            self.log_info(f"清理后的响应长度: {len(cleaned_output)} 字符")
            self.log_info(f"清理后的响应: {cleaned_output}")
            
            # 尝试多种方法解析JSON
            result = None
            
            # 方法1: 直接解析
            try:
                result = json.loads(cleaned_output)
                self.log_info("JSON解析成功（直接解析）")
            except JSONDecodeError as e:
                error_msg = str(e)
                self.log_info(f"直接JSON解析失败: {error_msg}")
                
                # 方法2: 尝试解析第一个完整的JSON对象（处理"Extra data"错误）
                if "Extra data" in error_msg or "unexpected" in error_msg.lower():
                    try:
                        # 找到第一个完整的JSON对象
                        brace_count = 0
                        start_idx = -1
                        json_end = -1
                        in_string = False
                        escape_next = False
                        
                        for i, char in enumerate(cleaned_output):
                            if escape_next:
                                escape_next = False
                                continue
                            
                            if char == '\\':
                                escape_next = True
                                continue
                            
                            if char == '"':
                                in_string = not in_string
                                continue
                            
                            if in_string:
                                continue
                            
                            if char == '{':
                                if brace_count == 0:
                                    start_idx = i
                                brace_count += 1
                            elif char == '}':
                                brace_count -= 1
                                if brace_count == 0 and start_idx != -1:
                                    json_end = i + 1
                                    break
                        
                        if start_idx != -1 and json_end != -1:
                            json_str = cleaned_output[start_idx:json_end]
                            self.log_info(f"提取的JSON字符串长度: {len(json_str)} 字符")
                            try:
                                result = json.loads(json_str)
                                if isinstance(result, dict):
                                    self.log_info(f"JSON解析成功（提取第一个完整JSON对象，位置 {start_idx}-{json_end}）")
                                    self.log_info(f"提取的JSON包含字段: {list(result.keys())}")
                                else:
                                    result = None
                            except JSONDecodeError as e2:
                                self.log_info(f"提取的JSON字符串解析失败: {str(e2)}")
                                self.log_info(f"提取的JSON字符串前200字符: {json_str[:200]}")
                                result = None
                        else:
                            self.log_info("未能找到完整的JSON对象边界")
                            result = None
                    except Exception as e2:
                        self.log_info(f"提取第一个JSON对象失败: {str(e2)}")
                        import traceback
                        self.log_info(f"详细错误: {traceback.format_exc()}")
                        result = None
                else:
                    result = None
                
                # 方法3: 使用extract_clean_response
                if result is None:
                    try:
                        result = extract_clean_response(cleaned_output)
                        if isinstance(result, dict):
                            self.log_info("JSON解析成功（使用extract_clean_response）")
                        else:
                            result = None
                    except Exception as e3:
                        self.log_info(f"extract_clean_response失败: {str(e3)}")
                
                # 方法4: 尝试查找并提取完整的JSON对象（通过匹配大括号）
                if result is None:
                    try:
                        # 查找所有可能的JSON对象
                        brace_count = 0
                        start_idx = -1
                        json_objects = []
                        for i, char in enumerate(cleaned_output):
                            if char == '{':
                                if brace_count == 0:
                                    start_idx = i
                                brace_count += 1
                            elif char == '}':
                                brace_count -= 1
                                if brace_count == 0 and start_idx != -1:
                                    json_str = cleaned_output[start_idx:i+1]
                                    json_objects.append((start_idx, i+1, json_str))
                                    start_idx = -1
                        
                        # 尝试解析找到的JSON对象（从最长的开始）
                        if json_objects:
                            json_objects.sort(key=lambda x: x[1] - x[0], reverse=True)
                            for start, end, json_str in json_objects:
                                try:
                                    result = json.loads(json_str)
                                    if isinstance(result, dict):
                                        self.log_info(f"JSON解析成功（提取JSON对象，位置 {start}-{end}）")
                                        break
                                except JSONDecodeError:
                                    continue
                    except Exception as e4:
                        self.log_info(f"JSON对象提取失败: {str(e4)}")
            
            # 如果仍然无法解析，抛出错误
            if result is None or not isinstance(result, dict):
                self.log_error(f"无法解析JSON响应，清理后的文本长度: {len(cleaned_output)}")
                self.log_error(f"清理后的文本前1000字符: {cleaned_output[:1000]}")
                raise ValueError("输入完整性检查结果格式错误：无法解析JSON")
            
            # 检查是否是新格式（包含data和markdown_summary）
            markdown_summary = None
            if "data" in result and "markdown_summary" in result:
                # 新格式：包含data和markdown_summary
                markdown_summary = result.get("markdown_summary")
                result = result["data"]  # 提取data字段作为实际结果
                self.log_info("检测到新格式输出（包含data和markdown_summary）")
            elif "markdown_summary" in result:
                # markdown_summary 在顶层，但 data 不在（可能是旧格式但包含summary）
                markdown_summary = result.pop("markdown_summary")
            
            # 验证必需字段
            required_fields = ["is_complete", "current_perspective", "perspective_details", "suggestions"]
            missing_fields = []
            for field in required_fields:
                if field not in result:
                    missing_fields.append(field)
            
            if missing_fields:
                self.log_error(f"缺少必需字段: {', '.join(missing_fields)}")
                self.log_error(f"当前结果包含的字段: {list(result.keys())}")
                
                # 检查是否有perspective_details但结构不对
                if "perspective_details" not in result:
                    # 检查是否perspective_details的内容直接在result中
                    if "technical" in result or "user_painpoint" in result or "market" in result:
                        self.log_info("检测到perspective_details内容在顶层，进行重组")
                        perspective_details = {}
                        for perspective in ["technical", "user_painpoint", "market"]:
                            if perspective in result:
                                perspective_details[perspective] = result.pop(perspective)
                        result["perspective_details"] = perspective_details
                
                # 尝试补充缺失的字段
                if "is_complete" not in result:
                    # 尝试从perspective_details推断：至少需要2个视角是"complete"
                    perspective_details = result.get("perspective_details", {})
                    complete_count = 0
                    for details in perspective_details.values():
                        if isinstance(details, dict) and details.get("completeness") == "complete":
                            complete_count += 1
                    is_complete = complete_count >= 2
                    result["is_complete"] = is_complete
                    self.log_info(f"自动补充is_complete字段: {is_complete} (完整视角数量: {complete_count})")
                
                if "current_perspective" not in result:
                    # 尝试从perspective_details推断
                    perspective_details = result.get("perspective_details", {})
                    max_completeness = 0
                    best_perspective = "none"
                    for perspective, details in perspective_details.items():
                        if isinstance(details, dict):
                            checklist = details.get("checklist", {})
                            checked_count = sum(1 for v in checklist.values() if v)
                            if checked_count > max_completeness:
                                max_completeness = checked_count
                                best_perspective = perspective
                    result["current_perspective"] = best_perspective
                    self.log_info(f"自动补充current_perspective字段: {best_perspective}")
                
                if "perspective_details" not in result:
                    result["perspective_details"] = {}
                    self.log_info("自动补充perspective_details字段: {}")
                
                if "suggestions" not in result:
                    result["suggestions"] = []
                    self.log_info("自动补充suggestions字段: []")
            
            # 确保is_complete是布尔值，并验证是否符合至少2个视角的要求
            if isinstance(result.get("is_complete"), bool):
                # 如果已经是布尔值，验证是否符合至少2个视角的要求
                if result["is_complete"]:
                    perspective_details = result.get("perspective_details", {})
                    complete_count = sum(1 for details in perspective_details.values() 
                                       if isinstance(details, dict) and details.get("completeness") == "complete")
                    if complete_count < 2:
                        result["is_complete"] = False
                        self.log_info(f"修正is_complete: 虽然LLM返回true，但只有{complete_count}个完整视角，需要至少2个")
            else:
                # 尝试转换
                is_complete_str = str(result.get("is_complete", "false")).lower()
                is_complete_bool = is_complete_str in ("true", "1", "yes", "是", "完整")
                # 验证是否符合至少2个视角的要求
                if is_complete_bool:
                    perspective_details = result.get("perspective_details", {})
                    complete_count = sum(1 for details in perspective_details.values() 
                                       if isinstance(details, dict) and details.get("completeness") == "complete")
                    if complete_count < 2:
                        is_complete_bool = False
                        self.log_info(f"修正is_complete: 虽然转换后为true，但只有{complete_count}个完整视角，需要至少2个")
                result["is_complete"] = is_complete_bool
            
            # 确保每个视角都有checklist和missing_checkpoints字段
            perspective_details = result.get("perspective_details", {})
            for perspective in ["technical", "user_painpoint", "market"]:
                if perspective in perspective_details:
                    details = perspective_details[perspective]
                    # 如果没有checklist，创建空的checklist
                    if "checklist" not in details:
                        details["checklist"] = {}
                    # 如果没有missing_checkpoints，根据checklist生成
                    if "missing_checkpoints" not in details:
                        checklist = details.get("checklist", {})
                        missing = []
                        checkpoint_names = self._get_checkpoint_names(perspective)
                        for key, value in checklist.items():
                            if not value:  # 如果检查点未勾选
                                missing.append(checkpoint_names.get(key, key))
                        details["missing_checkpoints"] = missing
            
            # 添加格式化的检查清单信息
            result["formatted_checklist"] = self._format_checklist(result)
            
            # 如果提取到了markdown_summary，添加到结果中
            if markdown_summary:
                result["markdown_summary"] = markdown_summary
            
            return result
            
        except Exception as e:
            self.log_error(f"处理输出失败: {str(e)}")
            # 返回默认的不完整结果
            return {
                "is_complete": False,
                "current_perspective": "none",
                "perspective_details": {
                    "technical": {
                        "has_content": False,
                        "completeness": "missing",
                        "description": "",
                        "checklist": {
                            "technology_stack": False,
                            "technical_architecture": False,
                            "implementation_method": False,
                            "technical_advantages": False,
                            "development_approach": False
                        },
                        "missing_checkpoints": ["技术栈", "技术架构", "实现方法", "技术优势", "开发方式"]
                    },
                    "user_painpoint": {
                        "has_content": False,
                        "completeness": "missing",
                        "description": "",
                        "checklist": {
                            "specific_pain_points": False,
                            "target_user_groups": False,
                            "problem_scenarios": False,
                            "user_needs": False,
                            "use_cases": False
                        },
                        "missing_checkpoints": ["具体痛点", "目标用户群体", "问题场景", "用户需求", "使用场景"]
                    },
                    "market": {
                        "has_content": False,
                        "completeness": "missing",
                        "description": "",
                        "checklist": {
                            "market_size": False,
                            "market_trends": False,
                            "competitive_analysis": False,
                            "market_opportunities": False,
                            "target_market_segments": False,
                            "market_positioning": False
                        },
                        "missing_checkpoints": ["市场规模", "市场趋势", "竞争分析", "市场机会", "目标市场细分", "市场定位"]
                    }
                },
                "suggestions": ["无法解析检查结果，请提供更详细的商业创意描述"]
            }

