"""
BP分析节点的提示词和Schema定义
包含BP分析的提示词、输入输出Schema
"""

import json

# ===== JSON Schema 定义 =====

# BP分析输入Schema
input_schema_bp_analysis = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "company_description": {"type": "string"},
        "market_analysis": {"type": "string"},
        "financial_planning": {"type": "string"},
        "risk_assessment": {"type": "string"}
    }
}

# BP分析输出Schema
output_schema_bp_analysis = {
    "type": "object",
    "properties": {
        "market_potential": {"type": "string"},
        "financial_feasibility": {"type": "string"},
        "key_risks": {"type": "string"},
        "improvement_suggestions": {"type": "string"}
    }
}

# ===== 系统提示词定义 =====

# BP分析系统提示词
SYSTEM_PROMPT_BP_ANALYSIS = f"""
你是一位创业计划书分析专家。你将获得一份创业计划书的JSON格式数据，内容包括摘要、公司描述、市场分析、财务规划和风险评估。
请按照以下JSON模式定义格式化输出：

<INPUT JSON SCHEMA>
{json.dumps(input_schema_bp_analysis, indent=2, ensure_ascii=False)}
</INPUT JSON SCHEMA>

你的任务是分析BP的完整性、逻辑性和可行性，并输出以下内容：
1. **市场潜力**：评估市场机会和竞争环境。
2. **财务可行性**：分析财务预测的合理性。
3. **关键风险**：指出BP中未提及或未解决的风险。
4. **改进建议**：提供优化BP的建议。

请按照以下JSON模式定义格式化输出：

<OUTPUT JSON SCHEMA>
{json.dumps(output_schema_bp_analysis, indent=2, ensure_ascii=False)}
</OUTPUT JSON SCHEMA>

确保输出是一个符合上述输出JSON模式定义的JSON对象。
只返回JSON对象，不要有解释或额外文本。
"""

