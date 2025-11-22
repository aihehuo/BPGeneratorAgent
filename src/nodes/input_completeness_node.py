"""
输入完整性检查节点
检查用户输入是否至少从一个视角做了完整描述
"""

import json
from typing import Dict, Any, Tuple, Optional
from json.decoder import JSONDecodeError


from .base_node import BaseNode
from ..utils.text_processing import (
    remove_reasoning_from_output,
    clean_json_tags,
    extract_clean_response,
    detect_language
)


# 输入完整性检查的输出Schema
output_schema_input_completeness = {
    "type": "object",
    "properties": {
        "is_complete": {
            "type": "boolean",
            "description": "输入是否至少从一个视角做了基本描述"
        },
        "current_perspective": {
            "type": "string",
            "enum": ["technical", "user_painpoint", "market", "mixed", "none"],
            "description": "当前输入属于哪个视角：technical(技术视角)、user_painpoint(用户痛点视角/需求视角)、market(市场视角)、mixed(混合视角)、none(无法确定)"
        },
        "perspective_details": {
            "type": "object",
            "properties": {
                "technical": {
                    "type": "object",
                    "properties": {
                        "has_content": {"type": "boolean"},
                        "completeness": {"type": "string", "enum": ["complete", "partial", "missing"]},
                        "description": {"type": "string"},
                        "checklist": {
                            "type": "object",
                            "properties": {
                                "technology_mention": {"type": "boolean", "description": "是否提及任何技术、平台或技术方法"},
                                "solution_approach": {"type": "boolean", "description": "是否描述了解决方案的基本工作原理"}
                            }
                        },
                        "missing_checkpoints": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "缺失的检查点列表"
                        }
                    }
                },
                "user_painpoint": {
                    "type": "object",
                    "properties": {
                        "has_content": {"type": "boolean"},
                        "completeness": {"type": "string", "enum": ["complete", "partial", "missing"]},
                        "description": {"type": "string"},
                        "checklist": {
                            "type": "object",
                            "properties": {
                                "problem_need_mention": {"type": "boolean", "description": "是否提及用户面临的问题或需求"},
                                "target_users": {"type": "boolean", "description": "是否提及目标用户是谁"}
                            }
                        },
                        "missing_checkpoints": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "缺失的检查点列表"
                        }
                    }
                },
                "market": {
                    "type": "object",
                    "properties": {
                        "has_content": {"type": "boolean"},
                        "completeness": {"type": "string", "enum": ["complete", "partial", "missing"]},
                        "description": {"type": "string"},
                        "checklist": {
                            "type": "object",
                            "properties": {
                                "market_mention": {"type": "boolean", "description": "是否提及任何市场、行业或目标受众"},
                                "opportunity_mention": {"type": "boolean", "description": "是否暗示了市场机会或需求"}
                            }
                        },
                        "missing_checkpoints": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "缺失的检查点列表"
                        }
                    }
                }
            }
        },
        "suggestions": {
            "type": "array",
            "items": {"type": "string"},
            "description": "改进建议"
        }
    },
    "required": ["is_complete", "current_perspective", "perspective_details", "suggestions"]
}


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
        if is_english:
            system_prompt = f"""You are a business plan expert. Your task is to evaluate whether the user's input provides a basic description from at least two perspectives.

**IMPORTANT**: This is NOT a business plan completeness check. The user only needs to provide a BASIC description of their business idea. Detailed technical specifications, comprehensive market analysis, or complete business plan details are NOT required.

The user must provide a basic description from at least TWO of the following perspectives:
1. **Technical Perspective**: Basic mention of technology, approach, or solution method (e.g., "using AI", "web platform", "mobile app")
2. **User Painpoint Perspective**: Basic description of the problem or need (e.g., "students need personalized learning", "elderly people struggle with smartphones")
3. **Market Perspective**: Basic mention of target market or opportunity (e.g., "K12 education market", "aging population")

Output JSON Schema:
{json.dumps(output_schema_input_completeness, indent=2, ensure_ascii=False)}

## Evaluation Checklist

### Technical Perspective Checklist:
- [ ] **Technology Mention**: Does the input mention any technology, platform, or technical approach? (e.g., AI, web, mobile, blockchain)
- [ ] **Solution Approach**: Does the input describe how the solution works at a basic level?

**Completeness Criteria**: At least 1 out of 2 checkpoints should be checked for "complete" status.

### User Painpoint Perspective Checklist:
- [ ] **Problem/Need Mention**: Does the input mention what problem users face or what they need?
- [ ] **Target Users**: Does the input mention who the target users are? (can be very general, e.g., "students", "elderly", "small businesses")

**Completeness Criteria**: At least 1 out of 2 checkpoints should be checked for "complete" status.

### Market Perspective Checklist:
- [ ] **Market Mention**: Does the input mention any market, industry, or target audience? (can be very general)
- [ ] **Opportunity Mention**: Does the input hint at a market opportunity or need?

**Completeness Criteria**: At least 1 out of 2 checkpoints should be checked for "complete" status.

## Evaluation Rules:
1. For each perspective, check ALL checklist items and mark them as true/false
2. Count how many checkpoints are checked (true) for each perspective
3. Determine completeness:
   - **complete**: Meets the completeness criteria (1+ checkpoints checked)
   - **partial**: 1 checkpoint checked but description is very vague
   - **missing**: 0 checkpoints checked
4. List all unchecked items in the "missing_checkpoints" array for each perspective
5. **IMPORTANT**: At least TWO perspectives must be "complete" for is_complete to be true
6. If fewer than 2 perspectives are "complete", set is_complete to false
7. Determine current_perspective based on which perspective has the most checked items (use "mixed" if multiple perspectives have similar scores)
8. Provide brief, simple suggestions for improvement, focusing on adding content from the missing perspective(s)

**Be lenient**: If the input provides meaningful description from at least 2 perspectives, it should pass. Only reject inputs that are completely empty, meaningless, or provide no context at all.

Return only a JSON object that conforms to the output schema. Do not include any explanation or additional text."""
            
            user_prompt = f"""Please evaluate the completeness of the following business idea. Remember: we only need a BASIC description, not a detailed business plan.

**IMPORTANT**: The input must provide basic descriptions from at least TWO perspectives to pass.

{business_idea}

Analyze from three perspectives (technical, user painpoint, market) and determine if at least two perspectives provide basic descriptions."""
        else:
            system_prompt = f"""你是一位商业计划书专家。你的任务是评估用户的输入是否至少从两个视角做了基本描述。

**重要提示**：这不是商业计划书的完整性检查。用户只需要提供商业创意的**基本描述**即可。不需要详细的技术规格、全面的市场分析或完整的商业计划细节。

用户必须至少从以下三个视角中的两个提供基本描述：
1. **技术视角**：基本提及技术、方法或解决方案（例如："使用AI"、"Web平台"、"移动应用"）
2. **用户痛点视角（需求视角）**：基本描述问题或需求（例如："学生需要个性化学习"、"老年人使用智能手机困难"）
3. **市场视角**：基本提及目标市场或机会（例如："K12教育市场"、"老龄化人群"）

输出JSON模式：
{json.dumps(output_schema_input_completeness, indent=2, ensure_ascii=False)}

## 评估检查清单

### 技术视角检查清单：
- [ ] **技术提及**：输入是否提及任何技术、平台或技术方法？（例如：AI、Web、移动应用、区块链等）
- [ ] **解决方案方法**：输入是否描述了解决方案的基本工作原理？

**完整性标准**：至少满足2项中的1项即可判定为"完整"。

### 用户痛点视角检查清单：
- [ ] **问题/需求提及**：输入是否提及用户面临的问题或需求？
- [ ] **目标用户**：输入是否提及目标用户是谁？（可以非常笼统，例如："学生"、"老年人"、"小企业"）

**完整性标准**：至少满足2项中的1项即可判定为"完整"。

### 市场视角检查清单：
- [ ] **市场提及**：输入是否提及任何市场、行业或目标受众？（可以非常笼统）
- [ ] **机会提及**：输入是否暗示了市场机会或需求？

**完整性标准**：至少满足2项中的1项即可判定为"完整"。

## 评估规则：
1. 对每个视角，检查所有检查清单项目并标记为true/false
2. 统计每个视角有多少个检查点被勾选（true）
3. 确定完整性：
   - **complete**：满足完整性标准（1个或以上检查点被勾选）
   - **partial**：1个检查点被勾选但描述非常模糊
   - **missing**：0个检查点被勾选
4. 将所有未勾选的项目列在"missing_checkpoints"数组中
5. **重要**：至少需要两个视角是"complete"，is_complete才能设置为true
6. 如果少于2个视角是"complete"，则设置is_complete为false
7. 根据检查点最多的视角确定current_perspective（如果多个视角得分相近，使用"mixed"）
8. 提供简洁的改进建议，重点关注补充缺失视角的内容

**请宽松评估**：如果输入从至少2个视角提供了有意义的描述，应该通过。只有完全空白、无意义或完全没有上下文的输入才应该被拒绝。

只返回符合输出模式的JSON对象，不要有解释或额外文本。"""
            
            user_prompt = f"""请评估以下商业创意的完整性。记住：我们只需要基本描述，不需要详细的商业计划。

**重要**：输入必须从至少两个视角提供基本描述才能通过。

{business_idea}

从三个视角（技术视角、用户痛点视角、市场视角）进行分析，判断是否至少有两个视角提供了基本描述。"""
        
        return system_prompt, user_prompt
    
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

