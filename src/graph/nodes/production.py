from typing import Dict, Any, Optional
from langchain_core.language_models.chat_models import BaseChatModel
from ...nodes.pitch_60s_node import Pitch60sNode
from ...nodes.ppt_generation_node import PPTGenerationNode
from ...nodes.partner_search_node import PartnerSearchNode
from ..state import AgentState
from ..chat_history import ChatHistoryManager

class ProductionNodes:
    def __init__(self, llm: BaseChatModel, aihehuo_api_key: Optional[str] = None, aihehuo_api_base: Optional[str] = None, chat_history_manager: Optional[ChatHistoryManager] = None):
        self.pitch_logic = Pitch60sNode(llm)
        self.ppt_logic = PPTGenerationNode(llm)
        self.partner_logic = None
        self.chat_history_manager = chat_history_manager
        if aihehuo_api_key:
            try:
                self.partner_logic = PartnerSearchNode(llm, api_key=aihehuo_api_key, api_base=aihehuo_api_base)
            except Exception:
                pass

    def generate_pitch(self, state: AgentState) -> Dict[str, Any]:
        business_idea = state["business_idea"]
        bp_structure = state["bp_structure"]
        
        pitch_result = self.pitch_logic.generate_pitch(business_idea, bp_structure)
        
        history_item = {
            "iteration": "60s_pitch",
            "pitch_result": pitch_result
        }
        
        output = {
            "pitch_result": pitch_result,
            "iteration_history": [history_item]
        }
        
        # Persist node output to chat history
        if self.chat_history_manager:
            self.chat_history_manager.persist_node_output("pitch_gen", output)
        
        return output

    def generate_ppt(self, state: AgentState) -> Dict[str, Any]:
        business_idea = state["business_idea"]
        bp_structure = state["bp_structure"]
        
        ppt_result = self.ppt_logic.generate_ppt(business_idea, bp_structure)
        
        history_item = {
            "iteration": "ppt_generation",
            "ppt_result": ppt_result
        }
        
        output = {
            "ppt_result": ppt_result,
            "iteration_history": [history_item]
        }
        
        # Persist node output to chat history
        if self.chat_history_manager:
            self.chat_history_manager.persist_node_output("ppt_gen", output)
        
        return output

    def search_partners(self, state: AgentState) -> Dict[str, Any]:
        if not self.partner_logic:
            return {}
            
        business_idea = state["business_idea"]
        bp_structure = state["bp_structure"]
        
        try:
            partner_result = self.partner_logic.run(
                input_data={
                    "business_idea": business_idea,
                    "bp_structure": bp_structure
                },
                partner_per_page=10,
                investor_per_page=10,
                wechat_reachable_only=True
            )
            
            history_item = {
                "iteration": "partner_search",
                "partner_search_result": partner_result
            }
            
            output = {
                "partner_search_result": partner_result,
                "iteration_history": [history_item]
            }
            
            # Persist node output to chat history
            if self.chat_history_manager:
                self.chat_history_manager.persist_node_output("partner_search", output)
            
            return output
        except Exception:
            return {}

