from typing import Dict, Any, Optional
from langchain_core.language_models.chat_models import BaseChatModel
from ...nodes.bp_structure_node import BPStructureNode
from ..state import AgentState
from ..chat_history import ChatHistoryManager

class StructureNode:
    def __init__(self, llm: BaseChatModel, chat_history_manager: Optional[ChatHistoryManager] = None):
        self.llm = llm
        self.chat_history_manager = chat_history_manager

    def generate(self, state: AgentState) -> Dict[str, Any]:
        """Generate the initial BP structure."""
        business_idea = state["business_idea"]
        
        # Get complete business idea from chat history (all previous user inputs)
        complete_business_idea = business_idea
        if self.chat_history_manager:
            conversation_history = self.chat_history_manager.get_conversation_history()
            if conversation_history:
                # Combine all previous inputs with current input
                # Format: previous inputs (separated by \n\n) + current input
                complete_business_idea = f"{conversation_history}\n\n{business_idea}"
                print(f"[StructureNode] Using complete business idea from chat history (length: {len(complete_business_idea)} chars)")
            else:
                print(f"[StructureNode] No chat history found, using current business_idea only")
        
        # Initialize logic node with complete business idea
        node_logic = BPStructureNode(self.llm, complete_business_idea)
        
        node_result = node_logic.run()
        
        # Extract bp_structure and markdown_summary from node result
        structure = node_result.get("bp_structure", [])
        markdown_summary = node_result.get("markdown_summary")
        
        result = {
            "bp_structure": structure
        }
        if markdown_summary:
            result["markdown_summary"] = markdown_summary
        
        # Persist node output to chat history
        if self.chat_history_manager:
            self.chat_history_manager.persist_node_output("structure_gen", result)
        
        return result
    
    def regenerate(self, state: AgentState) -> Dict[str, Any]:
        """Regenerate BP structure based on feedback."""
        business_idea = state["business_idea"]
        
        # Get complete business idea from chat history (all previous user inputs)
        complete_business_idea = business_idea
        if self.chat_history_manager:
            conversation_history = self.chat_history_manager.get_conversation_history()
            if conversation_history:
                # Combine all previous inputs with current input
                complete_business_idea = f"{conversation_history}\n\n{business_idea}"
                print(f"[StructureNode] Using complete business idea from chat history for regeneration (length: {len(complete_business_idea)} chars)")
        
        node_logic = BPStructureNode(self.llm, complete_business_idea)
        
        evaluation_result = state["evaluation_result"]
        current_structure = state["bp_structure"]
        
        if not evaluation_result:
            # Should not happen in normal flow, but safe fallback
            return {}
            
        node_result = node_logic.regenerate(
            evaluation_result=evaluation_result.get("evaluation_result", ""),
            suggestions=evaluation_result.get("suggestions", ""),
            current_structure=current_structure
        )
        
        # Extract bp_structure and markdown_summary from node result
        structure = node_result.get("bp_structure", [])
        markdown_summary = node_result.get("markdown_summary")
        
        result = {
            "bp_structure": structure
        }
        if markdown_summary:
            result["markdown_summary"] = markdown_summary
        
        # Persist node output to chat history
        if self.chat_history_manager:
            self.chat_history_manager.persist_node_output("structure_regenerate", result)
        
        return result

