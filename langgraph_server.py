"""
LangGraph Server for BP Generation Agent

This server uses LangServe to expose the LangGraph workflow as a REST API.
It provides a simpler alternative to the custom FastAPI server (api_server.py).

Key differences from api_server.py:
- Uses LangServe's built-in endpoints (/invoke, /stream, /batch)
- Provides interactive playground UI at /bp-generation/playground
- Directly exposes the LangGraph workflow without custom wrapper logic
- Simpler implementation, but less control over API structure

Usage:
    python langgraph_server.py [--host 0.0.0.0] [--port 8000] [--reload]

Endpoints:
    POST /bp-generation/invoke - Synchronous graph execution
    POST /bp-generation/stream - Streaming graph execution
    POST /bp-generation/batch - Batch graph execution
    GET  /bp-generation/playground - Interactive playground UI
    GET  /health - Health check
    GET  /docs - API documentation

Input format:
    The graph expects AgentState as input. Minimum required fields:
    {
        "business_idea": "Your business idea here",
        "session_id": "optional-session-id",  # Used for state persistence and tracking
        "is_english": false,
        "iteration_count": 0,
        "max_iterations": 3,
        "iteration_history": []
    }

Graph ID / Thread ID:
    - The graph uses session_id from AgentState as the primary identifier
    - session_id serves as both the session identifier and can be used as thread_id
      for LangGraph checkpointing (if checkpointing is enabled)
    - When using LangServe endpoints, you can pass config with thread_id:
      {
        "input": { ... AgentState ... },
        "config": {"configurable": {"thread_id": "your-session-id"}}
      }
    - This allows resuming interrupted workflows and state persistence
"""

import os
import sys
import argparse
from typing import Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langchain_openai import ChatOpenAI

try:
    from langserve import add_routes
except ImportError:
    print("Error: langserve is not installed.")
    print("Please install it with: pip install langserve>=0.0.40")
    sys.exit(1)

from src.graph.workflow import create_bp_graph
from src.graph.chat_history import ChatHistoryManager
from src.utils.config import load_config


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


def create_app(config=None, enable_checkpointing: bool = False):
    """
    Create FastAPI app with LangGraph workflow exposed via LangServe.
    
    Args:
        config: Optional config object. If None, loads from config.py
        enable_checkpointing: If True, enables LangGraph checkpointing for state persistence.
                            Requires a checkpoint saver (e.g., MemorySaver, SqliteSaver).
                            Default: False (uses ChatHistoryManager instead)
        
    Returns:
        FastAPI app instance
        
    Note:
        To enable checkpointing, you need to:
        1. Install a checkpoint backend: pip install langgraph-checkpoint-<backend>
        2. Create a checkpointer: from langgraph.checkpoint.memory import MemorySaver
        3. Compile graph with checkpointer: graph = graph.compile(checkpointer=checkpointer)
        4. Use thread_id in config when invoking (mapped from session_id)
    """
    # Load config
    if config is None:
        config = load_config()
    
    # Initialize LLM
    llm = get_llm(config)
    
    # Create chat history manager (optional, can be None for stateless operation)
    chat_history_manager = ChatHistoryManager()
    
    # Optional: Enable checkpointing for state persistence
    # This allows resuming interrupted workflows and better state management
    checkpointer = None
    if enable_checkpointing:
        try:
            from langgraph.checkpoint.memory import MemorySaver
            checkpointer = MemorySaver()
            print("✓ LangGraph checkpointing enabled (MemorySaver)")
        except ImportError:
            print("⚠ Checkpointing requested but langgraph checkpoint backend not installed.")
            print("  Install with: pip install langgraph-checkpoint-memory")
            print("  Or use: pip install langgraph-checkpoint-sqlite")
            print("  Continuing without checkpointing...")
            checkpointer = None
    
    # Create the LangGraph workflow (with optional checkpointing)
    graph = create_bp_graph(
        llm=llm,
        aihehuo_api_key=config.aihehuo_api_key,
        aihehuo_api_base=getattr(config, 'aihehuo_api_base', None),
        chat_history_manager=chat_history_manager,
        checkpointer=checkpointer
    )
    
    # Create FastAPI app
    app = FastAPI(
        title="BP Generation Agent (LangGraph Server)",
        description="商业计划书生成API服务 - 使用LangGraph内置服务器",
        version="1.0.0",
    )
    
    # Add CORS support
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allow all origins (restrict in production)
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add LangGraph routes via LangServe
    # This exposes the graph at /invoke, /stream, /batch endpoints
    # 
    # Note: LangServe automatically handles checkpointing if a checkpoint saver is configured.
    # The graph uses session_id from AgentState, which can be mapped to thread_id for checkpointing.
    # To enable checkpointing, you would need to:
    # 1. Create a checkpoint saver (e.g., MemorySaver, SqliteSaver)
    # 2. Compile the graph with checkpointing: graph = graph.compile(checkpointer=checkpointer)
    # 3. Use thread_id in config when invoking: graph.invoke(inputs, config={"configurable": {"thread_id": session_id}})
    #
    # For now, we use the existing ChatHistoryManager for state persistence.
    add_routes(
        app,
        graph,
        path="/bp-generation",
        playground_type="default",  # Enable playground UI
    )
    
    # Add health check endpoint
    @app.get("/health")
    async def health_check():
        """Health check endpoint"""
        return {
            "status": "healthy",
            "service": "BP Generation Agent (LangGraph Server)",
            "llm_provider": config.default_llm_provider,
        }
    
    # Add root endpoint
    @app.get("/")
    async def root():
        """Root endpoint with API information"""
        return {
            "name": "BP Generation Agent (LangGraph Server)",
            "version": "1.0.0",
            "description": "商业计划书生成API服务 - 使用LangGraph内置服务器",
            "endpoints": {
                "health": "/health",
                "graph_invoke": "/bp-generation/invoke",
                "graph_stream": "/bp-generation/stream",
                "graph_batch": "/bp-generation/batch",
                "playground": "/bp-generation/playground",
                "docs": "/docs",
            },
            "note": "This server uses LangServe to expose the LangGraph workflow. "
                   "Use /bp-generation/invoke for synchronous calls, "
                   "/bp-generation/stream for streaming, and "
                   "/bp-generation/batch for batch processing.",
            "session_management": {
                "session_id": "Use session_id in AgentState input to track sessions. "
                             "This can also be used as thread_id for checkpointing.",
                "checkpointing": "To enable LangGraph checkpointing, compile the graph "
                               "with a checkpointer and use thread_id in config."
            }
        }
    
    return app


