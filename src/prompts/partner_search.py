"""
合伙人搜索节点的提示词和Schema定义
包含合伙人搜索短语提取的提示词
"""

import json

# ===== JSON Schema 定义 =====

# 搜索短语提取输出Schema（内部数据）
output_schema_search_phrases_data = {
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

# 搜索短语提取的最终输出Schema（包含 data 和 markdown_summary）
output_schema_search_phrases = {
    "type": "object",
    "properties": {
        "data": output_schema_search_phrases_data,
        "markdown_summary": {
            "type": "string",
            "description": "A brief, human-readable Markdown summary (2-4 sentences or short bullet list) describing the extracted search phrases and their purpose. Use the same language as the business plan."
        }
    },
    "required": ["data", "markdown_summary"]
}

# ===== 系统提示词定义 =====

# 合伙人搜索短语提取系统提示词
SYSTEM_PROMPT_PARTNER_SEARCH = f"""
你是一个专业的商业计划书分析助手。根据商业计划书内容，提炼出搜索合伙人和投资人的关键词短语。

**⚠️ 语言要求（最高优先级，必须严格遵守）⚠️**：
1. 首先检查用户输入的商业计划书内容中是否明确指定了语言（如"用英文"、"in English"、"用中文"、"in Chinese"等）
2. 如果用户明确指定了语言，则**严格且必须**使用用户指定的语言生成所有输出（包括partner_query、investor_query、markdown_summary）
3. 如果用户没有明确指定语言，则**自动检测**输入的商业计划书内容的语言：
   - 如果商业计划书主要是英文（包含大量英文单词和英文语法结构），则**所有输出必须使用英文**
   - 如果商业计划书主要是中文（包含大量中文字符和中文语法结构），则**所有输出必须使用中文**
4. **输出的语言必须与用户指定或检测到的输入语言完全一致**，不允许混合使用中英文

请按照以下JSON模式输出：

<OUTPUT JSON SCHEMA>
{{
  "type": "object",
  "properties": {{
    "data": {json.dumps(output_schema_search_phrases_data, indent=2, ensure_ascii=False)},
    "markdown_summary": {{
      "type": "string",
      "description": "一段简短、人类可读的Markdown格式摘要（2-4句话或简短列表），描述提取的搜索短语及其用途。使用与商业计划书相同的语言。"
    }}
  }},
  "required": ["data", "markdown_summary"]
}}
</OUTPUT JSON SCHEMA>

**输出格式要求：**
- 必须返回一个包含两个字段的JSON对象：
  1. `data`: 搜索短语对象（包含partner_query、investor_query）
     - `partner_query`: 合伙人搜索短语（10-50个字符，描述所需合伙人的技能、经验、背景等）
     - `investor_query`: 投资人搜索短语（10-50个字符，描述项目特点和投资需求）
  2. `markdown_summary`: 一段简短、人类可读的Markdown格式摘要（2-4句话或简短列表），描述：
     - 提取了哪些搜索短语
     - 每个搜索短语的用途
     - 它们针对的关键特征
     - **使用与商业计划书相同的语言**（英文输入用英文，中文输入用中文）

**重要**：
- 不要在你的响应中包含模式定义
- 不要包含 <OUTPUT JSON SCHEMA> 标签
- 只返回包含实际值的JSON数据，不要返回模式结构
- 正确输出的示例（中文）：
{{
  "data": {{
    "partner_query": "技术合伙人，AI经验",
    "investor_query": "教育科技投资人"
  }},
  "markdown_summary": "提取了搜索短语..."
}}
- 正确输出的示例（英文）：
{{
  "data": {{
    "partner_query": "Technical partner with AI experience",
    "investor_query": "EdTech investor"
  }},
  "markdown_summary": "Extracted search phrases..."
}}

不要包含任何解释、模式定义或额外文本。
"""

