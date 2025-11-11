"""
BP Structure Node Test Program (English Version)
Tests BP structure generation and outputs results to markdown document
"""

import os
import sys
from datetime import datetime

# Add project root directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.nodes.bp_structure_node import BPStructureNode
from src.nodes.bp_evaluation_node import BPEvaluationNode
from src.nodes.painpoint_enhancement_node import PainpointEnhancementNode
from src.nodes.investor_evaluation_node import InvestorEvaluationNode
from src.nodes.pitch_60s_node import Pitch60sNode
from src.llms import DeepSeekLLM, OpenAILLM, QwenLLM
from src.utils.config import load_config


def format_bp_structure_to_markdown(bp_structure, business_idea):
    """
    Format BP structure to Markdown document
    
    Args:
        bp_structure: BP structure list, each element contains title and content
        business_idea: Business idea
        
    Returns:
        Markdown formatted string
    """
    markdown = f"""# Business Plan Structure

## Business Idea

{business_idea.strip()}

---

## Plan Structure

"""
    
    for i, section in enumerate(bp_structure, 1):
        title = section.get("title", f"Section {i}")
        content = section.get("content", "")
        
        markdown += f"### {i}. {title}\n\n"
        markdown += f"{content}\n\n"
        markdown += "---\n\n"
    
    # Add generation info
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    markdown += f"\n\n---\n\n*Generated at: {timestamp}*\n"
    
    return markdown