def main():
    """Main entry point for the LangGraph server"""
    parser = argparse.ArgumentParser(
        description="BP Generation Agent - LangGraph Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start server on default port 8000
  python langgraph_server.py

  # Start server on custom port
  python langgraph_server.py --port 8001

  # Start with reload (development mode)
  python langgraph_server.py --reload

  # Enable checkpointing for state persistence
  python langgraph_server.py --enable-checkpointing

Note:
  This server uses LangServe to expose the LangGraph workflow.
  The graph is accessible at:
    - POST /bp-generation/invoke - Synchronous invocation
    - POST /bp-generation/stream - Streaming invocation
    - POST /bp-generation/batch - Batch invocation
    - GET  /bp-generation/playground - Interactive playground UI
  
  Session Management:
    - Use session_id in AgentState input to track sessions
    - With checkpointing enabled, use thread_id in config:
      {"configurable": {"thread_id": "your-session-id"}}
        """
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Server host address (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Server port (default: 8000)"
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload (development mode)"
    )
    parser.add_argument(
        "--enable-checkpointing",
        action="store_true",
        help="Enable LangGraph checkpointing for state persistence (requires checkpoint backend)"
    )
    
    args = parser.parse_args()
    
    # Create the app
    app = create_app(enable_checkpointing=args.enable_checkpointing)
    
    print("=" * 60)
    print("BP Generation Agent - LangGraph Server")
    print("=" * 60)
    print(f"Starting server: http://{args.host}:{args.port}")
    print(f"API Documentation: http://{args.host}:{args.port}/docs")
    print(f"Health Check: http://{args.host}:{args.port}/health")
    print(f"Graph Endpoint: http://{args.host}:{args.port}/bp-generation/invoke")
    print(f"Playground UI: http://{args.host}:{args.port}/bp-generation/playground")
    print("=" * 60)
    print("\nNote: This server uses LangServe to expose the LangGraph workflow.")
    print("The graph accepts AgentState as input and returns updated state.")
    print("\nSession Management:")
    print("  - Use 'session_id' in AgentState input to track sessions")
    print("  - session_id can be used as thread_id for checkpointing (if enabled)")
    print("  - Pass config with thread_id: {\"configurable\": {\"thread_id\": \"session-id\"}}")
    print("=" * 60)
    
    # Import uvicorn here to avoid requiring it at module level
    import uvicorn
    
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()

