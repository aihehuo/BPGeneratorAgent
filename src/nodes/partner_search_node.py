"""
合伙人员搜索节点
根据BP内容搜索符合条件的合伙人和投资人
"""

import json
import re
import traceback
from typing import Dict, Any, List, Optional
from .base_node import BaseNode
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
                "investor_count": 0
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
                "error": str(e)
            }
    
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
            包含partner_query和investor_query的字典
        """
        try:
            # 检测语言
            detected_lang = detect_language(business_idea)
            is_english = detected_lang == 'en'
            
            # 构建BP内容摘要（根据语言选择标签）
            if is_english:
                bp_content = f"Business Idea: {business_idea}\n\n"
                bp_content += "Business Plan Structure:\n"
            else:
                bp_content = f"商业创意：{business_idea}\n\n"
                bp_content += "商业计划书结构：\n"
            
            for idx, section in enumerate(bp_structure, 1):
                title = section.get("title", f"段落{idx}")
                content = section.get("content", "")
                bp_content += f"\n{idx}. {title}\n{content}\n"
            
            # 限制BP内容长度
            bp_summary = bp_content[:2500]  # 限制长度避免token过多
            
            # 使用LLM提炼搜索短语
            if is_english:
                system_prompt = "You are a professional business plan analyst. Extract search phrases for finding partners and investors from the business plan content. Return only JSON format."
                extraction_prompt = f"""Extract two search phrases from the following business plan:

1. **Partner Search Phrase**: For searching partners/team members (e.g., technical partners, marketing partners, product partners)
2. **Investor Search Phrase**: For searching investors/investment institutions interested in the project

Business Plan Content:
{bp_summary}

Output format (JSON only, no other text):
{{
    "partner_query": "Partner search phrase (10-50 characters, describing required skills, experience, background)",
    "investor_query": "Investor search phrase (10-50 characters, describing project characteristics and investment needs)"
}}

Requirements:
- Search phrases should be specific and clear for semantic search
- Partner search phrase should highlight required skills, experience, industry background
- Investor search phrase should highlight project characteristics, industry, stage
- Return ONLY JSON, no explanations"""
            else:
                system_prompt = "你是一个专业的商业计划书分析助手。根据商业计划书内容，提炼出搜索合伙人和投资人的关键词短语。只返回JSON格式。"
                extraction_prompt = f"""根据以下商业计划书内容，提炼出两个搜索短语：

1. **合伙人搜索短语**：用于搜索符合项目需求的合伙人/团队成员（如技术合伙人、市场合伙人、产品合伙人等）
2. **投资人搜索短语**：用于搜索可能对项目感兴趣的投资人/投资机构

商业计划书内容：
{bp_summary}

输出格式（只返回JSON，不要包含其他文本）：
{{
    "partner_query": "合伙人搜索短语（10-50个字符，描述所需合伙人的技能、经验、背景等）",
    "investor_query": "投资人搜索短语（10-50个字符，描述项目特点和投资需求）"
}}

要求：
- 搜索短语要具体、明确，便于语义搜索
- 合伙人搜索短语应突出所需技能、经验、行业背景等
- 投资人搜索短语应突出项目特点、行业、阶段等
- 只返回JSON，不要包含其他解释"""

            self.log_info("正在使用LLM提炼搜索短语...")
            response = self.invoke_llm(
                system_prompt,
                extraction_prompt
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
            self.log_info(f"解析后的合伙人搜索短语: {parsed_partner}")
            self.log_info(f"解析后的投资人搜索短语: {parsed_investor}")
            print(f"[PartnerSearch] 解析后的合伙人搜索短语: {parsed_partner}")
            print(f"[PartnerSearch] 解析后的投资人搜索短语: {parsed_investor}")
            
            return search_phrases
            
        except Exception as e:
            self.log_error(f"提炼搜索短语失败: {str(e)}")
            # 如果失败，使用简化的默认查询
            return {
                "partner_query": f"寻找{business_idea[:30]}项目的合伙人",
                "investor_query": f"寻找{business_idea[:30]}项目的投资人"
            }
    
    def _parse_search_phrases(self, response: str) -> Dict[str, str]:
        """
        解析LLM响应中的搜索短语
        
        Args:
            response: LLM响应文本
            
        Returns:
            包含partner_query和investor_query的字典
        """
        try:
            # 清理响应文本
            cleaned_response = remove_reasoning_from_output(response)
            cleaned_response = clean_json_tags(cleaned_response)
            cleaned_response = cleaned_response.strip()
            
            # 尝试使用extract_clean_response提取JSON
            try:
                extracted = extract_clean_response(cleaned_response)
                if isinstance(extracted, dict) and "partner_query" in extracted and "investor_query" in extracted:
                    return {
                        "partner_query": str(extracted.get("partner_query", "")).strip(),
                        "investor_query": str(extracted.get("investor_query", "")).strip()
                    }
            except:
                pass
            
            # 尝试直接解析JSON（使用更健壮的匹配）
            try:
                # 先尝试直接解析整个响应
                try:
                    result = json.loads(cleaned_response)
                    if isinstance(result, dict) and "partner_query" in result and "investor_query" in result:
                        return {
                            "partner_query": str(result.get("partner_query", "")).strip(),
                            "investor_query": str(result.get("investor_query", "")).strip()
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
                        if isinstance(result, dict) and "partner_query" in result and "investor_query" in result:
                            return {
                                "partner_query": str(result.get("partner_query", "")).strip(),
                                "investor_query": str(result.get("investor_query", "")).strip()
                            }
                    except json.JSONDecodeError:
                        continue
            except Exception as e:
                self.log_info(f"JSON解析尝试失败: {str(e)}")
            
            # 尝试正则表达式提取
            try:
                partner_match = re.search(r'"partner_query"\s*:\s*"([^"]+)"', cleaned_response, re.IGNORECASE)
                investor_match = re.search(r'"investor_query"\s*:\s*"([^"]+)"', cleaned_response, re.IGNORECASE)
                if partner_match and investor_match:
                    return {
                        "partner_query": partner_match.group(1).strip(),
                        "investor_query": investor_match.group(1).strip()
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
                "investor_query": investor_query
            }
            
        except Exception as e:
            self.log_error(f"解析搜索短语失败: {str(e)}")
            return {
                "partner_query": "",
                "investor_query": ""
            }
    

