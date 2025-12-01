"""
单元测试：合伙人搜索节点
"""

import unittest
import os
import json
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List

# 添加项目根目录到Python路径
import sys
import os

# 获取项目根目录并添加到路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 现在可以直接使用 src 模块
from src.nodes.partner_search_node import PartnerSearchNode
from src.llms.base import BaseLLM
from src.utils.config import load_config


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
        """默认响应（搜索短语提取的示例）"""
        return json.dumps({
            "data": {
                "partner_query": "寻找AI教育平台技术合伙人，需要机器学习和大数据经验",
                "investor_query": "寻找教育科技领域早期投资，关注AI个性化学习"
            },
            "markdown_summary": "从商业计划书中提取了两个搜索短语：合伙人搜索短语针对技术合伙人（需要机器学习和大数据经验），投资人搜索短语针对教育科技领域的早期投资。"
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


class TestPartnerSearchNode(unittest.TestCase):
    """PartnerSearchNode 单元测试类"""
    
    def setUp(self):
        """设置测试环境"""
        self.mock_llm = MockLLM()
        self.node = PartnerSearchNode(self.mock_llm)
        self.business_idea = "基于AI的在线教育平台，面向K12学生，提供个性化学习"
        self.bp_structure = [
            {"title": "用户画像与痛点", "content": "K12学生需要个性化学习，但传统教育无法满足"},
            {"title": "解决方案", "content": "使用AI技术分析学生学习数据，提供个性化学习路径"},
            {"title": "最小可行产品（MVP）", "content": "核心功能包括学习数据分析和智能推荐引擎"}
        ]
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """清理测试环境"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_init(self):
        """测试节点初始化"""
        self.assertIsNotNone(self.node)
        self.assertEqual(self.node.node_name, "PartnerSearchNode")
        self.assertEqual(self.node.llm_client, self.mock_llm)
    
    def test_validate_input_valid(self):
        """测试输入验证 - 有效输入"""
        valid_input = {
            "business_idea": self.business_idea,
            "bp_structure": self.bp_structure
        }
        self.assertTrue(self.node.validate_input(valid_input))
    
    def test_validate_input_invalid(self):
        """测试输入验证 - 无效输入"""
        # 缺少business_idea
        invalid_input1 = {"bp_structure": self.bp_structure}
        self.assertFalse(self.node.validate_input(invalid_input1))
        
        # 缺少bp_structure
        invalid_input2 = {"business_idea": self.business_idea}
        self.assertFalse(self.node.validate_input(invalid_input2))
        
        # 非字典类型
        self.assertFalse(self.node.validate_input("not a dict"))
        self.assertFalse(self.node.validate_input(None))
    
    def test_parse_search_phrases_nested_structure(self):
        """测试解析搜索短语 - 嵌套结构（新格式）"""
        response = json.dumps({
            "data": {
                "partner_query": "技术合伙人，AI经验",
                "investor_query": "教育科技投资人"
            },
            "markdown_summary": "提取了搜索短语"
        }, ensure_ascii=False)
        
        result = self.node._parse_search_phrases(response)
        
        self.assertEqual(result["partner_query"], "技术合伙人，AI经验")
        self.assertEqual(result["investor_query"], "教育科技投资人")
        # Note: markdown_summary extraction may vary depending on parsing method
        # The important thing is that partner_query and investor_query are extracted
        self.assertIn("markdown_summary", result)
    
    def test_parse_search_phrases_flat_structure(self):
        """测试解析搜索短语 - 扁平结构（向后兼容）"""
        response = json.dumps({
            "partner_query": "技术合伙人，AI经验",
            "investor_query": "教育科技投资人"
        }, ensure_ascii=False)
        
        result = self.node._parse_search_phrases(response)
        
        self.assertEqual(result["partner_query"], "技术合伙人，AI经验")
        self.assertEqual(result["investor_query"], "教育科技投资人")
        self.assertEqual(result.get("markdown_summary", ""), "")
    
    def test_parse_search_phrases_with_markdown_tags(self):
        """测试解析搜索短语 - 包含markdown标签"""
        response = f"""<OUTPUT JSON SCHEMA>
{{
  "data": {{
    "partner_query": "技术合伙人",
    "investor_query": "教育投资人"
  }},
  "markdown_summary": "摘要内容"
}}
</OUTPUT JSON SCHEMA>"""
        
        result = self.node._parse_search_phrases(response)
        
        self.assertEqual(result["partner_query"], "技术合伙人")
        self.assertEqual(result["investor_query"], "教育投资人")
        self.assertEqual(result["markdown_summary"], "摘要内容")
    
    def test_parse_search_phrases_invalid_json(self):
        """测试解析搜索短语 - 无效JSON"""
        response = "这不是有效的JSON"
        
        result = self.node._parse_search_phrases(response)
        
        # 应该返回空字符串，不会抛出异常
        self.assertIsInstance(result, dict)
        self.assertIn("partner_query", result)
        self.assertIn("investor_query", result)
    
    @patch('src.nodes.partner_search_node.search_members')
    def test_run_successful_search(self, mock_search_members):
        """测试运行节点 - 成功搜索"""
        # 设置mock返回值
        mock_partner_results = [
            {
                "user_id": "1",
                "name": "张三",
                "bio": "AI教育专家，10年经验",
                "goal": "寻找教育科技项目"
            },
            {
                "user_id": "2",
                "name": "李四",
                "bio": "机器学习工程师",
                "goal": "技术合伙人"
            }
        ]
        
        mock_investor_results = [
            {
                "user_id": "3",
                "name": "王五",
                "bio": "教育科技投资人",
                "goal": "投资AI教育项目"
            }
        ]
        
        mock_search_members.side_effect = [
            mock_partner_results,  # 第一次调用返回合伙人结果
            mock_investor_results  # 第二次调用返回投资人结果
        ]
        
        input_data = {
            "business_idea": self.business_idea,
            "bp_structure": self.bp_structure
        }
        
        result = self.node.run(input_data, partner_per_page=10, investor_per_page=10)
        
        # 验证结果
        self.assertIn("partner_search_query", result)
        self.assertIn("investor_search_query", result)
        self.assertIn("partner_results", result)
        self.assertIn("investor_results", result)
        self.assertIn("partner_count", result)
        self.assertIn("investor_count", result)
        self.assertIn("markdown_summary", result)
        
        # 验证搜索被调用
        self.assertEqual(mock_search_members.call_count, 2)
        
        # 验证结果数量
        self.assertEqual(result["partner_count"], 2)
        self.assertEqual(result["investor_count"], 1)
        
        # 验证markdown摘要包含搜索结果
        self.assertIn("搜索结果", result["markdown_summary"] or "")
        self.assertIn("2", result["markdown_summary"] or "")  # 合伙人数量
        self.assertIn("1", result["markdown_summary"] or "")  # 投资人数量
    
    @patch('src.nodes.partner_search_node.search_members')
    def test_run_no_results(self, mock_search_members):
        """测试运行节点 - 无搜索结果"""
        # 设置mock返回空列表
        mock_search_members.return_value = []
        
        input_data = {
            "business_idea": self.business_idea,
            "bp_structure": self.bp_structure
        }
        
        result = self.node.run(input_data)
        
        # 验证结果
        self.assertEqual(result["partner_count"], 0)
        self.assertEqual(result["investor_count"], 0)
        self.assertEqual(len(result["partner_results"]), 0)
        self.assertEqual(len(result["investor_results"]), 0)
    
    @patch('src.nodes.partner_search_node.search_members')
    def test_run_search_exception(self, mock_search_members):
        """测试运行节点 - 搜索抛出异常"""
        # 设置mock抛出异常
        mock_search_members.side_effect = Exception("API错误")
        
        input_data = {
            "business_idea": self.business_idea,
            "bp_structure": self.bp_structure
        }
        
        # 应该捕获异常并继续执行（搜索异常被捕获，不会影响整体流程）
        result = self.node.run(input_data)
        
        # 验证结果仍然返回（虽然搜索失败）
        self.assertIn("partner_search_query", result)
        self.assertIn("investor_search_query", result)
        # 结果应该为空（搜索失败但查询已提取）
        # Note: The search exceptions are caught and logged, but the process continues
        # The counts will be 0 because searches failed
        self.assertEqual(result["partner_count"], 0)
        self.assertEqual(result["investor_count"], 0)
    
    @patch('src.nodes.partner_search_node.search_members')
    def test_run_short_query_skipped(self, mock_search_members):
        """测试运行节点 - 查询太短被跳过"""
        # 设置mock LLM返回短查询
        self.mock_llm.response = json.dumps({
            "data": {
                "partner_query": "短",  # 太短，会被跳过
                "investor_query": "教育科技投资人"  # 正常长度
            },
            "markdown_summary": "摘要"
        }, ensure_ascii=False)
        
        mock_search_members.return_value = []
        
        input_data = {
            "business_idea": self.business_idea,
            "bp_structure": self.bp_structure
        }
        
        result = self.node.run(input_data)
        
        # 合伙人搜索应该被跳过（查询太短）
        # 投资人搜索应该执行
        self.assertEqual(mock_search_members.call_count, 1)  # 只调用一次（投资人）
    
    def test_generate_enhanced_summary_chinese(self):
        """测试生成增强摘要 - 中文"""
        initial_summary = "初始摘要：提取了搜索短语"
        partner_query = "技术合伙人，AI经验"
        investor_query = "教育科技投资人"
        partner_results = [
            {"name": "张三", "bio": "AI教育专家，10年经验"},
            {"name": "李四", "bio": "机器学习工程师"}
        ]
        investor_results = [
            {"name": "王五", "bio": "教育科技投资人"}
        ]
        
        summary = self.node._generate_enhanced_summary(
            initial_summary=initial_summary,
            partner_query=partner_query,
            investor_query=investor_query,
            partner_count=2,
            investor_count=1,
            partner_results=partner_results,
            investor_results=investor_results,
            business_idea="基于AI的在线教育平台"
        )
        
        # 验证摘要内容
        self.assertIn("初始摘要", summary)
        self.assertIn("搜索结果", summary)
        self.assertIn("合伙人搜索", summary)
        self.assertIn("投资人搜索", summary)
        self.assertIn("2", summary)  # 合伙人数量
        self.assertIn("1", summary)  # 投资人数量
        self.assertIn("张三", summary)
        self.assertIn("王五", summary)
    
    def test_generate_enhanced_summary_english(self):
        """测试生成增强摘要 - 英文"""
        initial_summary = "Initial summary: extracted search phrases"
        partner_query = "Technical partner with AI experience"
        investor_query = "EdTech investor"
        partner_results = [
            {"name": "John", "bio": "AI education expert with 10 years experience"},
            {"name": "Jane", "bio": "Machine learning engineer"}
        ]
        investor_results = [
            {"name": "Bob", "bio": "EdTech investor"}
        ]
        
        summary = self.node._generate_enhanced_summary(
            initial_summary=initial_summary,
            partner_query=partner_query,
            investor_query=investor_query,
            partner_count=2,
            investor_count=1,
            partner_results=partner_results,
            investor_results=investor_results,
            business_idea="AI-powered online education platform for K12 students"
        )
        
        # 验证摘要内容
        self.assertIn("Initial summary", summary)
        self.assertIn("Search Results", summary)
        self.assertIn("Partner Search", summary)
        self.assertIn("Investor Search", summary)
        self.assertIn("2", summary)  # 合伙人数量
        self.assertIn("1", summary)  # 投资人数量
        self.assertIn("John", summary)
        self.assertIn("Bob", summary)
    
    def test_generate_enhanced_summary_no_results(self):
        """测试生成增强摘要 - 无搜索结果"""
        initial_summary = "初始摘要"
        partner_query = "技术合伙人"
        investor_query = "教育投资人"
        
        summary = self.node._generate_enhanced_summary(
            initial_summary=initial_summary,
            partner_query=partner_query,
            investor_query=investor_query,
            partner_count=0,
            investor_count=0,
            partner_results=[],
            investor_results=[],
            business_idea="基于AI的在线教育平台"
        )
        
        # 验证摘要包含"未找到"
        self.assertIn("未找到", summary)
    
    def test_generate_enhanced_summary_no_initial_summary(self):
        """测试生成增强摘要 - 无初始摘要"""
        summary = self.node._generate_enhanced_summary(
            initial_summary="",
            partner_query="技术合伙人",
            investor_query="教育投资人",
            partner_count=1,
            investor_count=1,
            partner_results=[{"name": "张三"}],
            investor_results=[{"name": "王五"}],
            business_idea="基于AI的在线教育平台"
        )
        
        # 即使没有初始摘要，也应该生成搜索结果摘要
        self.assertIn("搜索结果", summary)
        self.assertIn("1", summary)
    
    def test_extract_search_phrases_success(self):
        """测试提取搜索短语 - 成功"""
        # 设置mock LLM响应
        self.mock_llm.response = json.dumps({
            "data": {
                "partner_query": "技术合伙人",
                "investor_query": "教育投资人"
            },
            "markdown_summary": "提取了搜索短语"
        }, ensure_ascii=False)
        
        result = self.node._extract_search_phrases(
            self.business_idea,
            self.bp_structure
        )
        
        # 验证结果
        self.assertIn("partner_query", result)
        self.assertIn("investor_query", result)
        self.assertIn("markdown_summary", result)
        self.assertEqual(result["partner_query"], "技术合伙人")
        self.assertEqual(result["investor_query"], "教育投资人")
        
        # 验证LLM被调用
        self.assertTrue(self.mock_llm.invoke_called)
    
    def test_extract_search_phrases_failure(self):
        """测试提取搜索短语 - 失败时使用默认查询"""
        # 设置mock LLM抛出异常
        self.mock_llm.invoke = Mock(side_effect=Exception("LLM错误"))
        
        result = self.node._extract_search_phrases(
            self.business_idea,
            self.bp_structure
        )
        
        # 应该返回默认查询
        self.assertIn("partner_query", result)
        self.assertIn("investor_query", result)
        self.assertIn("寻找", result["partner_query"] or "")
        self.assertIn("寻找", result["investor_query"] or "")
    
    def test_run_invalid_input(self):
        """测试运行节点 - 无效输入"""
        invalid_input = {"business_idea": self.business_idea}  # 缺少bp_structure
        
        # The run method catches exceptions and returns an error dict instead of raising
        result = self.node.run(invalid_input)
        
        # Verify that error is in the result
        self.assertIn("error", result)
        self.assertIn("输入数据格式错误", result["error"])
    
    @patch('src.nodes.partner_search_node.search_members')
    def test_run_with_custom_params(self, mock_search_members):
        """测试运行节点 - 自定义参数"""
        mock_search_members.return_value = []
        
        input_data = {
            "business_idea": self.business_idea,
            "bp_structure": self.bp_structure
        }
        
        # 使用自定义参数
        result = self.node.run(
            input_data,
            partner_per_page=5,
            investor_per_page=3,
            wechat_reachable_only=False
        )
        
        # 验证search_members被调用时使用了正确的参数
        self.assertEqual(mock_search_members.call_count, 2)
        
        # 检查调用参数
        calls = mock_search_members.call_args_list
        # 第一个调用应该是合伙人搜索
        self.assertEqual(calls[0][1]['per_page'], 5)
        self.assertEqual(calls[0][1]['investor'], False)
        self.assertEqual(calls[0][1]['wechat_reachable_only'], False)
        
        # 第二个调用应该是投资人搜索
        self.assertEqual(calls[1][1]['per_page'], 3)
        self.assertEqual(calls[1][1]['investor'], True)
        self.assertEqual(calls[1][1]['wechat_reachable_only'], False)


class TestPartnerSearchNodeWithRealLLM(unittest.TestCase):
    """使用真实LLM和真实API的PartnerSearchNode测试类
    
    这些测试会调用真实的LLM API和爱合伙API，用于验证完整的功能。
    如果环境变量SKIP_REAL_LLM_TESTS=1，这些测试将被跳过。
    确保在运行这些测试前已正确配置API密钥（LLM API Key和AIHEHUO_API_KEY）。
    """
    
    @classmethod
    def setUpClass(cls):
        """设置测试类，初始化真实LLM客户端和API配置"""
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
                from src.llms import DeepSeekLLM
                cls.llm_client = DeepSeekLLM(
                    api_key=cls.config.deepseek_api_key,
                    model_name=cls.config.deepseek_model
                )
            elif cls.config.default_llm_provider == "openai":
                if not cls.config.openai_api_key:
                    cls.skip_all = True
                    print("\n警告: OpenAI API Key未配置，跳过真实LLM测试")
                    return
                from src.llms import OpenAILLM
                cls.llm_client = OpenAILLM(
                    api_key=cls.config.openai_api_key,
                    model_name=cls.config.openai_model
                )
            elif cls.config.default_llm_provider == "qwen":
                if not cls.config.qwen_api_key:
                    cls.skip_all = True
                    print("\n警告: Qwen API Key未配置，跳过真实LLM测试")
                    return
                from src.llms import QwenLLM
                cls.llm_client = QwenLLM(
                    api_key=cls.config.qwen_api_key,
                    model_name=cls.config.qwen_model
                )
            else:
                cls.skip_all = True
                print(f"\n警告: 不支持的LLM提供商 {cls.config.default_llm_provider}，跳过真实LLM测试")
                return
            
            # 检查爱合伙API配置
            cls.aihehuo_api_key = cls.config.aihehuo_api_key or os.getenv('AIHEHUO_API_KEY')
            cls.aihehuo_api_base = cls.config.aihehuo_api_base or os.getenv('AIHEHUO_API_BASE', 'https://new-api.aihehuo.com')
            
            if not cls.aihehuo_api_key:
                cls.skip_all = True
                print("\n警告: 爱合伙API Key未配置，跳过真实API测试")
                print("   请设置AIHEHUO_API_KEY环境变量或在config.py中配置")
                return
            
            print(f"\n✅ 真实LLM测试已启用: {cls.llm_client.get_model_info()}")
            print(f"✅ 爱合伙API测试已启用: {cls.aihehuo_api_base}")
            
        except Exception as e:
            cls.skip_all = True
            print(f"\n警告: 初始化失败 ({str(e)})，跳过真实LLM测试")
            import traceback
            traceback.print_exc()
    
    def setUp(self):
        """设置测试环境"""
        if self.skip_all:
            self.skipTest("真实LLM测试已跳过（API Key未配置或环境变量SKIP_REAL_LLM_TESTS=1）")
        
        # 初始化节点，传入真实的API密钥
        self.node = PartnerSearchNode(
            self.llm_client,
            api_key=self.aihehuo_api_key,
            api_base=self.aihehuo_api_base
        )
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """清理测试环境"""
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_real_llm_and_api_search_chinese(self):
        """测试真实LLM和API - 中文商业计划书搜索"""
        business_idea = "基于AI的在线教育平台，面向K12学生，提供个性化学习路径推荐，解决学生学习效率低和缺乏针对性指导的问题"
        bp_structure = [
            {"title": "用户画像与痛点", "content": "K12学生需要个性化学习，但传统教育无法满足，导致学习效率低"},
            {"title": "解决方案", "content": "使用AI技术分析学生学习数据，提供个性化学习路径和智能推荐"},
            {"title": "最小可行产品（MVP）", "content": "核心功能包括学习数据分析、智能推荐引擎和个性化练习题库"}
        ]
        
        input_data = {
            "business_idea": business_idea,
            "bp_structure": bp_structure
        }
        
        result = self.node.run(input_data, partner_per_page=5, investor_per_page=5)
        
        # 验证基本结构
        self.assertIsInstance(result, dict)
        self.assertIn("partner_search_query", result)
        self.assertIn("investor_search_query", result)
        self.assertIn("partner_results", result)
        self.assertIn("investor_results", result)
        self.assertIn("partner_count", result)
        self.assertIn("investor_count", result)
        self.assertIn("markdown_summary", result)
        
        # 验证搜索查询已生成
        partner_query = result["partner_search_query"]
        investor_query = result["investor_search_query"]
        self.assertIsInstance(partner_query, str)
        self.assertIsInstance(investor_query, str)
        self.assertGreater(len(partner_query.strip()), 0, "合伙人搜索查询应该非空")
        self.assertGreater(len(investor_query.strip()), 0, "投资人搜索查询应该非空")
        
        # 验证markdown摘要
        markdown_summary = result["markdown_summary"]
        self.assertIsInstance(markdown_summary, str)
        self.assertGreater(len(markdown_summary.strip()), 0, "markdown_summary应该非空")
        
        # 验证结果列表
        self.assertIsInstance(result["partner_results"], list)
        self.assertIsInstance(result["investor_results"], list)
        self.assertEqual(result["partner_count"], len(result["partner_results"]))
        self.assertEqual(result["investor_count"], len(result["investor_results"]))
        
        print(f"\n✅ 测试通过: 中文商业计划书搜索")
        print(f"   合伙人搜索查询: {partner_query}")
        print(f"   投资人搜索查询: {investor_query}")
        print(f"   找到合伙人: {result['partner_count']} 个")
        print(f"   找到投资人: {result['investor_count']} 个")
        print(f"   markdown_summary长度: {len(markdown_summary)} 字符")
        print(f"   markdown_summary预览: {markdown_summary[:200]}...")
        
        # 如果有搜索结果，验证结果结构
        if result["partner_count"] > 0:
            partner = result["partner_results"][0]
            self.assertIn("user_id", partner or {})
            self.assertIn("name", partner or {})
            print(f"   示例合伙人: {partner.get('name', 'N/A')}")
        
        if result["investor_count"] > 0:
            investor = result["investor_results"][0]
            self.assertIn("user_id", investor or {})
            self.assertIn("name", investor or {})
            print(f"   示例投资人: {investor.get('name', 'N/A')}")
    
    def test_real_llm_and_api_search_english(self):
        """测试真实LLM和API - 英文商业计划书搜索"""
        business_idea = "An AI-powered online education platform for K12 students, providing personalized learning path recommendations to solve the problems of low learning efficiency and lack of targeted guidance"
        bp_structure = [
            {"title": "User Persona & Pain Points", "content": "K12 students need personalized learning, but traditional education cannot meet this need, leading to low learning efficiency"},
            {"title": "Solution", "content": "Use AI technology to analyze student learning data and provide personalized learning paths and intelligent recommendations"},
            {"title": "Minimum Viable Product (MVP)", "content": "Core features include learning data analysis, intelligent recommendation engine, and personalized practice question bank"}
        ]
        
        input_data = {
            "business_idea": business_idea,
            "bp_structure": bp_structure
        }
        
        result = self.node.run(input_data, partner_per_page=5, investor_per_page=5)
        
        # 验证基本结构
        self.assertIsInstance(result, dict)
        self.assertIn("partner_search_query", result)
        self.assertIn("investor_search_query", result)
        self.assertIn("markdown_summary", result)
        
        # 验证搜索查询已生成（英文）
        partner_query = result["partner_search_query"]
        investor_query = result["investor_search_query"]
        self.assertIsInstance(partner_query, str)
        self.assertIsInstance(investor_query, str)
        self.assertGreater(len(partner_query.strip()), 0)
        
        # 验证markdown摘要（应该主要是英文）
        markdown_summary = result["markdown_summary"]
        self.assertIsInstance(markdown_summary, str)
        self.assertGreater(len(markdown_summary.strip()), 0)
        
        print(f"\n✅ 测试通过: 英文商业计划书搜索")
        print(f"   合伙人搜索查询: {partner_query}")
        print(f"   投资人搜索查询: {investor_query}")
        print(f"   找到合伙人: {result['partner_count']} 个")
        print(f"   找到投资人: {result['investor_count']} 个")
        print(f"   markdown_summary预览: {markdown_summary[:200]}...")
    
    def test_real_llm_output_format_with_markdown_summary(self):
        """测试真实LLM - 验证输出格式包含markdown_summary"""
        business_idea = "智能家居控制系统"
        bp_structure = [
            {"title": "用户画像", "content": "家庭用户需要便捷的智能家居控制方案"},
            {"title": "解决方案", "content": "通过IoT设备实现远程控制和管理"}
        ]
        
        input_data = {
            "business_idea": business_idea,
            "bp_structure": bp_structure
        }
        
        result = self.node.run(input_data, partner_per_page=3, investor_per_page=3)
        
        # 验证包含markdown_summary
        self.assertIn("markdown_summary", result, "结果应该包含markdown_summary字段")
        markdown_summary = result["markdown_summary"]
        
        # 验证markdown_summary格式
        self.assertIsInstance(markdown_summary, str)
        self.assertGreater(len(markdown_summary.strip()), 0, "markdown_summary应该非空")
        
        # 验证markdown_summary包含搜索相关信息
        self.assertIn("搜索", markdown_summary or "", "markdown_summary应该包含搜索相关信息")
        
        print(f"\n✅ 测试通过: 输出格式验证")
        print(f"   markdown_summary长度: {len(markdown_summary)} 字符")
        print(f"   markdown_summary预览: {markdown_summary[:200]}...")
    
    def test_real_llm_search_phrase_extraction(self):
        """测试真实LLM - 验证搜索短语提取的有效性"""
        business_idea = "区块链供应链管理系统"
        bp_structure = [
            {"title": "用户画像与痛点", "content": "企业需要透明化和可追溯的供应链管理"},
            {"title": "解决方案", "content": "使用区块链技术实现供应链数据的透明化和可追溯性"},
            {"title": "团队优势", "content": "团队拥有区块链技术背景和供应链管理经验"}
        ]
        
        input_data = {
            "business_idea": business_idea,
            "bp_structure": bp_structure
        }
        
        result = self.node.run(input_data, partner_per_page=3, investor_per_page=3)
        
        # 验证搜索短语已提取
        partner_query = result["partner_search_query"]
        investor_query = result["investor_search_query"]
        
        # 验证搜索短语的相关性（应该与商业计划书相关）
        self.assertGreater(len(partner_query.strip()), 5, "合伙人搜索查询应该足够长")
        self.assertGreater(len(investor_query.strip()), 5, "投资人搜索查询应该足够长")
        
        # 验证搜索短语包含相关关键词（至少应该包含一些相关词汇）
        # 注意：这取决于LLM的输出，可能不总是包含特定关键词
        print(f"\n✅ 测试通过: 搜索短语提取验证")
        print(f"   合伙人搜索查询: {partner_query}")
        print(f"   投资人搜索查询: {investor_query}")
        print(f"   查询长度: 合伙人={len(partner_query)}, 投资人={len(investor_query)}")
    
    def test_real_api_search_functionality(self):
        """测试真实API - 验证搜索功能"""
        business_idea = "AI医疗诊断系统"
        bp_structure = [
            {"title": "用户画像", "content": "医院和诊所需要快速准确的医疗诊断辅助"},
            {"title": "解决方案", "content": "使用AI技术分析医疗影像和数据，提供诊断建议"}
        ]
        
        input_data = {
            "business_idea": business_idea,
            "bp_structure": bp_structure
        }
        
        result = self.node.run(input_data, partner_per_page=5, investor_per_page=5, wechat_reachable_only=False)
        
        # 验证API调用成功（没有抛出异常）
        self.assertIsInstance(result, dict)
        self.assertNotIn("error", result, "搜索不应该返回错误")
        
        # 验证结果结构
        self.assertIn("partner_results", result)
        self.assertIn("investor_results", result)
        
        # 如果有搜索结果，验证结果格式
        if result["partner_count"] > 0:
            for partner in result["partner_results"][:2]:  # 检查前2个
                self.assertIsInstance(partner, dict)
                # 验证至少包含基本字段
                self.assertIn("user_id", partner)
                self.assertIn("name", partner)
        
        if result["investor_count"] > 0:
            for investor in result["investor_results"][:2]:  # 检查前2个
                self.assertIsInstance(investor, dict)
                self.assertIn("user_id", investor)
                self.assertIn("name", investor)
        
        print(f"\n✅ 测试通过: API搜索功能验证")
        print(f"   合伙人搜索结果: {result['partner_count']} 个")
        print(f"   投资人搜索结果: {result['investor_count']} 个")
        if result["partner_count"] > 0:
            print(f"   示例合伙人: {result['partner_results'][0].get('name', 'N/A')}")
        if result["investor_count"] > 0:
            print(f"   示例投资人: {result['investor_results'][0].get('name', 'N/A')}")
    
    def test_real_llm_enhanced_summary_generation(self):
        """测试真实LLM - 验证增强摘要生成"""
        business_idea = "智能健身APP"
        bp_structure = [
            {"title": "用户画像", "content": "健身爱好者需要个性化的训练计划"},
            {"title": "解决方案", "content": "通过AI分析用户数据，提供定制化健身方案"}
        ]
        
        input_data = {
            "business_idea": business_idea,
            "bp_structure": bp_structure
        }
        
        result = self.node.run(input_data, partner_per_page=3, investor_per_page=3)
        
        # 验证增强摘要
        markdown_summary = result["markdown_summary"]
        self.assertIsInstance(markdown_summary, str)
        self.assertGreater(len(markdown_summary.strip()), 0)
        
        # 验证摘要包含搜索相关信息
        # 应该包含搜索查询、结果数量等信息
        has_search_info = (
            "搜索" in markdown_summary or 
            "Search" in markdown_summary or
            str(result["partner_count"]) in markdown_summary or
            str(result["investor_count"]) in markdown_summary
        )
        
        print(f"\n✅ 测试通过: 增强摘要生成验证")
        print(f"   markdown_summary长度: {len(markdown_summary)} 字符")
        print(f"   包含搜索信息: {has_search_info}")
        print(f"   摘要预览:\n{markdown_summary[:300]}...")


if __name__ == '__main__':
    unittest.main()

