from typing import Dict, Any, Optional
from langchain_core.language_models.chat_models import BaseChatModel
from ...nodes.input_completeness_node import InputCompletenessNode
from ..state import AgentState
from ..chat_history import ChatHistoryManager

class InputNode:
    def __init__(self, llm: BaseChatModel, chat_history_manager: Optional[ChatHistoryManager] = None):
        """
        Initialize Input Node.
        
        Args:
            llm: LangChain ChatModel
            chat_history_manager: Optional centralized chat history manager
        """
        self.node_logic = InputCompletenessNode(llm)
        self.chat_history_manager = chat_history_manager

    def __call__(self, state: AgentState) -> Dict[str, Any]:
        # Debug: Print the actual state structure to understand what's being passed
        print("=" * 60)
        print("DEBUG: InputNode received state:")
        print(f"State type: {type(state)}")
        print(f"State keys: {list(state.keys()) if isinstance(state, dict) else 'Not a dict'}")
        print(f"State content: {state}")
        print("=" * 60)
        
        # Handle missing required fields (e.g., when invoked through LangGraph CLI)
        # When using generic API interfaces, treat user message/input as business_idea
        business_idea = state.get("business_idea")
        
        if not business_idea:
            # Try various common input field names
            if "input" in state:
                input_val = state["input"]
                if isinstance(input_val, str):
                    # If input is a string, use it directly as business_idea
                    business_idea = input_val
                elif isinstance(input_val, dict):
                    # If input is a dict, try common field names
                    business_idea = (
                        input_val.get("business_idea") or 
                        input_val.get("message") or 
                        input_val.get("text") or 
                        input_val.get("query") or
                        input_val.get("prompt") or
                        input_val.get("content")
                    )
            
            # Try other common field names at top level
            if not business_idea:
                business_idea = (
                    state.get("message") or 
                    state.get("text") or 
                    state.get("query") or 
                    state.get("prompt") or
                    state.get("content") or
                    state.get("user_message")
                )
            
            # If still no business_idea, check all string values in state
            if not business_idea:
                # Check if there's any string value that could be the business idea
                for key, value in state.items():
                    if isinstance(value, str) and value.strip() and key not in ["session_id", "error"]:
                        # Use the first substantial string value found
                        business_idea = value
                        break
                
                # If still nothing, try to get any non-empty string from nested structures
                if not business_idea:
                    for key, value in state.items():
                        if isinstance(value, dict):
                            for sub_key, sub_value in value.items():
                                if isinstance(sub_value, str) and sub_value.strip():
                                    business_idea = sub_value
                                    break
                            if business_idea:
                                break
        
        if not business_idea or not business_idea.strip():
            # Provide helpful error message with actual state structure
            state_keys = list(state.keys()) if isinstance(state, dict) else []
            raise ValueError(
                f"'business_idea' is required but not found in input.\n"
                f"Received state keys: {state_keys}\n"
                f"Please provide it as:\n"
                f"- 'business_idea' field in the input\n"
                f"- 'message', 'text', 'query', 'prompt', or 'content' field\n"
                f"- Or as a string value in the 'input' field\n"
                f"Example: {{'input': {{'message': 'Your business idea here'}}}}"
            )
        
        session_id = state.get("session_id")
        
        # Update chat history manager's session_id if needed
        if self.chat_history_manager and session_id:
            if self.chat_history_manager.session_id != session_id:
                # Create a new manager with the correct session_id
                from ..chat_history import ChatHistoryManager
                self.chat_history_manager = ChatHistoryManager(session_id=session_id)
        
        # Load previous inputs from chat history (workflow-level)
        previous_inputs = ""
        if self.chat_history_manager:
            previous_inputs = self.chat_history_manager.get_conversation_history()
            if previous_inputs:
                self.node_logic.log_info(f"从工作流级别的聊天历史管理器加载了之前的用户输入")
        
        # Run the completeness check (node logic is now focused only on checking)
        # Pass empty string (not None) when no history, so backward compatibility doesn't kick in
        result = self.node_logic.run(
            business_idea,
            previous_inputs=previous_inputs,  # Empty string if no history, actual content otherwise
            session_id=session_id
        )
        
        # Extract markdown_summary from result if available (for consistency, move to state top level)
        markdown_summary = None
        if result and isinstance(result, dict):
            markdown_summary = result.get("markdown_summary")
            # Remove markdown_summary from result to keep input_completeness clean
            if markdown_summary:
                result = {k: v for k, v in result.items() if k != "markdown_summary"}
        
        # Save user input to chat history (workflow-level)
        if self.chat_history_manager:
            self.chat_history_manager.add_user_message(business_idea)
            
            # Save completeness result summary as AI message
            if result:
                is_complete = result.get("is_complete", False)
                perspective = result.get("current_perspective", "none")
                suggestions = result.get("suggestions", [])
                
                result_summary = f"输入完整性检查结果:\n"
                result_summary += f"- 是否完整: {'是' if is_complete else '否'}\n"
                result_summary += f"- 当前视角: {perspective}\n"
                if suggestions:
                    result_summary += f"- 改进建议: {', '.join(suggestions[:3])}\n"
                
                self.chat_history_manager.add_ai_message(result_summary)
            
            # Add saved file path to result (for backward compatibility)
            saved_file = self.chat_history_manager.get_history_file_path()
            if saved_file:
                result["saved_input_file"] = saved_file
                self.node_logic.log_info(f"用户输入已保存到工作流级别的聊天历史: {saved_file}")
            else:
                self.node_logic.log_info(f"用户输入已保存到工作流级别的聊天历史")
        
        # Persist node output to chat history (formatted summary)
        if self.chat_history_manager:
            persist_data = result.copy() if result else {}
            if markdown_summary:
                persist_data["markdown_summary"] = markdown_summary
            self.chat_history_manager.persist_node_output("input_check", persist_data)
        
        # Update state - markdown_summary at top level for consistency
        output = {
            "input_completeness": result
        }
        if markdown_summary:
            output["markdown_summary"] = markdown_summary
        
        return output

