from typing import Optional, Dict, Any, Literal, Union
import uuid

from langgraph.graph import StateGraph, END
from langchain_core.language_models.chat_models import BaseChatModel

from .state import AgentState
from .chat_history import ChatHistoryManager
from .nodes.input import InputNode
from .nodes.structure import StructureNode
from .nodes.evaluation import EvaluationNode, PainpointNode, InvestorEvaluationWrapperNode
from .nodes.production import ProductionNodes
from .nodes.html_generation import HTMLGenerationNode
from ..utils.text_processing import detect_language

def create_bp_graph(
    llm: BaseChatModel, 
    aihehuo_api_key: Optional[str] = None,
    aihehuo_api_base: Optional[str] = None,
    chat_history_manager: Optional[ChatHistoryManager] = None,
    checkpointer: Optional[Any] = None
):
    """
    Construct the BP Generation Graph.
    
    Args:
        llm: LangChain ChatModel for LLM operations
        aihehuo_api_key: API key for Aihehuo partner search
        aihehuo_api_base: Base URL for Aihehuo API
        chat_history_manager: Optional ChatHistoryManager for centralized chat history management
                             If None, nodes will manage their own history (legacy behavior)
        checkpointer: Optional checkpointer for LangGraph checkpointing (e.g., MemorySaver, SqliteSaver)
                     If provided, the graph will be compiled with checkpointing enabled
    """
    
    # Initialize Node Logic wrappers with chat history manager
    input_node = InputNode(llm, chat_history_manager=chat_history_manager)
    structure_node = StructureNode(llm, chat_history_manager=chat_history_manager)
    eval_node = EvaluationNode(llm, chat_history_manager=chat_history_manager)
    painpoint_node = PainpointNode(llm, chat_history_manager=chat_history_manager)
    investor_node = InvestorEvaluationWrapperNode(llm, chat_history_manager=chat_history_manager)
    production_nodes = ProductionNodes(llm, aihehuo_api_key, aihehuo_api_base, chat_history_manager=chat_history_manager)
    html_node = HTMLGenerationNode(chat_history_manager=chat_history_manager)
    
    # Initialize Graph with reducer to handle missing fields
    def reduce_state(left: Dict[str, Any], right: Dict[str, Any]) -> Dict[str, Any]:
        """Reducer function to merge state updates and provide defaults for missing required fields."""
        # Debug: Print what the reducer receives
        print("=" * 60)
        print("DEBUG: Reducer called")
        print(f"Left (existing state) type: {type(left)}, keys: {list(left.keys()) if isinstance(left, dict) else 'Not a dict'}")
        print(f"Left content: {left}")
        print(f"Right (new state) type: {type(right)}, keys: {list(right.keys()) if isinstance(right, dict) else 'Not a dict'}")
        print(f"Right content: {right}")
        print("=" * 60)
        
        result = {**left, **right}
        
        if "session_id" not in result:
            result["session_id"] = str(uuid.uuid4())
        
        if "is_english" not in result:
            business_idea = result.get("business_idea", "")
            result["is_english"] = detect_language(business_idea) == 'en' if business_idea else False
        
        if "iteration_count" not in result:
            result["iteration_count"] = 0
        
        if "max_iterations" not in result:
            result["max_iterations"] = 3
        
        if "iteration_history" not in result:
            result["iteration_history"] = []
        
        return result
    
    workflow = StateGraph(AgentState, reducer=reduce_state)
    
    # Add a wrapper node to intercept and debug the initial input
    def input_check_wrapper(state: AgentState) -> Dict[str, Any]:
        """Wrapper to debug and preprocess input before passing to input_check node."""
        print("=" * 60)
        print("DEBUG: input_check_wrapper received state:")
        print(f"State type: {type(state)}")
        print(f"State keys: {list(state.keys()) if isinstance(state, dict) else 'Not a dict'}")
        print(f"State content: {state}")
        print("=" * 60)
        
        # Call the actual input node
        return input_node(state)
    
    # Add Nodes
    workflow.add_node("input_check", input_check_wrapper)
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
    
    # Compile the graph, optionally with checkpointing
    compiled_graph = workflow.compile(checkpointer=checkpointer) if checkpointer is not None else workflow.compile()
    
    # Wrap the compiled graph to intercept and debug initial input
    original_invoke = compiled_graph.invoke
    original_astream = compiled_graph.astream
    
    def debug_invoke(input_data, config=None):
        print("=" * 60)
        print("DEBUG: Graph.invoke called with:")
        print(f"Input type: {type(input_data)}")
        print(f"Input keys: {list(input_data.keys()) if isinstance(input_data, dict) else 'Not a dict'}")
        print(f"Input content: {input_data}")
        print(f"Config: {config}")
        print("=" * 60)
        return original_invoke(input_data, config)
    
    async def debug_astream(input_data, config=None):
        print("=" * 60)
        print("DEBUG: Graph.astream called with:")
        print(f"Input type: {type(input_data)}")
        print(f"Input keys: {list(input_data.keys()) if isinstance(input_data, dict) else 'Not a dict'}")
        print(f"Input content: {input_data}")
        print(f"Config: {config}")
        print("=" * 60)
        async for item in original_astream(input_data, config):
            yield item
    
    compiled_graph.invoke = debug_invoke
    compiled_graph.astream = debug_astream
    
    return compiled_graph


def create_bp_graph_factory():
    """
    Factory function for LangGraph CLI.
    Creates a BP graph with configuration loaded from config.py.
    
    This function is used by LangGraph CLI (langgraph dev) to automatically
    create and serve the graph.
    
    Returns:
        Compiled LangGraph workflow
    """
    import os
    import sys
    from langchain_openai import ChatOpenAI
    
    # Add project root to path for imports
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    
    from src.utils.config import load_config
    
    # Load configuration
    config = load_config()
    
    # Initialize LLM based on config
    if config.default_llm_provider == "deepseek":
        llm = ChatOpenAI(
            api_key=config.deepseek_api_key,
            base_url="https://api.deepseek.com",
            model=config.deepseek_model,
            temperature=0.7
        )
    elif config.default_llm_provider == "openai":
        llm = ChatOpenAI(
            api_key=config.openai_api_key,
            model=config.openai_model,
            temperature=0.7
        )
    elif config.default_llm_provider == "qwen":
        llm = ChatOpenAI(
            api_key=config.qwen_api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            model=config.qwen_model,
            temperature=0.7
        )
    else:
        raise ValueError(f"Unsupported LLM provider: {config.default_llm_provider}")
    
    # Create chat history manager
    chat_history_manager = ChatHistoryManager()
    
    # Create and return the graph directly (reducer and input node handle input preprocessing)
    return create_bp_graph(
        llm=llm,
        aihehuo_api_key=config.aihehuo_api_key,
        aihehuo_api_base=getattr(config, 'aihehuo_api_base', None),
        chat_history_manager=chat_history_manager
    )

