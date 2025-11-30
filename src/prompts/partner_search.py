"""
合伙人搜索节点的提示词和Schema定义
包含合伙人搜索短语提取的提示词
"""

import json

# ===== JSON Schema 定义 =====

# 搜索短语提取输出Schema
output_schema_search_phrases = {
    "type": "object",
    "properties": {
        "partner_query": {
            "type": "string",
            "description": "合伙人搜索短语（10-50个字符，描述所需合伙人的技能、经验、背景等）"
        },
        "investor_query": {
            "type": "string",
            "description": "投资人搜索短语（10-50个字符，描述项目特点和投资需求）"
        }
    },
    "required": ["partner_query", "investor_query"]
}

# ===== 系统提示词定义 =====

def get_partner_search_extraction_prompt(bp_summary: str, is_english: bool):
    """
    构建合伙人搜索短语提取的系统提示词和用户提示词
    
    Args:
        bp_summary: BP内容摘要
        is_english: 是否为英文
        
    Returns:
        (system_prompt, extraction_prompt) 元组
    """
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
    
    return system_prompt, extraction_prompt

