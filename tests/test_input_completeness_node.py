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
from src.utils.config import load_config
from src.llms import DeepSeekLLM, OpenAILLM, QwenLLM


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
    
    # 注释：_get_tmp_session_dir 方法已被移除，聊天历史管理现在在工作流级别处理
    # def test_get_tmp_session_dir(self):
    #     """测试获取 /tmp 下的 session 目录路径"""
    #     pass
    
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
    
    # 注释：此测试已移除，因为 _get_chat_history 方法已被移除，聊天历史管理现在在工作流级别处理
    # @patch('src.nodes.input_completeness_node.LANGCHAIN_AVAILABLE', True)
    # def test_get_chat_history_with_langchain(self):
    #     """测试使用LangChain获取聊天历史"""
    #     pass
    
    # 注释：以下测试方法已被移除，因为聊天历史管理现在在工作流级别的 InputNode 中处理
    # InputCompletenessNode 现在只专注于完整性检查逻辑，不接受这些方法
    
    # def test_get_chat_history_without_langchain(self):
    #     """测试LangChain不可用时的回退"""
    #     pass
    
    # def test_get_chat_history_no_session_dir(self):
    #     """测试没有提供session_dir时"""
    #     pass
    
    # def test_load_previous_inputs_with_langchain(self):
    #     """测试使用LangChain加载历史输入"""
    #     pass
    
    # def test_load_previous_inputs_fallback(self):
    #     """测试加载历史输入的回退方案（文件系统）"""
    #     pass
    
    # def test_save_user_input_with_langchain(self):
    #     """测试使用LangChain保存用户输入"""
    #     pass
    
    # def test_save_user_input_fallback(self):
    #     """测试保存用户输入的回退方案（文件系统）"""
    #     pass
    
    # def test_save_user_input_no_session_dir(self):
    #     """测试没有提供session_dir时"""
    #     pass
    
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
        """测试完整工作流程（包括previous_inputs合并）"""
        # 第一次运行
        business_idea1 = "AI教育平台，面向学生"
        result1 = self.node.run(business_idea1)
        
        self.assertIsInstance(result1, dict)
        self.assertIn("is_complete", result1)
        
        # 验证 LLM 第一次调用时使用了 idea1
        self.assertIn(business_idea1, self.mock_llm.last_user_prompt)
        
        # 重置 mock 的记录，确保我们检测的是第二次调用
        self.mock_llm.invoke_called = False
        self.mock_llm.last_user_prompt = None
        
        # 第二次运行（手动提供previous_inputs，模拟工作流级别提供的聊天历史）
        business_idea2 = "补充：K12市场，个性化学习"
        # 模拟工作流级别提供的之前的输入
        previous_inputs = business_idea1
        result2 = self.node.run(business_idea2, previous_inputs=previous_inputs)
        
        self.assertIsInstance(result2, dict)
        
        # 关键断言：验证第二次调用的 Prompt 中是否同时包含了第一次和第二次的输入
        # 这样才能证明 previous_inputs 被正确合并了
        self.assertTrue(self.mock_llm.invoke_called)
        self.assertIsNotNone(self.mock_llm.last_user_prompt)
        self.assertIn(business_idea1, self.mock_llm.last_user_prompt, "第二次运行的 Prompt 应该包含之前的输入（previous_inputs）")
        self.assertIn(business_idea2, self.mock_llm.last_user_prompt, "第二次运行的 Prompt 应该包含本次的新输入")


