from typing import Dict, Any, List, Optional
from langchain_core.language_models.chat_models import BaseChatModel
from ...nodes.bp_evaluation_node import BPEvaluationNode
from ...nodes.painpoint_enhancement_node import PainpointEnhancementNode
from ...nodes.investor_evaluation_node import InvestorEvaluationNode
from ...nodes.bp_structure_node import BPStructureNode
from ..state import AgentState
from ..chat_history import ChatHistoryManager

class EvaluationNode:
    def __init__(self, llm: BaseChatModel, chat_history_manager: Optional[ChatHistoryManager] = None):
        self.eval_logic = BPEvaluationNode(llm)
        self.chat_history_manager = chat_history_manager

    def __call__(self, state: AgentState) -> Dict[str, Any]:
        business_idea = state["business_idea"]
        bp_structure = state["bp_structure"]
        
        result = self.eval_logic.evaluate_paragraphs(business_idea, bp_structure)
        
        # Extract markdown_summary from result if available
        markdown_summary = result.get("markdown_summary")
        # Remove markdown_summary from result to keep evaluation_result clean
        evaluation_result_clean = {k: v for k, v in result.items() if k != "markdown_summary"}
        
        # Update iteration history
        history_item = {
            "iteration": state["iteration_count"] + 1,
            "structure": bp_structure, # Note: simple reference, might need deepcopy if mutated
            "evaluation": evaluation_result_clean
        }
        
        output = {
            "evaluation_result": evaluation_result_clean,
            "iteration_count": state["iteration_count"] + 1,
            "iteration_history": [history_item]
        }
        
        # Include markdown_summary if available
        if markdown_summary:
            output["markdown_summary"] = markdown_summary
        
        # Persist node output to chat history
        if self.chat_history_manager:
            self.chat_history_manager.persist_node_output("structure_eval", output)
        
        return output

class PainpointNode:
    def __init__(self, llm: BaseChatModel, chat_history_manager: Optional[ChatHistoryManager] = None):
        self.logic = PainpointEnhancementNode(llm)
        self.chat_history_manager = chat_history_manager

    def __call__(self, state: AgentState) -> Dict[str, Any]:
        business_idea = state["business_idea"]
        bp_structure = state["bp_structure"] # This is a list of dicts
        
        # Find painpoint paragraph
        painpoint_idx = -1
        painpoint_para = None
        
        for idx, para in enumerate(bp_structure):
            title = para.get("title", "").strip()
            if ("用户画像" in title and "痛点" in title) or \
               ("User Persona" in title and "Pain Point" in title):
                painpoint_idx = idx
                painpoint_para = para
                break
        
        if not painpoint_para:
            return {} # No enhancement possible
            
        # Enhance
        result = self.logic.enhance(business_idea, painpoint_para)
        
        # Update structure
        enhanced_content = result.get("enhanced_content", "")
        if enhanced_content:
            # Create a new structure list to avoid mutating state in place implicitly
            new_structure = [p.copy() for p in bp_structure]
            new_structure[painpoint_idx]["content"] = enhanced_content
            
            history_item = {
                "iteration": "painpoint_enhancement",
                "paragraph_index": painpoint_idx,
                "paragraph_title": painpoint_para.get("title"),
                "content_before": painpoint_para.get("content"),
                "content_after": enhanced_content,
                "selected_dimensions": result.get("selected_dimensions"),
                "dimension_descriptions": result.get("dimension_descriptions"),
                "enhancement_explanation": result.get("enhancement_explanation")
            }
            
            output = {
                "bp_structure": new_structure,
                "iteration_history": [history_item]
            }
            
            # Persist node output to chat history
            if self.chat_history_manager:
                self.chat_history_manager.persist_node_output("painpoint_enhancement", output)
            
            return output
            
        return {}

class InvestorEvaluationWrapperNode:
    def __init__(self, llm: BaseChatModel, chat_history_manager: Optional[ChatHistoryManager] = None):
        self.eval_logic = InvestorEvaluationNode(llm)
        self.structure_logic_cls = BPStructureNode # We need to instantiate with idea
        self.llm = llm
        self.chat_history_manager = chat_history_manager

    def __call__(self, state: AgentState) -> Dict[str, Any]:
        business_idea = state["business_idea"]
        bp_structure = state["bp_structure"]
        
        # Store copy for history
        structure_before = [p.copy() for p in bp_structure]
        
        # Evaluate full BP
        investor_eval = self.eval_logic.evaluate_full_bp(business_idea, bp_structure)
        
        # Apply feedback (Refinement)
        paragraph_feedbacks = investor_eval.get("paragraph_specific_feedback", [])
        final_structure = []
        
        # Logic node for regeneration
        structure_node = self.structure_logic_cls(self.llm, business_idea)
        
        for idx, para in enumerate(bp_structure):
            para_title = para.get("title", f"Paragraph {idx + 1}")
            
            # Find feedback for this paragraph
            para_feedback = next(
                (fb for fb in paragraph_feedbacks if fb.get("paragraph_index") == idx),
                None
            )
            
            if para_feedback:
                feedback_text = para_feedback.get("feedback", "")
                suggestions_text = para_feedback.get("suggestions", "")
                
                try:
                    regenerated = structure_node.regenerate(
                        evaluation_result=(
                            f"Feedback for paragraph {idx + 1} ({para_title}): "
                            f"{feedback_text}. Note: MUST keep title '{para_title}' unchanged."
                        ),
                        suggestions=(
                            f"Suggestions for '{para_title}': "
                            f"{suggestions_text}. IMPORTANT: Keep title unchanged."
                        ),
                        current_structure=[para]
                    )
                    
                    if regenerated:
                        regenerated_item = regenerated[0]
                        # Ensure title consistency
                        if regenerated_item.get("title") != para_title:
                            regenerated_item["title"] = para_title
                        final_structure.append(regenerated_item)
                    else:
                        final_structure.append(para)
                        
                except Exception:
                    # Fallback to original
                    final_structure.append(para)
            else:
                final_structure.append(para)
        
        history_item = {
            "iteration": "investor_evaluation",
            "structure_before": structure_before,
            "structure_after": final_structure, # This matches the state update
            "investor_evaluation": investor_eval
        }
        
        output = {
            "bp_structure": final_structure,
            "iteration_history": [history_item]
        }
        
        # Persist node output to chat history
        if self.chat_history_manager:
            self.chat_history_manager.persist_node_output("investor_eval", output)
        
        return output

