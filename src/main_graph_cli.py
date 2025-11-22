import os
import uuid
import argparse
from typing import Optional

from langchain_openai import ChatOpenAI

from src.utils.config import load_config
from src.graph.workflow import create_bp_graph
from src.graph.chat_history import ChatHistoryManager
# Note: BPGenerationAgent is now graph-based, so we can use it directly
from src.bp_generation_agent import BPGenerationAgent
from src.utils.text_processing import detect_language

def get_llm(config):
    """Initialize LangChain Chat Model based on config."""
    if config.default_llm_provider == "deepseek":
        return ChatOpenAI(
            api_key=config.deepseek_api_key,
            base_url="https://api.deepseek.com",
            model=config.deepseek_model,
            temperature=0.7
        )
    elif config.default_llm_provider == "openai":
        return ChatOpenAI(
            api_key=config.openai_api_key,
            model=config.openai_model,
            temperature=0.7
        )
    elif config.default_llm_provider == "qwen":
         # Qwen compatible with OpenAI format
         return ChatOpenAI(
            api_key=config.qwen_api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1", 
            model=config.qwen_model,
            temperature=0.7
        )
    else:
        raise ValueError(f"Unsupported LLM provider: {config.default_llm_provider}")

def main():
    parser = argparse.ArgumentParser(description="BP Generation Agent (Graph Version)")
    parser.add_argument("idea", nargs="?", help="Business idea description")
    parser.add_argument("--file", help="Read business idea from file")
    parser.add_argument("--session", help="Session ID")
    args = parser.parse_args()

    # Get business idea
    business_idea = ""
    if args.file:
        with open(args.file, 'r', encoding='utf-8') as f:
            business_idea = f.read().strip()
    elif args.idea:
        business_idea = args.idea
    
    if not business_idea:
        print("Please provide a business idea via argument or file.")
        return

    # Load config
    config = load_config()
    
    # Initialize LLM
    print(f"Initializing LLM ({config.default_llm_provider})...")
    llm = get_llm(config)
    
    # Setup session (use session_id as primary identifier)
    session_id = args.session
    if not session_id:
        session_id = str(uuid.uuid4())
    else:
        # Validate session_id format
        try:
            uuid.UUID(session_id)
        except (ValueError, AttributeError):
            print(f"警告: 提供的session_id不是有效UUID格式，将生成新的Session ID")
            session_id = str(uuid.uuid4())
    
    print(f"Session ID: {session_id}")
    
    # Initialize workflow-level chat history manager
    chat_history_manager = ChatHistoryManager(session_id=session_id)
    
    # Create Graph with chat history manager
    print("Initializing Graph with chat history manager...")
    graph = create_bp_graph(llm, config.aihehuo_api_key, config.aihehuo_api_base, chat_history_manager=chat_history_manager)
    
    # Initial State (only session_id, nodes will handle storage internally)
    inputs = {
        "business_idea": business_idea,
        "session_id": session_id,
        "iteration_count": 0,
        "max_iterations": 3,
        "iteration_history": [],
        "is_english": detect_language(business_idea) == 'en'
    }
    
    print("\n" + "=" * 60)
    print(f"Starting BP Generation for: {business_idea[:50]}...")
    print("=" * 60)
    
    # Run Graph
    final_state = graph.invoke(inputs)
    
    # Determine where workflow stopped
    stop_node = None
    completeness = final_state.get("input_completeness", {})
    if completeness and not completeness.get("is_complete", False):
        stop_node = "input_check"
        print("\nInput check failed:")
        print(f"Perspective: {completeness.get('current_perspective')}")
        print("Suggestions:")
        for s in completeness.get("suggestions", []):
            print(f"- {s}")
    else:
        # Determine the last completed node based on state
        if final_state.get("partner_search_result"):
            stop_node = "partner_search"
        elif final_state.get("ppt_result"):
            stop_node = "ppt_gen"
        elif final_state.get("pitch_result"):
            stop_node = "pitch_gen"
        elif final_state.get("investor_evaluation_result") or final_state.get("bp_structure"):
            stop_node = "investor_eval"
        elif final_state.get("painpoint_enhancement_result"):
            stop_node = "painpoint_enhancement"
        elif final_state.get("evaluation_result"):
            stop_node = "structure_eval"
        elif final_state.get("bp_structure"):
            stop_node = "structure_gen"
        else:
            stop_node = "end"
        
        print("\nGraph execution completed.")
    
    # Persist final workflow state to chat history
    if chat_history_manager:
        chat_history_manager.persist_workflow_state(final_state, stop_node=stop_node)
    
    # Post-processing (Markdown & Files)
    # Reuse BPGenerationAgent's helper methods
    # We create a dummy agent just to access methods
    agent_helper = BPGenerationAgent(config)
    
    # 1. Build Markdown
    print("Generating report files...")
    markdown_content = agent_helper._build_markdown(
        business_idea,
        final_state.get("bp_structure", []),
        final_state.get("iteration_history", []),
        final_state.get("evaluation_result", {}),
        final_state.get("partner_search_result")
    )
    
    # 2. Save Markdown (convert session_id to session_dir for file operations)
    session_dir = agent_helper._get_session_dir(session_id)
    os.makedirs(session_dir, exist_ok=True)
    output_path = agent_helper._build_default_filename(business_idea, session_id=session_id)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(markdown_content)
    print(f"Saved report to: {output_path}")
    
    # 3. Save PPT Design
    ppt_result = final_state.get("ppt_result")
    if ppt_result and ppt_result.get("slides"):
        agent_helper._save_ppt_design_file(
            business_idea,
            final_state.get("bp_structure", []),
            ppt_result,
            output_path
        )
        
    # 4. Save Partner Report
    partner_result = final_state.get("partner_search_result")
    if partner_result:
         agent_helper._save_partner_report(
            business_idea,
            partner_result,
            output_path
         )

if __name__ == "__main__":
    main()

