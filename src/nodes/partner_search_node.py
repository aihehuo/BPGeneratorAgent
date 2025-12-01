"""
合伙人员搜索节点
根据BP内容搜索符合条件的合伙人和投资人
"""

import json
import re
import traceback
from typing import Dict, Any, List, Optional
from .base_node import BaseNode
from ..prompts.partner_search import SYSTEM_PROMPT_PARTNER_SEARCH
from ..tools.aihehuo import search_members
from ..utils.text_processing import (
    remove_reasoning_from_output,
    clean_json_tags,
    extract_clean_response,
    detect_language
)


class PartnerSearchNode(BaseNode):
    """合伙人员搜索节点"""
    
    def __init__(self, llm_client, api_key: Optional[str] = None, api_base: Optional[str] = None):
        """
        初始化合伙人员搜索节点
        
        Args:
            llm_client: LLM客户端（用于优化搜索查询，可选）
            api_key: 爱合伙API密钥（可选）
            api_base: 爱合伙API基础URL（可选）
        """
        super().__init__(llm_client, "PartnerSearchNode")
        self.api_key = api_key
        self.api_base = api_base
    
    def validate_input(self, input_data: Any) -> bool:
        """验证输入数据"""
        if isinstance(input_data, dict):
            # 需要包含business_idea和bp_structure
            return "business_idea" in input_data and "bp_structure" in input_data
        return False
    
    def run(
        self,
        input_data: Any,
        partner_per_page: int = 10,
        investor_per_page: int = 10,
        wechat_reachable_only: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        从BP中提炼搜索短语，搜索符合条件的合伙人和投资人
        
        Args:
            input_data: 包含business_idea和bp_structure的字典
            partner_per_page: 合伙人搜索结果每页数量
            investor_per_page: 投资人搜索结果每页数量
            wechat_reachable_only: 是否只返回微信上能直接触达的用户
            **kwargs: 额外参数
            
        Returns:
            搜索结果字典，包含：
            - partner_search_query: 合伙人搜索查询
            - partner_results: 合伙人搜索结果列表
            - investor_search_query: 投资人搜索查询
            - investor_results: 投资人搜索结果列表
            - partner_count: 合伙人结果总数
            - investor_count: 投资人结果总数
        """
        try:
            if not self.validate_input(input_data):
                raise ValueError("输入数据格式错误，需要包含business_idea和bp_structure字段")
            
            business_idea = input_data["business_idea"]
            bp_structure = input_data["bp_structure"]
            
            self.log_info("正在从BP中提炼搜索短语...")
            
            # 从BP中提炼搜索短语
            search_phrases = self._extract_search_phrases(business_idea, bp_structure)
            
            partner_query = search_phrases.get("partner_query", "")
            investor_query = search_phrases.get("investor_query", "")
            initial_summary = search_phrases.get("markdown_summary", "")
            
            # 打印提炼出的搜索短语
            self.log_info(f"提炼出的合伙人搜索短语: {partner_query}")
            self.log_info(f"提炼出的投资人搜索短语: {investor_query}")
            print(f"\n[PartnerSearch] 合伙人搜索短语: {partner_query}")
            print(f"[PartnerSearch] 投资人搜索短语: {investor_query}")
            
            result = {
                "partner_search_query": partner_query,
                "investor_search_query": investor_query,
                "partner_results": [],
                "investor_results": [],
                "partner_count": 0,
                "investor_count": 0,
                "markdown_summary": initial_summary
            }
            
            # 搜索合伙人
            if partner_query and len(partner_query.strip()) > 5:
                self.log_info(f"正在搜索合伙人: {partner_query}")
                print(f"[PartnerSearch] 执行合伙人搜索，查询: {partner_query}")
                try:
                    partner_results = search_members(
                        query=partner_query,
                        page=1,
                        per_page=partner_per_page,
                        wechat_reachable_only=wechat_reachable_only,
                        investor=False,
                        api_key=self.api_key,
                        api_base=self.api_base
                    )
                    # search_members已经返回字典列表，直接使用
                    result["partner_results"] = partner_results
                    result["partner_count"] = len(partner_results)
                    self.log_info(f"找到 {len(partner_results)} 个符合条件的合伙人")
                    print(f"[PartnerSearch] 合伙人搜索结果: {len(partner_results)} 个")
                except Exception as e:
                    self.log_error(f"搜索合伙人时出错: {str(e)}")
                    print(f"[PartnerSearch] 搜索合伙人失败: {str(e)}")
                    traceback.print_exc()
            else:
                reason = "查询为空" if not partner_query else f"查询太短（长度: {len(partner_query.strip())}，需要>5）"
                self.log_info(f"未生成有效的合伙人搜索查询，跳过合伙人搜索。原因: {reason}")
                print(f"[PartnerSearch] 跳过合伙人搜索。原因: {reason}")
                if partner_query:
                    print(f"[PartnerSearch] 合伙人搜索短语（无效）: {partner_query}")
            
            # 搜索投资人
            if investor_query and len(investor_query.strip()) > 5:
                self.log_info(f"正在搜索投资人: {investor_query}")
                print(f"[PartnerSearch] 执行投资人搜索，查询: {investor_query}")
                try:
                    investor_results = search_members(
                        query=investor_query,
                        page=1,
                        per_page=investor_per_page,
                        wechat_reachable_only=wechat_reachable_only,
                        investor=True,
                        api_key=self.api_key,
                        api_base=self.api_base
                    )
                    # search_members已经返回字典列表，直接使用
                    result["investor_results"] = investor_results
                    result["investor_count"] = len(investor_results)
                    self.log_info(f"找到 {len(investor_results)} 个符合条件的投资人")
                    print(f"[PartnerSearch] 投资人搜索结果: {len(investor_results)} 个")
                except Exception as e:
                    self.log_error(f"搜索投资人时出错: {str(e)}")
                    print(f"[PartnerSearch] 搜索投资人失败: {str(e)}")
                    traceback.print_exc()
            else:
                reason = "查询为空" if not investor_query else f"查询太短（长度: {len(investor_query.strip())}，需要>5）"
                self.log_info(f"未生成有效的投资人搜索查询，跳过投资人搜索。原因: {reason}")
                print(f"[PartnerSearch] 跳过投资人搜索。原因: {reason}")
                if investor_query:
                    print(f"[PartnerSearch] 投资人搜索短语（无效）: {investor_query}")
            
            # 生成增强的markdown摘要，包含搜索结果
            enhanced_summary = self._generate_enhanced_summary(
                initial_summary=initial_summary,
                partner_query=partner_query,
                investor_query=investor_query,
                partner_count=result["partner_count"],
                investor_count=result["investor_count"],
                partner_results=result["partner_results"],
                investor_results=result["investor_results"],
                business_idea=business_idea
            )
            result["markdown_summary"] = enhanced_summary
            
            return result
            
        except Exception as e:
            self.log_error(f"搜索合伙人员失败: {str(e)}")
            traceback.print_exc()
            return {
                "partner_search_query": "",
                "investor_search_query": "",
                "partner_results": [],
                "investor_results": [],
                "partner_count": 0,
                "investor_count": 0,
                "markdown_summary": "",
                "error": str(e)
            }
    
    def _generate_enhanced_summary(
        self,
        initial_summary: str,
        partner_query: str,
        investor_query: str,
        partner_count: int,
        investor_count: int,
        partner_results: List[Dict[str, Any]],
        investor_results: List[Dict[str, Any]],
        business_idea: str
    ) -> str:
        """
        生成增强的markdown摘要，包含搜索短语和搜索结果
        
        Args:
            initial_summary: 初始的markdown摘要（从LLM提取搜索短语时生成）
            partner_query: 合伙人搜索查询
            investor_query: 投资人搜索查询
            partner_count: 找到的合伙人数量
            investor_count: 找到的投资人数量
            partner_results: 合伙人搜索结果列表
            investor_results: 投资人搜索结果列表
            business_idea: 商业创意（用于语言检测）
            
        Returns:
            增强的markdown摘要
        """
        try:
            # 检测语言
            detected_lang = detect_language(business_idea)
            is_english = detected_lang == 'en'
            
            # 构建增强摘要
            summary_parts = []
            
            # 添加初始摘要（如果有）
            if initial_summary and initial_summary.strip():
                summary_parts.append(initial_summary.strip())
            
            # 添加搜索结果部分
            if is_english:
                summary_parts.append("\n## Search Results")
                
                # 合伙人搜索结果
                if partner_query:
                    summary_parts.append(f"\n**Partner Search**: Used query \"{partner_query}\"")
                    if partner_count > 0:
                        summary_parts.append(f"- Found **{partner_count}** potential partner(s)")
                        # 添加前3个合伙人的关键信息
                        if partner_results:
                            summary_parts.append("- Top matches:")
                            for i, partner in enumerate(partner_results[:3], 1):
                                name = partner.get("name", partner.get("nickname", "Unknown"))
                                bio = partner.get("bio", partner.get("goal", ""))
                                if bio:
                                    bio_preview = bio[:50] + "..." if len(bio) > 50 else bio
                                    summary_parts.append(f"  {i}. {name}: {bio_preview}")
                                else:
                                    summary_parts.append(f"  {i}. {name}")
                    else:
                        summary_parts.append("- No partners found matching the criteria")
                else:
                    summary_parts.append("\n**Partner Search**: No valid search query generated")
                
                # 投资人搜索结果
                if investor_query:
                    summary_parts.append(f"\n**Investor Search**: Used query \"{investor_query}\"")
                    if investor_count > 0:
                        summary_parts.append(f"- Found **{investor_count}** potential investor(s)")
                        # 添加前3个投资人的关键信息
                        if investor_results:
                            summary_parts.append("- Top matches:")
                            for i, investor in enumerate(investor_results[:3], 1):
                                name = investor.get("name", investor.get("nickname", "Unknown"))
                                bio = investor.get("bio", investor.get("goal", ""))
                                if bio:
                                    bio_preview = bio[:50] + "..." if len(bio) > 50 else bio
                                    summary_parts.append(f"  {i}. {name}: {bio_preview}")
                                else:
                                    summary_parts.append(f"  {i}. {name}")
                    else:
                        summary_parts.append("- No investors found matching the criteria")
                else:
                    summary_parts.append("\n**Investor Search**: No valid search query generated")
            else:
                summary_parts.append("\n## 搜索结果")
                
                # 合伙人搜索结果
                if partner_query:
                    summary_parts.append(f"\n**合伙人搜索**：使用查询 \"{partner_query}\"")
                    if partner_count > 0:
                        summary_parts.append(f"- 找到 **{partner_count}** 位潜在合伙人")
                        # 添加前3个合伙人的关键信息
                        if partner_results:
                            summary_parts.append("- 匹配结果：")
                            for i, partner in enumerate(partner_results[:3], 1):
                                name = partner.get("name", partner.get("nickname", "未知"))
                                bio = partner.get("bio", partner.get("goal", ""))
                                if bio:
                                    bio_preview = bio[:50] + "..." if len(bio) > 50 else bio
                                    summary_parts.append(f"  {i}. {name}：{bio_preview}")
                                else:
                                    summary_parts.append(f"  {i}. {name}")
                    else:
                        summary_parts.append("- 未找到符合条件的合伙人")
                else:
                    summary_parts.append("\n**合伙人搜索**：未生成有效的搜索查询")
                
                # 投资人搜索结果
                if investor_query:
                    summary_parts.append(f"\n**投资人搜索**：使用查询 \"{investor_query}\"")
                    if investor_count > 0:
                        summary_parts.append(f"- 找到 **{investor_count}** 位潜在投资人")
                        # 添加前3个投资人的关键信息
                        if investor_results:
                            summary_parts.append("- 匹配结果：")
                            for i, investor in enumerate(investor_results[:3], 1):
                                name = investor.get("name", investor.get("nickname", "未知"))
                                bio = investor.get("bio", investor.get("goal", ""))
                                if bio:
                                    bio_preview = bio[:50] + "..." if len(bio) > 50 else bio
                                    summary_parts.append(f"  {i}. {name}：{bio_preview}")
                                else:
                                    summary_parts.append(f"  {i}. {name}")
                    else:
                        summary_parts.append("- 未找到符合条件的投资人")
                else:
                    summary_parts.append("\n**投资人搜索**：未生成有效的搜索查询")
            
            return "\n".join(summary_parts)
            
        except Exception as e:
            self.log_error(f"生成增强摘要失败: {str(e)}")
            # 如果失败，至少返回初始摘要
            return initial_summary if initial_summary else ""
    
    def _extract_search_phrases(
        self,
        business_idea: str,
        bp_structure: List[Dict[str, str]]
    ) -> Dict[str, str]:
        """
        从BP中提炼搜索合伙人和投资人的短语
        
        Args:
            business_idea: 商业创意
            bp_structure: BP结构列表
            
        Returns:
            包含partner_query、investor_query和markdown_summary的字典
        """
        try:
            # 构建BP内容摘要
            bp_content = f"商业创意：{business_idea}\n\n"
            bp_content += "商业计划书结构：\n"
            
            for idx, section in enumerate(bp_structure, 1):
                title = section.get("title", f"段落{idx}")
                content = section.get("content", "")
                bp_content += f"\n{idx}. {title}\n{content}\n"
            
            # 限制BP内容长度
            bp_summary = bp_content[:2500]  # 限制长度避免token过多
            
            # 构建用户提示词
            user_prompt = f"""根据以下商业计划书内容，提炼出两个搜索短语：

1. **合伙人搜索短语**：用于搜索符合项目需求的合伙人/团队成员（如技术合伙人、市场合伙人、产品合伙人等）
2. **投资人搜索短语**：用于搜索可能对项目感兴趣的投资人/投资机构

商业计划书内容：
{bp_summary}

要求：
- 搜索短语要具体、明确，便于语义搜索
- 合伙人搜索短语应突出所需技能、经验、行业背景等
- 投资人搜索短语应突出项目特点、行业、阶段等
- 返回系统提示中指定格式的JSON，不要包含其他解释
- **输出的语言必须与商业计划书的语言一致**（英文输入用英文，中文输入用中文）"""

            self.log_info("正在使用LLM提炼搜索短语...")
            response = self.invoke_llm(
                SYSTEM_PROMPT_PARTNER_SEARCH,
                user_prompt
            )
            
            # 打印LLM原始响应（用于调试）
            self.log_info(f"LLM响应原始内容: {response[:500]}...")
            print(f"\n[PartnerSearch] LLM提炼搜索短语的原始响应:")
            print(f"{response[:500]}...")
            
            # 解析LLM响应
            search_phrases = self._parse_search_phrases(response)
            
            # 打印解析后的搜索短语
            parsed_partner = search_phrases.get("partner_query", "")
            parsed_investor = search_phrases.get("investor_query", "")
            initial_summary = search_phrases.get("markdown_summary", "")
            self.log_info(f"解析后的合伙人搜索短语: {parsed_partner}")
            self.log_info(f"解析后的投资人搜索短语: {parsed_investor}")
            if initial_summary:
                self.log_info(f"初始Markdown摘要: {initial_summary[:100]}...")
            print(f"[PartnerSearch] 解析后的合伙人搜索短语: {parsed_partner}")
            print(f"[PartnerSearch] 解析后的投资人搜索短语: {parsed_investor}")
            
            return search_phrases
            
        except Exception as e:
            self.log_error(f"提炼搜索短语失败: {str(e)}")
            # 如果失败，使用简化的默认查询
            return {
                "partner_query": f"寻找{business_idea[:30]}项目的合伙人",
                "investor_query": f"寻找{business_idea[:30]}项目的投资人",
                "markdown_summary": ""
            }
    
    def _parse_search_phrases(self, response: str) -> Dict[str, str]:
        """
        解析LLM响应中的搜索短语和markdown摘要
        
        Args:
            response: LLM响应文本
            
        Returns:
            包含partner_query、investor_query和markdown_summary的字典
        """
        try:
            # 清理响应文本
            cleaned_response = remove_reasoning_from_output(response)
            cleaned_response = clean_json_tags(cleaned_response)
            cleaned_response = cleaned_response.strip()
            
            # 如果响应包含schema定义，LLM可能把实际值放在"description"字段中
            # 尝试从schema的description字段提取实际值
            import re
            if '"type"' in cleaned_response and '"description"' in cleaned_response:
                # 尝试从schema的description字段提取partner_query和investor_query
                # 查找 "partner_query" 后面的第一个 "description" 字段的值
                partner_desc_match = re.search(r'"partner_query"[^}]*?"description"\s*:\s*"([^"]+)"', cleaned_response, re.DOTALL)
                investor_desc_match = re.search(r'"investor_query"[^}]*?"description"\s*:\s*"([^"]+)"', cleaned_response, re.DOTALL)
                
                if partner_desc_match and investor_desc_match:
                    # 找到了description字段中的值，构造正确的JSON结构
                    partner_value = partner_desc_match.group(1)
                    investor_value = investor_desc_match.group(1)
                    
                    # 尝试提取markdown_summary（可能在description中，也可能在别处）
                    markdown_desc_match = re.search(r'"markdown_summary"\s*:\s*\{[^}]*"description"\s*:\s*"([^"]+)"', cleaned_response, re.DOTALL)
                    markdown_value = markdown_desc_match.group(1) if markdown_desc_match else ""
                    
                    # 返回提取的值
                    self.log_info("从schema的description字段成功提取了搜索短语")
                    return {
                        "partner_query": partner_value.strip(),
                        "investor_query": investor_value.strip(),
                        "markdown_summary": markdown_value.strip()
                    }
            
            # 如果响应包含schema标签，尝试提取标签之后的内容
            if "</OUTPUT JSON SCHEMA>" in cleaned_response:
                parts = cleaned_response.split("</OUTPUT JSON SCHEMA>")
                if len(parts) > 1:
                    cleaned_response = parts[-1].strip()
            
            # 尝试使用extract_clean_response提取JSON
            try:
                extracted = extract_clean_response(cleaned_response)
                if isinstance(extracted, dict):
                    # 支持新的嵌套结构：{data: {partner_query, investor_query}, markdown_summary}
                    if "data" in extracted and isinstance(extracted["data"], dict):
                        data = extracted["data"]
                        if "partner_query" in data and "investor_query" in data:
                            return {
                                "partner_query": str(data.get("partner_query", "")).strip(),
                                "investor_query": str(data.get("investor_query", "")).strip(),
                                "markdown_summary": str(extracted.get("markdown_summary", "")).strip()
                            }
                    # 支持旧的扁平结构：{partner_query, investor_query}（向后兼容）
                    elif "partner_query" in extracted and "investor_query" in extracted:
                        return {
                            "partner_query": str(extracted.get("partner_query", "")).strip(),
                            "investor_query": str(extracted.get("investor_query", "")).strip(),
                            "markdown_summary": str(extracted.get("markdown_summary", "")).strip()
                        }
            except:
                pass
            
            # 尝试直接解析JSON（使用更健壮的匹配）
            try:
                # 先尝试直接解析整个响应
                try:
                    result = json.loads(cleaned_response)
                    if isinstance(result, dict):
                        # 支持新的嵌套结构：{data: {partner_query, investor_query}, markdown_summary}
                        if "data" in result and isinstance(result["data"], dict):
                            data = result["data"]
                            if "partner_query" in data and "investor_query" in data:
                                return {
                                    "partner_query": str(data.get("partner_query", "")).strip(),
                                    "investor_query": str(data.get("investor_query", "")).strip(),
                                    "markdown_summary": str(result.get("markdown_summary", "")).strip()
                                }
                        # 支持旧的扁平结构：{partner_query, investor_query}（向后兼容）
                        elif "partner_query" in result and "investor_query" in result:
                            return {
                                "partner_query": str(result.get("partner_query", "")).strip(),
                                "investor_query": str(result.get("investor_query", "")).strip(),
                                "markdown_summary": str(result.get("markdown_summary", "")).strip()
                            }
                except json.JSONDecodeError:
                    pass
                
                # 尝试查找JSON对象（支持嵌套）
                # 使用括号匹配来找到完整的JSON对象
                brace_count = 0
                start_idx = -1
                json_objects = []
                for i, char in enumerate(cleaned_response):
                    if char == '{':
                        if brace_count == 0:
                            start_idx = i
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0 and start_idx != -1:
                            json_str = cleaned_response[start_idx:i+1]
                            json_objects.append(json_str)
                            start_idx = -1
                
                # 尝试解析找到的JSON对象
                for json_str in json_objects:
                    try:
                        result = json.loads(json_str)
                        if isinstance(result, dict):
                            # 支持新的嵌套结构：{data: {partner_query, investor_query}, markdown_summary}
                            if "data" in result and isinstance(result["data"], dict):
                                data = result["data"]
                                if "partner_query" in data and "investor_query" in data:
                                    return {
                                        "partner_query": str(data.get("partner_query", "")).strip(),
                                        "investor_query": str(data.get("investor_query", "")).strip(),
                                        "markdown_summary": str(result.get("markdown_summary", "")).strip()
                                    }
                            # 支持旧的扁平结构：{partner_query, investor_query}（向后兼容）
                            elif "partner_query" in result and "investor_query" in result:
                                return {
                                    "partner_query": str(result.get("partner_query", "")).strip(),
                                    "investor_query": str(result.get("investor_query", "")).strip(),
                                    "markdown_summary": str(result.get("markdown_summary", "")).strip()
                                }
                    except json.JSONDecodeError:
                        continue
            except Exception as e:
                self.log_info(f"JSON解析尝试失败: {str(e)}")
            
            # 尝试正则表达式提取（支持嵌套和扁平结构）
            try:
                # 先尝试在"data"对象内查找（新结构）
                data_match = re.search(r'"data"\s*:\s*\{[^}]*"partner_query"\s*:\s*"([^"]+)"[^}]*"investor_query"\s*:\s*"([^"]+)"', cleaned_response, re.IGNORECASE | re.DOTALL)
                # 尝试提取markdown_summary
                summary_match = re.search(r'"markdown_summary"\s*:\s*"([^"]+)"', cleaned_response, re.IGNORECASE | re.DOTALL)
                summary_text = summary_match.group(1).strip() if summary_match else ""
                
                if data_match:
                    return {
                        "partner_query": data_match.group(1).strip(),
                        "investor_query": data_match.group(2).strip(),
                        "markdown_summary": summary_text
                    }
                
                # 如果没找到，尝试扁平结构（向后兼容）
                partner_match = re.search(r'"partner_query"\s*:\s*"([^"]+)"', cleaned_response, re.IGNORECASE)
                investor_match = re.search(r'"investor_query"\s*:\s*"([^"]+)"', cleaned_response, re.IGNORECASE)
                if partner_match and investor_match:
                    return {
                        "partner_query": partner_match.group(1).strip(),
                        "investor_query": investor_match.group(1).strip(),
                        "markdown_summary": summary_text
                    }
            except Exception as e:
                self.log_info(f"正则表达式提取失败: {str(e)}")
            
            # 如果JSON解析失败，尝试提取文本
            partner_query = ""
            investor_query = ""
            
            lines = cleaned_response.split("\n")
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # 查找partner_query
                if "partner_query" in line.lower() or ("合伙人" in line and "搜索" in line):
                    if ":" in line:
                        parts = line.split(":", 1)
                        if len(parts) > 1:
                            partner_query = parts[1].strip().strip('"').strip("'").strip()
                # 查找investor_query
                elif "investor_query" in line.lower() or ("投资人" in line and "搜索" in line):
                    if ":" in line:
                        parts = line.split(":", 1)
                        if len(parts) > 1:
                            investor_query = parts[1].strip().strip('"').strip("'").strip()
            
            return {
                "partner_query": partner_query,
                "investor_query": investor_query,
                "markdown_summary": ""
            }
            
        except Exception as e:
            self.log_error(f"解析搜索短语失败: {str(e)}")
            return {
                "partner_query": "",
                "investor_query": "",
                "markdown_summary": ""
            }
    

