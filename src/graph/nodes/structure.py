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
        # Initialize logic node with business idea
        node_logic = BPStructureNode(self.llm, business_idea)
        
        structure = node_logic.run()
        
        result = {
            "bp_structure": structure
        }
        
        # Persist node output to chat history
        if self.chat_history_manager:
            self.chat_history_manager.persist_node_output("structure_gen", result)
        
        return result
    
    def regenerate(self, state: AgentState) -> Dict[str, Any]:
        """Regenerate BP structure based on feedback."""
        business_idea = state["business_idea"]
        node_logic = BPStructureNode(self.llm, business_idea)
        
        evaluation_result = state["evaluation_result"]
        current_structure = state["bp_structure"]
        
        if not evaluation_result:
            # Should not happen in normal flow, but safe fallback
            return {}
            
        structure = node_logic.regenerate(
            evaluation_result=evaluation_result.get("evaluation_result", ""),
            suggestions=evaluation_result.get("suggestions", ""),
            current_structure=current_structure
        )
        
        result = {
            "bp_structure": structure
        }
        
        # Persist node output to chat history
        if self.chat_history_manager:
            self.chat_history_manager.persist_node_output("structure_regenerate", result)
        
        return result

