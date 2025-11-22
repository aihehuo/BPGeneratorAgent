"""
Chat History Management for BP Generation Graph
Centralized chat history persistence at workflow level
"""

import os
import json
from typing import Optional, Dict, Any
from datetime import datetime
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_community.chat_message_histories import FileChatMessageHistory

try:
    from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    BaseChatMessageHistory = None
    FileChatMessageHistory = None
    HumanMessage = None
    AIMessage = None
    BaseMessage = None


class ChatHistoryManager:
    """
    Centralized chat history manager for the BP Generation Graph.
    Manages chat history persistence at the workflow level, making it
    accessible to all nodes in the graph.
    """
    
    def __init__(self, session_id: Optional[str] = None, base_dir: str = "/tmp/bp_agent_sessions"):
        """
        Initialize chat history manager.
        
        Args:
            session_id: Session ID for the chat history
            base_dir: Base directory for storing chat history files
        """
        self.session_id = session_id
        self.base_dir = base_dir
        self._chat_history: Optional[BaseChatMessageHistory] = None
        self._history_file: Optional[str] = None
        
        if not LANGCHAIN_AVAILABLE:
            print("警告: LangChain 未安装，聊天历史功能不可用")
    
    def get_chat_history(self) -> Optional[BaseChatMessageHistory]:
        """
        Get or create the chat history object.
        
        Returns:
            ChatMessageHistory object, or None if LangChain is unavailable or session_id is None
        """
        if not LANGCHAIN_AVAILABLE or not self.session_id:
            return None
        
        if self._chat_history is None:
            try:
                # Create session directory
                session_dir = os.path.join(self.base_dir, self.session_id)
                os.makedirs(session_dir, exist_ok=True)
                
                # Create history file path (using .jsonl format)
                history_file = os.path.join(session_dir, "chat_history.jsonl")
                
                # Create FileChatMessageHistory instance
                self._chat_history = FileChatMessageHistory(file_path=history_file)
                self._history_file = history_file  # Store for later access
                print(f"聊天历史管理器已初始化: {history_file}")
            except Exception as e:
                print(f"创建聊天历史对象失败: {str(e)}")
                return None
        
        return self._chat_history
    
    def add_user_message(self, content: str) -> bool:
        """
        Add a user message to the chat history.
        
        Args:
            content: User message content
            
        Returns:
            True if successful, False otherwise
        """
        chat_history = self.get_chat_history()
        if not chat_history:
            return False
        
        try:
            chat_history.add_user_message(content)
            return True
        except Exception as e:
            print(f"保存用户消息失败: {str(e)}")
            return False
    
    def add_ai_message(self, content: str) -> bool:
        """
        Add an AI message to the chat history.
        
        Args:
            content: AI message content
            
        Returns:
            True if successful, False otherwise
        """
        chat_history = self.get_chat_history()
        if not chat_history:
            return False
        
        try:
            chat_history.add_ai_message(content)
            return True
        except Exception as e:
            print(f"保存AI消息失败: {str(e)}")
            return False
    
    def get_messages(self) -> list:
        """
        Get all messages from chat history.
        
        Returns:
            List of messages, or empty list if unavailable
        """
        chat_history = self.get_chat_history()
        if not chat_history:
            return []
        
        try:
            return chat_history.messages
        except Exception as e:
            print(f"获取消息失败: {str(e)}")
            return []
    
    def get_user_messages(self) -> list[str]:
        """
        Get all user messages from chat history.
        
        Returns:
            List of user message contents
        """
        messages = self.get_messages()
        user_messages = []
        for message in messages:
            if isinstance(message, HumanMessage):
                content = message.content
                if content and content.strip():
                    user_messages.append(content.strip())
        return user_messages
    
    def get_conversation_history(self) -> str:
        """
        Get formatted conversation history as a single string.
        
        Returns:
            Formatted conversation history, or empty string if unavailable
        """
        user_messages = self.get_user_messages()
        if not user_messages:
            return ""
        
        # Combine all user messages
        return "\n\n".join(user_messages)
    
    def get_history_file_path(self) -> Optional[str]:
        """
        Get the file path where chat history is stored.
        
        Returns:
            File path, or None if unavailable
        """
        return self._history_file
    
    def persist_node_output(self, node_name: str, output: Dict[str, Any]) -> bool:
        """
        Persist a node's output to chat history.
        
        Args:
            node_name: Name of the node (e.g., "input_check", "structure_gen")
            output: Output dictionary from the node
            
        Returns:
            True if successful, False otherwise
        """
        if not output:
            return False
        
        # Format the output as a summary message
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        summary = self._format_node_output(node_name, output, timestamp)
        
        return self.add_ai_message(summary)
    
    def persist_workflow_state(self, state: Dict[str, Any], stop_node: Optional[str] = None) -> bool:
        """
        Persist the final workflow state when workflow stops.
        
        Args:
            state: Final state dictionary from the workflow
            stop_node: Name of the node where workflow stopped (e.g., "input_check", "structure_eval")
            
        Returns:
            True if successful, False otherwise
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        summary = self._format_workflow_state(state, stop_node, timestamp)
        
        return self.add_ai_message(summary)
    
    def _format_node_output(self, node_name: str, output: Dict[str, Any], timestamp: str) -> str:
        """
        Format a node's output as a readable message.
        
        Args:
            node_name: Name of the node
            output: Output dictionary
            timestamp: Timestamp string
            
        Returns:
            Formatted message string
        """
        node_display_names = {
            "input_check": "输入完整性检查",
            "structure_gen": "BP结构生成",
            "structure_regenerate": "BP结构重新生成",
            "structure_eval": "BP结构评估",
            "painpoint_enhancement": "痛点增强",
            "investor_eval": "投资者评估",
            "pitch_gen": "60秒路演生成",
            "ppt_gen": "PPT设计生成",
            "partner_search": "合伙人搜索"
        }
        
        display_name = node_display_names.get(node_name, node_name)
        
        summary_parts = [f"[{timestamp}] {display_name} 完成:"]
        
        # Format based on node type and output structure
        if node_name == "input_check":
            is_complete = output.get("is_complete", False)
            perspective = output.get("current_perspective", "none")
            summary_parts.append(f"- 检查结果: {'通过' if is_complete else '未通过'}")
            summary_parts.append(f"- 当前视角: {perspective}")
            if not is_complete:
                suggestions = output.get("suggestions", [])
                if suggestions:
                    summary_parts.append(f"- 改进建议: {', '.join(suggestions[:3])}")
        
        elif node_name in ("structure_gen", "structure_regenerate"):
            bp_structure = output.get("bp_structure", [])
            if bp_structure:
                summary_parts.append(f"- 生成了 {len(bp_structure)} 个段落")
                for idx, para in enumerate(bp_structure[:5], 1):  # Show first 5
                    title = para.get("title", "N/A")
                    summary_parts.append(f"  {idx}. {title}")
        
        elif node_name == "structure_eval":
            passed = output.get("evaluation_result", {}).get("passed", False)
            iteration = output.get("iteration_count", 0)
            summary_parts.append(f"- 评估结果: {'通过' if passed else '未通过'}")
            summary_parts.append(f"- 迭代次数: {iteration}")
        
        elif node_name == "painpoint_enhancement":
            bp_structure = output.get("bp_structure", [])
            if bp_structure:
                summary_parts.append(f"- 已增强痛点段落")
                summary_parts.append(f"- 当前结构包含 {len(bp_structure)} 个段落")
        
        elif node_name == "investor_eval":
            bp_structure = output.get("bp_structure", [])
            if bp_structure:
                summary_parts.append(f"- 投资者评估完成")
                summary_parts.append(f"- 最终结构包含 {len(bp_structure)} 个段落")
        
        elif node_name == "pitch_gen":
            pitch_result = output.get("pitch_result", {})
            if pitch_result:
                summary_parts.append(f"- 60秒路演文案已生成")
        
        elif node_name == "ppt_gen":
            ppt_result = output.get("ppt_result", {})
            slides = ppt_result.get("slides", []) if ppt_result else []
            if slides:
                summary_parts.append(f"- PPT设计已生成 ({len(slides)} 张幻灯片)")
        
        elif node_name == "partner_search":
            partner_result = output.get("partner_search_result", {})
            if partner_result:
                partners = partner_result.get("partners", [])
                investors = partner_result.get("investors", [])
                summary_parts.append(f"- 合伙人搜索完成")
                if partners:
                    summary_parts.append(f"- 找到 {len(partners)} 个潜在合伙人")
                if investors:
                    summary_parts.append(f"- 找到 {len(investors)} 个潜在投资者")
        
        return "\n".join(summary_parts)
    
    def _format_workflow_state(self, state: Dict[str, Any], stop_node: Optional[str], timestamp: str) -> str:
        """
        Format the final workflow state as a readable message.
        
        Args:
            state: Final state dictionary
            stop_node: Node where workflow stopped
            timestamp: Timestamp string
            
        Returns:
            Formatted message string
        """
        stop_reasons = {
            "input_check": "输入完整性检查未通过",
            "structure_gen": "BP结构生成完成",
            "structure_eval": "BP结构评估完成",
            "painpoint_enhancement": "痛点增强完成",
            "investor_eval": "投资者评估完成",
            "pitch_gen": "路演生成完成",
            "ppt_gen": "PPT设计完成",
            "partner_search": "合伙人搜索完成",
            "end": "工作流正常结束"
        }
        
        reason = stop_reasons.get(stop_node, f"工作流在节点 {stop_node} 处结束" if stop_node else "工作流结束")
        
        summary_parts = [f"[{timestamp}] 工作流执行完成: {reason}"]
        
        # Add key state information
        has_structure = state.get("bp_structure") is not None
        has_evaluation = state.get("evaluation_result") is not None
        has_pitch = state.get("pitch_result") is not None
        has_ppt = state.get("ppt_result") is not None
        has_partners = state.get("partner_search_result") is not None
        
        summary_parts.append("\n工作流状态:")
        if has_structure:
            bp_structure = state.get("bp_structure", [])
            summary_parts.append(f"- BP结构: {'✓' if bp_structure else '✗'}")
        if has_evaluation:
            eval_passed = state.get("evaluation_result", {}).get("passed", False)
            summary_parts.append(f"- 结构评估: {'✓ 通过' if eval_passed else '✗ 未通过'}")
        if has_pitch:
            summary_parts.append(f"- 60秒路演: ✓")
        if has_ppt:
            summary_parts.append(f"- PPT设计: ✓")
        if has_partners:
            summary_parts.append(f"- 合伙人搜索: ✓")
        
        # Add error if present
        error = state.get("error")
        if error:
            summary_parts.append(f"\n错误: {error}")
        
        return "\n".join(summary_parts)

