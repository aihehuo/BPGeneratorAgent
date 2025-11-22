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
        business_idea = state["business_idea"]
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
            self.chat_history_manager.persist_node_output("input_check", result)
        
        # Update state
        return {
            "input_completeness": result
        }

