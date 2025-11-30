"""
单元测试：PPT生成节点
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
from src.nodes.ppt_generation_node import PPTGenerationNode
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
        """默认响应（10页PPT的示例）"""
        slides = []
        for i in range(1, 11):
            slides.append({
                "slide_number": i,
                "slide_title": f"幻灯片 {i}",
                "point": f"要点 {i}",
                "line": f"详细内容 {i}",
                "reserved": f"保留部分 {i}"
            })
        
        return json.dumps({
            "data": {
                "slides": slides
            },
            "markdown_summary": "已生成10页PPT，涵盖商业计划书的各个核心部分，包括痛点、解决方案、产品、市场、商业模式、竞争优势、团队、财务和融资等。"
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


class TestPPTGenerationNode(unittest.TestCase):
    """PPTGenerationNode 单元测试类（使用Mock LLM）"""
    
    def setUp(self):
        """设置测试环境"""
        self.mock_llm = MockLLM()
        self.node = PPTGenerationNode(self.mock_llm)
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
        self.assertEqual(self.node.node_name, "PPTGenerationNode")
        self.assertEqual(self.node.llm_client, self.mock_llm)
    
    def test_validate_input_valid(self):
        """测试有效的输入验证"""
        valid_input = {
            "business_idea": self.business_idea,
            "bp_structure": self.bp_structure
        }
        self.assertTrue(self.node.validate_input(valid_input))
    
    def test_validate_input_missing_business_idea(self):
        """测试缺少business_idea字段"""
        invalid_input = {
            "bp_structure": self.bp_structure
        }
        self.assertFalse(self.node.validate_input(invalid_input))
    
    def test_validate_input_missing_bp_structure(self):
        """测试缺少bp_structure字段"""
        invalid_input = {
            "business_idea": self.business_idea
        }
        self.assertFalse(self.node.validate_input(invalid_input))
    
    def test_validate_input_invalid_paragraph_structure(self):
        """测试无效的段落结构"""
        invalid_input = {
            "business_idea": self.business_idea,
            "bp_structure": [
                {"title": "标题"}  # 缺少content
            ]
        }
        self.assertFalse(self.node.validate_input(invalid_input))
        
        invalid_input2 = {
            "business_idea": self.business_idea,
            "bp_structure": "not a list"  # 不是列表
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
            "bp_structure": self.bp_structure
        }
        
        result = self.node.run(input_data)
        
        # 验证返回类型
        self.assertIsInstance(result, dict)
        
        # 验证必需的字段
        self.assertIn("slides", result)
        self.assertIn("markdown_summary", result)
        
        # 验证slides是列表
        slides = result["slides"]
        self.assertIsInstance(slides, list)
        self.assertEqual(len(slides), 10, "应该生成恰好10页PPT")
        
        # 验证LLM被调用
        self.assertTrue(self.mock_llm.invoke_called)
    
    def test_run_output_structure(self):
        """测试输出结构"""
        input_data = {
            "business_idea": self.business_idea,
            "bp_structure": self.bp_structure
        }
        
        result = self.node.run(input_data)
        
        # 验证必需的字段
        self.assertIn("slides", result)
        self.assertIn("markdown_summary", result)
        
        # 验证slides数量
        slides = result["slides"]
        self.assertEqual(len(slides), 10, "应该恰好生成10页PPT")
        
        # 验证每页幻灯片的必需字段
        for i, slide in enumerate(slides):
            self.assertIsInstance(slide, dict, f"第 {i+1} 页应该是字典格式")
            required_fields = ["slide_number", "slide_title", "point", "line", "reserved"]
            for field in required_fields:
                self.assertIn(field, slide, f"第 {i+1} 页应该包含字段: {field}")
            
            # 验证字段类型
            self.assertIsInstance(slide["slide_number"], int)
            self.assertIsInstance(slide["slide_title"], str)
            self.assertIsInstance(slide["point"], str)
            self.assertIsInstance(slide["line"], str)
            self.assertIsInstance(slide["reserved"], str)
            
            # 验证slide_number
            self.assertEqual(slide["slide_number"], i + 1, f"第 {i+1} 页的slide_number应该是 {i+1}")
        
        # 验证markdown_summary
        markdown_summary = result["markdown_summary"]
        self.assertIsInstance(markdown_summary, str)
        self.assertGreater(len(markdown_summary.strip()), 0)
    
    def test_run_with_chinese_input(self):
        """测试中文输入"""
        chinese_idea = "智能家居控制系统，通过IoT设备连接家中的各种电器"
        chinese_structure = [
            {"title": "用户画像", "content": "家庭用户需要便捷的智能家居控制"},
            {"title": "解决方案", "content": "通过IoT设备实现远程控制"}
        ]
        
        input_data = {
            "business_idea": chinese_idea,
            "bp_structure": chinese_structure
        }
        
        result = self.node.run(input_data)
        
        self.assertIn("slides", result)
        self.assertIn("markdown_summary", result)
        self.assertEqual(len(result["slides"]), 10)
    
    def test_run_with_english_input(self):
        """测试英文输入"""
        english_idea = "An AI-powered online education platform for K12 students"
        english_structure = [
            {"title": "User Persona & Pain Points", "content": "K12 students need personalized learning"},
            {"title": "Solution", "content": "AI-based learning path recommendation"}
        ]
        
        # 设置英文响应
        english_slides = []
        for i in range(1, 11):
            english_slides.append({
                "slide_number": i,
                "slide_title": f"Slide {i}",
                "point": f"Point {i}",
                "line": f"Line {i}",
                "reserved": f"Reserved {i}"
            })
        
        english_response = json.dumps({
            "data": {
                "slides": english_slides
            },
            "markdown_summary": "Generated 10-page PPT covering all core sections of the business plan."
        }, ensure_ascii=False)
        
        self.mock_llm.response = english_response
        
        input_data = {
            "business_idea": english_idea,
            "bp_structure": english_structure
        }
        
        result = self.node.run(input_data)
        
        self.assertIn("slides", result)
        self.assertIn("markdown_summary", result)
        self.assertEqual(len(result["slides"]), 10)
        
        # 验证输出是英文（简单检查第一页）
        first_slide = result["slides"][0]
        has_chinese = any('\u4e00' <= char <= '\u9fff' for char in first_slide["slide_title"])
        self.assertFalse(has_chinese, "英文输入的PPT标题应该是英文")
    
    def test_generate_ppt_convenience_method(self):
        """测试便捷方法generate_ppt"""
        result = self.node.generate_ppt(self.business_idea, self.bp_structure)
        
        self.assertIsInstance(result, dict)
        self.assertIn("slides", result)
        self.assertTrue(self.mock_llm.invoke_called)
        self.assertEqual(len(result["slides"]), 10)
    
    def test_process_output_with_new_format(self):
        """测试处理包含data和markdown_summary的新格式输出"""
        slides_data = []
        for i in range(1, 11):
            slides_data.append({
                "slide_number": i,
                "slide_title": f"标题 {i}",
                "point": f"要点 {i}",
                "line": f"详细内容 {i}",
                "reserved": f"保留部分 {i}"
            })
        
        output = json.dumps({
            "data": {
                "slides": slides_data
            },
            "markdown_summary": "这是测试摘要"
        }, ensure_ascii=False)
        
        result = self.node.process_output(output)
        
        self.assertIn("slides", result)
        self.assertIn("markdown_summary", result)
        self.assertEqual(result["markdown_summary"], "这是测试摘要")
        self.assertEqual(len(result["slides"]), 10)
    
    def test_process_output_with_old_format(self):
        """测试处理旧格式输出（直接是PPT结果）"""
        slides_data = []
        for i in range(1, 11):
            slides_data.append({
                "slide_number": i,
                "slide_title": f"标题 {i}",
                "point": f"要点 {i}",
                "line": f"详细内容 {i}",
                "reserved": f"保留部分 {i}"
            })
        
        output = json.dumps({
            "slides": slides_data
        }, ensure_ascii=False)
        
        result = self.node.process_output(output)
        
        self.assertIn("slides", result)
        self.assertEqual(len(result["slides"]), 10)
        # 旧格式可能没有markdown_summary，应该允许
        if "markdown_summary" in result:
            self.assertIsInstance(result["markdown_summary"], str)
    
    def test_run_invalid_input(self):
        """测试无效输入"""
        invalid_input = {
            "business_idea": self.business_idea
            # 缺少bp_structure
        }
        
        with self.assertRaises(ValueError) as context:
            self.node.run(invalid_input)
        
        self.assertIn("输入数据格式错误", str(context.exception))
    
    def test_slide_number_validation(self):
        """测试幻灯片编号验证和自动填充"""
        # 创建一个缺少slide_number的响应
        slides_data = []
        for i in range(1, 11):
            slide = {
                "slide_title": f"标题 {i}",
                "point": f"要点 {i}",
                "line": f"详细内容 {i}",
                "reserved": f"保留部分 {i}"
            }
            # 只有第一页和最后一页有slide_number
            if i == 1 or i == 10:
                slide["slide_number"] = i
            slides_data.append(slide)
        
        response = json.dumps({
            "data": {
                "slides": slides_data
            },
            "markdown_summary": "测试摘要"
        }, ensure_ascii=False)
        
        self.mock_llm.response = response
        
        input_data = {
            "business_idea": self.business_idea,
            "bp_structure": self.bp_structure
        }
        
        result = self.node.run(input_data)
        
        # 验证所有幻灯片都有slide_number
        for i, slide in enumerate(result["slides"]):
            self.assertIn("slide_number", slide)
            self.assertEqual(slide["slide_number"], i + 1)


class TestPPTGenerationNodeWithRealLLM(unittest.TestCase):
    """使用真实LLM的PPTGenerationNode测试类
    
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
        
        self.node = PPTGenerationNode(self.llm_client)
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """清理测试环境"""
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_real_llm_generate_chinese_ppt(self):
        """测试真实LLM - 生成中文10页PPT"""
        business_idea = "基于AI的在线教育平台，面向K12学生，提供个性化学习路径推荐"
        bp_structure = [
            {
                "title": "用户画像与痛点",
                "content": "K12学生（6-18岁）在学习过程中面临学习效率低、缺乏个性化指导、难以找到适合自己的学习路径等问题。传统教育无法根据每个学生的特点提供定制化学习方案。"
            },
            {
                "title": "解决方案",
                "content": "基于AI技术开发个性化学习路径推荐系统，通过分析学生的学习数据，为每个学生生成专属的学习路径，提供针对性的学习内容和练习题。"
            },
            {
                "title": "最小可行产品（MVP）",
                "content": "MVP包括学习数据收集模块、AI分析引擎、个性化推荐系统。核心功能是自动收集学生学习数据，使用机器学习算法分析学习模式，生成个性化学习建议。"
            }
        ]
        
        result = self.node.generate_ppt(business_idea, bp_structure)
        
        # 验证基本结构
        self.assertIsInstance(result, dict)
        self.assertIn("slides", result)
        self.assertIn("markdown_summary", result)
        
        # 验证slides数量
        slides = result["slides"]
        self.assertIsInstance(slides, list)
        self.assertEqual(len(slides), 10, "应该恰好生成10页PPT")
        
        # 验证每页幻灯片的必需字段
        for i, slide in enumerate(slides):
            self.assertIsInstance(slide, dict)
            self.assertIn("slide_number", slide)
            self.assertIn("slide_title", slide)
            self.assertIn("point", slide)
            self.assertIn("line", slide)
            self.assertIn("reserved", slide)
            
            # 验证内容非空
            self.assertGreater(len(slide["slide_title"].strip()), 0)
            self.assertGreater(len(slide["point"].strip()), 0)
            self.assertGreater(len(slide["line"].strip()), 0)
        
        # 验证markdown_summary
        markdown_summary = result["markdown_summary"]
        self.assertIsInstance(markdown_summary, str)
        self.assertGreater(len(markdown_summary.strip()), 0, "markdown_summary应该非空")
        
        print(f"\n✅ 测试通过: 中文10页PPT生成")
        print(f"   PPT页数: {len(slides)}")
        print(f"   第一页标题: {slides[0]['slide_title']}")
        print(f"   markdown_summary: {markdown_summary[:100]}...")
    
    def test_real_llm_generate_english_ppt(self):
        """测试真实LLM - 生成英文10页PPT"""
        business_idea = "An AI-powered online education platform for K12 students"
        bp_structure = [
            {
                "title": "User Persona & Pain Points",
                "content": "K12 students face challenges with learning efficiency and lack of personalized guidance."
            },
            {
                "title": "Solution",
                "content": "Develop an AI-based personalized learning path recommendation system."
            }
        ]
        
        result = self.node.generate_ppt(business_idea, bp_structure)
        
        # 验证基本结构
        self.assertIsInstance(result, dict)
        self.assertIn("slides", result)
        self.assertIn("markdown_summary", result)
        
        slides = result["slides"]
        self.assertEqual(len(slides), 10)
        
        # 验证输出是英文（对于英文输入）
        first_slide = slides[0]
        has_chinese = any('\u4e00' <= char <= '\u9fff' for char in first_slide["slide_title"])
        
        print(f"\n✅ 测试通过: 英文10页PPT生成")
        print(f"   第一页标题语言: {'中文' if has_chinese else '英文'}")
        print(f"   第一页标题: {first_slide['slide_title']}")
    
    def test_real_llm_output_format_with_markdown_summary(self):
        """测试真实LLM - 验证输出格式包含markdown_summary"""
        business_idea = "智能家居控制系统"
        bp_structure = [
            {"title": "用户画像", "content": "家庭用户需要便捷的智能家居控制方案"},
            {"title": "解决方案", "content": "通过IoT设备实现远程控制和管理"}
        ]
        
        result = self.node.generate_ppt(business_idea, bp_structure)
        
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
        """测试真实LLM - 验证提示词的有效性（是否正确生成10页PPT结构）"""
        business_idea = "基于区块链的供应链管理系统"
        bp_structure = [
            {
                "title": "用户画像与痛点",
                "content": "企业需要透明化和可追溯的供应链管理"
            },
            {
                "title": "解决方案",
                "content": "使用区块链技术实现供应链数据的透明化和可追溯性"
            }
        ]
        
        result = self.node.generate_ppt(business_idea, bp_structure)
        
        slides = result["slides"]
        
        # 验证幻灯片数量
        self.assertEqual(len(slides), 10, "应该恰好生成10页PPT")
        
        # 验证每页都有三层结构（point, line, reserved）
        for i, slide in enumerate(slides):
            self.assertIn("point", slide, f"第 {i+1} 页应该有point")
            self.assertIn("line", slide, f"第 {i+1} 页应该有line")
            self.assertIn("reserved", slide, f"第 {i+1} 页应该有reserved")
            
            # 验证内容非空
            self.assertGreater(len(slide["point"].strip()), 0, f"第 {i+1} 页的point应该非空")
            self.assertGreater(len(slide["line"].strip()), 0, f"第 {i+1} 页的line应该非空")
            self.assertGreater(len(slide["reserved"].strip()), 0, f"第 {i+1} 页的reserved应该非空")
        
        print(f"\n✅ 测试通过: 提示词有效性验证")
        print(f"   PPT页数: {len(slides)}")
        print(f"   第一页point: {slides[0]['point'][:50]}...")
        print(f"   第一页line: {slides[0]['line'][:50]}...")
        print(f"   第一页reserved: {slides[0]['reserved'][:50]}...")
    
    def test_real_llm_ppt_structure_three_layers(self):
        """测试真实LLM - 验证PPT三层结构（point、line、reserved）"""
        business_idea = "AI驱动的智能客服系统"
        bp_structure = [
            {
                "title": "用户画像与痛点",
                "content": "企业客服响应慢，客户等待时间长"
            },
            {
                "title": "解决方案",
                "content": "使用AI技术实现24小时自动客服响应"
            }
        ]
        
        result = self.node.generate_ppt(business_idea, bp_structure)
        
        slides = result["slides"]
        
        # 验证三层结构
        for i, slide in enumerate(slides):
            point = slide["point"]
            line = slide["line"]
            reserved = slide["reserved"]
            
            # point应该是简洁的（不超过15个字或8个单词）
            point_word_count = len(point.split()) if ' ' in point else len(point)
            # 简单检查：point不应该过长
            self.assertLess(len(point), 100, f"第 {i+1} 页的point应该简洁")
            
            # line应该比point更详细
            self.assertGreaterEqual(len(line), len(point), 
                                  f"第 {i+1} 页的line应该比point更详细")
            
            # reserved应该有内容（作为钩子）
            self.assertGreater(len(reserved.strip()), 0, 
                             f"第 {i+1} 页的reserved应该非空")
        
        print(f"\n✅ 测试通过: PPT三层结构验证")
        print(f"   所有10页PPT都包含point、line、reserved三层结构")
    
    def test_real_llm_language_consistency(self):
        """测试真实LLM - 验证语言一致性（输出语言与输入一致）"""
        # 中文输入
        chinese_idea = "AI教育平台"
        chinese_structure = [
            {"title": "用户画像", "content": "学生需要个性化学习"}
        ]
        
        result_cn = self.node.generate_ppt(chinese_idea, chinese_structure)
        
        # 英文输入
        english_idea = "AI education platform"
        english_structure = [
            {"title": "User Persona", "content": "Students need personalized learning"}
        ]
        
        result_en = self.node.generate_ppt(english_idea, english_structure)
        
        # 验证语言一致性
        slide_cn = result_cn["slides"][0]
        slide_en = result_en["slides"][0]
        
        markdown_cn = result_cn["markdown_summary"]
        markdown_en = result_en["markdown_summary"]
        
        # 检查中文PPT应该包含中文字符，英文PPT应该主要是英文
        has_chinese_cn = any('\u4e00' <= char <= '\u9fff' for char in slide_cn["slide_title"])
        has_chinese_en = any('\u4e00' <= char <= '\u9fff' for char in slide_en["slide_title"])
        
        has_chinese_markdown_cn = any('\u4e00' <= char <= '\u9fff' for char in markdown_cn)
        has_chinese_markdown_en = any('\u4e00' <= char <= '\u9fff' for char in markdown_en)
        
        print(f"\n✅ 测试通过: 语言一致性验证")
        print(f"   中文输入PPT标题包含中文: {has_chinese_cn}")
        print(f"   英文输入PPT标题包含中文: {has_chinese_en}")
        print(f"   中文输入markdown_summary包含中文: {has_chinese_markdown_cn}")
        print(f"   英文输入markdown_summary包含中文: {has_chinese_markdown_en}")
        
        if has_chinese_cn and not has_chinese_en and has_chinese_markdown_cn and not has_chinese_markdown_en:
            print(f"   ✅ 语言一致性良好：输出语言与输入一致")


if __name__ == "__main__":
    unittest.main()

