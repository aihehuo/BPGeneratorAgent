"""
格式化节点的提示词和Schema定义
包含报告格式化的提示词、输入输出Schema
"""

import json

# ===== JSON Schema 定义 =====

# 报告格式化输入Schema
input_schema_report_formatting = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "paragraph_latest_state": {"type": "string"}
        }
    }
}

# ===== 系统提示词定义 =====

# 最终研究报告格式化的系统提示词
SYSTEM_PROMPT_REPORT_FORMATTING = f"""
你是一位深度研究助手。你已经完成了研究并构建了报告中所有段落的最终版本。
你现在需要将所有这些段落格式化为最终的研究报告格式。
数据将按照以下JSON模式定义提供：

<INPUT JSON SCHEMA>
{json.dumps(input_schema_report_formatting, indent=2, ensure_ascii=False)}
</INPUT JSON SCHEMA>

你的任务是创建一个格式良好的研究报告，其中包含所有提供的段落，并适当地组织它们。
确保报告结构清晰，段落之间有适当的过渡。
输出应该是一个完整的Markdown格式的研究报告。

只返回格式化的研究报告内容（Markdown格式），不要有解释或额外文本。
"""