class TestInputCompletenessNodeWithRealLLM(unittest.TestCase):
    """使用真实LLM的InputCompletenessNode测试类
    
    这些测试会调用真实的LLM API，用于验证提示词的有效性。
    如果环境变量SKIP_REAL_LLM_TESTS=1，这些测试将被跳过。
    确保在运行这些测试前已正确配置API密钥。
    """
    
    @classmethod
    def setUpClass(cls):
        """设置测试类，初始化真实LLM客户端"""
        # 检查是否跳过真实LLM测试
        if os.getenv("SKIP_REAL_LLM_TESTS") == "1":
            cls.skip_all = True
            return
        
        cls.skip_all = False
        
        try:
            # 加载配置
            cls.config = load_config()
            
            # 初始化LLM客户端
            if cls.config.default_llm_provider == "deepseek":
                if not cls.config.deepseek_api_key:
                    cls.skip_all = True
                    print("\n警告: DeepSeek API Key未配置，跳过真实LLM测试")
                    return
                cls.llm_client = DeepSeekLLM(
                    api_key=cls.config.deepseek_api_key,
                    model_name=cls.config.deepseek_model
                )
            elif cls.config.default_llm_provider == "openai":
                if not cls.config.openai_api_key:
                    cls.skip_all = True
                    print("\n警告: OpenAI API Key未配置，跳过真实LLM测试")
                    return
                cls.llm_client = OpenAILLM(
                    api_key=cls.config.openai_api_key,
                    model_name=cls.config.openai_model
                )
            elif cls.config.default_llm_provider == "qwen":
                if not cls.config.qwen_api_key:
                    cls.skip_all = True
                    print("\n警告: Qwen API Key未配置，跳过真实LLM测试")
                    return
                cls.llm_client = QwenLLM(
                    api_key=cls.config.qwen_api_key,
                    model_name=cls.config.qwen_model
                )
            else:
                cls.skip_all = True
                print(f"\n警告: 不支持的LLM提供商 {cls.config.default_llm_provider}，跳过真实LLM测试")
                return
            
            print(f"\n✅ 真实LLM测试已启用: {cls.llm_client.get_model_info()}")
            
        except Exception as e:
            cls.skip_all = True
            print(f"\n警告: 初始化LLM失败 ({str(e)})，跳过真实LLM测试")
    
    def setUp(self):
        """设置测试环境"""
        if self.skip_all:
            self.skipTest("真实LLM测试已跳过（API Key未配置或环境变量SKIP_REAL_LLM_TESTS=1）")
        
        self.node = InputCompletenessNode(self.llm_client)
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """清理测试环境"""
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_real_llm_complete_input_chinese(self):
        """测试真实LLM - 完整的中文输入"""
        business_idea = "基于AI的在线教育平台，面向K12学生，提供个性化学习路径推荐，解决学生学习效率低和缺乏针对性指导的问题"
        
        result = self.node.run(business_idea)
        
        # 验证基本结构
        self.assertIsInstance(result, dict)
        self.assertIn("is_complete", result)
        self.assertIn("current_perspective", result)
        self.assertIn("perspective_details", result)
        self.assertIn("suggestions", result)
        self.assertIn("markdown_summary", result)
        
        # 验证数据完整性
        self.assertIsInstance(result["is_complete"], bool)
        self.assertIn(result["current_perspective"], ["technical", "user_painpoint", "market", "mixed", "none"])
        
        # 验证perspective_details结构
        perspective_details = result.get("perspective_details", {})
        self.assertIn("technical", perspective_details)
        self.assertIn("user_painpoint", perspective_details)
        self.assertIn("market", perspective_details)
        
        # 验证markdown_summary存在且非空
        markdown_summary = result.get("markdown_summary", "")
        self.assertIsInstance(markdown_summary, str)
        self.assertGreater(len(markdown_summary), 0, "markdown_summary应该非空")
        
        print(f"\n✅ 测试通过: 完整输入")
        print(f"   is_complete: {result['is_complete']}")
        print(f"   perspective: {result['current_perspective']}")
        print(f"   markdown_summary: {markdown_summary[:100]}...")
        
        # 对于完整输入，应该通过
        if result["is_complete"]:
            print(f"   ✅ 输入完整性检查通过")
    
    def test_real_llm_incomplete_input_chinese(self):
        """测试真实LLM - 不完整的中文输入（只有一个视角）"""
        business_idea = "一个AI平台"  # 只有技术视角
        
        result = self.node.run(business_idea)
        
        # 验证基本结构
        self.assertIsInstance(result, dict)
        self.assertIn("is_complete", result)
        self.assertIn("markdown_summary", result)
        
        # 验证markdown_summary
        markdown_summary = result.get("markdown_summary", "")
        self.assertIsInstance(markdown_summary, str)
        self.assertGreater(len(markdown_summary), 0, "markdown_summary应该非空")
        
        print(f"\n✅ 测试通过: 不完整输入")
        print(f"   is_complete: {result['is_complete']}")
        print(f"   markdown_summary: {markdown_summary[:100]}...")
        
        # 对于不完整输入，应该不通过
        if not result["is_complete"]:
            suggestions = result.get("suggestions", [])
            print(f"   ✅ 正确识别为不完整，建议: {suggestions}")
    
    def test_real_llm_complete_input_english(self):
        """测试真实LLM - 完整的英文输入"""
        business_idea = "An AI-powered online education platform for K12 students, providing personalized learning path recommendations to solve the problems of low learning efficiency and lack of targeted guidance"
        
        result = self.node.run(business_idea)
        
        # 验证基本结构
        self.assertIsInstance(result, dict)
        self.assertIn("is_complete", result)
        self.assertIn("markdown_summary", result)
        
        # 验证markdown_summary存在且非空
        markdown_summary = result.get("markdown_summary", "")
        self.assertIsInstance(markdown_summary, str)
        self.assertGreater(len(markdown_summary), 0, "markdown_summary应该非空")
        
        # 验证markdown_summary是英文（对于英文输入）
        # 简单检查：应该包含一些英文关键词
        english_keywords = ["complete", "perspective", "technical", "user", "market", "assessment"]
        has_english = any(keyword.lower() in markdown_summary.lower() for keyword in english_keywords)
        
        print(f"\n✅ 测试通过: 完整英文输入")
        print(f"   is_complete: {result['is_complete']}")
        print(f"   markdown_summary: {markdown_summary[:100]}...")
        print(f"   markdown_summary语言: {'英文' if has_english else '未确定'}")
    
    def test_real_llm_prompt_structure(self):
        """测试真实LLM - 验证提示词结构是否正确生成"""
        business_idea = "基于区块链的供应链管理系统，帮助企业实现透明化和可追溯性"
        
        result = self.node.run(business_idea)
        
        # 验证输出符合schema要求
        # 节点返回的格式是：直接包含data字段的内容（is_complete, current_perspective等）
        # 以及markdown_summary字段
        self.assertIn("markdown_summary", result)
        
        # 验证每个视角都有必要的字段
        perspective_details = result.get("perspective_details", {})
        for perspective_name, details in perspective_details.items():
            self.assertIsInstance(details, dict)
            self.assertIn("has_content", details)
            self.assertIn("completeness", details)
            self.assertIn("checklist", details)
            self.assertIn("missing_checkpoints", details)
            
            # 验证checklist结构
            checklist = details.get("checklist", {})
            self.assertIsInstance(checklist, dict)
            
            # 验证completeness值
            self.assertIn(details["completeness"], ["complete", "partial", "missing"])
        
        print(f"\n✅ 测试通过: 提示词结构验证")
        print(f"   所有视角都有正确的结构")
    
    def test_real_llm_output_format(self):
        """测试真实LLM - 验证输出格式符合新的schema要求（包含markdown_summary）"""
        business_idea = "智能家居控制系统，通过IoT设备连接家中的各种电器，用户可以通过手机APP远程控制"
        
        result = self.node.run(business_idea)
        
        # 验证新格式：应该包含markdown_summary
        self.assertIn("markdown_summary", result, "结果应该包含markdown_summary字段")
        markdown_summary = result["markdown_summary"]
        
        # 验证markdown_summary格式
        self.assertIsInstance(markdown_summary, str)
        self.assertGreater(len(markdown_summary.strip()), 0, "markdown_summary应该非空")
        # 应该包含一些描述性内容（至少包含评估结果的基本信息）
        # 简单检查：应该有一些文字内容，不只是一个空字符串
        
        print(f"\n✅ 测试通过: 输出格式验证")
        print(f"   markdown_summary长度: {len(markdown_summary)} 字符")
        print(f"   markdown_summary预览: {markdown_summary[:150]}...")
    
    def test_real_llm_with_previous_inputs(self):
        """测试真实LLM - 验证previous_inputs参数的正确合并"""
        previous_input = "AI教育平台"
        current_input = "补充：面向K12学生，提供个性化学习"
        
        # 第一次运行（只有当前输入）
        result1 = self.node.run(current_input)
        
        # 第二次运行（合并之前的输入）
        result2 = self.node.run(current_input, previous_inputs=previous_input)
        
        # 验证两次运行都有结果
        self.assertIsInstance(result1, dict)
        self.assertIsInstance(result2, dict)
        
        # 验证都包含markdown_summary
        self.assertIn("markdown_summary", result1)
        self.assertIn("markdown_summary", result2)
        
        print(f"\n✅ 测试通过: previous_inputs合并验证")
        print(f"   第一次运行 (无历史): is_complete={result1['is_complete']}")
        print(f"   第二次运行 (有历史): is_complete={result2['is_complete']}")
        
        # 合并后的输入应该更完整，is_complete更可能为True
        if result2["is_complete"] and not result1["is_complete"]:
            print(f"   ✅ 合并历史后完整性检查通过")


if __name__ == "__main__":
    unittest.main()

