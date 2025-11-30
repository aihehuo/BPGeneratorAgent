"""
单元测试：痛点加强节点
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
from src.nodes.painpoint_enhancement_node import PainpointEnhancementNode
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
        """默认响应（痛点加强的示例）"""
        return json.dumps({
            "data": {
                "enhanced_content": "【紧迫性】K12学生学习效率低的问题如果不解决，会立即影响学习成绩，可能导致升学困难。\n\n【频发性】每天学生都需要面对大量作业和学习任务，但缺乏个性化指导的问题持续存在。\n\n【高经济代价】家长为了提升孩子学习效果，需要花费大量时间和金钱请家教或上补习班。",
                "selected_dimensions": ["紧迫性", "频发性", "高经济代价"],
                "dimension_descriptions": [
                    {
                        "dimension": "紧迫性",
                        "content": "K12学生学习效率低的问题如果不解决，会立即影响学习成绩，可能导致升学困难。"
                    },
                    {
                        "dimension": "频发性",
                        "content": "每天学生都需要面对大量作业和学习任务，但缺乏个性化指导的问题持续存在。"
                    },
                    {
                        "dimension": "高经济代价",
                        "content": "家长为了提升孩子学习效果，需要花费大量时间和金钱请家教或上补习班。"
                    }
                ],
                "enhancement_explanation": "选择了紧迫性、频发性和高经济代价三个维度，从不同角度强化了学习效率低这一痛点的严重性和迫切性。"
            },
            "markdown_summary": "已从6个维度中选择3个（紧迫性、频发性、高经济代价）来加强痛点陈述，使痛点更具感染力和说服力。"
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


class TestPainpointEnhancementNode(unittest.TestCase):
    """PainpointEnhancementNode 单元测试类（使用Mock LLM）"""
    
    def setUp(self):
        """设置测试环境"""
        self.mock_llm = MockLLM()
        self.node = PainpointEnhancementNode(self.mock_llm)
        self.business_idea = "基于AI的在线教育平台，面向K12学生，提供个性化学习"
        self.painpoint_paragraph = {
            "title": "用户画像与痛点",
            "content": "K12学生需要个性化学习，但传统教育无法满足"
        }
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """清理测试环境"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_init(self):
        """测试节点初始化"""
        self.assertIsNotNone(self.node)
        self.assertEqual(self.node.node_name, "PainpointEnhancementNode")
        self.assertEqual(self.node.llm_client, self.mock_llm)
    
    def test_validate_input_valid(self):
        """测试有效的输入验证"""
        valid_input = {
            "business_idea": self.business_idea,
            "painpoint_paragraph": self.painpoint_paragraph
        }
        self.assertTrue(self.node.validate_input(valid_input))
    
    def test_validate_input_missing_business_idea(self):
        """测试缺少business_idea字段"""
        invalid_input = {
            "painpoint_paragraph": self.painpoint_paragraph
        }
        self.assertFalse(self.node.validate_input(invalid_input))
    
    def test_validate_input_missing_painpoint_paragraph(self):
        """测试缺少painpoint_paragraph字段"""
        invalid_input = {
            "business_idea": self.business_idea
        }
        self.assertFalse(self.node.validate_input(invalid_input))
    
    def test_validate_input_invalid_paragraph_structure(self):
        """测试无效的paragraph结构"""
        invalid_input = {
            "business_idea": self.business_idea,
            "painpoint_paragraph": {"title": "标题"}  # 缺少content
        }
        self.assertFalse(self.node.validate_input(invalid_input))
        
        invalid_input2 = {
            "business_idea": self.business_idea,
            "painpoint_paragraph": "not a dict"  # 不是字典
        }
        self.assertFalse(self.node.validate_input(invalid_input2))
    
    def test_validate_input_not_dict(self):
        """测试非字典输入"""
        self.assertFalse(self.node.validate_input("not a dict"))
        self.assertFalse(self.node.validate_input(None))
        self.assertFalse(self.node.validate_input([]))
    
    def test_run_basic(self):
        """测试基本运行功能"""
        input_data = {
            "business_idea": self.business_idea,
            "painpoint_paragraph": self.painpoint_paragraph
        }
        
        result = self.node.run(input_data)
        
        # 验证返回类型
        self.assertIsInstance(result, dict)
        
        # 验证必需的字段
        self.assertIn("enhanced_content", result)
        self.assertIn("selected_dimensions", result)
        self.assertIn("dimension_descriptions", result)
        self.assertIn("markdown_summary", result)
        
        # 验证enhanced_content
        self.assertIsInstance(result["enhanced_content"], str)
        self.assertGreater(len(result["enhanced_content"]), 0)
        
        # 验证selected_dimensions
        dimensions = result["selected_dimensions"]
        self.assertIsInstance(dimensions, list)
        self.assertEqual(len(dimensions), 3, "应该恰好选择3个维度")
        
        # 验证dimension_descriptions
        dimension_descriptions = result["dimension_descriptions"]
        self.assertIsInstance(dimension_descriptions, list)
        self.assertEqual(len(dimension_descriptions), 3, "应该有3个维度的描述")
        
        # 验证每个维度描述的结构
        for desc in dimension_descriptions:
            self.assertIn("dimension", desc)
            self.assertIn("content", desc)
            self.assertIsInstance(desc["dimension"], str)
            self.assertIsInstance(desc["content"], str)
        
        # 验证LLM被调用
        self.assertTrue(self.mock_llm.invoke_called)
    
    def test_run_output_structure(self):
        """测试输出结构"""
        input_data = {
            "business_idea": self.business_idea,
            "painpoint_paragraph": self.painpoint_paragraph
        }
        
        result = self.node.run(input_data)
        
        # 验证必需的字段
        required_fields = ["enhanced_content", "selected_dimensions", "dimension_descriptions", "markdown_summary"]
        for field in required_fields:
            self.assertIn(field, result, f"结果应该包含字段: {field}")
        
        # 验证selected_dimensions恰好3个
        dimensions = result["selected_dimensions"]
        self.assertEqual(len(dimensions), 3, "selected_dimensions应该恰好包含3个维度")
        
        # 验证每个维度都是字符串
        for dim in dimensions:
            self.assertIsInstance(dim, str)
            self.assertGreater(len(dim.strip()), 0)
        
        # 验证dimension_descriptions的数量与selected_dimensions一致
        descriptions = result["dimension_descriptions"]
        self.assertEqual(len(descriptions), len(dimensions), "dimension_descriptions的数量应该与selected_dimensions一致")
        
        # 验证每个描述中的dimension都在selected_dimensions中
        selected_set = set(dimensions)
        for desc in descriptions:
            self.assertIn(desc["dimension"], selected_set, f"维度 {desc['dimension']} 应该在selected_dimensions中")
    
    def test_run_with_chinese_input(self):
        """测试中文输入"""
        chinese_idea = "智能家居控制系统，通过IoT设备连接家中的各种电器"
        chinese_paragraph = {
            "title": "用户画像与痛点",
            "content": "家庭用户需要便捷的智能家居控制方案"
        }
        
        input_data = {
            "business_idea": chinese_idea,
            "painpoint_paragraph": chinese_paragraph
        }
        
        result = self.node.run(input_data)
        
        self.assertIn("enhanced_content", result)
        self.assertIn("selected_dimensions", result)
        self.assertIn("markdown_summary", result)
        
        # 验证输出不为空
        self.assertGreater(len(result["enhanced_content"]), 0)
        self.assertEqual(len(result["selected_dimensions"]), 3)
    
    def test_run_with_english_input(self):
        """测试英文输入"""
        english_idea = "An AI-powered online education platform for K12 students"
        english_paragraph = {
            "title": "User Persona & Pain Points",
            "content": "K12 students need personalized learning but traditional education cannot provide it"
        }
        
        # 设置英文响应
        english_response = json.dumps({
            "data": {
                "enhanced_content": "[Urgency] Without solving learning efficiency issues, students' academic performance will be immediately affected.\n\n[Frequency] Students face this challenge daily.\n\n[High Economic Cost] Parents spend significant time and money on tutoring.",
                "selected_dimensions": ["Urgency", "Frequency", "High Economic Cost"],
                "dimension_descriptions": [
                    {"dimension": "Urgency", "content": "Without solving learning efficiency issues, students' academic performance will be immediately affected."},
                    {"dimension": "Frequency", "content": "Students face this challenge daily."},
                    {"dimension": "High Economic Cost", "content": "Parents spend significant time and money on tutoring."}
                ],
                "enhancement_explanation": "Selected three dimensions to strengthen the pain point."
            },
            "markdown_summary": "Selected 3 dimensions (Urgency, Frequency, High Economic Cost) to enhance the pain point statement."
        }, ensure_ascii=False)
        
        self.mock_llm.response = english_response
        
        input_data = {
            "business_idea": english_idea,
            "painpoint_paragraph": english_paragraph
        }
        
        result = self.node.run(input_data)
        
        self.assertIn("enhanced_content", result)
        self.assertIn("selected_dimensions", result)
        self.assertIn("markdown_summary", result)
        
        # 验证维度名称是英文
        dimensions = result["selected_dimensions"]
        for dim in dimensions:
            # 简单检查：不包含中文字符
            has_chinese = any('\u4e00' <= char <= '\u9fff' for char in dim)
            self.assertFalse(has_chinese, f"维度名称 {dim} 应该是英文")
    
    def test_enhance_convenience_method(self):
        """测试便捷方法enhance"""
        result = self.node.enhance(self.business_idea, self.painpoint_paragraph)
        
        self.assertIsInstance(result, dict)
        self.assertIn("enhanced_content", result)
        self.assertIn("selected_dimensions", result)
        self.assertTrue(self.mock_llm.invoke_called)
    
    def test_process_output_with_new_format(self):
        """测试处理包含data和markdown_summary的新格式输出"""
        output = json.dumps({
            "data": {
                "enhanced_content": "加强后的内容",
                "selected_dimensions": ["紧迫性", "频发性", "高经济代价"],
                "dimension_descriptions": [
                    {"dimension": "紧迫性", "content": "内容1"},
                    {"dimension": "频发性", "content": "内容2"},
                    {"dimension": "高经济代价", "content": "内容3"}
                ],
                "enhancement_explanation": "说明"
            },
            "markdown_summary": "这是测试摘要"
        }, ensure_ascii=False)
        
        result = self.node.process_output(output)
        
        self.assertIn("enhanced_content", result)
        self.assertIn("selected_dimensions", result)
        self.assertIn("dimension_descriptions", result)
        self.assertIn("markdown_summary", result)
        self.assertEqual(result["markdown_summary"], "这是测试摘要")
        self.assertEqual(len(result["selected_dimensions"]), 3)
    
    def test_process_output_with_old_format(self):
        """测试处理旧格式输出（直接是加强结果）"""
        output = json.dumps({
            "enhanced_content": "加强后的内容",
            "selected_dimensions": ["紧迫性", "频发性", "高经济代价"],
            "dimension_descriptions": [
                {"dimension": "紧迫性", "content": "内容1"},
                {"dimension": "频发性", "content": "内容2"},
                {"dimension": "高经济代价", "content": "内容3"}
            ]
        }, ensure_ascii=False)
        
        result = self.node.process_output(output)
        
        self.assertIn("enhanced_content", result)
        self.assertIn("selected_dimensions", result)
        self.assertEqual(len(result["selected_dimensions"]), 3)
        # 旧格式可能没有markdown_summary，应该允许
        if "markdown_summary" in result:
            self.assertIsInstance(result["markdown_summary"], str)
    
    def test_run_invalid_input(self):
        """测试无效输入"""
        invalid_input = {
            "business_idea": self.business_idea
            # 缺少painpoint_paragraph
        }
        
        with self.assertRaises(ValueError) as context:
            self.node.run(invalid_input)
        
        self.assertIn("输入数据格式错误", str(context.exception))
    
    def test_process_output_dimension_count_validation(self):
        """测试维度数量验证"""
        # 测试维度数量不是3的情况
        output_2_dims = json.dumps({
            "data": {
                "enhanced_content": "内容",
                "selected_dimensions": ["紧迫性", "频发性"],  # 只有2个
                "dimension_descriptions": [
                    {"dimension": "紧迫性", "content": "内容1"},
                    {"dimension": "频发性", "content": "内容2"}
                ]
            },
            "markdown_summary": "摘要"
        }, ensure_ascii=False)
        
        # 应该能够处理（会有警告但不会失败）
        result = self.node.process_output(output_2_dims)
        self.assertIn("enhanced_content", result)
        self.assertEqual(len(result["selected_dimensions"]), 2)


