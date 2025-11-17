"""
BP Generation Agent
按照 test_bp_structure 的流程生成 BP 结构、评估、Pitch、PPT，并输出 Markdown
"""

import os
import traceback
import uuid
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
    PartnerSearchNode,
    InputCompletenessNode,
)
from .utils.config import Config, load_config
from .utils.text_processing import detect_language


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

        # 检查爱合伙API密钥是否可用
        self.aihehuo_available = bool(self.config.aihehuo_api_key)
        if self.aihehuo_available:
            print("✓ 爱合伙API密钥已配置，合伙人搜索功能可用")
        else:
            print("⚠ 爱合伙API密钥未配置，将跳过合伙人搜索功能")

        print("BP Generation Agent 已初始化")
        print(f"使用LLM: {self.llm_client.get_model_info()}")
        print(f"输出目录: {self.config.output_dir}")

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
        session_dir: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        生成BP结构、评估、Pitch和PPT；最终输出Markdown

        Args:
            business_idea: 商业创意
            output_file: 指定输出Markdown文件路径（可选）
            save_report: 是否保存Markdown到文件
            session_dir: Session目录路径（可选），如果未提供则自动生成session ID和目录

        Returns:
            包含输出文件路径、Markdown文本等信息的字典，包括：
            - session_id: 会话ID（如果未提供session_dir则自动生成）
            - session_dir: 会话目录路径（如果save_report为True）
        """
        print("\n" + "=" * 60)
        print(f"开始生成BP: {business_idea[:80]}...")
        print("=" * 60)

        # 如果没有提供session_dir，自动生成session ID和目录
        session_id = None
        if session_dir is None:
            session_id = str(uuid.uuid4())
            session_dir = os.path.join(self.config.output_dir, session_id)
            os.makedirs(session_dir, exist_ok=True)
            print(f"自动生成Session ID: {session_id}")
            print(f"Session目录: {session_dir}")
        else:
            # 如果提供了session_dir，从路径中提取session_id（如果可能）
            session_id = os.path.basename(session_dir)
            # 验证是否是有效的UUID格式
            try:
                uuid.UUID(session_id)
            except (ValueError, AttributeError):
                # 如果不是UUID格式，生成一个新的
                session_id = str(uuid.uuid4())
                print(f"从session_dir提取的ID不是有效UUID，生成新的Session ID: {session_id}")

        # 首先检查输入完整性
        input_completeness_node = InputCompletenessNode(self.llm_client)
        completeness_result = input_completeness_node.run(business_idea, session_dir=session_dir)
        
        # 如果输入不完整，返回错误信息
        if not completeness_result.get("is_complete", False):
            current_perspective = completeness_result.get("current_perspective", "none")
            suggestions = completeness_result.get("suggestions", [])
            perspective_details = completeness_result.get("perspective_details", {})
            
            # 构建错误消息
            perspective_names = {
                "technical": "技术视角",
                "user_painpoint": "用户痛点视角（需求视角）",
                "market": "市场视角",
                "mixed": "混合视角",
                "none": "无法确定"
            }
            perspective_name = perspective_names.get(current_perspective, "未知视角")
            
            error_message = f"输入不完整：当前输入主要属于{perspective_name}，但描述不够完整。\n\n"
            error_message += "各视角完整性评估：\n"
            
            # 使用节点返回的格式化信息
            formatted_checklist = completeness_result.get("formatted_checklist", {})
            
            for perspective, details in perspective_details.items():
                perspective_cn = {
                    "technical": "技术视角",
                    "user_painpoint": "用户痛点视角",
                    "market": "市场视角"
                }.get(perspective, perspective)
                completeness = details.get("completeness", "missing")
                completeness_cn = {
                    "complete": "完整",
                    "partial": "部分",
                    "missing": "缺失"
                }.get(completeness, completeness)
                error_message += f"- {perspective_cn}: {completeness_cn}\n"
                
                # 使用节点格式化的信息
                if perspective in formatted_checklist:
                    formatted = formatted_checklist[perspective]
                    
                    # 显示缺失的检查点
                    missing_checkpoints = formatted.get("missing_checkpoints", [])
                    if missing_checkpoints:
                        error_message += f"  缺失的检查点：\n"
                        for checkpoint in missing_checkpoints:
                            error_message += f"    - {checkpoint}\n"
                    
                    # 显示检查清单状态
                    checklist_status = formatted.get("checklist_status", [])
                    if checklist_status:
                        error_message += f"  检查清单状态：\n"
                        for item in checklist_status:
                            error_message += f"    {item['status']} {item['name']}\n"
            
            if suggestions:
                error_message += "\n改进建议：\n"
                for i, suggestion in enumerate(suggestions, 1):
                    error_message += f"{i}. {suggestion}\n"
            
            print("\n" + "=" * 60)
            print("输入完整性检查失败")
            print("=" * 60)
            print(error_message)
            
            return {
                "output_file": None,
                "markdown": None,
                "bp_structure": None,
                "iteration_history": [],
                "evaluation_result": None,
                "pitch_result": None,
                "ppt_result": None,
                "partner_search_result": None,
                "partner_report_file": None,
                "ppt_design_file": None,
                "session_id": session_id,
                "session_dir": session_dir if save_report else None,
                "input_completeness": completeness_result,
                "error": error_message
            }
        
        print("✓ 输入完整性检查通过")
        
        # 初始化节点
        bp_structure_node = BPStructureNode(self.llm_client, business_idea)
        evaluation_node = BPEvaluationNode(self.llm_client)
        painpoint_enhancement_node = PainpointEnhancementNode(self.llm_client)
        investor_eval_node = InvestorEvaluationNode(self.llm_client)
        pitch_node = Pitch60sNode(self.llm_client)
        ppt_node = PPTGenerationNode(self.llm_client)
        
        # 初始化合伙人搜索节点（需要爱合伙API密钥）
        partner_search_node = None
        if self.aihehuo_available:
            try:
                partner_search_node = PartnerSearchNode(
                    llm_client=self.llm_client,
                    api_key=self.config.aihehuo_api_key,
                    api_base=self.config.aihehuo_api_base
                )
                print("✓ 合伙人搜索节点已初始化")
            except Exception as e:
                print(f"警告: 初始化合伙人搜索节点失败: {e}，将跳过合伙人搜索")
                self.aihehuo_available = False
        else:
            print("提示: 未配置爱合伙API密钥，将跳过合伙人搜索")

        bp_structure: Optional[List[Dict[str, str]]] = None
        evaluation_result: Optional[Dict[str, Any]] = None
        iteration_history: List[Dict[str, Any]] = []
        pitch_result: Optional[Dict[str, Any]] = None
        ppt_result: Optional[Dict[str, Any]] = None
        partner_search_result: Optional[Dict[str, Any]] = None

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
                            if (
                                ("用户画像" in title and "痛点" in title)
                                or ("User Persona" in title and "Pain Point" in title)
                            ):
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

                        # ------------------------------------------------------------------
                        # 搜索合伙人和投资人
                        # ------------------------------------------------------------------
                        if partner_search_node:
                            print("\n" + "=" * 60)
                            print("开始搜索合伙人和投资人")
                            print("=" * 60)
                            try:
                                partner_search_result = partner_search_node.run(
                                    input_data={
                                        "business_idea": business_idea,
                                        "bp_structure": bp_structure
                                    },
                                    partner_per_page=10,
                                    investor_per_page=10,
                                    wechat_reachable_only=True
                                )
                                iteration_history.append(
                                    {"iteration": "partner_search", "partner_search_result": partner_search_result}
                                )
                                partner_count = partner_search_result.get("partner_count", 0)
                                investor_count = partner_search_result.get("investor_count", 0)
                                partner_query = partner_search_result.get("partner_search_query", "")
                                investor_query = partner_search_result.get("investor_search_query", "")
                                print(f"✓ 合伙人搜索完成，找到 {partner_count} 个合伙人，{investor_count} 个投资人")
                                if partner_query:
                                    print(f"  合伙人搜索查询: {partner_query}")
                                if investor_query:
                                    print(f"  投资人搜索查询: {investor_query}")
                                if partner_count == 0 and investor_count == 0:
                                    print("  警告: 未找到任何合伙人或投资人")
                            except Exception as exc:
                                print(f"搜索合伙人和投资人失败: {exc}")
                                traceback.print_exc()
                                partner_search_result = None

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
            # 从iteration_history中提取partner_search_result（如果存在）
            if not partner_search_result:
                for hist in iteration_history:
                    if hist.get("iteration") == "partner_search":
                        partner_search_result = hist.get("partner_search_result")
                        if partner_search_result:
                            break
            
            # 调试信息：检查partner_search_result
            if partner_search_result:
                partner_count = partner_search_result.get("partner_count", 0)
                investor_count = partner_search_result.get("investor_count", 0)
                partner_query = partner_search_result.get("partner_search_query", "")
                investor_query = partner_search_result.get("investor_search_query", "")
                print(f"\n[DEBUG] 合伙人搜索结果: {partner_count} 个合伙人, {investor_count} 个投资人")
                print(f"[DEBUG] 合伙人搜索短语: {partner_query}")
                print(f"[DEBUG] 投资人搜索短语: {investor_query}")
            else:
                print("\n[DEBUG] 合伙人搜索结果为空，将不会添加到报告中")
                # 尝试从iteration_history中检查是否有搜索短语
                for hist in iteration_history:
                    if hist.get("iteration") == "partner_search":
                        search_result = hist.get("partner_search_result")
                        if search_result:
                            partner_query = search_result.get("partner_search_query", "")
                            investor_query = search_result.get("investor_search_query", "")
                            if partner_query or investor_query:
                                print(f"[DEBUG] 发现搜索短语但结果为空:")
                                print(f"[DEBUG]   合伙人搜索短语: {partner_query}")
                                print(f"[DEBUG]   投资人搜索短语: {investor_query}")
                        break
            
            markdown_content = self._build_markdown(
                business_idea, bp_structure, iteration_history, evaluation_result, partner_search_result
            )

            # 从iteration_history中提取ppt_result（如果存在）
            if not ppt_result:
                for hist in iteration_history:
                    if hist.get("iteration") == "ppt_generation":
                        ppt_result = hist.get("ppt_result")
                        if ppt_result:
                            break
            
            # 调试信息：检查ppt_result
            if ppt_result:
                slides = ppt_result.get("slides", [])
                if slides:
                    print(f"\n检测到PPT结果，包含 {len(slides)} 页幻灯片")
                else:
                    print("\n警告: PPT结果存在但slides为空")

            if save_report:
                output_path = output_file or self._build_default_filename(business_idea, session_dir)
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(markdown_content)
                print("\n" + "=" * 60)
                print("Markdown已保存")
                print("=" * 60)
                print(f"输出文件: {output_path}")
                
                # 如果生成了PPT，保存到单独的文件
                print(f"\n[DEBUG] 检查PPT保存条件:")
                print(f"  - ppt_result存在: {ppt_result is not None}")
                if ppt_result:
                    slides = ppt_result.get("slides", [])
                    print(f"  - slides存在: {slides is not None}")
                    print(f"  - slides长度: {len(slides) if slides else 0}")
                    if slides and len(slides) > 0:
                        print(f"  - 条件满足，开始保存PPT设计文件...")
                        try:
                            ppt_file_path = self._save_ppt_design_file(
                                business_idea, bp_structure, ppt_result, output_path
                            )
                            if ppt_file_path:
                                print(f"PPT设计文件已保存: {ppt_file_path}")
                            else:
                                print("警告: PPT设计文件保存失败")
                        except Exception as e:
                            print(f"保存PPT设计文件时出错: {e}")
                            traceback.print_exc()
                    else:
                        print("提示: PPT结果存在但slides为空，跳过PPT设计文件保存")
                else:
                    print("提示: 未生成PPT内容，跳过PPT设计文件保存")
                
                # 保存人脉报告（合伙人搜索结果）
                partner_report_path = None
                if partner_search_result:
                    partner_count = partner_search_result.get("partner_count", 0)
                    investor_count = partner_search_result.get("investor_count", 0)
                    partner_query = partner_search_result.get("partner_search_query", "")
                    investor_query = partner_search_result.get("investor_search_query", "")
                    if partner_count > 0 or investor_count > 0 or partner_query or investor_query:
                        try:
                            partner_report_path = self._save_partner_report(
                                business_idea, partner_search_result, output_path
                            )
                            if partner_report_path:
                                print(f"\n✓ 人脉报告已保存: {partner_report_path}")
                            else:
                                print("\n警告: 人脉报告保存失败")
                        except Exception as e:
                            print(f"\n保存人脉报告时出错: {e}")
                            traceback.print_exc()
                
                # 从保存的PPT文件路径中提取ppt_design_file
                ppt_design_file = None
                if ppt_result and output_path:
                    base_name = os.path.splitext(os.path.basename(output_path))[0]
                    ppt_dir = os.path.dirname(output_path)
                    ppt_design_file = os.path.join(ppt_dir, f"{base_name}_ppt_design.md")
                    if not os.path.exists(ppt_design_file):
                        ppt_design_file = None
            else:
                print("\n[DEBUG] save_report为False，跳过文件保存")
                output_path = None
                partner_report_path = None
                ppt_design_file = None

            return {
                "output_file": output_path,
                "markdown": markdown_content,
                "bp_structure": bp_structure,
                "iteration_history": iteration_history,
                "evaluation_result": evaluation_result,
                "pitch_result": pitch_result,
                "ppt_result": ppt_result,
                "partner_search_result": partner_search_result,
                "partner_report_file": partner_report_path if save_report and partner_search_result else None,
                "ppt_design_file": ppt_design_file if save_report and ppt_result else None,
                "session_id": session_id,
                "session_dir": session_dir if save_report else None,
                "input_completeness": completeness_result,
            }

        except Exception as exc:
            print(f"生成过程中发生错误: {exc}")
            raise

    # ---------------------------------------------------------------------- #
    # Markdown 构建 & 工具方法
    # ---------------------------------------------------------------------- #

    def _build_default_filename(self, business_idea: str, session_dir: Optional[str] = None) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_idea = "".join(
            c for c in business_idea[:30] if c.isalnum() or c in (" ", "-", "_")
        ).rstrip()
        safe_idea = safe_idea.replace(" ", "_")
        
        # 如果提供了session_dir，使用session_dir作为输出目录
        output_dir = session_dir if session_dir else self.config.output_dir
        return os.path.join(
            output_dir, f"bp_structure_{safe_idea}_{timestamp}.md"
        )
    
    def _save_ppt_design_file(
        self,
        business_idea: str,
        bp_structure: List[Dict[str, str]],
        ppt_result: Dict[str, Any],
        main_report_path: str,
    ) -> Optional[str]:
        """
        保存PPT设计文件，包含详细的视觉设计指令
        
        Args:
            business_idea: 商业创意
            bp_structure: BP结构
            ppt_result: PPT生成结果
            main_report_path: 主报告文件路径
            
        Returns:
            保存的文件路径，如果失败则返回None
        """
        try:
            # 基于主报告路径生成PPT文件路径
            base_name = os.path.splitext(os.path.basename(main_report_path))[0]
            ppt_dir = os.path.dirname(main_report_path)
            ppt_file_path = os.path.join(ppt_dir, f"{base_name}_ppt_design.md")
            
            print(f"\n[DEBUG] 准备保存PPT设计文件:")
            print(f"  - 主报告路径: {main_report_path}")
            print(f"  - PPT文件路径: {ppt_file_path}")
            print(f"  - 目录存在: {os.path.exists(ppt_dir)}")
            
            # 检测语言
            detected_lang = detect_language(business_idea)
            is_english = detected_lang == 'en'
            print(f"  - 检测到的语言: {'英文' if is_english else '中文'}")
            
            # 生成PPT设计内容
            print(f"  - 开始生成PPT设计内容...")
            ppt_content = self._format_ppt_design_prompt(
                business_idea, bp_structure, ppt_result, is_english
            )
            print(f"  - PPT设计内容长度: {len(ppt_content)} 字符")
            
            # 保存文件
            print(f"  - 正在写入文件...")
            with open(ppt_file_path, "w", encoding="utf-8") as f:
                f.write(ppt_content)
            
            # 验证文件是否成功创建
            if os.path.exists(ppt_file_path):
                file_size = os.path.getsize(ppt_file_path)
                print(f"  - 文件已成功创建，大小: {file_size} 字节")
                return ppt_file_path
            else:
                print(f"  - 错误: 文件创建后不存在!")
                return None
        except Exception as e:
            print(f"保存PPT设计文件失败: {e}")
            traceback.print_exc()
            return None
    
    def _format_ppt_design_prompt(
        self,
        business_idea: str,
        bp_structure: List[Dict[str, str]],
        ppt_result: Dict[str, Any],
        is_english: bool = False,
    ) -> str:
        """
        格式化PPT设计提示词，包含详细的视觉设计指令
        
        Args:
            business_idea: 商业创意
            bp_structure: BP结构
            ppt_result: PPT生成结果
            is_english: 是否为英文
            
        Returns:
            格式化后的PPT设计提示词
        """
        slides = ppt_result.get("slides", [])
        
        if is_english:
            content = "# PowerPoint Slide Design Brief\n\n"
            content += "## Business Idea\n\n"
            content += f"{business_idea.strip()}\n\n"
            content += "---\n\n"
            content += "## Design Requirements\n\n"
            content += "Please create a professional 10-slide PowerPoint presentation based on the following content. "
            content += "Each slide should follow modern design principles with clear visual hierarchy, appropriate use of whitespace, and consistent branding.\n\n"
            content += "### Design Guidelines:\n\n"
            content += "1. **Color Scheme**: Use a professional color palette (suggested: primary brand color + complementary colors, avoid too many colors)\n"
            content += "2. **Typography**: Use clear, readable fonts (suggested: sans-serif for headings, serif or sans-serif for body text)\n"
            content += "3. **Layout**: Maintain consistent margins and spacing across all slides\n"
            content += "4. **Visual Elements**: Use icons, charts, and images appropriately to support the content\n"
            content += "5. **Slide Transitions**: Keep transitions subtle and professional\n"
            content += "6. **Data Visualization**: If slides contain data, use appropriate charts (bar, line, pie, etc.)\n"
            content += "7. **Branding**: Include company/logo placement consistently (typically top-right or bottom-right)\n\n"
            content += "---\n\n"
            content += "## Slide Content and Design Specifications\n\n"
            
            for slide in slides:
                slide_no = slide.get("slide_number", "?")
                slide_title = slide.get("slide_title", "")
                slide_point = slide.get("point", "")
                slide_line = slide.get("line", "")
                slide_reserved = slide.get("reserved", "")
                
                content += f"### Slide {slide_no}: {slide_title}\n\n"
                
                # Content specifications
                content += "**Content to Include:**\n\n"
                if slide_point:
                    content += f"- **Main Point**: {slide_point}\n"
                if slide_line:
                    content += f"- **Supporting Line**: {slide_line}\n"
                if slide_reserved:
                    content += f"- **Reserved Hook**: {slide_reserved}\n"
                
                # Design specifications based on slide number
                content += "\n**Design Specifications:**\n\n"
                
                if slide_no == 1:
                    content += "- **Layout**: Title slide with large, bold title\n"
                    content += "- **Visual**: Hero image or abstract background related to the business idea\n"
                    content += "- **Typography**: Large title font (suggested: 48-60pt), subtitle in smaller font\n"
                    content += "- **Color**: Use brand primary color prominently\n"
                elif slide_no == 2:
                    content += "- **Layout**: Problem statement slide\n"
                    content += "- **Visual**: Use icons or illustrations to represent pain points\n"
                    content += "- **Typography**: Clear heading with bullet points or numbered list\n"
                    content += "- **Color**: Consider using contrasting colors to highlight problems\n"
                elif slide_no in [3, 4, 5]:
                    content += "- **Layout**: Content slide with clear sections\n"
                    content += "- **Visual**: Use icons, charts, or diagrams to illustrate key concepts\n"
                    content += "- **Typography**: Hierarchical text structure (heading, subheading, body)\n"
                    content += "- **Color**: Maintain brand consistency\n"
                elif slide_no in [6, 7, 8]:
                    content += "- **Layout**: Feature or benefit-focused slide\n"
                    content += "- **Visual**: Use comparison tables, before/after visuals, or feature icons\n"
                    content += "- **Typography**: Emphasize key benefits with larger font or bold text\n"
                    content += "- **Color**: Use accent colors to highlight important information\n"
                elif slide_no == 9:
                    content += "- **Layout**: Business model or financial slide\n"
                    content += "- **Visual**: Use charts, graphs, or infographics to present data\n"
                    content += "- **Typography**: Ensure numbers and data are clearly readable\n"
                    content += "- **Color**: Use color coding for different data categories\n"
                elif slide_no == 10:
                    content += "- **Layout**: Call-to-action or closing slide\n"
                    content += "- **Visual**: Strong visual element (CTA button, contact info, or closing image)\n"
                    content += "- **Typography**: Large, bold call-to-action text\n"
                    content += "- **Color**: Use high-contrast colors for CTA elements\n"
                else:
                    content += "- **Layout**: Standard content slide\n"
                    content += "- **Visual**: Use appropriate icons or images to support content\n"
                    content += "- **Typography**: Clear hierarchy with readable fonts\n"
                    content += "- **Color**: Maintain brand consistency\n"
                
                content += "\n---\n\n"
            
            content += "## Additional Design Notes\n\n"
            content += "- Ensure all slides maintain visual consistency\n"
            content += "- Use high-quality images and graphics (avoid pixelated or low-resolution images)\n"
            content += "- Keep text concise and readable (avoid overcrowding slides)\n"
            content += "- Use animations sparingly and only when they add value\n"
            content += "- Ensure good contrast between text and background colors for readability\n"
            content += "- Consider accessibility: use alt text for images and ensure color-blind friendly palettes\n\n"
            content += "---\n\n"
            content += "*This design brief can be used as a prompt for AI tools like Claude, Midjourney, or other design tools to generate the actual PowerPoint slides.*\n"
        else:
            content = "# PowerPoint幻灯片设计说明\n\n"
            content += "## 商业创意\n\n"
            content += f"{business_idea.strip()}\n\n"
            content += "---\n\n"
            content += "## 设计要求\n\n"
            content += "请根据以下内容创建专业的10页PowerPoint演示文稿。每页幻灯片应遵循现代设计原则，具有清晰的视觉层次、适当的留白和一致的品牌风格。\n\n"
            content += "### 设计指南：\n\n"
            content += "1. **配色方案**：使用专业的配色方案（建议：主品牌色+互补色，避免使用过多颜色）\n"
            content += "2. **字体**：使用清晰易读的字体（建议：标题使用无衬线字体，正文使用衬线或无衬线字体）\n"
            content += "3. **布局**：在所有幻灯片中保持一致的边距和间距\n"
            content += "4. **视觉元素**：适当使用图标、图表和图片来支持内容\n"
            content += "5. **幻灯片过渡**：保持过渡效果微妙且专业\n"
            content += "6. **数据可视化**：如果幻灯片包含数据，使用适当的图表（柱状图、折线图、饼图等）\n"
            content += "7. **品牌标识**：一致地放置公司/logo（通常在右上角或右下角）\n\n"
            content += "---\n\n"
            content += "## 幻灯片内容和设计规范\n\n"
            
            for slide in slides:
                slide_no = slide.get("slide_number", "?")
                slide_title = slide.get("slide_title", "")
                slide_point = slide.get("point", "")
                slide_line = slide.get("line", "")
                slide_reserved = slide.get("reserved", "")
                
                content += f"### 第 {slide_no} 页：{slide_title}\n\n"
                
                # Content specifications
                content += "**需要包含的内容：**\n\n"
                if slide_point:
                    content += f"- **要点**：{slide_point}\n"
                if slide_line:
                    content += f"- **支持性文字**：{slide_line}\n"
                if slide_reserved:
                    content += f"- **预留钩子**：{slide_reserved}\n"
                
                # Design specifications based on slide number
                content += "\n**设计规范：**\n\n"
                
                if slide_no == 1:
                    content += "- **布局**：标题页，使用大号粗体标题\n"
                    content += "- **视觉**：与商业创意相关的英雄图片或抽象背景\n"
                    content += "- **字体**：大号标题字体（建议：48-60pt），副标题使用较小字体\n"
                    content += "- **颜色**：突出使用品牌主色\n"
                elif slide_no == 2:
                    content += "- **布局**：问题陈述页\n"
                    content += "- **视觉**：使用图标或插图来代表痛点\n"
                    content += "- **字体**：清晰的标题，配合项目符号或编号列表\n"
                    content += "- **颜色**：考虑使用对比色来突出显示问题\n"
                elif slide_no in [3, 4, 5]:
                    content += "- **布局**：内容页，具有清晰的部分划分\n"
                    content += "- **视觉**：使用图标、图表或图表来说明关键概念\n"
                    content += "- **字体**：层次化的文本结构（标题、副标题、正文）\n"
                    content += "- **颜色**：保持品牌一致性\n"
                elif slide_no in [6, 7, 8]:
                    content += "- **布局**：功能或优势聚焦页\n"
                    content += "- **视觉**：使用对比表格、前后对比图或功能图标\n"
                    content += "- **字体**：用较大字体或粗体强调关键优势\n"
                    content += "- **颜色**：使用强调色来突出重要信息\n"
                elif slide_no == 9:
                    content += "- **布局**：商业模式或财务页\n"
                    content += "- **视觉**：使用图表、图形或信息图来呈现数据\n"
                    content += "- **字体**：确保数字和数据清晰可读\n"
                    content += "- **颜色**：使用颜色编码来区分不同的数据类别\n"
                elif slide_no == 10:
                    content += "- **布局**：行动号召或结束页\n"
                    content += "- **视觉**：强烈的视觉元素（CTA按钮、联系信息或结束图片）\n"
                    content += "- **字体**：大号、粗体的行动号召文字\n"
                    content += "- **颜色**：为CTA元素使用高对比度颜色\n"
                else:
                    content += "- **布局**：标准内容页\n"
                    content += "- **视觉**：使用适当的图标或图片来支持内容\n"
                    content += "- **字体**：清晰的层次结构和易读的字体\n"
                    content += "- **颜色**：保持品牌一致性\n"
                
                content += "\n---\n\n"
            
            content += "## 其他设计注意事项\n\n"
            content += "- 确保所有幻灯片保持视觉一致性\n"
            content += "- 使用高质量的图片和图形（避免像素化或低分辨率图像）\n"
            content += "- 保持文字简洁易读（避免幻灯片过于拥挤）\n"
            content += "- 谨慎使用动画，仅在它们增加价值时使用\n"
            content += "- 确保文本和背景颜色之间有良好的对比度以便阅读\n"
            content += "- 考虑可访问性：为图片使用替代文本，确保色盲友好的调色板\n\n"
            content += "---\n\n"
            content += "*此设计说明可用作Claude、Midjourney或其他设计工具的提示词，以生成实际的PowerPoint幻灯片。*\n"
        
        return content

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
        partner_search_result: Optional[Dict[str, Any]] = None,
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
            
            elif iteration_key == "partner_search":
                # 合伙人搜索结果已经在最终评估结果之后单独添加，这里跳过
                pass

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
        
        # 注意：合伙人搜索结果现在保存到单独的人脉报告文档中，不再添加到主BP报告
        # 如果需要添加到主BP报告，可以取消下面的注释
        # if partner_search_result:
        #     partner_count = partner_search_result.get("partner_count", 0)
        #     investor_count = partner_search_result.get("investor_count", 0)
        #     partner_query = partner_search_result.get("partner_search_query", "")
        #     investor_query = partner_search_result.get("investor_search_query", "")
        #     if partner_count > 0 or investor_count > 0 or partner_query or investor_query:
        #         markdown_content += self._format_partner_search_results(partner_search_result)
        
        return markdown_content
    
    def _format_partner_search_results(self, partner_search_result: Dict[str, Any]) -> str:
        """
        格式化合伙人搜索结果为Markdown
        
        Args:
            partner_search_result: 合伙人搜索结果
            
        Returns:
            Markdown格式的合伙人搜索结果
        """
        content = "\n\n## 合伙人与投资人推荐\n\n"
        
        # 检测语言
        partner_query = partner_search_result.get("partner_search_query", "")
        is_english = detect_language(partner_query) == 'en' if partner_query else False
        
        if is_english:
            content += "### Partner Search\n\n"
            partner_query = partner_search_result.get("partner_search_query", "")
            if partner_query:
                content += f"**Search Query**: {partner_query}\n\n"
            
            partner_results = partner_search_result.get("partner_results", [])
            partner_count = partner_search_result.get("partner_count", 0)
            if partner_count > 0:
                content += f"**Found {partner_count} Partners**:\n\n"
                for i, partner in enumerate(partner_results[:10], 1):
                    content += f"#### Partner {i}\n\n"
                    content += f"- **User ID**: {partner.get('user_id', 'N/A')}\n"
                    content += f"- **Name**: {partner.get('name', 'N/A')}\n"
                    if partner.get('age_range'):
                        content += f"- **Age Range**: {partner.get('age_range')}\n"
                    elif partner.get('age'):
                        age = partner.get('age')
                        age_range = self._calculate_age_range(age)
                        content += f"- **Age Range**: {age_range}\n"
                    if partner.get('bio'):
                        bio = partner.get('bio', '').strip()
                        if bio:
                            content += f"- **Bio**: {bio}\n"
                    if partner.get('tags'):
                        tags = partner.get('tags', [])
                        if isinstance(tags, list):
                            content += f"- **Tags**: {', '.join(tags[:5])}\n"
                    content += "\n---\n\n"
            else:
                content += "No partners found.\n\n"
            
            content += "### Investor Search\n\n"
            investor_query = partner_search_result.get("investor_search_query", "")
            if investor_query:
                content += f"**Search Query**: {investor_query}\n\n"
            
            investor_results = partner_search_result.get("investor_results", [])
            investor_count = partner_search_result.get("investor_count", 0)
            if investor_count > 0:
                content += f"**Found {investor_count} Investors**:\n\n"
                for i, investor in enumerate(investor_results[:10], 1):
                    content += f"#### Investor {i}\n\n"
                    content += f"- **User ID**: {investor.get('user_id', 'N/A')}\n"
                    content += f"- **Name**: {investor.get('name', 'N/A')}\n"
                    if investor.get('age_range'):
                        content += f"- **Age Range**: {investor.get('age_range')}\n"
                    elif investor.get('age'):
                        age = investor.get('age')
                        age_range = self._calculate_age_range(age)
                        content += f"- **Age Range**: {age_range}\n"
                    if investor.get('bio'):
                        bio = investor.get('bio', '').strip()
                        if bio:
                            content += f"- **Bio**: {bio}\n"
                    if investor.get('tags'):
                        tags = investor.get('tags', [])
                        if isinstance(tags, list):
                            content += f"- **Tags**: {', '.join(tags[:5])}\n"
                    content += "\n---\n\n"
            else:
                content += "No investors found.\n\n"
        else:
            content += "### 合伙人搜索\n\n"
            partner_query = partner_search_result.get("partner_search_query", "")
            if partner_query:
                content += f"**搜索查询**: {partner_query}\n\n"
            
            partner_results = partner_search_result.get("partner_results", [])
            partner_count = partner_search_result.get("partner_count", 0)
            if partner_count > 0:
                content += f"**找到 {partner_count} 个合伙人**:\n\n"
                for i, partner in enumerate(partner_results[:10], 1):
                    content += f"#### 合伙人 {i}\n\n"
                    content += f"- **用户ID**: {partner.get('user_id', 'N/A')}\n"
                    content += f"- **姓名**: {partner.get('name', 'N/A')}\n"
                    if partner.get('age_range'):
                        content += f"- **年龄段**: {partner.get('age_range')}\n"
                    elif partner.get('age'):
                        age = partner.get('age')
                        age_range = self._calculate_age_range(age)
                        content += f"- **年龄段**: {age_range}\n"
                    if partner.get('bio'):
                        bio = partner.get('bio', '').strip()
                        if bio:
                            content += f"- **简介**: {bio}\n"
                    if partner.get('tags'):
                        tags = partner.get('tags', [])
                        if isinstance(tags, list):
                            content += f"- **标签**: {', '.join(tags[:5])}\n"
                    content += "\n---\n\n"
            else:
                content += "未找到合伙人。\n\n"
            
            content += "### 投资人搜索\n\n"
            investor_query = partner_search_result.get("investor_search_query", "")
            if investor_query:
                content += f"**搜索查询**: {investor_query}\n\n"
            
            investor_results = partner_search_result.get("investor_results", [])
            investor_count = partner_search_result.get("investor_count", 0)
            if investor_count > 0:
                content += f"**找到 {investor_count} 个投资人**:\n\n"
                for i, investor in enumerate(investor_results[:10], 1):
                    content += f"#### 投资人 {i}\n\n"
                    content += f"- **用户ID**: {investor.get('user_id', 'N/A')}\n"
                    content += f"- **姓名**: {investor.get('name', 'N/A')}\n"
                    if investor.get('age_range'):
                        content += f"- **年龄段**: {investor.get('age_range')}\n"
                    elif investor.get('age'):
                        age = investor.get('age')
                        age_range = self._calculate_age_range(age)
                        content += f"- **年龄段**: {age_range}\n"
                    if investor.get('bio'):
                        bio = investor.get('bio', '').strip()
                        if bio:
                            content += f"- **简介**: {bio}\n"
                    if investor.get('tags'):
                        tags = investor.get('tags', [])
                        if isinstance(tags, list):
                            content += f"- **标签**: {', '.join(tags[:5])}\n"
                    content += "\n---\n\n"
            else:
                content += "未找到投资人。\n\n"
        
        return content
    
    def _save_partner_report(
        self,
        business_idea: str,
        partner_search_result: Dict[str, Any],
        main_report_path: str,
    ) -> Optional[str]:
        """
        保存人脉报告到单独的文件
        
        Args:
            business_idea: 商业创意
            partner_search_result: 合伙人搜索结果
            main_report_path: 主报告文件路径
            
        Returns:
            人脉报告文件路径，如果失败则返回None
        """
        try:
            # 基于主报告文件名生成人脉报告文件名
            base_name = os.path.splitext(os.path.basename(main_report_path))[0]
            report_dir = os.path.dirname(main_report_path)
            
            # 移除文件名中的"bp_structure_"前缀（如果存在）
            if base_name.startswith("bp_structure_"):
                base_name = base_name[len("bp_structure_"):]
            
            # 生成人脉报告文件名
            partner_report_path = os.path.join(report_dir, f"partner_report_{base_name}.md")
            
            print(f"\n[DEBUG] 准备保存人脉报告:")
            print(f"  - 主报告路径: {main_report_path}")
            print(f"  - 人脉报告路径: {partner_report_path}")
            print(f"  - 目录存在: {os.path.exists(report_dir)}")
            
            # 生成人脉报告内容
            report_content = self._build_partner_report_content(
                business_idea, partner_search_result
            )
            
            print(f"  - 人脉报告内容长度: {len(report_content)} 字符")
            
            # 写入文件
            print(f"  - 正在写入文件...")
            with open(partner_report_path, "w", encoding="utf-8") as f:
                f.write(report_content)
            
            if os.path.exists(partner_report_path):
                file_size = os.path.getsize(partner_report_path)
                print(f"  - 文件已成功创建，大小: {file_size} 字节")
                return partner_report_path
            else:
                print(f"  - 错误: 文件创建后不存在!")
                return None
        except Exception as e:
            print(f"保存人脉报告失败: {e}")
            traceback.print_exc()
            return None
    
    def _build_partner_report_content(
        self,
        business_idea: str,
        partner_search_result: Dict[str, Any],
    ) -> str:
        """
        构建人脉报告内容
        
        Args:
            business_idea: 商业创意
            partner_search_result: 合伙人搜索结果
            
        Returns:
            人脉报告的Markdown内容
        """
        # 检测语言
        is_english = detect_language(business_idea) == 'en'
        
        if is_english:
            content = "# Partner & Investor Network Report\n\n"
            content += f"## Business Idea\n\n"
            content += f"{business_idea.strip()}\n\n"
            content += "---\n\n"
        else:
            content = "# 人脉报告\n\n"
            content += f"## 商业创意\n\n"
            content += f"{business_idea.strip()}\n\n"
            content += "---\n\n"
        
        # 添加合伙人搜索结果
        content += self._format_partner_search_results(partner_search_result)
        
        # 添加生成时间
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if is_english:
            content += f"\n\n---\n\n*Generated at: {timestamp}*\n"
        else:
            content += f"\n\n---\n\n*生成时间: {timestamp}*\n"
        
        return content
    
    def _calculate_age_range(self, age: int) -> str:
        """
        根据年龄计算年龄段
        
        Args:
            age: 年龄
            
        Returns:
            年龄段字符串
        """
        if age < 25:
            return "20-24岁"
        elif age < 30:
            return "25-29岁"
        elif age < 35:
            return "30-34岁"
        elif age < 40:
            return "35-39岁"
        elif age < 45:
            return "40-44岁"
        elif age < 50:
            return "45-49岁"
        elif age < 55:
            return "50-54岁"
        elif age < 60:
            return "55-59岁"
        else:
            return "60岁以上"


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
