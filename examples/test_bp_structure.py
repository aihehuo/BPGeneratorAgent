"""
BP Structure Node 测试程序
只测试 BP 结构生成，将结果输出到 markdown 文档
"""

import os
import sys
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.nodes.bp_structure_node import BPStructureNode
from src.nodes.bp_evaluation_node import BPEvaluationNode
from src.nodes.painpoint_enhancement_node import PainpointEnhancementNode
from src.nodes.investor_evaluation_node import InvestorEvaluationNode
from src.nodes.pitch_60s_node import Pitch60sNode
from src.nodes.ppt_generation_node import PPTGenerationNode
from src.llms import DeepSeekLLM, OpenAILLM, QwenLLM
from src.utils.config import load_config


def format_bp_structure_to_markdown(bp_structure, business_idea):
    """
    将BP结构格式化为Markdown文档
    
    Args:
        bp_structure: BP结构列表，每个元素包含 title 和 content
        business_idea: 商业创意
        
    Returns:
        Markdown格式的字符串
    """
    markdown = f"""# 商业计划书结构

## 商业创意

{business_idea.strip()}

---

## 计划书结构

"""
    
    for i, section in enumerate(bp_structure, 1):
        title = section.get("title", f"段落 {i}")
        content = section.get("content", "")
        
        markdown += f"### {i}. {title}\n\n"
        markdown += f"{content}\n\n"
        markdown += "---\n\n"
    
    # 添加生成信息
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    markdown += f"\n\n---\n\n*生成时间: {timestamp}*\n"
    
    return markdown


