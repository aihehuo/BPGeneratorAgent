"""
BP Generation Agent
按照 test_bp_structure 的流程生成 BP 结构、评估、Pitch、PPT，并输出 Markdown
"""

import os
from datetime import datetime
from typing import Optional, Dict, Any, List

from .llms import DeepSeekLLM, OpenAILLM, QwenLLM, BaseLLM
from .nodes import (
    BPStructureNode,
    BPEvaluationNode,
    PainpointEnhancementNode,
    InvestorEvaluationNode,
    Pitch60sNode,
    PPTGenerationNode,
)
from .utils.config import Config, load_config


class BPGenerationAgent:
    """BP Generation Agent主类"""

    def __init__(self, config: Optional[Config] = None):
        """
        初始化BP Generation Agent

        Args:
            config: 配置对象，如果不提供则自动加载
        """
        self.config = config or load_config()
        self.llm_client = self._initialize_llm()
        self.max_iterations = 3

        os.makedirs(self.config.output_dir, exist_ok=True)

        print("BP Generation Agent 已初始化")
        print(f"使用LLM: {self.llm_client.get_model_info()}")

    def _initialize_llm(self) -> BaseLLM:
        """初始化LLM客户端"""
        if self.config.default_llm_provider == "deepseek":
            return DeepSeekLLM(
                api_key=self.config.deepseek_api_key,
                model_name=self.config.deepseek_model,
            )
        if self.config.default_llm_provider == "openai":
            return OpenAILLM(
                api_key=self.config.openai_api_key,
                model_name=self.config.openai_model,
            )
        if self.config.default_llm_provider == "qwen":
            return QwenLLM(
                api_key=self.config.qwen_api_key,
                model_name=self.config.qwen_model,
            )
        raise ValueError(f"不支持的LLM提供商: {self.config.default_llm_provider}")

    # --------------------------------------------------------------------- #
    # 核心流程
    # --------------------------------------------------------------------- #

    def generate_bp(
        self,
        business_idea: str,
        output_file: Optional[str] = None,
        save_report: bool = True,
    ) -> Dict[str, Any]:
        """
        生成BP结构、评估、Pitch和PPT；最终输出Markdown

        Args:
            business_idea: 商业创意
            output_file: 指定输出Markdown文件路径（可选）
            save_report: 是否保存Markdown到文件

        Returns:
            包含输出文件路径、Markdown文本等信息的字典
        """
        print("\n" + "=" * 60)
        print(f"开始生成BP: {business_idea[:80]}...")
        print("=" * 60)

        # 初始化节点
        bp_structure_node = BPStructureNode(self.llm_client, business_idea)
        evaluation_node = BPEvaluationNode(self.llm_client)
        painpoint_enhancement_node = PainpointEnhancementNode(self.llm_client)
        investor_eval_node = InvestorEvaluationNode(self.llm_client)
        pitch_node = Pitch60sNode(self.llm_client)
        ppt_node = PPTGenerationNode(self.llm_client)

        bp_structure: Optional[List[Dict[str, str]]] = None
        evaluation_result: Optional[Dict[str, Any]] = None
        iteration_history: List[Dict[str, Any]] = []
        pitch_result: Optional[Dict[str, Any]] = None
        ppt_result: Optional[Dict[str, Any]] = None

        try:
            for iteration in range(self.max_iterations):
                iteration_num = iteration + 1
                print("\n" + "=" * 60)
                print(f"迭代 {iteration_num}/{self.max_iterations}")
                print("=" * 60)

                try:
                    if iteration == 0:
                        print("正在生成BP结构...")
                        bp_structure = bp_structure_node.run()
                    else:
                        print("正在根据反馈重新生成BP结构...")
                        bp_structure = bp_structure_node.regenerate(
                            evaluation_result=evaluation_result.get("evaluation_result", ""),
                            suggestions=evaluation_result.get("suggestions", ""),
                            current_structure=bp_structure,
                        )
                except Exception as exc:
                    print("\n" + "=" * 60)
                    print("错误: 生成BP结构失败")
                    print("=" * 60)
                    print(f"错误信息: {exc}")
                    raise

                print(f"\n成功生成 {len(bp_structure)} 个段落:")
                for idx, section in enumerate(bp_structure, 1):
                    print(f"  {idx}. {section.get('title', 'N/A')}")

                # 评估BP结构
                print("\n正在评估BP结构...")
                evaluation_result = evaluation_node.evaluate_paragraphs(
                    business_idea, bp_structure
                )

                iteration_history.append(
                    {
                        "iteration": iteration_num,
                        "structure": bp_structure.copy(),
                        "evaluation": evaluation_result.copy(),
                    }
                )

                if evaluation_result.get("passed"):
                    print("✓ BP结构评估通过")
                    print(f"  评估结果: {evaluation_result.get('evaluation_result', 'N/A')}")

                    # ------------------------------------------------------------------
                    # 痛点加强
                    # ------------------------------------------------------------------
                    print("\n" + "=" * 60)
                    print("BP评估通过，开始痛点加强")
                    print("=" * 60)

                    try:
                        painpoint_para_index = None
                        painpoint_para = None

                        for idx, para in enumerate(bp_structure):
                            title = para.get("title", "").strip()
                            if "用户画像" in title and "痛点" in title:
                                painpoint_para_index = idx
                                painpoint_para = para
                                break

                        if painpoint_para:
                            print(f"找到痛点段落: {painpoint_para.get('title', 'N/A')}")
                            enhancement_result = painpoint_enhancement_node.enhance(
                                business_idea, painpoint_para
                            )

                            enhanced_content = enhancement_result.get(
                                "enhanced_content", ""
                            )
                            selected_dimensions = enhancement_result.get(
                                "selected_dimensions", []
                            )
                            dimension_descriptions = enhancement_result.get(
                                "dimension_descriptions", []
                            )
                            enhancement_explanation = enhancement_result.get(
                                "enhancement_explanation", ""
                            )

                            print("✓ 痛点加强完成")
                            if selected_dimensions:
                                print(f"  选择的维度: {', '.join(selected_dimensions)}")

                            bp_structure[painpoint_para_index] = {
                                "title": painpoint_para.get("title", "用户画像与痛点"),
                                "content": enhanced_content,
                            }

                            iteration_history.append(
                                {
                                    "iteration": "painpoint_enhancement",
                                    "paragraph_index": painpoint_para_index,
                                    "paragraph_title": painpoint_para.get(
                                        "title", "用户画像与痛点"
                                    ),
                                    "content_before": painpoint_para.get("content", ""),
                                    "content_after": enhanced_content,
                                    "selected_dimensions": selected_dimensions,
                                    "dimension_descriptions": dimension_descriptions,
                                    "enhancement_explanation": enhancement_explanation,
                                }
                            )
                        else:
                            print("未找到 '用户画像与痛点' 段落，跳过痛点加强")
                    except Exception as exc:
                        print(f"痛点加强失败: {exc}")

                    # ------------------------------------------------------------------
                    # 投资者评估
                    # ------------------------------------------------------------------
                    print("\n" + "=" * 60)
                    print("痛点加强完成，开始投资者评估")
                    print("=" * 60)

                    try:
                        bp_structure_before = [para.copy() for para in bp_structure]
                        investor_evaluation = investor_eval_node.evaluate_full_bp(
                            business_idea, bp_structure
                        )

                        print("\n投资者整体评估:")
                        overall_assessment = investor_evaluation.get(
                            "overall_assessment", ""
                        )
                        print(f"  整体评估: {overall_assessment[:200]}...")

                        paragraph_feedbacks = investor_evaluation.get(
                            "paragraph_specific_feedback", []
                        )
                        print(
                            f"\n投资者评估完成，共 {len(paragraph_feedbacks)} 个段落反馈"
                        )

                        final_bp_structure: List[Dict[str, str]] = []
                        for idx, para in enumerate(bp_structure):
                            para_title = para.get("title", f"段落 {idx + 1}")
                            print(f"  处理段落 {idx + 1}: {para_title}")

                            para_feedback = next(
                                (
                                    fb
                                    for fb in paragraph_feedbacks
                                    if fb.get("paragraph_index") == idx
                                ),
                                None,
                            )

                            if para_feedback:
                                feedback_text = para_feedback.get("feedback", "")
                                suggestions_text = para_feedback.get("suggestions", "")
                                try:
                                    regenerated = bp_structure_node.regenerate(
                                        evaluation_result=(
                                            f"段落 {idx + 1} ({para_title}) 的评估反馈: "
                                            f"{feedback_text}。注意：必须保持标题 '{para_title}' 不变，只修改内容。"
                                        ),
                                        suggestions=(
                                            f"针对段落 '{para_title}' 的改进建议: "
                                            f"{suggestions_text}。重要：必须保持标题不变。"
                                        ),
                                        current_structure=[para],
                                    )
                                    if regenerated:
                                        regenerated_item = regenerated[0]
                                        if regenerated_item.get("title") != para_title:
                                            print(
                                                "    警告: 重新生成的段落标题不匹配，已修正为原标题"
                                            )
                                            regenerated_item["title"] = para_title
                                        final_bp_structure.append(regenerated_item)
                                    else:
                                        final_bp_structure.append(para)
                                except Exception as exc:
                                    print(
                                        f"    警告: 重新生成段落 {idx + 1} 失败，使用原段落: {exc}"
                                    )
                                    final_bp_structure.append(para)
                            else:
                                final_bp_structure.append(para)

                        print(f"✓ 最终BP结构生成完成，共 {len(final_bp_structure)} 个段落")
                        bp_structure = final_bp_structure

                        iteration_history.append(
                            {
                                "iteration": "investor_evaluation",
                                "structure_before": bp_structure_before,
                                "structure_after": bp_structure.copy(),
                                "investor_evaluation": investor_evaluation,
                            }
                        )

                        # ------------------------------------------------------------------
                        # 生成60秒Pitch
                        # ------------------------------------------------------------------
                        print("\n" + "=" * 60)
                        print("投资者评估完成，开始生成黄金60秒Pitch")
                        print("=" * 60)
                        try:
                            pitch_result = pitch_node.generate_pitch(
                                business_idea, bp_structure
                            )
                            iteration_history.append(
                                {"iteration": "60s_pitch", "pitch_result": pitch_result}
                            )
                            painpoint_dims = pitch_result.get(
                                "painpoint_resonance", {}
                            ).get("selected_dimensions", [])
                            team_advs = pitch_result.get("team_advantages", {}).get(
                                "selected_advantages", []
                            )
                            if painpoint_dims:
                                print(f"  痛点维度: {', '.join(painpoint_dims)}")
                            if team_advs:
                                print(f"  团队优势: {', '.join(team_advs)}")
                        except Exception as exc:
                            print(f"生成黄金60秒Pitch失败: {exc}")

                        # ------------------------------------------------------------------
                        # 生成10页PPT草稿
                        # ------------------------------------------------------------------
                        print("\n" + "=" * 60)
                        print("开始生成10页PPT草稿")
                        print("=" * 60)
                        try:
                            ppt_result = ppt_node.generate_ppt(
                                business_idea, bp_structure
                            )
                            iteration_history.append(
                                {"iteration": "ppt_generation", "ppt_result": ppt_result}
                            )
                            slides = ppt_result.get("slides", [])
                            print(f"✓ PPT草稿生成成功，共 {len(slides)} 页")
                        except Exception as exc:
                            print(f"生成PPT草稿失败: {exc}")

                    except Exception as exc:
                        print(f"投资者评估或重新生成失败: {exc}")
                        print("将使用BP评估通过的结构作为最终结构")
                        break

                    break  # 评估通过退出主循环
                else:
                    print("✗ BP结构评估不通过")
                    failed_index = evaluation_result.get("failed_paragraph_index", -1)
                    failed_title = evaluation_result.get("failed_paragraph_title", "未知")
                    print(f"  失败段落索引: {failed_index}")
                    print(f"  失败段落标题: {failed_title}")
                    print(f"  评估结果: {evaluation_result.get('evaluation_result', 'N/A')}")
                    if iteration_num == self.max_iterations:
                        print("已达到最大迭代次数，停止循环")

            # ----------------------------------------------------------------------
            # 构建Markdown并输出
            # ----------------------------------------------------------------------
            markdown_content = self._build_markdown(
                business_idea, bp_structure, iteration_history, evaluation_result
            )

            if save_report:
                output_path = output_file or self._build_default_filename(business_idea)
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(markdown_content)
                print("\n" + "=" * 60)
                print("Markdown已保存")
                print("=" * 60)
                print(f"输出文件: {output_path}")
            else:
                output_path = None

            return {
                "output_file": output_path,
                "markdown": markdown_content,
                "bp_structure": bp_structure,
                "iteration_history": iteration_history,
                "evaluation_result": evaluation_result,
                "pitch_result": pitch_result,
                "ppt_result": ppt_result,
            }

        except Exception as exc:
            print(f"生成过程中发生错误: {exc}")
            raise

    # ---------------------------------------------------------------------- #
    # Markdown 构建 & 工具方法
    # ---------------------------------------------------------------------- #

    def _build_default_filename(self, business_idea: str) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_idea = "".join(
            c for c in business_idea[:30] if c.isalnum() or c in (" ", "-", "_")
        ).rstrip()
        safe_idea = safe_idea.replace(" ", "_")
        return os.path.join(
            self.config.output_dir, f"bp_structure_{safe_idea}_{timestamp}.md"
        )

    def _format_bp_structure_to_markdown(
        self, bp_structure: List[Dict[str, str]], business_idea: str
    ) -> str:
        markdown = (
            "# 商业计划书结构\n\n"
            "## 商业创意\n\n"
            f"{business_idea.strip()}\n\n"
            "---\n\n"
            "## 计划书结构\n\n"
        )

        for idx, section in enumerate(bp_structure, 1):
            title = section.get("title", f"段落 {idx}")
            content = section.get("content", "")
            markdown += f"### {idx}. {title}\n\n{content}\n\n---\n\n"

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        markdown += f"\n\n---\n\n*生成时间: {timestamp}*\n"
        return markdown

    def _build_markdown(
        self,
        business_idea: str,
        bp_structure: List[Dict[str, str]],
        iteration_history: List[Dict[str, Any]],
        evaluation_result: Dict[str, Any],
    ) -> str:
        markdown_content = self._format_bp_structure_to_markdown(
            bp_structure, business_idea
        )

        markdown_content += "\n\n## 迭代历史\n\n"
        markdown_content += (
            f"**总迭代次数**: {len([h for h in iteration_history if isinstance(h.get('iteration'), int)])}\n\n"
        )

        for hist in iteration_history:
            iteration_key = hist.get("iteration")

            if isinstance(iteration_key, int):
                eval_result = hist.get("evaluation", {})
                markdown_content += f"### 迭代 {iteration_key}\n\n"
                if eval_result.get("passed"):
                    markdown_content += "- **状态**: ✓ 通过\n"
                else:
                    markdown_content += "- **状态**: ✗ 不通过\n"
                    failed_index = eval_result.get("failed_paragraph_index", -1)
                    failed_title = eval_result.get("failed_paragraph_title", "未知")
                    markdown_content += f"- **失败段落**: {failed_index + 1}. {failed_title}\n"
                markdown_content += (
                    f"- **评估说明**: {eval_result.get('evaluation_result', 'N/A')}\n"
                )
                if eval_result.get("suggestions"):
                    markdown_content += (
                        f"- **修改建议**: {eval_result.get('suggestions')}\n"
                    )
                markdown_content += "\n"

            elif iteration_key == "painpoint_enhancement":
                markdown_content += "### 痛点加强\n\n"
                para_index = hist.get("paragraph_index", -1)
                para_title = hist.get("paragraph_title", "用户画像与痛点")
                content_before = hist.get("content_before", "")
                content_after = hist.get("content_after", "")
                selected_dimensions = hist.get("selected_dimensions", [])
                dimension_descriptions = hist.get("dimension_descriptions", [])
                enhancement_explanation = hist.get("enhancement_explanation", "")

                markdown_content += f"**段落**: {para_index + 1}. {para_title}\n\n"
                if selected_dimensions:
                    markdown_content += (
                        f"**选择的维度**: {', '.join(selected_dimensions)}（共{len(selected_dimensions)}个）\n\n"
                    )
                if enhancement_explanation:
                    markdown_content += f"**加强说明**: {enhancement_explanation}\n\n"
                if dimension_descriptions:
                    markdown_content += "#### 按维度分开的痛点描述\n\n"
                    for idx, dim_desc in enumerate(dimension_descriptions, 1):
                        dim_name = dim_desc.get("dimension", f"维度{idx}")
                        dim_content = dim_desc.get("content", "")
                        markdown_content += f"**{idx}. {dim_name}**\n\n{dim_content}\n\n"
                markdown_content += f"**加强前**:\n\n{content_before}\n\n"
                markdown_content += f"**加强后（完整内容）**:\n\n{content_after}\n\n"
                markdown_content += "---\n\n"

            elif iteration_key == "investor_evaluation":
                markdown_content += "### 投资者评估\n\n"
                investor_eval = hist.get("investor_evaluation", {})
                structure_before = hist.get("structure_before", [])
                structure_after = hist.get("structure_after", [])

                markdown_content += "#### 整体评估\n\n"
                for key, label in [
                    ("market_size", "市场大小"),
                    ("replicability", "可复制性"),
                    ("competitive_barriers", "竞争壁垒"),
                    ("unique_competitive_advantage", "独特竞争力"),
                    ("revenue_model", "盈利模型"),
                    ("overall_assessment", "整体评估"),
                    ("concerns", "关注点"),
                    ("suggestions", "整体改进建议"),
                ]:
                    if investor_eval.get(key):
                        markdown_content += f"- **{label}**: {investor_eval.get(key)}\n"
                markdown_content += "\n"

                paragraph_feedbacks = investor_eval.get("paragraph_specific_feedback", [])
                markdown_content += "#### 段落反馈与改进\n\n"
                markdown_content += f"**评估段落数**: {len(paragraph_feedbacks)}\n\n"

                for idx, para_fb in enumerate(paragraph_feedbacks):
                    para_index = para_fb.get("paragraph_index", idx)
                    para_title = para_fb.get("paragraph_title", f"段落 {para_index + 1}")
                    markdown_content += f"##### 段落 {para_index + 1}: {para_title}\n\n"
                    if para_fb.get("feedback"):
                        markdown_content += f"**投资者反馈**: {para_fb.get('feedback')}\n\n"
                    if para_fb.get("suggestions"):
                        markdown_content += (
                            f"**改进建议**: {para_fb.get('suggestions')}\n\n"
                        )
                    if para_index < len(structure_before) and para_index < len(
                        structure_after
                    ):
                        para_before = structure_before[para_index]
                        para_after = structure_after[para_index]
                        content_before = para_before.get("content", "")
                        content_after = para_after.get("content", "")
                        if content_before != content_after:
                            markdown_content += f"**修改前**:\n\n{content_before}\n\n"
                            markdown_content += f"**修改后**:\n\n{content_after}\n\n"
                        else:
                            markdown_content += "*（该段落未修改）*\n\n"
                    markdown_content += "---\n\n"

            elif iteration_key == "60s_pitch":
                markdown_content += "### 黄金60秒Pitch\n\n"
                pitch_result = hist.get("pitch_result", {})
                painpoint_resonance = pitch_result.get("painpoint_resonance", {})
                if painpoint_resonance:
                    markdown_content += "#### ① 痛点共鸣\n\n"
                    selected_dims = painpoint_resonance.get("selected_dimensions", [])
                    if selected_dims:
                        markdown_content += (
                            f"**选择的维度**: {', '.join(selected_dims)}\n\n"
                        )
                    content = painpoint_resonance.get("content", "")
                    if content:
                        markdown_content += f"{content}\n\n"
                    markdown_content += "---\n\n"

                team_advantages = pitch_result.get("team_advantages", {})
                if team_advantages:
                    markdown_content += "#### ② 团队优势\n\n"
                    selected_advs = team_advantages.get("selected_advantages", [])
                    if selected_advs:
                        markdown_content += (
                            f"**选择的优势**: {', '.join(selected_advs)}\n\n"
                        )
                    content = team_advantages.get("content", "")
                    if content:
                        markdown_content += f"{content}\n\n"
                    markdown_content += "---\n\n"

                call_to_action = pitch_result.get("call_to_action", {})
                if call_to_action:
                    markdown_content += "#### ③ 召唤行动\n\n"
                    target_audience = call_to_action.get("target_audience", "")
                    action = call_to_action.get("action", "")
                    if target_audience:
                        markdown_content += f"**目标受众**: {target_audience}\n\n"
                    if action:
                        markdown_content += f"**行动**: {action}\n\n"
                    content = call_to_action.get("content", "")
                    if content:
                        markdown_content += f"{content}\n\n"
                    markdown_content += "---\n\n"

                full_pitch = pitch_result.get("full_pitch", "")
                if full_pitch:
                    markdown_content += "#### 完整60秒Pitch文本\n\n"
                    markdown_content += f"> {full_pitch}\n\n"
                    markdown_content += "---\n\n"

            elif iteration_key == "ppt_generation":
                markdown_content += "### PPT草稿\n\n"
                ppt_result = hist.get("ppt_result", {})
                slides = ppt_result.get("slides", [])
                markdown_content += f"**总页数**: {len(slides)}\n\n"
                for slide in slides:
                    slide_no = slide.get("slide_number", "?")
                    slide_title = slide.get("slide_title", "")
                    slide_point = slide.get("point", "")
                    slide_line = slide.get("line", "")
                    slide_reserved = slide.get("reserved", "")
                    markdown_content += f"#### 第 {slide_no} 页: {slide_title}\n\n"
                    if slide_point:
                        markdown_content += f"- **Point**: {slide_point}\n"
                    if slide_line:
                        markdown_content += f"- **Line**: {slide_line}\n"
                    if slide_reserved:
                        markdown_content += (
                            f"- **Reserved Hook**: {slide_reserved}\n"
                        )
                    markdown_content += "\n---\n\n"

        markdown_content += "\n## 最终评估结果\n\n"
        if evaluation_result.get("passed"):
            markdown_content += "**评估状态**: ✓ 通过\n\n"
            markdown_content += (
                f"**评估说明**: {evaluation_result.get('evaluation_result', 'N/A')}\n\n"
            )
        else:
            markdown_content += "**评估状态**: ✗ 不通过（已达到最大迭代次数）\n\n"
            failed_index = evaluation_result.get("failed_paragraph_index", -1)
            failed_title = evaluation_result.get("failed_paragraph_title", "未知")
            markdown_content += f"**失败段落**: {failed_index + 1}. {failed_title}\n\n"
            markdown_content += (
                f"**评估说明**: {evaluation_result.get('evaluation_result', 'N/A')}\n\n"
            )
            if evaluation_result.get("suggestions"):
                markdown_content += (
                    f"**修改建议**: {evaluation_result.get('suggestions')}\n\n"
                )

        return markdown_content


def create_bp_agent(config_file: Optional[str] = None) -> BPGenerationAgent:
    """
    创建BP Generation Agent实例的便捷函数

    Args:
        config_file: 配置文件路径

    Returns:
        BPGenerationAgent实例
    """
    config = load_config(config_file)
    return BPGenerationAgent(config)
