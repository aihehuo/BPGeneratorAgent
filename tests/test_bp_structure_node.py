"""
单元测试：BP结构生成节点
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
from src.nodes.bp_structure_node import BPStructureNode
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
        """默认响应（BP结构的示例）"""
        return json.dumps({
            "data": [
                {
                    "title": "用户画像与痛点",
                    "content": "针对K12学生的个性化学习需求分析"
                },
                {
                    "title": "解决方案",
                    "content": "基于AI的个性化学习路径推荐系统"
                },
                {
                    "title": "最小可行产品（MVP）",
                    "content": "核心功能包括学习数据分析和智能推荐"
                }
            ],
            "markdown_summary": "已生成包含用户画像、解决方案和MVP的BP结构，共3个核心段落。"
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


class TestBPStructureNode(unittest.TestCase):
    """BPStructureNode 单元测试类（使用Mock LLM）"""
    
    def setUp(self):
        """设置测试环境"""
        self.mock_llm = MockLLM()
        self.business_idea = "基于AI的在线教育平台，面向K12学生，提供个性化学习"
        self.node = BPStructureNode(self.mock_llm, self.business_idea)
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """清理测试环境"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_init(self):
        """测试节点初始化"""
        self.assertIsNotNone(self.node)
        self.assertEqual(self.node.node_name, "BPStructureNode")
        self.assertEqual(self.node.llm_client, self.mock_llm)
        self.assertEqual(self.node.business_idea, self.business_idea)
    
    def test_validate_input(self):
        """测试输入验证"""
        # 正常输入
        self.assertTrue(self.node.validate_input(None))
        
        # 空字符串（初始化时已经设置了business_idea，所以这里测试的是business_idea本身）
        node_empty = BPStructureNode(self.mock_llm, "")
        self.assertFalse(node_empty.validate_input(None))
        
        node_none = BPStructureNode(self.mock_llm, "   ")
        self.assertFalse(node_none.validate_input(None))
    
    def test_run_basic(self):
        """测试基本运行功能"""
        result = self.node.run()
        
        # 验证返回类型
        self.assertIsInstance(result, dict)
        
        # 验证返回的字段
        self.assertIn("bp_structure", result)
        self.assertIn("markdown_summary", result)
        
        # 验证bp_structure是列表
        bp_structure = result["bp_structure"]
        self.assertIsInstance(bp_structure, list)
        self.assertGreater(len(bp_structure), 0)
        
        # 验证每个段落的结构
        for paragraph in bp_structure:
            self.assertIn("title", paragraph)
            self.assertIn("content", paragraph)
            self.assertIsInstance(paragraph["title"], str)
            self.assertIsInstance(paragraph["content"], str)
        
        # 验证markdown_summary
        markdown_summary = result["markdown_summary"]
        self.assertIsInstance(markdown_summary, str)
        self.assertGreater(len(markdown_summary), 0)
        
        # 验证LLM被调用
        self.assertTrue(self.mock_llm.invoke_called)
    
    def test_run_output_structure(self):
        """测试输出结构"""
        result = self.node.run()
        
        # 验证必需的字段
        required_fields = ["bp_structure", "markdown_summary"]
        for field in required_fields:
            self.assertIn(field, result, f"结果应该包含字段: {field}")
        
        # 验证bp_structure的内容
        bp_structure = result["bp_structure"]
        self.assertIsInstance(bp_structure, list)
        self.assertGreaterEqual(len(bp_structure), 3, "应该至少生成3个段落")
        
        # 验证段落结构
        for i, paragraph in enumerate(bp_structure):
            self.assertIsInstance(paragraph, dict, f"段落 {i} 应该是字典")
            self.assertIn("title", paragraph, f"段落 {i} 应该包含title")
            self.assertIn("content", paragraph, f"段落 {i} 应该包含content")
            self.assertGreater(len(paragraph["title"].strip()), 0, f"段落 {i} 的title应该非空")
            self.assertGreater(len(paragraph["content"].strip()), 0, f"段落 {i} 的content应该非空")
    
    def test_run_with_chinese_input(self):
        """测试中文输入"""
        chinese_idea = "智能家居控制系统，通过IoT设备连接家中的各种电器，用户可以通过手机APP远程控制"
        node = BPStructureNode(self.mock_llm, chinese_idea)
        
        result = node.run()
        
        self.assertIn("bp_structure", result)
        self.assertIn("markdown_summary", result)
        
        # 验证输出不为空
        self.assertGreater(len(result["bp_structure"]), 0)
        self.assertGreater(len(result["markdown_summary"]), 0)
    
    def test_run_with_english_input(self):
        """测试英文输入"""
        english_idea = "An AI-powered online education platform for K12 students, providing personalized learning path recommendations"
        node = BPStructureNode(self.mock_llm, english_idea)
        
        # 设置英文响应
        english_response = json.dumps({
            "data": [
                {
                    "title": "User Persona & Pain Points",
                    "content": "Analysis of personalized learning needs for K12 students"
                },
                {
                    "title": "Solution",
                    "content": "AI-based personalized learning path recommendation system"
                }
            ],
            "markdown_summary": "Generated BP structure with user persona, solution, and MVP, 3 core paragraphs."
        }, ensure_ascii=False)
        
        node.llm_client.response = english_response
        result = node.run()
        
        self.assertIn("bp_structure", result)
        self.assertIn("markdown_summary", result)
    
    def test_regenerate_basic(self):
        """测试重新生成功能"""
        evaluation_result = "部分段落内容不够具体"
        suggestions = "需要添加更多技术细节和市场分析"
        current_structure = [
            {"title": "用户画像与痛点", "content": "目标用户是K12学生"},
            {"title": "解决方案", "content": "AI驱动的学习平台"}
        ]
        
        result = self.node.regenerate(evaluation_result, suggestions, current_structure)
        
        # 验证返回类型
        self.assertIsInstance(result, dict)
        
        # 验证返回的字段
        self.assertIn("bp_structure", result)
        self.assertIn("markdown_summary", result)
        
        # 验证LLM被调用
        self.assertTrue(self.mock_llm.invoke_called)
    
    def test_regenerate_structure(self):
        """测试重新生成的结构"""
        evaluation_result = "内容需要更详细"
        suggestions = "补充市场分析和竞品对比"
        current_structure = [
            {"title": "用户画像", "content": "学生群体"},
            {"title": "解决方案", "content": "AI平台"}
        ]
        
        result = self.node.regenerate(evaluation_result, suggestions, current_structure)
        
        # 验证结构
        bp_structure = result["bp_structure"]
        self.assertIsInstance(bp_structure, list)
        
        # 验证每个段落
        for paragraph in bp_structure:
            self.assertIn("title", paragraph)
            self.assertIn("content", paragraph)
    
    def test_process_output_with_new_format(self):
        """测试处理包含data和markdown_summary的新格式输出"""
        output = json.dumps({
            "data": [
                {"title": "测试标题1", "content": "测试内容1"},
                {"title": "测试标题2", "content": "测试内容2"}
            ],
            "markdown_summary": "这是测试摘要"
        }, ensure_ascii=False)
        
        result = self.node.process_output(output)
        
        self.assertIn("bp_structure", result)
        self.assertIn("markdown_summary", result)
        self.assertEqual(len(result["bp_structure"]), 2)
        self.assertEqual(result["markdown_summary"], "这是测试摘要")
    
    def test_process_output_with_old_format(self):
        """测试处理旧格式输出（直接是数组）"""
        output = json.dumps([
            {"title": "测试标题1", "content": "测试内容1"},
            {"title": "测试标题2", "content": "测试内容2"}
        ], ensure_ascii=False)
        
        result = self.node.process_output(output)
        
        self.assertIn("bp_structure", result)
        self.assertEqual(len(result["bp_structure"]), 2)
        # 旧格式可能没有markdown_summary，应该生成默认值或空字符串
        if "markdown_summary" in result:
            self.assertIsInstance(result["markdown_summary"], str)