def test_bp_structure(business_idea, output_file=None):
    """
    测试BP结构生成
    
    Args:
        business_idea: 商业创意
        output_file: 输出文件路径，如果为None则自动生成
    """
    print("=" * 60)
    print("BP Structure Node 测试")
    print("=" * 60)
    
    try:
        # 加载配置
        print("\n正在加载配置...")
        config = load_config()
        
        # 初始化LLM客户端
        print(f"正在初始化LLM客户端 ({config.default_llm_provider})...")
        if config.default_llm_provider == "deepseek":
            llm_client = DeepSeekLLM(
                api_key=config.deepseek_api_key,
                model_name=config.deepseek_model
            )
        elif config.default_llm_provider == "openai":
            llm_client = OpenAILLM(
                api_key=config.openai_api_key,
                model_name=config.openai_model
            )
        elif config.default_llm_provider == "qwen":
            llm_client = QwenLLM(
                api_key=config.qwen_api_key,
                model_name=config.qwen_model
            )
        else:
            raise ValueError(f"不支持的LLM提供商: {config.default_llm_provider}")
        
        print(f"LLM模型: {llm_client.get_model_info()}")
        
        # 创建BP结构节点和评估节点
        print("\n正在创建BP结构节点和评估节点...")
        bp_structure_node = BPStructureNode(llm_client, business_idea)
        evaluation_node = BPEvaluationNode(llm_client)
        painpoint_enhancement_node = PainpointEnhancementNode(llm_client)
        investor_eval_node = InvestorEvaluationNode(llm_client)
        pitch_60s_node = Pitch60sNode(llm_client)
        ppt_generation_node = PPTGenerationNode(llm_client)
        
        # 循环生成和评估，最多3次
        max_iterations = 3
        bp_structure = None
        evaluation_result = None
        iteration_history = []
        
        for iteration in range(max_iterations):
            iteration_num = iteration + 1
            print(f"\n{'='*60}")
            print(f"迭代 {iteration_num}/{max_iterations}")
            print(f"{'='*60}")
            
            try:
                # 生成或重新生成BP结构
                if iteration == 0:
                    print("正在生成BP结构...")
                    bp_structure = bp_structure_node.run()
                else:
                    print("正在根据反馈重新生成BP结构...")
                    bp_structure = bp_structure_node.regenerate(
                        evaluation_result=evaluation_result.get("evaluation_result", ""),
                        suggestions=evaluation_result.get("suggestions", ""),
                        current_structure=bp_structure
                    )
            except ValueError as e:
                # JSON解析失败，中断程序
                print(f"\n{'='*60}")
                print("错误: JSON解析失败，程序中断")
                print(f"{'='*60}")
                print(f"错误信息: {str(e)}")
                print(f"\n迭代 {iteration_num} 失败，无法继续")
                raise e
            except Exception as e:
                # 其他异常，也中断程序
                print(f"\n{'='*60}")
                print("错误: 生成BP结构时发生异常，程序中断")
                print(f"{'='*60}")
                print(f"错误信息: {str(e)}")
                print(f"\n迭代 {iteration_num} 失败，无法继续")
                raise e
            
            print(f"\n成功生成 {len(bp_structure)} 个段落:")
            for i, section in enumerate(bp_structure, 1):
                print(f"  {i}. {section.get('title', 'N/A')}")
            
            # 评估BP结构
            print("\n正在评估BP结构...")
            evaluation_result = evaluation_node.evaluate_paragraphs(business_idea, bp_structure)
            
            # 记录迭代历史
            iteration_history.append({
                "iteration": iteration_num,
                "structure": bp_structure.copy(),
                "evaluation": evaluation_result.copy()
            })
            
            if evaluation_result.get("passed"):
                print("✓ BP结构评估通过")
                print(f"  评估结果: {evaluation_result.get('evaluation_result', 'N/A')}")
                
                # BP评估通过后，进行痛点加强
                print(f"\n{'='*60}")
                print("BP评估通过，开始痛点加强")
                print(f"{'='*60}")
                
                try:
                    # 查找"用户画像与痛点"段落
                    painpoint_para_index = None
                    painpoint_para = None
                    
                    for i, para in enumerate(bp_structure):
                        title = para.get('title', '').strip()
                        # 匹配可能的标题变体
                        if '用户画像' in title and '痛点' in title:
                            painpoint_para_index = i
                            painpoint_para = para
                            break
                    
                    if painpoint_para:
                        print(f"找到痛点段落: {painpoint_para.get('title', 'N/A')}")
                        print("正在根据六个维度加强痛点陈述...")
                        
                        # 加强痛点段落
                        enhancement_result = painpoint_enhancement_node.enhance(
                            business_idea, 
                            painpoint_para
                        )
                        
                        # 获取加强后的内容
                        enhanced_content = enhancement_result.get('enhanced_content', '')
                        selected_dimensions = enhancement_result.get('selected_dimensions', [])
                        dimension_descriptions = enhancement_result.get('dimension_descriptions', [])
                        enhancement_explanation = enhancement_result.get('enhancement_explanation', '')
                        
                        print(f"✓ 痛点加强完成")
                        print(f"  选择的维度: {', '.join(selected_dimensions) if selected_dimensions else '无'}")
                        print(f"  维度数量: {len(selected_dimensions)}")
                        
                        # 更新BP结构中的痛点段落
                        bp_structure[painpoint_para_index] = {
                            "title": painpoint_para.get('title', '用户画像与痛点'),
                            "content": enhanced_content
                        }
                        
                        # 记录痛点加强结果
                        iteration_history.append({
                            "iteration": "painpoint_enhancement",
                            "paragraph_index": painpoint_para_index,
                            "paragraph_title": painpoint_para.get('title', '用户画像与痛点'),
                            "content_before": painpoint_para.get('content', ''),
                            "content_after": enhanced_content,
                            "selected_dimensions": selected_dimensions,
                            "dimension_descriptions": dimension_descriptions,
                            "enhancement_explanation": enhancement_explanation
                        })
                    else:
                        print("未找到'用户画像与痛点'段落，跳过痛点加强")
                        
                except Exception as e:
                    print(f"痛点加强失败: {str(e)}")
                    print("将继续使用原始痛点段落")
                    import traceback
                    traceback.print_exc()
                
                # 痛点加强后，进行投资者评估
                print(f"\n{'='*60}")
                print("痛点加强完成，开始投资者评估")
                print(f"{'='*60}")
                
                try:
                    # 保存评估前的结构
                    bp_structure_before = [para.copy() for para in bp_structure]
                    
                    # 评估整篇BP
                    print("正在从投资者角度评估整篇BP...")
                    investor_evaluation = investor_eval_node.evaluate_full_bp(business_idea, bp_structure)
                    
                    print(f"\n投资者整体评估:")
                    print(f"  整体评估: {investor_evaluation.get('overall_assessment', 'N/A')[:200]}...")
                    if investor_evaluation.get('concerns'):
                        print(f"  关注点: {investor_evaluation.get('concerns')[:200]}...")
                    
                    # 获取每个段落的反馈
                    paragraph_feedbacks = investor_evaluation.get('paragraph_specific_feedback', [])
                    print(f"\n投资者评估完成，共 {len(paragraph_feedbacks)} 个段落反馈")
                    
                    # 根据每个段落的反馈，逐个重新生成段落
                    print("正在根据投资者反馈重新生成每个段落...")
                    final_bp_structure = []
                    
                    for i, para in enumerate(bp_structure):
                        para_title = para.get('title', f'段落 {i+1}')
                        print(f"  处理段落 {i+1}: {para_title}")
                        
                        # 查找该段落的反馈
                        para_feedback = None
                        for fb in paragraph_feedbacks:
                            if fb.get('paragraph_index') == i:
                                para_feedback = fb
                                break
                        
                        if para_feedback:
                            # 根据反馈重新生成该段落
                            feedback_text = para_feedback.get('feedback', '')
                            suggestions_text = para_feedback.get('suggestions', '')
                            
                            try:
                                # 重新生成单个段落，明确要求保持标题
                                regenerated_para = bp_structure_node.regenerate(
                                    evaluation_result=f"段落 {i+1} ({para_title}) 的评估反馈: {feedback_text}。注意：必须保持标题 '{para_title}' 不变，只修改内容。",
                                    suggestions=f"针对段落 '{para_title}' 的改进建议: {suggestions_text}。重要：必须保持标题不变。",
                                    current_structure=[para]
                                )
                                if regenerated_para and len(regenerated_para) > 0:
                                    regenerated_item = regenerated_para[0]
                                    # 确保标题保持不变
                                    if regenerated_item.get('title') != para_title:
                                        print(f"    警告: 重新生成的段落标题不匹配，已修正为原标题")
                                        regenerated_item['title'] = para_title
                                    final_bp_structure.append(regenerated_item)
                                else:
                                    final_bp_structure.append(para)
                            except Exception as e:
                                print(f"    警告: 重新生成段落 {i+1} 失败，使用原段落: {str(e)}")
                                final_bp_structure.append(para)
                        else:
                            # 没有反馈，保持原段落
                            final_bp_structure.append(para)
                    
                    print(f"✓ 最终BP结构生成完成，共 {len(final_bp_structure)} 个段落")
                    bp_structure = final_bp_structure
                    
                    # 记录投资者评估结果（包含评估前后的结构）
                    iteration_history.append({
                        "iteration": "investor_evaluation",
                        "structure_before": bp_structure_before,
                        "structure_after": bp_structure.copy(),
                        "investor_evaluation": investor_evaluation
                    })
                    
                    # 投资者评估完成后，生成黄金60秒pitch
                    print(f"\n{'='*60}")
                    print("投资者评估完成，开始生成黄金60秒pitch")
                    print(f"{'='*60}")
                    
                    try:
                        print("正在根据BP结构生成黄金60秒pitch...")
                        pitch_result = pitch_60s_node.generate_pitch(business_idea, bp_structure)
                        
                        print(f"✓ 黄金60秒pitch生成成功")
                        painpoint_dims = pitch_result.get('painpoint_resonance', {}).get('selected_dimensions', [])
                        team_advs = pitch_result.get('team_advantages', {}).get('selected_advantages', [])
                        if painpoint_dims:
                            print(f"  痛点维度: {', '.join(painpoint_dims)}")
                        if team_advs:
                            print(f"  团队优势: {', '.join(team_advs)}")
                        
                        # 记录pitch结果
                        iteration_history.append({
                            "iteration": "60s_pitch",
                            "pitch_result": pitch_result
                        })
                        
                    except Exception as e:
                        print(f"生成黄金60秒pitch失败: {str(e)}")
                        import traceback
                        traceback.print_exc()
                        # 即使pitch生成失败，也继续使用BP结构
                    
                    # 生成10页PPT草稿
                    print(f"\n{'='*60}")
                    print("开始生成10页PPT草稿")
                    print(f"{'='*60}")
                    
                    try:
                        ppt_result = ppt_generation_node.generate_ppt(business_idea, bp_structure)
                        slides = ppt_result.get('slides', [])
                        print(f"✓ PPT草稿生成成功，共 {len(slides)} 页")
                        if slides:
                            preview_slides = slides[:3]
                            for slide in preview_slides:
                                slide_no = slide.get('slide_number')
                                slide_title = slide.get('slide_title', '')
                                slide_point = slide.get('point', '')
                                print(f"  第{slide_no}页: {slide_title} -> {slide_point}")
                        iteration_history.append({
                            "iteration": "ppt_generation",
                            "ppt_result": ppt_result
                        })
                    except Exception as e:
                        print(f"生成PPT草稿失败: {str(e)}")
                        import traceback
                        traceback.print_exc()
                    
                except Exception as e:
                    print(f"投资者评估或重新生成失败: {str(e)}")
                    print("将使用BP评估通过的结构作为最终结构")
                    import traceback
                    traceback.print_exc()
                
                break
            else:
                print("✗ BP结构评估不通过")
                failed_index = evaluation_result.get("failed_paragraph_index", -1)
                failed_title = evaluation_result.get("failed_paragraph_title", "未知")
                print(f"  失败段落索引: {failed_index}")
                print(f"  失败段落标题: {failed_title}")
                print(f"  评估结果: {evaluation_result.get('evaluation_result', 'N/A')}")
                if evaluation_result.get("suggestions"):
                    print(f"  修改建议: {evaluation_result.get('suggestions')}")
                
                if iteration_num < max_iterations:
                    print(f"\n将进行第 {iteration_num + 1} 次迭代...")
                else:
                    print(f"\n已达到最大迭代次数 ({max_iterations})，停止循环")
        
        # 最终结果
        print(f"\n{'='*60}")
        print("最终结果")
        print(f"{'='*60}")
        if evaluation_result.get("passed"):
            print("✓ BP结构最终评估通过")
        else:
            print("✗ BP结构最终评估不通过（已达到最大迭代次数）")
        
        # 格式化为Markdown
        print("\n正在格式化Markdown...")
        markdown_content = format_bp_structure_to_markdown(bp_structure, business_idea)
        
        # 在Markdown中添加迭代历史和评估结果
        markdown_content += f"\n\n## 迭代历史\n\n"
        markdown_content += f"**总迭代次数**: {len([h for h in iteration_history if isinstance(h.get('iteration'), int)])}\n\n"
        for hist in iteration_history:
            iteration_key = hist.get('iteration')
            
            if isinstance(iteration_key, int):
                # BP评估迭代
                markdown_content += f"### 迭代 {iteration_key}\n\n"
                eval_result = hist.get('evaluation', {})
                if eval_result.get("passed"):
                    markdown_content += f"- **状态**: ✓ 通过\n"
                else:
                    markdown_content += f"- **状态**: ✗ 不通过\n"
                    failed_index = eval_result.get("failed_paragraph_index", -1)
                    failed_title = eval_result.get("failed_paragraph_title", "未知")
                    markdown_content += f"- **失败段落**: {failed_index + 1}. {failed_title}\n"
                markdown_content += f"- **评估说明**: {eval_result.get('evaluation_result', 'N/A')}\n"
                if eval_result.get("suggestions"):
                    markdown_content += f"- **修改建议**: {eval_result.get('suggestions')}\n"
                markdown_content += "\n"
            elif iteration_key == "painpoint_enhancement":
                # 痛点加强
                markdown_content += f"### 痛点加强\n\n"
                para_index = hist.get('paragraph_index', -1)
                para_title = hist.get('paragraph_title', '用户画像与痛点')
                content_before = hist.get('content_before', '')
                content_after = hist.get('content_after', '')
                selected_dimensions = hist.get('selected_dimensions', [])
                dimension_descriptions = hist.get('dimension_descriptions', [])
                enhancement_explanation = hist.get('enhancement_explanation', '')
                
                markdown_content += f"**段落**: {para_index + 1}. {para_title}\n\n"
                
                if selected_dimensions:
                    markdown_content += f"**选择的维度**: {', '.join(selected_dimensions)}（共{len(selected_dimensions)}个）\n\n"
                
                if enhancement_explanation:
                    markdown_content += f"**加强说明**: {enhancement_explanation}\n\n"
                
                # 按维度展示描述
                if dimension_descriptions:
                    markdown_content += f"#### 按维度分开的痛点描述\n\n"
                    for i, dim_desc in enumerate(dimension_descriptions, 1):
                        dim_name = dim_desc.get('dimension', f'维度{i}')
                        dim_content = dim_desc.get('content', '')
                        markdown_content += f"**{i}. {dim_name}**\n\n{dim_content}\n\n"
                
                markdown_content += f"**加强前**:\n\n{content_before}\n\n"
                markdown_content += f"**加强后（完整内容）**:\n\n{content_after}\n\n"
                markdown_content += "---\n\n"
            elif iteration_key == "investor_evaluation":
                # 投资者评估
                markdown_content += f"### 投资者评估\n\n"
                investor_eval = hist.get('investor_evaluation', {})
                structure_before = hist.get('structure_before', [])
                structure_after = hist.get('structure_after', [])
                
                # 整体评估
                markdown_content += f"#### 整体评估\n\n"
                if investor_eval.get("market_size"):
                    markdown_content += f"- **市场大小**: {investor_eval.get('market_size')}\n"
                if investor_eval.get("replicability"):
                    markdown_content += f"- **可复制性**: {investor_eval.get('replicability')}\n"
                if investor_eval.get("competitive_barriers"):
                    markdown_content += f"- **竞争壁垒**: {investor_eval.get('competitive_barriers')}\n"
                if investor_eval.get("unique_competitive_advantage"):
                    markdown_content += f"- **独特竞争力**: {investor_eval.get('unique_competitive_advantage')}\n"
                if investor_eval.get("revenue_model"):
                    markdown_content += f"- **盈利模型**: {investor_eval.get('revenue_model')}\n"
                if investor_eval.get("overall_assessment"):
                    markdown_content += f"- **整体评估**: {investor_eval.get('overall_assessment')}\n"
                if investor_eval.get("concerns"):
                    markdown_content += f"- **关注点**: {investor_eval.get('concerns')}\n"
                if investor_eval.get("suggestions"):
                    markdown_content += f"- **整体改进建议**: {investor_eval.get('suggestions')}\n"
                markdown_content += "\n"
                
                # 段落反馈和前后对比
                paragraph_feedbacks = investor_eval.get('paragraph_specific_feedback', [])
                markdown_content += f"#### 段落反馈与改进\n\n"
                markdown_content += f"**评估段落数**: {len(paragraph_feedbacks)}\n\n"
                
                for i, para_fb in enumerate(paragraph_feedbacks):
                    para_index = para_fb.get("paragraph_index", i)
                    para_title = para_fb.get("paragraph_title", f"段落 {para_index + 1}")
                    
                    markdown_content += f"##### 段落 {para_index + 1}: {para_title}\n\n"
                    
                    # 反馈
                    if para_fb.get("feedback"):
                        markdown_content += f"**投资者反馈**: {para_fb.get('feedback')}\n\n"
                    if para_fb.get("suggestions"):
                        markdown_content += f"**改进建议**: {para_fb.get('suggestions')}\n\n"
                    
                    # 展示前后对比
                    if para_index < len(structure_before) and para_index < len(structure_after):
                        para_before = structure_before[para_index]
                        para_after = structure_after[para_index]
                        
                        content_before = para_before.get('content', '')
                        content_after = para_after.get('content', '')
                        
                        if content_before != content_after:
                            markdown_content += f"**修改前**:\n\n{content_before}\n\n"
                            markdown_content += f"**修改后**:\n\n{content_after}\n\n"
                        else:
                            markdown_content += f"*（该段落未修改）*\n\n"
                    
                    markdown_content += "---\n\n"
            elif iteration_key == "60s_pitch":
                # 黄金60秒pitch
                markdown_content += f"### 黄金60秒Pitch\n\n"
                pitch_result = hist.get('pitch_result', {})
                
                # 痛点共鸣部分
                painpoint_resonance = pitch_result.get('painpoint_resonance', {})
                if painpoint_resonance:
                    markdown_content += f"#### ① 痛点共鸣\n\n"
                    selected_dims = painpoint_resonance.get('selected_dimensions', [])
                    if selected_dims:
                        markdown_content += f"**选择的维度**: {', '.join(selected_dims)}\n\n"
                    painpoint_content = painpoint_resonance.get('content', '')
                    if painpoint_content:
                        markdown_content += f"{painpoint_content}\n\n"
                    markdown_content += "---\n\n"
                
                # 团队优势部分
                team_advantages = pitch_result.get('team_advantages', {})
                if team_advantages:
                    markdown_content += f"#### ② 团队优势\n\n"
                    selected_advs = team_advantages.get('selected_advantages', [])
                    if selected_advs:
                        markdown_content += f"**选择的优势**: {', '.join(selected_advs)}\n\n"
                    team_content = team_advantages.get('content', '')
                    if team_content:
                        markdown_content += f"{team_content}\n\n"
                    markdown_content += "---\n\n"
                
                # 召唤行动部分
                call_to_action = pitch_result.get('call_to_action', {})
                if call_to_action:
                    markdown_content += f"#### ③ 召唤行动\n\n"
                    target_audience = call_to_action.get('target_audience', '')
                    action = call_to_action.get('action', '')
                    if target_audience:
                        markdown_content += f"**目标受众**: {target_audience}\n\n"
                    if action:
                        markdown_content += f"**行动**: {action}\n\n"
                    cta_content = call_to_action.get('content', '')
                    if cta_content:
                        markdown_content += f"{cta_content}\n\n"
                    markdown_content += "---\n\n"
                
                # 完整pitch文本
                full_pitch = pitch_result.get('full_pitch', '')
                if full_pitch:
                    markdown_content += f"#### 完整60秒Pitch文本\n\n"
                    markdown_content += f"> {full_pitch}\n\n"
                    markdown_content += "---\n\n"
            elif iteration_key == "ppt_generation":
                # PPT草稿
                markdown_content += f"### PPT草稿\n\n"
                ppt_result = hist.get('ppt_result', {})
                slides = ppt_result.get('slides', [])
                markdown_content += f"**总页数**: {len(slides)}\n\n"
                
                for slide in slides:
                    slide_no = slide.get('slide_number', '?')
                    slide_title = slide.get('slide_title', '')
                    slide_point = slide.get('point', '')
                    slide_line = slide.get('line', '')
                    slide_reserved = slide.get('reserved', '')
                    
                    markdown_content += f"#### 第 {slide_no} 页: {slide_title}\n\n"
                    if slide_point:
                        markdown_content += f"- **Point**: {slide_point}\n"
                    if slide_line:
                        markdown_content += f"- **Line**: {slide_line}\n"
                    if slide_reserved:
                        markdown_content += f"- **Reserved Hook**: {slide_reserved}\n"
                    markdown_content += "\n---\n\n"
        
        # 添加最终评估结果
        markdown_content += f"\n## 最终评估结果\n\n"
        if evaluation_result.get("passed"):
            markdown_content += f"**评估状态**: ✓ 通过\n\n"
            markdown_content += f"**评估说明**: {evaluation_result.get('evaluation_result', 'N/A')}\n\n"
        else:
            markdown_content += f"**评估状态**: ✗ 不通过（已达到最大迭代次数）\n\n"
            failed_index = evaluation_result.get("failed_paragraph_index", -1)
            failed_title = evaluation_result.get("failed_paragraph_title", "未知")
            markdown_content += f"**失败段落**: {failed_index + 1}. {failed_title}\n\n"
            markdown_content += f"**评估说明**: {evaluation_result.get('evaluation_result', 'N/A')}\n\n"
            if evaluation_result.get("suggestions"):
                markdown_content += f"**修改建议**: {evaluation_result.get('suggestions')}\n\n"
        
        # 确定输出文件路径
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_idea = "".join(c for c in business_idea[:30] if c.isalnum() or c in (' ', '-', '_')).rstrip()
            safe_idea = safe_idea.replace(' ', '_')
            output_file = os.path.join(config.output_dir, f"bp_structure_{safe_idea}_{timestamp}.md")
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        # 保存到文件
        print(f"正在保存到文件: {output_file}")
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        print("\n" + "=" * 60)
        print("测试完成！")
        print("=" * 60)
        print(f"输出文件: {output_file}")
        print(f"文件大小: {len(markdown_content)} 字符")
        
        # 显示Markdown预览
        print("\nMarkdown预览（前500字符）:")
        print("-" * 60)
        print(markdown_content[:500] + "..." if len(markdown_content) > 500 else markdown_content)
        
        return output_file, bp_structure
        
    except Exception as e:
        print(f"\n测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        print("\n请检查：")
        print("1. 是否安装了所有依赖：pip install -r requirements.txt")
        print("2. 是否设置了必要的API密钥")
        print("3. 网络连接是否正常")
        print("4. 配置文件是否正确")
        raise


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="BP Structure Node 测试程序")
    parser.add_argument(
        "--idea",
        type=str,
        default="一个基于AI的在线教育平台，主要面向K12学生，提供个性化学习路径推荐",
        help="商业创意（如果不提供则使用默认值）"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="输出文件路径（如果不提供则自动生成）"
    )
    
    args = parser.parse_args()
    
    test_bp_structure(args.idea, args.output)


if __name__ == "__main__":
    main()

