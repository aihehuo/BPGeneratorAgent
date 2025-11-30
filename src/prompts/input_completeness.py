"""
输入完整性检查节点的提示词和Schema定义
包含输入完整性检查的提示词、输入输出Schema
"""

import json

# ===== JSON Schema 定义 =====

# 输入完整性检查的输出Schema（内部数据）
output_schema_input_completeness_data = {
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

# 输入完整性检查的最终输出Schema（包含 data 和 markdown_summary）
output_schema_input_completeness = {
    "type": "object",
    "properties": {
        "data": output_schema_input_completeness_data,
        "markdown_summary": {
            "type": "string",
            "description": "A brief, human-readable Markdown summary (2-4 sentences or short bullet list) describing the evaluation results. Use the same language as the business_idea."
        }
    },
    "required": ["data", "markdown_summary"]
}

# ===== 系统提示词定义 =====

def get_input_completeness_prompt(business_idea: str, is_english: bool):
    """
    构建输入完整性检查的系统提示词和用户提示词
    
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

Please output a JSON object with the following structure:

<OUTPUT JSON SCHEMA>
{{
  "type": "object",
  "properties": {{
    "data": {json.dumps(output_schema_input_completeness_data, indent=2, ensure_ascii=False)},
    "markdown_summary": {{
      "type": "string",
      "description": "A brief, human-readable Markdown summary (2-4 sentences or short bullet list) describing the evaluation results and key findings. Use the same language as the business_idea."
    }}
  }},
  "required": ["data", "markdown_summary"]
}}
</OUTPUT JSON SCHEMA>

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

**Output Format Requirements:**
- You must return a JSON object containing two fields:
  1. `data`: The evaluation result object (is_complete, current_perspective, perspective_details, suggestions)
  2. `markdown_summary`: A brief, human-readable Markdown summary (2-4 sentences or short bullet list) describing:
     - The evaluation result (passed/failed)
     - Which perspectives were complete/partial/missing
     - Key findings from the evaluation
     - Main suggestions for improvement (if any)
     - Use the same language as the business_idea (English if English, Chinese if Chinese)

**Important**: Return only a JSON object that conforms to the output schema. Do not include any explanation or additional text."""
        
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

请按照以下JSON模式输出：

<OUTPUT JSON SCHEMA>
{{
  "type": "object",
  "properties": {{
    "data": {json.dumps(output_schema_input_completeness_data, indent=2, ensure_ascii=False)},
    "markdown_summary": {{
      "type": "string",
      "description": "一段简短、人类可读的Markdown格式摘要（2-4句话或简短列表），描述评估结果和关键发现。使用与商业创意相同的语言。"
    }}
  }},
  "required": ["data", "markdown_summary"]
}}
</OUTPUT JSON SCHEMA>

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
   - **完整**：满足完整性标准（至少1个检查点被勾选）
   - **部分**：1个检查点被勾选但描述非常模糊
   - **缺失**：0个检查点被勾选
4. 将所有未勾选的项目列在每个视角的"missing_checkpoints"数组中
5. **重要**：至少两个视角必须为"完整"，is_complete才为true
6. 如果少于2个视角为"完整"，将is_complete设置为false
7. 根据哪个视角有最多的勾选项目来确定current_perspective（如果多个视角得分相似，使用"mixed"）
8. 提供简短、简单的改进建议，重点关注添加缺失视角的内容

**要宽松**：如果输入从至少2个视角提供了有意义的描述，应该通过。只拒绝完全空白、无意义或完全没有上下文的输入。

**输出格式要求：**
- 必须返回一个包含两个字段的JSON对象：
  1. `data`: 评估结果对象（包含is_complete、current_perspective、perspective_details、suggestions）
  2. `markdown_summary`: 一段简短、人类可读的Markdown格式摘要（2-4句话或简短列表），描述：
     - 评估结果（通过/未通过）
     - 哪些视角是完整/部分/缺失的
     - 评估的关键发现
     - 主要改进建议（如果有）
     - 使用与商业创意相同的语言（英文输入用英文，中文输入用中文）

**重要**：只返回符合输出模式的JSON对象。不要包含任何解释或额外文本。"""
        
        user_prompt = f"""请评估以下商业创意的完整性。记住：我们只需要基本描述，不需要详细的商业计划。

**重要**：输入必须从至少两个视角提供基本描述才能通过。

{business_idea}

从三个视角（技术、用户痛点、市场）进行分析，确定是否至少有两个视角提供了基本描述。"""
    
    return system_prompt, user_prompt

