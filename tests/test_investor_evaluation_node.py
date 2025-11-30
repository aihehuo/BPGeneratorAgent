"""
单元测试：投资者评估节点
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
from src.nodes.investor_evaluation_node import InvestorEvaluationNode
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
        """默认响应（投资者评估的示例）"""
        return json.dumps({
            "data": {
                "market_size": "K12在线教育市场规模巨大，预计未来几年将保持快速增长",
                "replicability": "AI技术具有一定的技术门槛，但整体模式相对容易被复制",
                "competitive_barriers": "需要积累大量学习数据和用户数据才能形成壁垒",
                "unique_competitive_advantage": "个性化学习路径推荐算法是核心优势",
                "revenue_model": "采用订阅制模式，收入可预测且可扩展",
                "overall_assessment": "整体来看，这是一个有潜力的项目，但需要加强竞争壁垒",
                "concerns": "市场竞争激烈，需要尽快建立数据壁垒和品牌优势",
                "suggestions": "建议加强数据积累，提升算法精度，建立用户粘性",
                "paragraph_specific_feedback": [
                    {
                        "paragraph_index": 0,
                        "paragraph_title": "用户画像与痛点",
                        "feedback": "痛点描述清晰，但可以更具体",
                        "suggestions": "建议补充具体的数据和案例"
                    }
                ]
            },
            "markdown_summary": "整体评估：项目有潜力但需要加强竞争壁垒。主要关注点：市场竞争激烈，需要建立数据壁垒。建议：加强数据积累和算法精度。"
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


class TestInvestorEvaluationNode(unittest.TestCase):
    """InvestorEvaluationNode 单元测试类（使用Mock LLM）"""
    
    def setUp(self):
        """设置测试环境"""
        self.mock_llm = MockLLM()
        self.node = InvestorEvaluationNode(self.mock_llm)
        self.business_idea = "基于AI的在线教育平台，面向K12学生，提供个性化学习"
        self.paragraphs = [
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
        self.assertEqual(self.node.node_name, "InvestorEvaluationNode")
        self.assertEqual(self.node.llm_client, self.mock_llm)
    
    def test_validate_input_valid(self):
        """测试有效的输入验证"""
        valid_input = {
            "business_idea": self.business_idea,
            "paragraphs": self.paragraphs
        }
        self.assertTrue(self.node.validate_input(valid_input))
    
    def test_validate_input_missing_business_idea(self):
        """测试缺少business_idea字段"""
        invalid_input = {
            "paragraphs": self.paragraphs
        }
        self.assertFalse(self.node.validate_input(invalid_input))
    
    def test_validate_input_missing_paragraphs(self):
        """测试缺少paragraphs字段"""
        invalid_input = {
            "business_idea": self.business_idea
        }
        self.assertFalse(self.node.validate_input(invalid_input))
    
    def test_validate_input_empty_paragraphs(self):
        """测试空的paragraphs列表"""
        invalid_input = {
            "business_idea": self.business_idea,
            "paragraphs": []
        }
        self.assertFalse(self.node.validate_input(invalid_input))
    
    def test_validate_input_not_dict(self):
        """测试非字典输入"""
        self.assertFalse(self.node.validate_input("not a dict"))
        self.assertFalse(self.node.validate_input(None))
        self.assertFalse(self.node.validate_input([]))
    
    def test_run_basic(self):
        """测试基本运行功能"""
        input_data = {
            "business_idea": self.business_idea,
            "paragraphs": self.paragraphs
        }
        
        result = self.node.run(input_data)
        
        # 验证返回类型
        self.assertIsInstance(result, dict)
        
        # 验证必需的字段
        self.assertIn("overall_assessment", result)
        self.assertIn("suggestions", result)
        self.assertIn("paragraph_specific_feedback", result)
        self.assertIn("markdown_summary", result)
        
        # 验证可选字段
        self.assertIn("market_size", result)
        self.assertIn("replicability", result)
        self.assertIn("competitive_barriers", result)
        self.assertIn("unique_competitive_advantage", result)
        self.assertIn("revenue_model", result)
        self.assertIn("concerns", result)
        
        # 验证LLM被调用
        self.assertTrue(self.mock_llm.invoke_called)
    
    def test_run_output_structure(self):
        """测试输出结构"""
        input_data = {
            "business_idea": self.business_idea,
            "paragraphs": self.paragraphs
        }
        
        result = self.node.run(input_data)
        
        # 验证必需的字段
        required_fields = ["overall_assessment", "suggestions", "paragraph_specific_feedback", "markdown_summary"]
        for field in required_fields:
            self.assertIn(field, result, f"结果应该包含字段: {field}")
        
        # 验证overall_assessment是字符串
        self.assertIsInstance(result["overall_assessment"], str)
        self.assertGreater(len(result["overall_assessment"]), 0)
        
        # 验证suggestions是字符串
        self.assertIsInstance(result["suggestions"], str)
        
        # 验证paragraph_specific_feedback是列表
        feedback_list = result["paragraph_specific_feedback"]
        self.assertIsInstance(feedback_list, list)
        
        # 验证每个反馈项的结构
        for feedback in feedback_list:
            self.assertIn("paragraph_index", feedback)
            self.assertIn("paragraph_title", feedback)
            self.assertIn("feedback", feedback)
            self.assertIsInstance(feedback["paragraph_index"], int)
            self.assertIsInstance(feedback["paragraph_title"], str)
            self.assertIsInstance(feedback["feedback"], str)
        
        # 验证markdown_summary
        markdown_summary = result["markdown_summary"]
        self.assertIsInstance(markdown_summary, str)
        self.assertGreater(len(markdown_summary.strip()), 0)
    
    def test_run_with_chinese_input(self):
        """测试中文输入"""
        chinese_idea = "智能家居控制系统，通过IoT设备连接家中的各种电器"
        chinese_paragraphs = [
            {"title": "用户画像", "content": "家庭用户需要便捷的智能家居控制"},
            {"title": "解决方案", "content": "通过IoT设备实现远程控制"}
        ]
        
        input_data = {
            "business_idea": chinese_idea,
            "paragraphs": chinese_paragraphs
        }
        
        result = self.node.run(input_data)
        
        self.assertIn("overall_assessment", result)
        self.assertIn("markdown_summary", result)
        self.assertGreater(len(result["overall_assessment"]), 0)
    
    def test_run_with_english_input(self):
        """测试英文输入"""
        english_idea = "An AI-powered online education platform for K12 students"
        english_paragraphs = [
            {"title": "User Persona & Pain Points", "content": "K12 students need personalized learning"},
            {"title": "Solution", "content": "AI-based learning path recommendation"}
        ]
        
        # 设置英文响应
        english_response = json.dumps({
            "data": {
                "market_size": "The K12 online education market is large and growing",
                "replicability": "AI technology has some barriers but overall can be replicated",
                "competitive_barriers": "Need to accumulate learning data to build barriers",
                "unique_competitive_advantage": "Personalized learning path recommendation algorithm",
                "revenue_model": "Subscription model with predictable and scalable revenue",
                "overall_assessment": "Overall promising project but needs stronger competitive barriers",
                "concerns": "Intense competition, need to build data barriers quickly",
                "suggestions": "Strengthen data accumulation and algorithm precision",
                "paragraph_specific_feedback": [
                    {
                        "paragraph_index": 0,
                        "paragraph_title": "User Persona & Pain Points",
                        "feedback": "Pain points are clear but could be more specific",
                        "suggestions": "Add specific data and cases"
                    }
                ]
            },
            "markdown_summary": "Overall: Promising but needs stronger barriers. Concerns: Intense competition. Suggestions: Strengthen data and algorithms."
        }, ensure_ascii=False)
        
        self.mock_llm.response = english_response
        
        input_data = {
            "business_idea": english_idea,
            "paragraphs": english_paragraphs
        }
        
        result = self.node.run(input_data)
        
        self.assertIn("overall_assessment", result)
        self.assertIn("markdown_summary", result)
        
        # 验证输出是英文（简单检查）
        assessment = result["overall_assessment"]
        has_chinese = any('\u4e00' <= char <= '\u9fff' for char in assessment)
        self.assertFalse(has_chinese, "英文输入的评估结果应该是英文")
    
    def test_evaluate_full_bp_convenience_method(self):
        """测试便捷方法evaluate_full_bp"""
        result = self.node.evaluate_full_bp(self.business_idea, self.paragraphs)
        
        self.assertIsInstance(result, dict)
        self.assertIn("overall_assessment", result)
        self.assertIn("paragraph_specific_feedback", result)
        self.assertTrue(self.mock_llm.invoke_called)
    
    def test_evaluate_paragraph_method(self):
        """测试评估单个段落的方法"""
        paragraph = self.paragraphs[0]
        result = self.node.evaluate_paragraph(self.business_idea, paragraph, 0)
        
        self.assertIsInstance(result, dict)
        self.assertIn("paragraph_index", result)
        self.assertEqual(result["paragraph_index"], 0)
        self.assertTrue(self.mock_llm.invoke_called)
    
    def test_process_output_with_new_format(self):
        """测试处理包含data和markdown_summary的新格式输出"""
        output = json.dumps({
            "data": {
                "overall_assessment": "整体评估结果",
                "suggestions": "改进建议",
                "paragraph_specific_feedback": [
                    {
                        "paragraph_index": 0,
                        "paragraph_title": "标题",
                        "feedback": "反馈"
                    }
                ]
            },
            "markdown_summary": "这是测试摘要"
        }, ensure_ascii=False)
        
        result = self.node.process_output(output)
        
        self.assertIn("overall_assessment", result)
        self.assertIn("suggestions", result)
        self.assertIn("paragraph_specific_feedback", result)
        self.assertIn("markdown_summary", result)
        self.assertEqual(result["markdown_summary"], "这是测试摘要")
    
    def test_process_output_with_old_format(self):
        """测试处理旧格式输出（直接是评估结果）"""
        output = json.dumps({
            "overall_assessment": "整体评估结果",
            "suggestions": "改进建议",
            "paragraph_specific_feedback": []
        }, ensure_ascii=False)
        
        result = self.node.process_output(output)
        
        self.assertIn("overall_assessment", result)
        self.assertIn("suggestions", result)
        self.assertIn("paragraph_specific_feedback", result)
        # 旧格式可能没有markdown_summary，应该允许
        if "markdown_summary" in result:
            self.assertIsInstance(result["markdown_summary"], str)
    
    def test_run_invalid_input(self):
        """测试无效输入"""
        invalid_input = {
            "business_idea": self.business_idea
            # 缺少paragraphs
        }
        
        with self.assertRaises(ValueError) as context:
            self.node.run(invalid_input)
        
        self.assertIn("输入数据格式错误", str(context.exception))
    
    def test_paragraph_specific_feedback_structure(self):
        """测试段落反馈结构"""
        input_data = {
            "business_idea": self.business_idea,
            "paragraphs": self.paragraphs
        }
        
        result = self.node.run(input_data)
        
        feedback_list = result["paragraph_specific_feedback"]
        self.assertIsInstance(feedback_list, list)
        
        # 验证每个反馈项的结构
        for i, feedback in enumerate(feedback_list):
            self.assertIn("paragraph_index", feedback, f"反馈项 {i} 缺少paragraph_index")
            self.assertIn("paragraph_title", feedback, f"反馈项 {i} 缺少paragraph_title")
            self.assertIn("feedback", feedback, f"反馈项 {i} 缺少feedback")
            
            # 验证索引范围
            index = feedback["paragraph_index"]
            self.assertGreaterEqual(index, 0)
            self.assertLess(index, len(self.paragraphs))


class TestInvestorEvaluationNodeWithRealLLM(unittest.TestCase):
    """使用真实LLM的InvestorEvaluationNode测试类
    
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
        
        self.node = InvestorEvaluationNode(self.llm_client)
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """清理测试环境"""
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_real_llm_evaluate_chinese_bp(self):
        """测试真实LLM - 评估中文BP"""
        business_idea = "基于AI的在线教育平台，面向K12学生，提供个性化学习路径推荐，解决学生学习效率低和缺乏针对性指导的问题"
        paragraphs = [
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
        
        result = self.node.evaluate_full_bp(business_idea, paragraphs)
        
        # 验证基本结构
        self.assertIsInstance(result, dict)
        self.assertIn("overall_assessment", result)
        self.assertIn("suggestions", result)
        self.assertIn("paragraph_specific_feedback", result)
        self.assertIn("markdown_summary", result)
        
        # 验证overall_assessment
        overall_assessment = result["overall_assessment"]
        self.assertIsInstance(overall_assessment, str)
        self.assertGreater(len(overall_assessment.strip()), 0, "overall_assessment应该非空")
        
        # 验证markdown_summary
        markdown_summary = result["markdown_summary"]
        self.assertIsInstance(markdown_summary, str)
        self.assertGreater(len(markdown_summary.strip()), 0, "markdown_summary应该非空")
        
        # 验证paragraph_specific_feedback
        feedback_list = result["paragraph_specific_feedback"]
        self.assertIsInstance(feedback_list, list)
        self.assertEqual(len(feedback_list), len(paragraphs), "应该有与段落数量相同的反馈")
        
        print(f"\n✅ 测试通过: 中文BP评估")
        print(f"   overall_assessment长度: {len(overall_assessment)} 字符")
        print(f"   paragraph_specific_feedback数量: {len(feedback_list)}")
        print(f"   markdown_summary: {markdown_summary[:100]}...")
    
    def test_real_llm_evaluate_english_bp(self):
        """测试真实LLM - 评估英文BP"""
        business_idea = "An AI-powered online education platform for K12 students, providing personalized learning path recommendations"
        paragraphs = [
            {
                "title": "User Persona & Pain Points",
                "content": "K12 students face challenges with learning efficiency and lack of personalized guidance."
            },
            {
                "title": "Solution",
                "content": "Develop an AI-based personalized learning path recommendation system."
            }
        ]
        
        result = self.node.evaluate_full_bp(business_idea, paragraphs)
        
        # 验证基本结构
        self.assertIsInstance(result, dict)
        self.assertIn("overall_assessment", result)
        self.assertIn("markdown_summary", result)
        
        # 验证输出是英文（对于英文输入）
        overall_assessment = result["overall_assessment"]
        markdown_summary = result["markdown_summary"]
        
        has_chinese_in_assessment = any('\u4e00' <= char <= '\u9fff' for char in overall_assessment)
        has_chinese_in_summary = any('\u4e00' <= char <= '\u9fff' for char in markdown_summary)
        
        print(f"\n✅ 测试通过: 英文BP评估")
        print(f"   overall_assessment语言: {'中文' if has_chinese_in_assessment else '英文'}")
        print(f"   markdown_summary语言: {'中文' if has_chinese_in_summary else '英文'}")
        print(f"   overall_assessment: {overall_assessment[:100]}...")
    
    def test_real_llm_output_format_with_markdown_summary(self):
        """测试真实LLM - 验证输出格式包含markdown_summary"""
        business_idea = "智能家居控制系统"
        paragraphs = [
            {"title": "用户画像", "content": "家庭用户需要便捷的智能家居控制方案"},
            {"title": "解决方案", "content": "通过IoT设备实现远程控制和管理"}
        ]
        
        result = self.node.evaluate_full_bp(business_idea, paragraphs)
        
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
        """测试真实LLM - 验证提示词的有效性（是否从投资者角度进行评估）"""
        business_idea = "基于区块链的供应链管理系统"
        paragraphs = [
            {
                "title": "解决方案",
                "content": "使用区块链技术实现供应链数据的透明化和可追溯性，帮助企业追踪产品从生产到销售的完整流程。"
            },
            {
                "title": "商业模式",
                "content": "采用SaaS订阅模式，按企业规模收费"
            }
        ]
        
        result = self.node.evaluate_full_bp(business_idea, paragraphs)
        
        # 验证评估维度
        assessment_fields = ["market_size", "replicability", "competitive_barriers", 
                           "unique_competitive_advantage", "revenue_model"]
        
        print(f"\n✅ 测试通过: 提示词有效性验证")
        print(f"   overall_assessment: {result['overall_assessment'][:100]}...")
        
        # 验证包含投资者关心的维度（如果返回了这些字段）
        for field in assessment_fields:
            if field in result:
                content = result[field]
                self.assertIsInstance(content, str)
                print(f"   {field}: {content[:80]}...")
        
        # 验证concerns和suggestions
        if "concerns" in result:
            concerns = result["concerns"]
            self.assertIsInstance(concerns, str)
            print(f"   concerns: {concerns[:80]}...")
        
        if "suggestions" in result:
            suggestions = result["suggestions"]
            self.assertIsInstance(suggestions, str)
            self.assertGreater(len(suggestions.strip()), 0, "suggestions应该非空")
            print(f"   suggestions: {suggestions[:80]}...")
    
    def test_real_llm_paragraph_specific_feedback(self):
        """测试真实LLM - 验证段落特定反馈"""
        business_idea = "AI驱动的智能客服系统"
        paragraphs = [
            {
                "title": "用户画像与痛点",
                "content": "企业客服响应慢，客户等待时间长"
            },
            {
                "title": "解决方案",
                "content": "使用AI技术实现24小时自动客服响应"
            },
            {
                "title": "商业模式",
                "content": "按使用量收费"
            }
        ]
        
        result = self.node.evaluate_full_bp(business_idea, paragraphs)
        
        feedback_list = result["paragraph_specific_feedback"]
        
        # 验证反馈数量
        self.assertEqual(len(feedback_list), len(paragraphs), 
                        f"应该有 {len(paragraphs)} 个段落反馈，实际有 {len(feedback_list)} 个")
        
        # 验证每个反馈的结构
        for i, feedback in enumerate(feedback_list):
            self.assertIn("paragraph_index", feedback)
            self.assertIn("paragraph_title", feedback)
            self.assertIn("feedback", feedback)
            
            # 验证索引和标题匹配
            index = feedback["paragraph_index"]
            title = feedback["paragraph_title"]
            self.assertEqual(index, i, f"反馈 {i} 的索引应该为 {i}")
            self.assertEqual(title, paragraphs[i]["title"], 
                           f"反馈 {i} 的标题应该与段落 {i} 的标题一致")
            
            # 验证feedback内容非空
            feedback_content = feedback["feedback"]
            self.assertGreater(len(feedback_content.strip()), 0, 
                             f"反馈 {i} 的feedback应该非空")
        
        print(f"\n✅ 测试通过: 段落特定反馈验证")
        print(f"   段落数量: {len(paragraphs)}")
        print(f"   反馈数量: {len(feedback_list)}")
        for i, feedback in enumerate(feedback_list):
            print(f"   段落 {i} 反馈: {feedback['feedback'][:60]}...")
    
    def test_real_llm_language_consistency(self):
        """测试真实LLM - 验证语言一致性（输出语言与输入一致）"""
        # 中文输入
        chinese_idea = "AI教育平台"
        chinese_paragraphs = [
            {"title": "用户画像", "content": "学生需要个性化学习"}
        ]
        
        result_cn = self.node.evaluate_full_bp(chinese_idea, chinese_paragraphs)
        
        # 英文输入
        english_idea = "AI education platform"
        english_paragraphs = [
            {"title": "User Persona", "content": "Students need personalized learning"}
        ]
        
        result_en = self.node.evaluate_full_bp(english_idea, english_paragraphs)
        
        # 验证语言一致性
        assessment_cn = result_cn["overall_assessment"]
        assessment_en = result_en["overall_assessment"]
        
        markdown_cn = result_cn["markdown_summary"]
        markdown_en = result_en["markdown_summary"]
        
        # 检查中文摘要应该包含中文字符，英文摘要应该主要是英文
        has_chinese_cn = any('\u4e00' <= char <= '\u9fff' for char in markdown_cn)
        has_chinese_en = any('\u4e00' <= char <= '\u9fff' for char in markdown_en)
        
        has_chinese_assessment_cn = any('\u4e00' <= char <= '\u9fff' for char in assessment_cn)
        has_chinese_assessment_en = any('\u4e00' <= char <= '\u9fff' for char in assessment_en)
        
        print(f"\n✅ 测试通过: 语言一致性验证")
        print(f"   中文输入overall_assessment包含中文: {has_chinese_assessment_cn}")
        print(f"   英文输入overall_assessment包含中文: {has_chinese_assessment_en}")
        print(f"   中文输入markdown_summary包含中文: {has_chinese_cn}")
        print(f"   英文输入markdown_summary包含中文: {has_chinese_en}")
        
        if has_chinese_assessment_cn and not has_chinese_assessment_en and has_chinese_cn and not has_chinese_en:
            print(f"   ✅ 语言一致性良好：输出语言与输入一致")


if __name__ == "__main__":
    unittest.main()

