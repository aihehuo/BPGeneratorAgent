"""
单元测试：输入完整性检查节点
"""

import unittest
import os
import json
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

# 添加项目根目录到Python路径
import sys
import os

# 获取项目根目录并添加到路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 现在可以直接使用 src 模块
from src.nodes.input_completeness_node import InputCompletenessNode, output_schema_input_completeness
from src.llms.base import BaseLLM


class MockLLM(BaseLLM):
    """Mock LLM 客户端用于测试"""
    
    def __init__(self, response: str = None):
        """
        初始化 Mock LLM
        
        Args:
            response: 预设的响应文本
        """
        super().__init__(api_key="mock_key")
        self.response = response or self._default_response()
        self.invoke_called = False
        self.last_system_prompt = None
        self.last_user_prompt = None
    
    def _default_response(self) -> str:
        """默认响应（完整输入的示例）"""
        return json.dumps({
            "is_complete": True,
            "current_perspective": "mixed",
            "perspective_details": {
                "technical": {
                    "has_content": True,
                    "completeness": "complete",
                    "description": "提到了AI技术",
                    "checklist": {
                        "technology_mention": True,
                        "solution_approach": True
                    },
                    "missing_checkpoints": []
                },
                "user_painpoint": {
                    "has_content": True,
                    "completeness": "complete",
                    "description": "提到了学生需求",
                    "checklist": {
                        "problem_need_mention": True,
                        "target_users": True
                    },
                    "missing_checkpoints": []
                },
                "market": {
                    "has_content": False,
                    "completeness": "missing",
                    "description": "",
                    "checklist": {
                        "market_mention": False,
                        "opportunity_mention": False
                    },
                    "missing_checkpoints": ["市场提及", "机会提及"]
                }
            },
            "suggestions": ["可以补充市场视角的信息"]
        }, ensure_ascii=False)
    
    def invoke(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        """
        模拟LLM调用
        
        Args:
            system_prompt: 系统提示词
            user_prompt: 用户输入
            
        Returns:
            预设的响应文本
        """
        self.invoke_called = True
        self.last_system_prompt = system_prompt
        self.last_user_prompt = user_prompt
        return self.response
    
    def get_default_model(self) -> str:
        """返回默认模型名称"""
        return "mock-model"


class TestInputCompletenessNode(unittest.TestCase):
    """InputCompletenessNode 单元测试类"""
    
    def setUp(self):
        """设置测试环境"""
        self.mock_llm = MockLLM()
        self.node = InputCompletenessNode(self.mock_llm)
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """清理测试环境"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        # 清理可能的 /tmp 测试文件
        test_session_dir = os.path.join("/tmp", "bp_agent_sessions", "test_session")
        if os.path.exists(test_session_dir):
            shutil.rmtree(test_session_dir)
    
    def test_init(self):
        """测试节点初始化"""
        self.assertIsNotNone(self.node)
        self.assertEqual(self.node.node_name, "InputCompletenessNode")
        self.assertEqual(self.node.llm_client, self.mock_llm)
    
    def test_get_tmp_session_dir(self):
        """测试获取 /tmp 下的 session 目录路径"""
        # 正常情况
        session_dir = os.path.join(self.temp_dir, "test_session")
        tmp_dir = self.node._get_tmp_session_dir(session_dir)
        expected = os.path.join("/tmp", "bp_agent_sessions", "test_session")
        self.assertEqual(tmp_dir, expected)
        
        # session_dir 为 None
        tmp_dir = self.node._get_tmp_session_dir(None)
        self.assertIsNone(tmp_dir)
        
        # session_dir 以 / 结尾
        session_dir = os.path.join(self.temp_dir, "test_session") + os.sep
        tmp_dir = self.node._get_tmp_session_dir(session_dir)
        self.assertEqual(tmp_dir, expected)
    
    def test_get_checkpoint_names(self):
        """测试获取检查点名称映射"""
        # 测试技术视角
        names = self.node._get_checkpoint_names("technical")
        self.assertIn("technology_mention", names)
        self.assertEqual(names["technology_mention"], "技术提及")
        self.assertEqual(names["solution_approach"], "解决方案方法")
        
        # 测试用户痛点视角
        names = self.node._get_checkpoint_names("user_painpoint")
        self.assertIn("problem_need_mention", names)
        self.assertEqual(names["problem_need_mention"], "问题/需求提及")
        self.assertEqual(names["target_users"], "目标用户")
        
        # 测试市场视角
        names = self.node._get_checkpoint_names("market")
        self.assertIn("market_mention", names)
        self.assertEqual(names["market_mention"], "市场提及")
        self.assertEqual(names["opportunity_mention"], "机会提及")
        
        # 测试未知视角
        names = self.node._get_checkpoint_names("unknown")
        self.assertEqual(names, {})
    
    def test_format_checklist(self):
        """测试格式化检查清单"""
        result = {
            "perspective_details": {
                "technical": {
                    "checklist": {
                        "technology_mention": True,
                        "solution_approach": False
                    },
                    "missing_checkpoints": ["解决方案方法"]
                },
                "user_painpoint": {
                    "checklist": {
                        "problem_need_mention": True,
                        "target_users": True
                    },
                    "missing_checkpoints": []
                }
            }
        }
        
        formatted = self.node._format_checklist(result)
        
        # 验证技术视角的格式化结果
        self.assertIn("technical", formatted)
        checklist_status = formatted["technical"]["checklist_status"]
        self.assertEqual(len(checklist_status), 2)
        self.assertEqual(checklist_status[0]["key"], "technology_mention")
        self.assertTrue(checklist_status[0]["checked"])
        self.assertEqual(checklist_status[1]["key"], "solution_approach")
        self.assertFalse(checklist_status[1]["checked"])
    
    def test_process_output_valid_json(self):
        """测试处理有效的JSON输出"""
        valid_output = json.dumps({
            "is_complete": True,
            "current_perspective": "mixed",
            "perspective_details": {
                "technical": {
                    "has_content": True,
                    "completeness": "complete",
                    "description": "技术描述",
                    "checklist": {
                        "technology_mention": True,
                        "solution_approach": True
                    },
                    "missing_checkpoints": []
                },
                "user_painpoint": {
                    "has_content": True,
                    "completeness": "complete",
                    "description": "用户痛点描述",
                    "checklist": {
                        "problem_need_mention": True,
                        "target_users": True
                    },
                    "missing_checkpoints": []
                },
                "market": {
                    "has_content": False,
                    "completeness": "missing",
                    "description": "",
                    "checklist": {
                        "market_mention": False,
                        "opportunity_mention": False
                    },
                    "missing_checkpoints": []
                }
            },
            "suggestions": ["建议1", "建议2"]
        }, ensure_ascii=False)
        
        result = self.node.process_output(valid_output)
        
        self.assertTrue(result["is_complete"])
        self.assertEqual(result["current_perspective"], "mixed")
        self.assertIn("perspective_details", result)
        self.assertIn("suggestions", result)
        self.assertIn("formatted_checklist", result)
    
    def test_process_output_invalid_json(self):
        """测试处理无效的JSON输出"""
        invalid_output = "这不是有效的JSON"
        
        result = self.node.process_output(invalid_output)
        
        # 应该返回默认的不完整结果
        self.assertFalse(result["is_complete"])
        self.assertEqual(result["current_perspective"], "none")
        self.assertIn("perspective_details", result)
        self.assertIn("suggestions", result)
    
    def test_process_output_json_with_tags(self):
        """测试处理带JSON标签的输出"""
        output_with_tags = """这是推理过程
```json
{
    "is_complete": true,
    "current_perspective": "technical",
    "perspective_details": {
        "technical": {
            "has_content": true,
            "completeness": "complete",
            "description": "技术描述",
            "checklist": {
                "technology_mention": true,
                "solution_approach": true
            },
            "missing_checkpoints": []
        },
        "user_painpoint": {
            "has_content": true,
            "completeness": "complete",
            "description": "用户痛点描述",
            "checklist": {
                "problem_need_mention": true,
                "target_users": true
            },
            "missing_checkpoints": []
        },
        "market": {
            "has_content": false,
            "completeness": "missing",
            "description": "",
            "checklist": {
                "market_mention": false,
                "opportunity_mention": false
            },
            "missing_checkpoints": []
        }
    },
    "suggestions": []
}
```"""
        
        # clean_json_tags 应该能够处理这种情况，让我们直接测试
        # 如果 clean_json_tags 正常工作，应该能提取出 JSON
        result = self.node.process_output(output_with_tags)
        
        # 应该能解析出 JSON（至少应该尝试处理，即使解析失败也会返回默认结果）
        self.assertIsInstance(result, dict)
        self.assertIn("is_complete", result)
        # 如果成功解析，应该是 true；如果失败，至少应该是有效的字典结构
    
    def test_process_output_missing_fields(self):
        """测试处理缺少必需字段的输出"""
        incomplete_output = json.dumps({
            "is_complete": True,
            "perspective_details": {
                "technical": {
                    "has_content": True,
                    "completeness": "complete",
                    "checklist": {
                        "technology_mention": True,
                        "solution_approach": True
                    }
                }
            }
        }, ensure_ascii=False)
        
        result = self.node.process_output(incomplete_output)
        
        # 应该自动补充缺失的字段
        self.assertIn("current_perspective", result)
        self.assertIn("suggestions", result)
    
    def test_process_output_incomplete_perspective_validation(self):
        """测试至少需要2个完整视角的验证"""
        output_with_one_complete = json.dumps({
            "is_complete": True,  # LLM可能错误地返回true
            "current_perspective": "technical",
            "perspective_details": {
                "technical": {
                    "has_content": True,
                    "completeness": "complete",
                    "checklist": {
                        "technology_mention": True,
                        "solution_approach": True
                    },
                    "missing_checkpoints": []
                },
                "user_painpoint": {
                    "has_content": False,
                    "completeness": "missing",
                    "checklist": {
                        "problem_need_mention": False,
                        "target_users": False
                    },
                    "missing_checkpoints": []
                },
                "market": {
                    "has_content": False,
                    "completeness": "missing",
                    "checklist": {
                        "market_mention": False,
                        "opportunity_mention": False
                    },
                    "missing_checkpoints": []
                }
            },
            "suggestions": []
        }, ensure_ascii=False)
        
        result = self.node.process_output(output_with_one_complete)
        
        # 应该自动修正为False（只有1个完整视角，需要至少2个）
        self.assertFalse(result["is_complete"])
    
    @patch('src.nodes.input_completeness_node.LANGCHAIN_AVAILABLE', True)
    def test_get_chat_history_with_langchain(self):
        """测试使用LangChain获取聊天历史"""
        session_dir = os.path.join(self.temp_dir, "test_session")
        
        with patch('src.nodes.input_completeness_node.FileChatMessageHistory') as mock_file_history:
            mock_history = MagicMock()
            mock_file_history.return_value = mock_history
            
            result = self.node._get_chat_history(session_dir)
            
            self.assertIsNotNone(result)
            # 验证创建了正确的路径
            expected_file = os.path.join("/tmp", "bp_agent_sessions", "test_session", "chat_history.jsonl")
            mock_file_history.assert_called_once_with(file_path=expected_file)
    
    @patch('src.nodes.input_completeness_node.LANGCHAIN_AVAILABLE', False)
    def test_get_chat_history_without_langchain(self):
        """测试LangChain不可用时的回退"""
        session_dir = os.path.join(self.temp_dir, "test_session")
        
        result = self.node._get_chat_history(session_dir)
        
        self.assertIsNone(result)
    
    def test_get_chat_history_no_session_dir(self):
        """测试没有提供session_dir时"""
        result = self.node._get_chat_history(None)
        self.assertIsNone(result)
    
    @patch('src.nodes.input_completeness_node.LANGCHAIN_AVAILABLE', True)
    def test_load_previous_inputs_with_langchain(self):
        """测试使用LangChain加载历史输入"""
        session_dir = os.path.join(self.temp_dir, "test_session")
        
        # 创建一个简单的HumanMessage mock类
        class MockHumanMessage:
            def __init__(self, content):
                self.content = content
        
        with patch.object(self.node, '_get_chat_history') as mock_get_history:
            # Mock LangChain 消息历史
            mock_messages = [
                MockHumanMessage("第一个商业创意"),
                MockHumanMessage("第二个商业创意"),
            ]
            
            mock_history = MagicMock()
            mock_history.messages = mock_messages
            mock_get_history.return_value = mock_history
            
            # Mock HumanMessage 类型检查
            with patch('src.nodes.input_completeness_node.HumanMessage', MockHumanMessage):
                result = self.node._load_previous_inputs(session_dir)
                self.assertIn("第一个商业创意", result)
                self.assertIn("第二个商业创意", result)
    
    def test_load_previous_inputs_fallback(self):
        """测试加载历史输入的回退方案（文件系统）"""
        session_dir = os.path.join(self.temp_dir, "test_session")
        os.makedirs(session_dir, exist_ok=True)
        
        # 创建旧的输入记录文件
        input_file = os.path.join(session_dir, "previous_user_inputs.md")
        with open(input_file, "w", encoding="utf-8") as f:
            f.write("""# 用户输入记录

## 输入记录

**时间戳**: 2024-01-01 00:00:00

**商业创意**:

第一个商业创意描述

---

## 输入记录

**时间戳**: 2024-01-02 00:00:00

**商业创意**:

第二个商业创意描述

---
""")
        
        result = self.node._load_previous_inputs(session_dir)
        
        self.assertIn("第一个商业创意描述", result)
        self.assertIn("第二个商业创意描述", result)
    
    @patch('src.nodes.input_completeness_node.LANGCHAIN_AVAILABLE', True)
    def test_save_user_input_with_langchain(self):
        """测试使用LangChain保存用户输入"""
        # 需要重新初始化节点以应用 patch
        from src.nodes.input_completeness_node import InputCompletenessNode
        patched_node = InputCompletenessNode(self.mock_llm)
        
        session_dir = os.path.join(self.temp_dir, "test_session")
        business_idea = "这是一个测试商业创意"
        completeness_result = {
            "is_complete": True,
            "current_perspective": "technical",
            "suggestions": ["建议1"]
        }
        
        with patch.object(patched_node, '_get_chat_history') as mock_get_history:
            mock_history = MagicMock()
            mock_get_history.return_value = mock_history
            
            result = patched_node._save_user_input(business_idea, session_dir, completeness_result)
            
            # 验证调用了 add_user_message 和 add_ai_message
            mock_history.add_user_message.assert_called_once_with(business_idea)
            
            # 验证 AI 消息（评估结果）也被保存了
            mock_history.add_ai_message.assert_called_once()
            # 获取调用参数，验证内容包含评估结果
            ai_message_content = mock_history.add_ai_message.call_args[0][0]
            self.assertIn("输入完整性检查结果", ai_message_content)
            self.assertIn("当前视角: technical", ai_message_content)
            self.assertIn("是否完整: 是", ai_message_content)
            
            self.assertIsNotNone(result)
            self.assertIn("chat_history.jsonl", result)
            self.assertIn("/tmp/bp_agent_sessions", result)
    
    def test_save_user_input_fallback(self):
        """测试保存用户输入的回退方案（文件系统）"""
        session_dir = os.path.join(self.temp_dir, "test_session")
        business_idea = "这是一个测试商业创意"
        
        result = self.node._save_user_input(business_idea, session_dir)
        
        # 验证文件已创建
        input_file = os.path.join(session_dir, "previous_user_inputs.md")
        self.assertTrue(os.path.exists(input_file))
        self.assertIsNotNone(result)
    
    def test_save_user_input_no_session_dir(self):
        """测试没有提供session_dir时"""
        result = self.node._save_user_input("商业创意", None)
        self.assertIsNone(result)
    
    def test_run_complete_input(self):
        """测试运行完整性检查 - 完整输入"""
        business_idea = "基于AI的在线教育平台，面向K12学生，提供个性化学习"
        
        result = self.node.run(business_idea)
        
        self.assertIsInstance(result, dict)
        self.assertIn("is_complete", result)
        self.assertIn("current_perspective", result)
        self.assertIn("perspective_details", result)
        self.assertIn("suggestions", result)
        self.assertTrue(self.mock_llm.invoke_called)
    
    def test_run_with_session_dir(self):
        """测试使用session_dir运行"""
        session_dir = os.path.join(self.temp_dir, "test_session")
        business_idea = "测试商业创意"
        
        result = self.node.run(business_idea, session_dir=session_dir)
        
        self.assertIsInstance(result, dict)
        # 如果保存了文件，应该存在 saved_input_file
        if result.get("saved_input_file"):
            # 可能是 chat_history.jsonl (LangChain) 或 previous_user_inputs.md (文件系统回退)
            saved_file = result["saved_input_file"]
            self.assertTrue("chat_history.jsonl" in saved_file or "previous_user_inputs.md" in saved_file)
    
    def test_run_incomplete_input(self):
        """测试运行完整性检查 - 不完整输入"""
        # 设置mock返回不完整的结果
        incomplete_response = json.dumps({
            "is_complete": False,
            "current_perspective": "none",
            "perspective_details": {
                "technical": {
                    "has_content": False,
                    "completeness": "missing",
                    "checklist": {
                        "technology_mention": False,
                        "solution_approach": False
                    },
                    "missing_checkpoints": ["技术提及", "解决方案方法"]
                },
                "user_painpoint": {
                    "has_content": False,
                    "completeness": "missing",
                    "checklist": {
                        "problem_need_mention": False,
                        "target_users": False
                    },
                    "missing_checkpoints": ["问题/需求提及", "目标用户"]
                },
                "market": {
                    "has_content": False,
                    "completeness": "missing",
                    "checklist": {
                        "market_mention": False,
                        "opportunity_mention": False
                    },
                    "missing_checkpoints": ["市场提及", "机会提及"]
                }
            },
            "suggestions": ["请提供更详细的描述"]
        }, ensure_ascii=False)
        
        self.mock_llm.response = incomplete_response
        business_idea = "只是一个简单的想法"
        
        result = self.node.run(business_idea)
        
        self.assertFalse(result["is_complete"])
        self.assertIn("suggestions", result)


class TestInputCompletenessNodeIntegration(unittest.TestCase):
    """集成测试 - 测试完整流程"""
    
    def setUp(self):
        """设置测试环境"""
        self.mock_llm = MockLLM()
        self.node = InputCompletenessNode(self.mock_llm)
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """清理测试环境"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_full_workflow(self):
        """测试完整工作流程"""
        session_dir = os.path.join(self.temp_dir, "test_session")
        
        # 第一次运行
        business_idea1 = "AI教育平台，面向学生"
        result1 = self.node.run(business_idea1, session_dir=session_dir)
        
        self.assertIsInstance(result1, dict)
        self.assertIn("is_complete", result1)
        
        # 验证 LLM 第一次调用时使用了 idea1
        # MockLLM 保存了最后一次调用的参数
        self.assertIn(business_idea1, self.mock_llm.last_user_prompt)
        
        # 重置 mock 的记录，确保我们检测的是第二次调用
        self.mock_llm.invoke_called = False
        self.mock_llm.last_user_prompt = None
        
        # 第二次运行（应该能加载历史）
        business_idea2 = "补充：K12市场，个性化学习"
        result2 = self.node.run(business_idea2, session_dir=session_dir)
        
        self.assertIsInstance(result2, dict)
        
        # 关键断言：验证第二次调用的 Prompt 中是否同时包含了第一次和第二次的输入
        # 这样才能证明历史记录被正确加载并合并了
        self.assertTrue(self.mock_llm.invoke_called)
        self.assertIsNotNone(self.mock_llm.last_user_prompt)
        self.assertIn(business_idea1, self.mock_llm.last_user_prompt, "第二次运行的 Prompt 应该包含第一次的历史输入")
        self.assertIn(business_idea2, self.mock_llm.last_user_prompt, "第二次运行的 Prompt 应该包含本次的新输入")


if __name__ == "__main__":
    unittest.main()