def test_bp_structure(business_idea, output_file=None):
    """
    Test BP structure generation
    
    Args:
        business_idea: Business idea
        output_file: Output file path, if None then auto-generate
    """
    print("=" * 60)
    print("BP Structure Node Test")
    print("=" * 60)
    
    try:
        # Load configuration
        print("\nLoading configuration...")
        config = load_config()
        
        # Initialize LLM client
        print(f"Initializing LLM client ({config.default_llm_provider})...")
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
            raise ValueError(f"Unsupported LLM provider: {config.default_llm_provider}")
        
        print(f"LLM Model: {llm_client.get_model_info()}")
        
        # Create BP structure node and evaluation nodes
        print("\nCreating BP structure node and evaluation nodes...")
        bp_structure_node = BPStructureNode(llm_client, business_idea)
        evaluation_node = BPEvaluationNode(llm_client)
        painpoint_enhancement_node = PainpointEnhancementNode(llm_client)
        investor_eval_node = InvestorEvaluationNode(llm_client)
        pitch_60s_node = Pitch60sNode(llm_client)
        
        # Loop generation and evaluation, max 3 times
        max_iterations = 3
        bp_structure = None
        evaluation_result = None
        iteration_history = []
        
        for iteration in range(max_iterations):
            iteration_num = iteration + 1
            print(f"\n{'='*60}")
            print(f"Iteration {iteration_num}/{max_iterations}")
            print(f"{'='*60}")
            
            try:
                # Generate or regenerate BP structure
                if iteration == 0:
                    print("Generating BP structure...")
                    bp_structure = bp_structure_node.run()
                else:
                    print("Regenerating BP structure based on feedback...")
                    bp_structure = bp_structure_node.regenerate(
                        evaluation_result=evaluation_result.get("evaluation_result", ""),
                        suggestions=evaluation_result.get("suggestions", ""),
                        current_structure=bp_structure
                    )
            except ValueError as e:
                # JSON parsing failed, interrupt program
                print(f"\n{'='*60}")
                print("Error: JSON parsing failed, program interrupted")
                print(f"{'='*60}")
                print(f"Error message: {str(e)}")
                print(f"\nIteration {iteration_num} failed, cannot continue")
                raise e
            except Exception as e:
                # Other exceptions, also interrupt program
                print(f"\n{'='*60}")
                print("Error: Exception occurred while generating BP structure, program interrupted")
                print(f"{'='*60}")
                print(f"Error message: {str(e)}")
                print(f"\nIteration {iteration_num} failed, cannot continue")
                raise e
            
            print(f"\nSuccessfully generated {len(bp_structure)} sections:")
            for i, section in enumerate(bp_structure, 1):
                print(f"  {i}. {section.get('title', 'N/A')}")
            
            # Evaluate BP structure
            print("\nEvaluating BP structure...")
            evaluation_result = evaluation_node.evaluate_paragraphs(business_idea, bp_structure)
            
            # Record iteration history
            iteration_history.append({
                "iteration": iteration_num,
                "structure": bp_structure.copy(),
                "evaluation": evaluation_result.copy()
            })
            
            if evaluation_result.get("passed"):
                print("✓ BP structure evaluation passed")
                print(f"  Evaluation result: {evaluation_result.get('evaluation_result', 'N/A')}")
                
                # After BP evaluation passes, perform painpoint enhancement
                print(f"\n{'='*60}")
                print("BP evaluation passed, starting painpoint enhancement")
                print(f"{'='*60}")
                
                try:
                    # Find "User Persona & Pain Points" paragraph
                    painpoint_para_index = None
                    painpoint_para = None
                    
                    for i, para in enumerate(bp_structure):
                        title = para.get('title', '').strip()
                        # Match possible title variants (both Chinese and English)
                        if ('用户画像' in title and '痛点' in title) or \
                           ('User Persona' in title and 'Pain Point' in title) or \
                           ('User Persona' in title and 'Pain Points' in title):
                            painpoint_para_index = i
                            painpoint_para = para
                            break
                    
                    if painpoint_para:
                        print(f"Found painpoint paragraph: {painpoint_para.get('title', 'N/A')}")
                        print("Enhancing painpoint statement based on six dimensions...")
                        
                        # Enhance painpoint paragraph
                        enhancement_result = painpoint_enhancement_node.enhance(
                            business_idea, 
                            painpoint_para
                        )
                        
                        # Get enhanced content
                        enhanced_content = enhancement_result.get('enhanced_content', '')
                        selected_dimensions = enhancement_result.get('selected_dimensions', [])
                        dimension_descriptions = enhancement_result.get('dimension_descriptions', [])
                        enhancement_explanation = enhancement_result.get('enhancement_explanation', '')
                        
                        print(f"✓ Painpoint enhancement completed")
                        print(f"  Selected dimensions: {', '.join(selected_dimensions) if selected_dimensions else 'None'}")
                        print(f"  Number of dimensions: {len(selected_dimensions)}")
                        
                        # Update painpoint paragraph in BP structure
                        bp_structure[painpoint_para_index] = {
                            "title": painpoint_para.get('title', 'User Persona & Pain Points'),
                            "content": enhanced_content
                        }
                        
                        # Record painpoint enhancement result
                        iteration_history.append({
                            "iteration": "painpoint_enhancement",
                            "paragraph_index": painpoint_para_index,
                            "paragraph_title": painpoint_para.get('title', 'User Persona & Pain Points'),
                            "content_before": painpoint_para.get('content', ''),
                            "content_after": enhanced_content,
                            "selected_dimensions": selected_dimensions,
                            "dimension_descriptions": dimension_descriptions,
                            "enhancement_explanation": enhancement_explanation
                        })
                    else:
                        print("Could not find 'User Persona & Pain Points' paragraph, skipping painpoint enhancement")
                        
                except Exception as e:
                    print(f"Painpoint enhancement failed: {str(e)}")
                    print("Will continue using original painpoint paragraph")
                    import traceback
                    traceback.print_exc()
                
                # After painpoint enhancement, perform investor evaluation
                print(f"\n{'='*60}")
                print("Painpoint enhancement completed, starting investor evaluation")
                print(f"{'='*60}")
                
                try:
                    # Save structure before evaluation
                    bp_structure_before = [para.copy() for para in bp_structure]
                    
                    # Evaluate entire BP
                    print("Evaluating entire BP from investor perspective...")
                    investor_evaluation = investor_eval_node.evaluate_full_bp(business_idea, bp_structure)
                    
                    print(f"\nInvestor overall assessment:")
                    print(f"  Overall assessment: {investor_evaluation.get('overall_assessment', 'N/A')[:200]}...")
                    if investor_evaluation.get('concerns'):
                        print(f"  Concerns: {investor_evaluation.get('concerns')[:200]}...")
                    
                    # Get feedback for each paragraph
                    paragraph_feedbacks = investor_evaluation.get('paragraph_specific_feedback', [])
                    print(f"\nInvestor evaluation completed, {len(paragraph_feedbacks)} paragraph feedbacks received")
                    
                    # Regenerate each paragraph based on feedback
                    print("Regenerating each paragraph based on investor feedback...")
                    final_bp_structure = []
                    
                    for i, para in enumerate(bp_structure):
                        para_title = para.get('title', f'Section {i+1}')
                        print(f"  Processing section {i+1}: {para_title}")
                        
                        # Find feedback for this paragraph
                        para_feedback = None
                        for fb in paragraph_feedbacks:
                            if fb.get('paragraph_index') == i:
                                para_feedback = fb
                                break
                        
                        if para_feedback:
                            # Regenerate paragraph based on feedback
                            feedback_text = para_feedback.get('feedback', '')
                            suggestions_text = para_feedback.get('suggestions', '')
                            
                            try:
                                # Regenerate single paragraph, explicitly require keeping title
                                regenerated_para = bp_structure_node.regenerate(
                                    evaluation_result=f"Section {i+1} ({para_title}) evaluation feedback: {feedback_text}. Note: Must keep title '{para_title}' unchanged, only modify content.",
                                    suggestions=f"Improvement suggestions for section '{para_title}': {suggestions_text}. Important: Must keep title unchanged.",
                                    current_structure=[para]
                                )
                                if regenerated_para and len(regenerated_para) > 0:
                                    regenerated_item = regenerated_para[0]
                                    # Ensure title remains unchanged
                                    if regenerated_item.get('title') != para_title:
                                        print(f"    Warning: Regenerated paragraph title mismatch, corrected to original title")
                                        regenerated_item['title'] = para_title
                                    final_bp_structure.append(regenerated_item)
                                else:
                                    final_bp_structure.append(para)
                            except Exception as e:
                                print(f"    Warning: Failed to regenerate section {i+1}, using original: {str(e)}")
                                final_bp_structure.append(para)
                        else:
                            # No feedback, keep original paragraph
                            final_bp_structure.append(para)
                    
                    print(f"✓ Final BP structure generation completed, {len(final_bp_structure)} sections")
                    bp_structure = final_bp_structure
                    
                    # Record investor evaluation result (including structure before and after)
                    iteration_history.append({
                        "iteration": "investor_evaluation",
                        "structure_before": bp_structure_before,
                        "structure_after": bp_structure.copy(),
                        "investor_evaluation": investor_evaluation
                    })
                    
                    # After investor evaluation, generate 60-second pitch
                    print(f"\n{'='*60}")
                    print("Investor evaluation completed, starting 60-second pitch generation")
                    print(f"{'='*60}")
                    
                    try:
                        print("Generating 60-second pitch based on BP structure...")
                        pitch_result = pitch_60s_node.generate_pitch(business_idea, bp_structure)
                        
                        print(f"✓ 60-second pitch generation successful")
                        painpoint_dims = pitch_result.get('painpoint_resonance', {}).get('selected_dimensions', [])
                        team_advs = pitch_result.get('team_advantages', {}).get('selected_advantages', [])
                        if painpoint_dims:
                            print(f"  Painpoint dimensions: {', '.join(painpoint_dims)}")
                        if team_advs:
                            print(f"  Team advantages: {', '.join(team_advs)}")
                        
                        # Record pitch result
                        iteration_history.append({
                            "iteration": "60s_pitch",
                            "pitch_result": pitch_result
                        })
                        
                    except Exception as e:
                        print(f"60-second pitch generation failed: {str(e)}")
                        import traceback
                        traceback.print_exc()
                        # Even if pitch generation fails, continue using BP structure
                    
                except Exception as e:
                    print(f"Investor evaluation or regeneration failed: {str(e)}")
                    print("Will use BP evaluation passed structure as final structure")
                    import traceback
                    traceback.print_exc()
                
                break
            else:
                print("✗ BP structure evaluation failed")
                failed_index = evaluation_result.get("failed_paragraph_index", -1)
                failed_title = evaluation_result.get("failed_paragraph_title", "Unknown")
                print(f"  Failed section index: {failed_index}")
                print(f"  Failed section title: {failed_title}")
                print(f"  Evaluation result: {evaluation_result.get('evaluation_result', 'N/A')}")
                if evaluation_result.get("suggestions"):
                    print(f"  Suggestions: {evaluation_result.get('suggestions')}")
                
                if iteration_num < max_iterations:
                    print(f"\nWill proceed to iteration {iteration_num + 1}...")
                else:
                    print(f"\nReached maximum iterations ({max_iterations}), stopping loop")
        
        # Final result
        print(f"\n{'='*60}")
        print("Final Result")
        print(f"{'='*60}")
        if evaluation_result.get("passed"):
            print("✓ BP structure final evaluation passed")
        else:
            print("✗ BP structure final evaluation failed (reached maximum iterations)")
        
        # Format to Markdown
        print("\nFormatting Markdown...")
        markdown_content = format_bp_structure_to_markdown(bp_structure, business_idea)
        
        # Add iteration history and evaluation results to Markdown
        markdown_content += f"\n\n## Iteration History\n\n"
        markdown_content += f"**Total Iterations**: {len([h for h in iteration_history if isinstance(h.get('iteration'), int)])}\n\n"
        for hist in iteration_history:
            iteration_key = hist.get('iteration')
            
            if isinstance(iteration_key, int):
                # BP evaluation iteration
                markdown_content += f"### Iteration {iteration_key}\n\n"
                eval_result = hist.get('evaluation', {})
                if eval_result.get("passed"):
                    markdown_content += f"- **Status**: ✓ Passed\n"
                else:
                    markdown_content += f"- **Status**: ✗ Failed\n"
                    failed_index = eval_result.get("failed_paragraph_index", -1)
                    failed_title = eval_result.get("failed_paragraph_title", "Unknown")
                    markdown_content += f"- **Failed Section**: {failed_index + 1}. {failed_title}\n"
                markdown_content += f"- **Evaluation Note**: {eval_result.get('evaluation_result', 'N/A')}\n"
                if eval_result.get("suggestions"):
                    markdown_content += f"- **Suggestions**: {eval_result.get('suggestions')}\n"
                markdown_content += "\n"
            elif iteration_key == "painpoint_enhancement":
                # Painpoint enhancement
                markdown_content += f"### Painpoint Enhancement\n\n"
                para_index = hist.get('paragraph_index', -1)
                para_title = hist.get('paragraph_title', 'User Persona & Pain Points')
                content_before = hist.get('content_before', '')
                content_after = hist.get('content_after', '')
                selected_dimensions = hist.get('selected_dimensions', [])
                dimension_descriptions = hist.get('dimension_descriptions', [])
                enhancement_explanation = hist.get('enhancement_explanation', '')
                
                markdown_content += f"**Section**: {para_index + 1}. {para_title}\n\n"
                
                if selected_dimensions:
                    markdown_content += f"**Selected Dimensions**: {', '.join(selected_dimensions)} ({len(selected_dimensions)} total)\n\n"
                
                if enhancement_explanation:
                    markdown_content += f"**Enhancement Explanation**: {enhancement_explanation}\n\n"
                
                # Display descriptions by dimension
                if dimension_descriptions:
                    markdown_content += f"#### Painpoint Descriptions by Dimension\n\n"
                    for i, dim_desc in enumerate(dimension_descriptions, 1):
                        dim_name = dim_desc.get('dimension', f'Dimension {i}')
                        dim_content = dim_desc.get('content', '')
                        markdown_content += f"**{i}. {dim_name}**\n\n{dim_content}\n\n"
                
                markdown_content += f"**Before Enhancement**:\n\n{content_before}\n\n"
                markdown_content += f"**After Enhancement (Full Content)**:\n\n{content_after}\n\n"
                markdown_content += "---\n\n"
            elif iteration_key == "investor_evaluation":
                # Investor evaluation
                markdown_content += f"### Investor Evaluation\n\n"
                investor_eval = hist.get('investor_evaluation', {})
                structure_before = hist.get('structure_before', [])
                structure_after = hist.get('structure_after', [])
                
                # Overall assessment
                markdown_content += f"#### Overall Assessment\n\n"
                if investor_eval.get("market_size"):
                    markdown_content += f"- **Market Size**: {investor_eval.get('market_size')}\n"
                if investor_eval.get("replicability"):
                    markdown_content += f"- **Replicability**: {investor_eval.get('replicability')}\n"
                if investor_eval.get("competitive_barriers"):
                    markdown_content += f"- **Competitive Barriers**: {investor_eval.get('competitive_barriers')}\n"
                if investor_eval.get("unique_competitive_advantage"):
                    markdown_content += f"- **Unique Competitive Advantage**: {investor_eval.get('unique_competitive_advantage')}\n"
                if investor_eval.get("revenue_model"):
                    markdown_content += f"- **Revenue Model**: {investor_eval.get('revenue_model')}\n"
                if investor_eval.get("overall_assessment"):
                    markdown_content += f"- **Overall Assessment**: {investor_eval.get('overall_assessment')}\n"
                if investor_eval.get("concerns"):
                    markdown_content += f"- **Concerns**: {investor_eval.get('concerns')}\n"
                if investor_eval.get("suggestions"):
                    markdown_content += f"- **Overall Improvement Suggestions**: {investor_eval.get('suggestions')}\n"
                markdown_content += "\n"
                
                # Paragraph feedback and before/after comparison
                paragraph_feedbacks = investor_eval.get('paragraph_specific_feedback', [])
                markdown_content += f"#### Section Feedback and Improvements\n\n"
                markdown_content += f"**Evaluated Sections**: {len(paragraph_feedbacks)}\n\n"
                
                for i, para_fb in enumerate(paragraph_feedbacks):
                    para_index = para_fb.get("paragraph_index", i)
                    para_title = para_fb.get("paragraph_title", f"Section {para_index + 1}")
                    
                    markdown_content += f"##### Section {para_index + 1}: {para_title}\n\n"
                    
                    # Feedback
                    if para_fb.get("feedback"):
                        markdown_content += f"**Investor Feedback**: {para_fb.get('feedback')}\n\n"
                    if para_fb.get("suggestions"):
                        markdown_content += f"**Improvement Suggestions**: {para_fb.get('suggestions')}\n\n"
                    
                    # Show before/after comparison
                    if para_index < len(structure_before) and para_index < len(structure_after):
                        para_before = structure_before[para_index]
                        para_after = structure_after[para_index]
                        
                        content_before = para_before.get('content', '')
                        content_after = para_after.get('content', '')
                        
                        if content_before != content_after:
                            markdown_content += f"**Before Modification**:\n\n{content_before}\n\n"
                            markdown_content += f"**After Modification**:\n\n{content_after}\n\n"
                        else:
                            markdown_content += f"*（This section was not modified）*\n\n"
                    
                    markdown_content += "---\n\n"
            elif iteration_key == "60s_pitch":
                # 60-second pitch
                markdown_content += f"### 60-Second Pitch\n\n"
                pitch_result = hist.get('pitch_result', {})
                
                # Painpoint resonance section
                painpoint_resonance = pitch_result.get('painpoint_resonance', {})
                if painpoint_resonance:
                    markdown_content += f"#### ① Painpoint Resonance\n\n"
                    selected_dims = painpoint_resonance.get('selected_dimensions', [])
                    if selected_dims:
                        markdown_content += f"**Selected Dimensions**: {', '.join(selected_dims)}\n\n"
                    painpoint_content = painpoint_resonance.get('content', '')
                    if painpoint_content:
                        markdown_content += f"{painpoint_content}\n\n"
                    markdown_content += "---\n\n"
                
                # Team advantages section
                team_advantages = pitch_result.get('team_advantages', {})
                if team_advantages:
                    markdown_content += f"#### ② Team Advantages\n\n"
                    selected_advs = team_advantages.get('selected_advantages', [])
                    if selected_advs:
                        markdown_content += f"**Selected Advantages**: {', '.join(selected_advs)}\n\n"
                    team_content = team_advantages.get('content', '')
                    if team_content:
                        markdown_content += f"{team_content}\n\n"
                    markdown_content += "---\n\n"
                
                # Call to action section
                call_to_action = pitch_result.get('call_to_action', {})
                if call_to_action:
                    markdown_content += f"#### ③ Call to Action\n\n"
                    target_audience = call_to_action.get('target_audience', '')
                    action = call_to_action.get('action', '')
                    if target_audience:
                        markdown_content += f"**Target Audience**: {target_audience}\n\n"
                    if action:
                        markdown_content += f"**Action**: {action}\n\n"
                    cta_content = call_to_action.get('content', '')
                    if cta_content:
                        markdown_content += f"{cta_content}\n\n"
                    markdown_content += "---\n\n"
                
                # Full pitch text
                full_pitch = pitch_result.get('full_pitch', '')
                if full_pitch:
                    markdown_content += f"#### Full 60-Second Pitch Text\n\n"
                    markdown_content += f"> {full_pitch}\n\n"
                    markdown_content += "---\n\n"
        
        # Add final evaluation result
        markdown_content += f"\n## Final Evaluation Result\n\n"
        if evaluation_result.get("passed"):
            markdown_content += f"**Evaluation Status**: ✓ Passed\n\n"
            markdown_content += f"**Evaluation Note**: {evaluation_result.get('evaluation_result', 'N/A')}\n\n"
        else:
            markdown_content += f"**Evaluation Status**: ✗ Failed (reached maximum iterations)\n\n"
            failed_index = evaluation_result.get("failed_paragraph_index", -1)
            failed_title = evaluation_result.get("failed_paragraph_title", "Unknown")
            markdown_content += f"**Failed Section**: {failed_index + 1}. {failed_title}\n\n"
            markdown_content += f"**Evaluation Note**: {evaluation_result.get('evaluation_result', 'N/A')}\n\n"
            if evaluation_result.get("suggestions"):
                markdown_content += f"**Suggestions**: {evaluation_result.get('suggestions')}\n\n"
        
        # Determine output file path
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_idea = "".join(c for c in business_idea[:30] if c.isalnum() or c in (' ', '-', '_')).rstrip()
            safe_idea = safe_idea.replace(' ', '_')
            output_file = os.path.join(config.output_dir, f"bp_structure_en_{safe_idea}_{timestamp}.md")
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        # Save to file
        print(f"Saving to file: {output_file}")
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        print("\n" + "=" * 60)
        print("Test Completed!")
        print("=" * 60)
        print(f"Output file: {output_file}")
        print(f"File size: {len(markdown_content)} characters")
        
        # Display Markdown preview
        print("\nMarkdown preview (first 500 characters):")
        print("-" * 60)
        print(markdown_content[:500] + "..." if len(markdown_content) > 500 else markdown_content)
        
        return output_file, bp_structure
        
    except Exception as e:
        print(f"\nTest failed: {str(e)}")
        import traceback
        traceback.print_exc()
        print("\nPlease check:")
        print("1. Are all dependencies installed: pip install -r requirements.txt")
        print("2. Are necessary API keys set")
        print("3. Is network connection normal")
        print("4. Is configuration file correct")
        raise


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="BP Structure Node Test Program (English Version)")
    parser.add_argument(
        "--idea",
        type=str,
        default="An AI-powered online education platform targeting K12 students, providing personalized learning path recommendations",
        help="Business idea (if not provided, uses default value)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output file path (if not provided, auto-generates)"
    )
    
    args = parser.parse_args()
    
    test_bp_structure(args.idea, args.output)


if __name__ == "__main__":
    main()

