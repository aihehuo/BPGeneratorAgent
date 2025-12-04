from typing import Optional, Dict, Any, Literal

from langgraph.graph import StateGraph, END
from langchain_core.language_models.chat_models import BaseChatModel

from .state import AgentState
from .chat_history import ChatHistoryManager
from .nodes.input import InputNode
from .nodes.structure import StructureNode
from .nodes.evaluation import EvaluationNode, PainpointNode, InvestorEvaluationWrapperNode
from .nodes.production import ProductionNodes
from .nodes.html_generation import HTMLGenerationNode

def create_bp_graph(
    llm: BaseChatModel, 
    aihehuo_api_key: Optional[str] = None,
    aihehuo_api_base: Optional[str] = None,
    chat_history_manager: Optional[ChatHistoryManager] = None
):
    """
    Construct the BP Generation Graph.
    
    Args:
        llm: LangChain ChatModel for LLM operations
        aihehuo_api_key: API key for Aihehuo partner search
        aihehuo_api_base: Base URL for Aihehuo API
        chat_history_manager: Optional ChatHistoryManager for centralized chat history management
                             If None, nodes will manage their own history (legacy behavior)
    """
    
    # Initialize Node Logic wrappers with chat history manager
    input_node = InputNode(llm, chat_history_manager=chat_history_manager)
    structure_node = StructureNode(llm, chat_history_manager=chat_history_manager)
    eval_node = EvaluationNode(llm, chat_history_manager=chat_history_manager)
    painpoint_node = PainpointNode(llm, chat_history_manager=chat_history_manager)
    investor_node = InvestorEvaluationWrapperNode(llm, chat_history_manager=chat_history_manager)
    production_nodes = ProductionNodes(llm, aihehuo_api_key, aihehuo_api_base, chat_history_manager=chat_history_manager)
    html_node = HTMLGenerationNode(chat_history_manager=chat_history_manager)
    
    # Initialize Graph
    workflow = StateGraph(AgentState)
    
    # Add Nodes
    workflow.add_node("input_check", input_node)
    workflow.add_node("structure_gen", structure_node.generate)
    workflow.add_node("structure_regenerate", structure_node.regenerate)
    workflow.add_node("structure_eval", eval_node)
    workflow.add_node("painpoint_enhancement", painpoint_node)
    workflow.add_node("investor_eval", investor_node)
    
    workflow.add_node("pitch_gen", production_nodes.generate_pitch)
    workflow.add_node("ppt_gen", production_nodes.generate_ppt)
    workflow.add_node("partner_search", production_nodes.search_partners)
    workflow.add_node("html_gen", html_node)
    
    # Define Edges
    workflow.set_entry_point("input_check")
    
    # Conditional Edge for Input Check
    def check_input_completeness(state: AgentState) -> Literal["structure_gen", "end"]:
        result = state.get("input_completeness", {})
        if result.get("is_complete"):
            return "structure_gen"
        return "end"
        
    workflow.add_conditional_edges(
        "input_check",
        check_input_completeness,
        {
            "structure_gen": "structure_gen",
            "end": END
        }
    )
    
    workflow.add_edge("structure_gen", "structure_eval")
    workflow.add_edge("structure_regenerate", "structure_eval")
    
    # Conditional Edge for Structure Evaluation
    def check_structure_eval(state: AgentState) -> Literal["painpoint_enhancement", "structure_regenerate"]:
        eval_result = state.get("evaluation_result", {})
        iteration = state.get("iteration_count", 0)
        max_iterations = state.get("max_iterations", 3)
        
        if eval_result.get("passed"):
            return "painpoint_enhancement"
            
        if iteration < max_iterations:
            return "structure_regenerate"
            
        # If max iterations reached, proceed anyway (best effort)
        return "painpoint_enhancement"

    workflow.add_conditional_edges(
        "structure_eval",
        check_structure_eval,
        {
            "painpoint_enhancement": "painpoint_enhancement",
            "structure_regenerate": "structure_regenerate"
        }
    )
    
    workflow.add_edge("painpoint_enhancement", "investor_eval")
    
    # Parallel Production
    workflow.add_edge("investor_eval", "pitch_gen")
    workflow.add_edge("investor_eval", "ppt_gen")
    workflow.add_edge("investor_eval", "partner_search")
    
    # After all production nodes complete, generate HTML report
    # Use a conditional edge to wait for all three nodes to complete
    workflow.add_edge("pitch_gen", "html_gen")
    workflow.add_edge("ppt_gen", "html_gen")
    workflow.add_edge("partner_search", "html_gen")
    
    # HTML generation is the final step
    workflow.add_edge("html_gen", END)
    
    return workflow.compile()