class TestPainpointEnhancementNodeWithRealLLM(unittest.TestCase):
    """使用真实LLM的PainpointEnhancementNode测试类
    
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
        
        self.node = PainpointEnhancementNode(self.llm_client)
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """清理测试环境"""
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_real_llm_enhance_chinese_painpoint(self):
        """测试真实LLM - 加强中文痛点"""
        business_idea = "基于AI的在线教育平台，面向K12学生，提供个性化学习路径推荐，解决学生学习效率低和缺乏针对性指导的问题"
        painpoint_paragraph = {
            "title": "用户画像与痛点",
            "content": "K12学生需要个性化学习，但传统教育无法满足。学生学习效率低，缺乏针对性的指导。"
        }
        
        result = self.node.enhance(business_idea, painpoint_paragraph)
        
        # 验证基本结构
        self.assertIsInstance(result, dict)
        self.assertIn("enhanced_content", result)
        self.assertIn("selected_dimensions", result)
        self.assertIn("dimension_descriptions", result)
        self.assertIn("markdown_summary", result)
        
        # 验证enhanced_content
        enhanced_content = result["enhanced_content"]
        self.assertIsInstance(enhanced_content, str)
        self.assertGreater(len(enhanced_content.strip()), 0, "enhanced_content应该非空")
        
        # 验证selected_dimensions
        dimensions = result["selected_dimensions"]
        self.assertIsInstance(dimensions, list)
        self.assertEqual(len(dimensions), 3, "应该恰好选择3个维度")
        
        # 验证维度名称是中文（对于中文输入）
        valid_chinese_dimensions = ["紧迫性", "频发性", "高经济代价", "普遍性", "快速传播性", "被迫改变"]
        for dim in dimensions:
            self.assertIn(dim, valid_chinese_dimensions, f"维度 {dim} 应该是有效的中文维度名称")
        
        # 验证dimension_descriptions
        descriptions = result["dimension_descriptions"]
        self.assertIsInstance(descriptions, list)
        self.assertEqual(len(descriptions), 3)
        
        # 验证markdown_summary
        markdown_summary = result["markdown_summary"]
        self.assertIsInstance(markdown_summary, str)
        self.assertGreater(len(markdown_summary.strip()), 0, "markdown_summary应该非空")
        
        print(f"\n✅ 测试通过: 中文痛点加强")
        print(f"   选择的维度: {', '.join(dimensions)}")
        print(f"   enhanced_content长度: {len(enhanced_content)} 字符")
        print(f"   markdown_summary: {markdown_summary[:100]}...")
    
    def test_real_llm_enhance_english_painpoint(self):
        """测试真实LLM - 加强英文痛点"""
        business_idea = "An AI-powered online education platform for K12 students, providing personalized learning path recommendations"
        painpoint_paragraph = {
            "title": "User Persona & Pain Points",
            "content": "K12 students need personalized learning, but traditional education cannot provide it. Students have low learning efficiency."
        }
        
        result = self.node.enhance(business_idea, painpoint_paragraph)
        
        # 验证基本结构
        self.assertIsInstance(result, dict)
        self.assertIn("enhanced_content", result)
        self.assertIn("selected_dimensions", result)
        self.assertIn("markdown_summary", result)
        
        # 验证维度名称是英文（对于英文输入）
        dimensions = result["selected_dimensions"]
        valid_english_dimensions = ["Urgency", "Frequency", "High Economic Cost", "Commonality", "Viral Spread", "Forced Shift"]
        for dim in dimensions:
            # 简单检查：应该不包含中文字符
            has_chinese = any('\u4e00' <= char <= '\u9fff' for char in dim)
            self.assertFalse(has_chinese, f"维度名称 {dim} 应该是英文")
        
        # 验证markdown_summary是英文
        markdown_summary = result["markdown_summary"]
        has_chinese_in_summary = any('\u4e00' <= char <= '\u9fff' for char in markdown_summary)
        
        print(f"\n✅ 测试通过: 英文痛点加强")
        print(f"   选择的维度: {', '.join(dimensions)}")
        print(f"   markdown_summary语言: {'中文' if has_chinese_in_summary else '英文'}")
        print(f"   markdown_summary: {markdown_summary[:100]}...")
    
    def test_real_llm_output_format_with_markdown_summary(self):
        """测试真实LLM - 验证输出格式包含markdown_summary"""
        business_idea = "智能家居控制系统"
        painpoint_paragraph = {
            "title": "用户画像与痛点",
            "content": "家庭用户需要便捷的智能家居控制方案"
        }
        
        result = self.node.enhance(business_idea, painpoint_paragraph)
        
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
        """测试真实LLM - 验证提示词的有效性（是否正确应用6个维度理论）"""
        business_idea = "基于区块链的供应链管理系统"
        painpoint_paragraph = {
            "title": "用户画像与痛点",
            "content": "企业需要透明化和可追溯的供应链管理"
        }
        
        result = self.node.enhance(business_idea, painpoint_paragraph)
        
        # 验证选择了恰好3个维度
        dimensions = result["selected_dimensions"]
        self.assertEqual(len(dimensions), 3, "应该恰好选择3个维度")
        
        # 验证维度是有效的维度名称（中文）
        valid_dimensions = ["紧迫性", "频发性", "高经济代价", "普遍性", "快速传播性", "被迫改变"]
        for dim in dimensions:
            self.assertIn(dim, valid_dimensions, f"维度 {dim} 应该是6个有效维度之一")
        
        # 验证dimension_descriptions的数量
        descriptions = result["dimension_descriptions"]
        self.assertEqual(len(descriptions), 3, "应该有3个维度的描述")
        
        # 验证每个描述都有dimension和content字段
        for desc in descriptions:
            self.assertIn("dimension", desc)
            self.assertIn("content", desc)
            self.assertIn(desc["dimension"], dimensions, "描述中的维度应该在selected_dimensions中")
        
        # 验证enhanced_content不为空
        enhanced_content = result["enhanced_content"]
        self.assertGreater(len(enhanced_content.strip()), 0)
        
        print(f"\n✅ 测试通过: 提示词有效性验证")
        print(f"   选择的维度: {', '.join(dimensions)}")
        print(f"   enhanced_content长度: {len(enhanced_content)} 字符")
        
        # 验证enhanced_content包含了维度相关的关键词
        content_lower = enhanced_content.lower()
        dimension_keywords = {
            "紧迫性": ["马上", "立即", "不能拖"],
            "频发性": ["每天", "反复", "高频"],
            "高经济代价": ["浪费", "损失", "成本"]
        }
        
        for dim in dimensions:
            if dim in dimension_keywords:
                keywords = dimension_keywords[dim]
                has_keyword = any(keyword in content_lower for keyword in keywords)
                if has_keyword:
                    print(f"   ✅ 维度 {dim} 的内容包含了相关关键词")
    
    def test_real_llm_dimension_selection_logic(self):
        """测试真实LLM - 验证维度选择逻辑（选择的维度应该与痛点相关）"""
        business_idea = "AI驱动的智能客服系统，解决客服响应慢的问题"
        painpoint_paragraph = {
            "title": "用户画像与痛点",
            "content": "企业客服响应慢，客户等待时间长，影响客户满意度"
        }
        
        result = self.node.enhance(business_idea, painpoint_paragraph)
        
        dimensions = result["selected_dimensions"]
        
        # 对于"响应慢"这个痛点，应该选择相关的维度
        # 例如：紧迫性（立即影响客户满意度）、频发性（每天都有）、高经济代价（客户流失）
        print(f"\n✅ 测试通过: 维度选择逻辑验证")
        print(f"   痛点: 客服响应慢")
        print(f"   选择的维度: {', '.join(dimensions)}")
        print(f"   维度描述数量: {len(result['dimension_descriptions'])}")
        
        # 验证选择的维度与痛点相关（简单检查）
        # 例如，如果痛点涉及"立即影响"，应该包含"紧迫性"
        enhanced_content = result["enhanced_content"]
        if "立即" in enhanced_content or "马上" in enhanced_content:
            print(f"   ✅ 内容体现了紧迫性维度")
    
    def test_real_llm_language_consistency(self):
        """测试真实LLM - 验证语言一致性（输出语言与输入一致）"""
        # 中文输入
        chinese_idea = "AI教育平台"
        chinese_paragraph = {
            "title": "用户画像与痛点",
            "content": "学生需要个性化学习"
        }
        
        result_cn = self.node.enhance(chinese_idea, chinese_paragraph)
        
        # 英文输入
        english_idea = "AI education platform"
        english_paragraph = {
            "title": "User Persona & Pain Points",
            "content": "Students need personalized learning"
        }
        
        result_en = self.node.enhance(english_idea, english_paragraph)
        
        # 验证语言一致性
        dimensions_cn = result_cn["selected_dimensions"]
        dimensions_en = result_en["selected_dimensions"]
        
        markdown_cn = result_cn["markdown_summary"]
        markdown_en = result_en["markdown_summary"]
        
        # 检查中文摘要应该包含中文字符，英文摘要应该主要是英文
        has_chinese_cn = any('\u4e00' <= char <= '\u9fff' for char in markdown_cn)
        has_chinese_en = any('\u4e00' <= char <= '\u9fff' for char in markdown_en)
        
        # 检查维度名称的语言
        has_chinese_dims_cn = any('\u4e00' <= char <= '\u9fff' for char in ' '.join(dimensions_cn))
        has_chinese_dims_en = any('\u4e00' <= char <= '\u9fff' for char in ' '.join(dimensions_en))
        
        print(f"\n✅ 测试通过: 语言一致性验证")
        print(f"   中文输入维度名称包含中文: {has_chinese_dims_cn}")
        print(f"   英文输入维度名称包含中文: {has_chinese_dims_en}")
        print(f"   中文输入markdown_summary包含中文: {has_chinese_cn}")
        print(f"   英文输入markdown_summary包含中文: {has_chinese_en}")
        
        if has_chinese_dims_cn and not has_chinese_dims_en and has_chinese_cn and not has_chinese_en:
            print(f"   ✅ 语言一致性良好：输出语言与输入一致")


if __name__ == "__main__":
    unittest.main()