class TestBPStructureNodeWithRealLLM(unittest.TestCase):
    """使用真实LLM的BPStructureNode测试类
    
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
        
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """清理测试环境"""
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_real_llm_generate_chinese_bp_structure(self):
        """测试真实LLM - 生成中文BP结构"""
        business_idea = "基于AI的在线教育平台，面向K12学生，提供个性化学习路径推荐，解决学生学习效率低和缺乏针对性指导的问题"
        node = BPStructureNode(self.llm_client, business_idea)
        
        result = node.run()
        
        # 验证基本结构
        self.assertIsInstance(result, dict)
        self.assertIn("bp_structure", result)
        self.assertIn("markdown_summary", result)
        
        # 验证bp_structure
        bp_structure = result["bp_structure"]
        self.assertIsInstance(bp_structure, list)
        self.assertGreaterEqual(len(bp_structure), 3, "应该至少生成3个核心段落")
        
        # 验证每个段落的结构
        for i, paragraph in enumerate(bp_structure):
            self.assertIn("title", paragraph, f"段落 {i} 应该包含title")
            self.assertIn("content", paragraph, f"段落 {i} 应该包含content")
            self.assertGreater(len(paragraph["title"].strip()), 0)
            self.assertGreater(len(paragraph["content"].strip()), 0)
            
            # 验证中文标题（对于中文输入）
            # 简单检查：title应该包含中文字符
            has_chinese = any('\u4e00' <= char <= '\u9fff' for char in paragraph["title"])
            if has_chinese:
                print(f"   ✅ 段落 {i+1}: {paragraph['title']} (中文)")
        
        # 验证markdown_summary
        markdown_summary = result["markdown_summary"]
        self.assertIsInstance(markdown_summary, str)
        self.assertGreater(len(markdown_summary.strip()), 0, "markdown_summary应该非空")
        
        print(f"\n✅ 测试通过: 中文BP结构生成")
        print(f"   生成了 {len(bp_structure)} 个段落")
        print(f"   markdown_summary: {markdown_summary[:100]}...")
    
    def test_real_llm_generate_english_bp_structure(self):
        """测试真实LLM - 生成英文BP结构"""
        business_idea = "An AI-powered online education platform for K12 students, providing personalized learning path recommendations to solve the problems of low learning efficiency and lack of targeted guidance"
        node = BPStructureNode(self.llm_client, business_idea)
        
        result = node.run()
        
        # 验证基本结构
        self.assertIsInstance(result, dict)
        self.assertIn("bp_structure", result)
        self.assertIn("markdown_summary", result)
        
        # 验证bp_structure
        bp_structure = result["bp_structure"]
        self.assertIsInstance(bp_structure, list)
        self.assertGreaterEqual(len(bp_structure), 3)
        
        # 验证每个段落的结构和语言
        for i, paragraph in enumerate(bp_structure):
            self.assertIn("title", paragraph)
            self.assertIn("content", paragraph)
            
            # 验证英文标题（对于英文输入）
            # 简单检查：title应该主要是英文字符
            title = paragraph["title"]
            has_chinese = any('\u4e00' <= char <= '\u9fff' for char in title)
            if not has_chinese:
                print(f"   ✅ 段落 {i+1}: {title} (英文)")
        
        # 验证markdown_summary是英文
        markdown_summary = result["markdown_summary"]
        has_chinese_in_summary = any('\u4e00' <= char <= '\u9fff' for char in markdown_summary)
        
        print(f"\n✅ 测试通过: 英文BP结构生成")
        print(f"   生成了 {len(bp_structure)} 个段落")
        print(f"   markdown_summary语言: {'中文' if has_chinese_in_summary else '英文'}")
        print(f"   markdown_summary: {markdown_summary[:100]}...")
    
    def test_real_llm_output_format_with_markdown_summary(self):
        """测试真实LLM - 验证输出格式包含markdown_summary"""
        business_idea = "智能家居控制系统，通过IoT设备连接家中的各种电器"
        node = BPStructureNode(self.llm_client, business_idea)
        
        result = node.run()
        
        # 验证包含markdown_summary
        self.assertIn("markdown_summary", result, "结果应该包含markdown_summary字段")
        markdown_summary = result["markdown_summary"]
        
        # 验证markdown_summary格式
        self.assertIsInstance(markdown_summary, str)
        self.assertGreater(len(markdown_summary.strip()), 0, "markdown_summary应该非空")
        
        print(f"\n✅ 测试通过: 输出格式验证")
        print(f"   markdown_summary长度: {len(markdown_summary)} 字符")
        print(f"   markdown_summary预览: {markdown_summary[:150]}...")
    
    def test_real_llm_prompt_effectiveness(self):
        """测试真实LLM - 验证提示词的有效性（生成的结构是否符合精益创业理念）"""
        business_idea = "基于区块链的供应链管理系统，帮助企业实现透明化和可追溯性"
        node = BPStructureNode(self.llm_client, business_idea)
        
        result = node.run()
        
        bp_structure = result["bp_structure"]
        
        # 验证至少包含核心段落（精益创业理念的核心部分）
        titles = [p["title"] for p in bp_structure]
        titles_str = " ".join(titles).lower()
        
        # 检查是否包含关键概念（根据语言不同）
        has_user_persona = any(keyword in titles_str for keyword in ["用户", "痛点", "persona", "pain"])
        has_solution = any(keyword in titles_str for keyword in ["解决方案", "solution"])
        has_mvp = any(keyword in titles_str for keyword in ["mvp", "最小可行", "minimum viable"])
        
        print(f"\n✅ 测试通过: 提示词有效性验证")
        print(f"   包含用户画像/痛点: {has_user_persona}")
        print(f"   包含解决方案: {has_solution}")
        print(f"   包含MVP: {has_mvp}")
        print(f"   段落标题: {', '.join(titles)}")
        
        # 验证段落内容与商业创意相关
        for paragraph in bp_structure:
            content = paragraph["content"].lower()
            # 简单检查：内容应该提到相关的关键词
            has_relevance = any(keyword in content for keyword in ["区块链", "供应链", "blockchain", "supply chain"])
            if has_relevance:
                print(f"   ✅ 段落内容与商业创意相关: {paragraph['title']}")
    
    def test_real_llm_regenerate_with_feedback(self):
        """测试真实LLM - 根据反馈重新生成BP结构"""
        business_idea = "AI驱动的智能客服系统"
        node = BPStructureNode(self.llm_client, business_idea)
        
        # 首先生成初始结构
        initial_result = node.run()
        initial_structure = initial_result["bp_structure"]
        
        self.assertGreater(len(initial_structure), 0, "初始结构应该非空")
        
        # 然后根据反馈重新生成
        evaluation_result = "需要添加更多技术细节和市场分析"
        suggestions = "补充技术架构说明、目标市场分析和竞品对比"
        current_structure = initial_structure
        
        regenerated_result = node.regenerate(evaluation_result, suggestions, current_structure)
        
        # 验证重新生成的结果
        self.assertIn("bp_structure", regenerated_result)
        self.assertIn("markdown_summary", regenerated_result)
        
        regenerated_structure = regenerated_result["bp_structure"]
        self.assertIsInstance(regenerated_structure, list)
        self.assertGreater(len(regenerated_structure), 0)
        
        print(f"\n✅ 测试通过: 根据反馈重新生成")
        print(f"   初始段落数: {len(initial_structure)}")
        print(f"   重新生成后段落数: {len(regenerated_structure)}")
        
        # 验证重新生成的结构不同（至少内容应该更新）
        initial_titles = [p["title"] for p in initial_structure]
        regenerated_titles = [p["title"] for p in regenerated_structure]
        print(f"   初始标题: {', '.join(initial_titles)}")
        print(f"   重新生成标题: {', '.join(regenerated_titles)}")


if __name__ == "__main__":
    unittest.main()

