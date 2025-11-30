"""
Prompt模块
定义Deep Search Agent各个阶段使用的系统提示词
支持按节点组织的提示词文件结构
"""

# 从新的按节点组织的文件导入
from .bp_structure import (
    SYSTEM_PROMPT_BP_STRUCTURE,
    SYSTEM_PROMPT_BP_STRUCTURE_REGENERATE,
    input_schema_bp_structure,
    input_schema_bp_structure_regenerate,
    output_schema_bp_structure,
)

from .bp_evaluation import (
    SYSTEM_PROMPT_BP_EVALUATION,
    input_schema_bp_evaluation,
    output_schema_bp_evaluation,
)

from .investor_evaluation import (
    SYSTEM_PROMPT_INVESTOR_EVALUATION,
    input_schema_investor_evaluation,
    output_schema_investor_evaluation,
)

from .painpoint_enhancement import (
    SYSTEM_PROMPT_PAINPOINT_ENHANCEMENT,
    input_schema_painpoint_enhancement,
    output_schema_painpoint_enhancement,
)

from .pitch_60s import (
    SYSTEM_PROMPT_60S_PITCH,
    input_schema_60s_pitch,
    output_schema_60s_pitch,
)

from .ppt_generation import (
    SYSTEM_PROMPT_PPT_GENERATION,
    input_schema_ppt_generation,
    output_schema_ppt_generation,
)

from .bp_analysis import (
    SYSTEM_PROMPT_BP_ANALYSIS,
    input_schema_bp_analysis,
    output_schema_bp_analysis,
)

from .bp_completion_guide import (
    SYSTEM_PROMPT_BP_COMPLETION_GUIDE,
    input_schema_bp_completion_guide,
    output_schema_bp_completion_guide,
)

from .report_structure import (
    SYSTEM_PROMPT_REPORT_STRUCTURE,
    output_schema_report_structure,
)

from .search import (
    SYSTEM_PROMPT_FIRST_SEARCH,
    SYSTEM_PROMPT_REFLECTION,
    input_schema_first_search,
    output_schema_first_search,
    input_schema_reflection,
    output_schema_reflection,
)

from .summary import (
    SYSTEM_PROMPT_FIRST_SUMMARY,
    SYSTEM_PROMPT_REFLECTION_SUMMARY,
    input_schema_first_summary,
    output_schema_first_summary,
    input_schema_reflection_summary,
    output_schema_reflection_summary,
)

from .formatting import (
    SYSTEM_PROMPT_REPORT_FORMATTING,
    input_schema_report_formatting,
)

from .input_completeness import (
    output_schema_input_completeness,
    get_input_completeness_prompt,
)

from .partner_search import (
    get_partner_search_extraction_prompt,
    output_schema_search_phrases,
)

__all__ = [
    # BP结构相关
    "SYSTEM_PROMPT_BP_STRUCTURE",
    "SYSTEM_PROMPT_BP_STRUCTURE_REGENERATE",
    "input_schema_bp_structure",
    "input_schema_bp_structure_regenerate",
    "output_schema_bp_structure",
    # BP评估相关
    "SYSTEM_PROMPT_BP_EVALUATION",
    "input_schema_bp_evaluation",
    "output_schema_bp_evaluation",
    # 投资者评估相关
    "SYSTEM_PROMPT_INVESTOR_EVALUATION",
    "input_schema_investor_evaluation",
    "output_schema_investor_evaluation",
    # 痛点增强相关
    "SYSTEM_PROMPT_PAINPOINT_ENHANCEMENT",
    "input_schema_painpoint_enhancement",
    "output_schema_painpoint_enhancement",
    # 60秒路演相关
    "SYSTEM_PROMPT_60S_PITCH",
    "input_schema_60s_pitch",
    "output_schema_60s_pitch",
    # PPT生成相关
    "SYSTEM_PROMPT_PPT_GENERATION",
    "input_schema_ppt_generation",
    "output_schema_ppt_generation",
    # BP分析相关
    "SYSTEM_PROMPT_BP_ANALYSIS",
    "input_schema_bp_analysis",
    "output_schema_bp_analysis",
    # BP完整性引导相关
    "SYSTEM_PROMPT_BP_COMPLETION_GUIDE",
    "input_schema_bp_completion_guide",
    "output_schema_bp_completion_guide",
    # 报告结构相关
    "SYSTEM_PROMPT_REPORT_STRUCTURE",
    "output_schema_report_structure",
    # 搜索相关
    "SYSTEM_PROMPT_FIRST_SEARCH",
    "SYSTEM_PROMPT_REFLECTION",
    "input_schema_first_search",
    "output_schema_first_search",
    "input_schema_reflection",
    "output_schema_reflection",
    # 总结相关
    "SYSTEM_PROMPT_FIRST_SUMMARY",
    "SYSTEM_PROMPT_REFLECTION_SUMMARY",
    "input_schema_first_summary",
    "output_schema_first_summary",
    "input_schema_reflection_summary",
    "output_schema_reflection_summary",
    # 格式化相关
    "SYSTEM_PROMPT_REPORT_FORMATTING",
    "input_schema_report_formatting",
    # 输入完整性检查相关
    "output_schema_input_completeness",
    "get_input_completeness_prompt",
    # 合伙人搜索相关
    "get_partner_search_extraction_prompt",
    "output_schema_search_phrases",
]
