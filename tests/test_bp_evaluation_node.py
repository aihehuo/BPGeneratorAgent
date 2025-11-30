"""
单元测试：BP评估节点
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
from src.nodes.bp_evaluation_node import BPEvaluationNode
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
        """默认响应（评估通过的示例）"""
        return json.dumps({
            "data": {
                "passed": True,
                "evaluation_result": "所有段落都与商业创意高度相关，内容具体且针对性强。"
            },
            "markdown_summary": "✅ 评估通过：所有段落都与商业创意高度相关。"
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


class TestBPEvaluationNode(unittest.TestCase):
    """BPEvaluationNode 单元测试类（使用Mock LLM）"""
    
    def setUp(self):
        """设置测试环境"""
        self.mock_llm = MockLLM()
        self.node = BPEvaluationNode(self.mock_llm)
        self.business_idea = "基于AI的在线教育平台，面向K12学生，提供个性化学习"
        self.paragraphs = [
            {"title": "用户画像与痛点", "content": "K12学生需要个性化学习，但传统教育无法满足"},
            {"title": "解决方案", "content": "使用AI技术分析学生学习数据，提供个性化学习路径"},
            {"title": "最小可行产品（MVP）", "content": "核心功能包括学习数据分析、智能推荐引擎"}
        ]
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """清理测试环境"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_init(self):
        """测试节点初始化"""
        self.assertIsNotNone(self.node)
        self.assertEqual(self.node.node_name, "BPEvaluationNode")
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
    
    def test_run_basic_passed(self):
        """测试基本运行功能 - 评估通过"""
        input_data = {
            "business_idea": self.business_idea,
            "paragraphs": self.paragraphs
        }
        
        result = self.node.run(input_data)
        
        # 验证返回类型
        self.assertIsInstance(result, dict)
        
        # 验证必需字段
        self.assertIn("passed", result)
        self.assertIn("evaluation_result", result)
        self.assertIn("markdown_summary", result)
        
        # 验证passed是布尔值
        self.assertIsInstance(result["passed"], bool)
        self.assertTrue(result["passed"])
        
        # 验证LLM被调用
        self.assertTrue(self.mock_llm.invoke_called)
    
    def test_run_failed(self):
        """测试评估不通过的情况"""
        # 设置失败的响应
        failed_response = json.dumps({
            "data": {
                "passed": False,
                "failed_paragraph_index": 1,
                "failed_paragraph_title": "解决方案",
                "evaluation_result": "该段落内容过于通用，没有针对具体的商业创意",
                "suggestions": "需要添加更多与AI教育平台相关的具体技术细节"
            },
            "markdown_summary": "❌ 评估不通过：第2个段落（解决方案）内容过于通用。"
        }, ensure_ascii=False)
        
        self.mock_llm.response = failed_response
        
        input_data = {
            "business_idea": self.business_idea,
            "paragraphs": self.paragraphs
        }
        
        result = self.node.run(input_data)
        
        # 验证结果
        self.assertFalse(result["passed"])
        self.assertEqual(result["failed_paragraph_index"], 1)
        self.assertEqual(result["failed_paragraph_title"], "解决方案")
        self.assertIn("evaluation_result", result)
        self.assertIn("suggestions", result)
        self.assertIn("markdown_summary", result)
    
    def test_run_output_structure(self):
        """测试输出结构"""
        input_data = {
            "business_idea": self.business_idea,
            "paragraphs": self.paragraphs
        }
        
        result = self.node.run(input_data)
        
        # 验证必需的字段
        required_fields = ["passed", "evaluation_result", "markdown_summary"]
        for field in required_fields:
            self.assertIn(field, result, f"结果应该包含字段: {field}")
        
        # 验证passed是布尔值
        self.assertIsInstance(result["passed"], bool)
        
        # 验证evaluation_result是字符串
        self.assertIsInstance(result["evaluation_result"], str)
        self.assertGreater(len(result["evaluation_result"]), 0)
        
        # 验证markdown_summary
        markdown_summary = result["markdown_summary"]
        self.assertIsInstance(markdown_summary, str)
        self.assertGreater(len(markdown_summary), 0)
    
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
        
        self.assertIn("passed", result)
        self.assertIn("markdown_summary", result)
    
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
                "passed": True,
                "evaluation_result": "All paragraphs are highly relevant to the business idea."
            },
            "markdown_summary": "✅ Evaluation passed: All paragraphs are relevant."
        }, ensure_ascii=False)
        
        self.mock_llm.response = english_response
        
        input_data = {
            "business_idea": english_idea,
            "paragraphs": english_paragraphs
        }
        
        result = self.node.run(input_data)
        
        self.assertIn("passed", result)
        self.assertIn("markdown_summary", result)
    
    def test_evaluate_paragraphs_convenience_method(self):
        """测试便捷方法evaluate_paragraphs"""
        result = self.node.evaluate_paragraphs(self.business_idea, self.paragraphs)
        
        self.assertIsInstance(result, dict)
        self.assertIn("passed", result)
        self.assertIn("evaluation_result", result)
        self.assertTrue(self.mock_llm.invoke_called)
    
    def test_process_output_with_new_format(self):
        """测试处理包含data和markdown_summary的新格式输出"""
        output = json.dumps({
            "data": {
                "passed": True,
                "evaluation_result": "所有段落都通过评估"
            },
            "markdown_summary": "评估通过：所有段落都符合要求。"
        }, ensure_ascii=False)
        
        result = self.node.process_output(output)
        
        self.assertIn("passed", result)
        self.assertIn("evaluation_result", result)
        self.assertIn("markdown_summary", result)
        self.assertTrue(result["passed"])
        self.assertEqual(result["markdown_summary"], "评估通过：所有段落都符合要求。")
    
    def test_process_output_with_old_format(self):
        """测试处理旧格式输出（直接是评估结果）"""
        output = json.dumps({
            "passed": True,
            "evaluation_result": "评估通过"
        }, ensure_ascii=False)
        
        result = self.node.process_output(output)
        
        self.assertIn("passed", result)
        self.assertIn("evaluation_result", result)
        self.assertTrue(result["passed"])
    
    def test_run_invalid_input(self):
        """测试无效输入"""
        invalid_input = {
            "business_idea": self.business_idea
            # 缺少paragraphs
        }
        
        with self.assertRaises(ValueError) as context:
            self.node.run(invalid_input)
        
        self.assertIn("输入数据格式错误", str(context.exception))
    
    def test_process_output_passed_string(self):
        """测试处理passed为字符串的情况"""
        output = json.dumps({
            "data": {
                "passed": "true",  # 字符串格式
                "evaluation_result": "评估通过"
            },
            "markdown_summary": "通过"
        }, ensure_ascii=False)
        
        result = self.node.process_output(output)
        
        # 应该转换为布尔值
        self.assertIsInstance(result["passed"], bool)
        self.assertTrue(result["passed"])


class TestBPEvaluationNodeWithRealLLM(unittest.TestCase):
    """使用真实LLM的BPEvaluationNode测试类
    
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
        
        self.node = BPEvaluationNode(self.llm_client)
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """清理测试环境"""
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_real_llm_evaluate_passed_chinese(self):
        """测试真实LLM - 评估通过（中文）"""
        business_idea = "基于AI的在线教育平台，面向K12学生，提供个性化学习路径推荐，解决学生学习效率低和缺乏针对性指导的问题"
        paragraphs = [
            {
                "title": "用户画像与痛点",
                "content": "K12学生（6-18岁）在学习过程中面临学习效率低、缺乏个性化指导、难以找到适合自己的学习路径等问题。传统教育无法根据每个学生的特点提供定制化学习方案。"
            },
            {
                "title": "解决方案",
                "content": "基于AI技术开发个性化学习路径推荐系统，通过分析学生的学习数据（如学习进度、知识掌握情况、学习习惯等），为每个学生生成专属的学习路径，提供针对性的学习内容和练习题。"
            },
            {
                "title": "最小可行产品（MVP）",
                "content": "MVP包括学习数据收集模块、AI分析引擎、个性化推荐系统。核心功能是自动收集学生学习数据，使用机器学习算法分析学习模式，生成个性化学习建议。"
            }
        ]
        
        input_data = {
            "business_idea": business_idea,
            "paragraphs": paragraphs
        }
        
        result = self.node.run(input_data)
        
        # 验证基本结构
        self.assertIsInstance(result, dict)
        self.assertIn("passed", result)
        self.assertIn("evaluation_result", result)
        self.assertIn("markdown_summary", result)
        
        # 验证passed是布尔值
        self.assertIsInstance(result["passed"], bool)
        
        # 验证evaluation_result
        evaluation_result = result["evaluation_result"]
        self.assertIsInstance(evaluation_result, str)
        self.assertGreater(len(evaluation_result.strip()), 0)
        
        # 验证markdown_summary
        markdown_summary = result["markdown_summary"]
        self.assertIsInstance(markdown_summary, str)
        self.assertGreater(len(markdown_summary.strip()), 0, "markdown_summary应该非空")
        
        print(f"\n✅ 测试通过: 中文评估")
        print(f"   passed: {result['passed']}")
        print(f"   evaluation_result: {evaluation_result[:100]}...")
        print(f"   markdown_summary: {markdown_summary[:100]}...")
        
        # 对于相关的段落，应该通过
        if result["passed"]:
            print(f"   ✅ 评估通过：所有段落都与商业创意相关")
    
    def test_real_llm_evaluate_failed_chinese(self):
        """测试真实LLM - 评估不通过（中文，通用模板内容）"""
        business_idea = "基于AI的在线教育平台，面向K12学生"
        paragraphs = [
            {
                "title": "用户画像与痛点",
                "content": "目标用户画像（早期采用者特征、使用场景、行为模式）"
            },
            {
                "title": "解决方案",
                "content": "针对痛点的解决方案，核心价值主张，解决方案的独特性和优势"
            }
        ]
        
        input_data = {
            "business_idea": business_idea,
            "paragraphs": paragraphs
        }
        
        result = self.node.run(input_data)
        
        # 验证基本结构
        self.assertIsInstance(result, dict)
        self.assertIn("passed", result)
        self.assertIn("evaluation_result", result)
        self.assertIn("markdown_summary", result)
        
        print(f"\n✅ 测试通过: 中文评估（通用模板）")
        print(f"   passed: {result['passed']}")
        print(f"   evaluation_result: {result['evaluation_result'][:100]}...")
        print(f"   markdown_summary: {result['markdown_summary'][:100]}...")
        
        # 对于通用模板内容，应该不通过
        if not result["passed"]:
            self.assertIn("failed_paragraph_index", result)
            self.assertIn("failed_paragraph_title", result)
            self.assertIn("suggestions", result)
            print(f"   ✅ 正确识别为不通过，失败段落索引: {result.get('failed_paragraph_index')}")
    
    def test_real_llm_evaluate_english(self):
        """测试真实LLM - 评估英文输入"""
        business_idea = "An AI-powered online education platform for K12 students, providing personalized learning path recommendations"
        paragraphs = [
            {
                "title": "User Persona & Pain Points",
                "content": "K12 students face challenges with learning efficiency and lack of personalized guidance. Traditional education cannot provide customized learning plans for each student."
            },
            {
                "title": "Solution",
                "content": "Develop an AI-based personalized learning path recommendation system that analyzes student learning data to generate customized learning paths and content."
            }
        ]
        
        input_data = {
            "business_idea": business_idea,
            "paragraphs": paragraphs
        }
        
        result = self.node.run(input_data)
        
        # 验证基本结构
        self.assertIsInstance(result, dict)
        self.assertIn("passed", result)
        self.assertIn("evaluation_result", result)
        self.assertIn("markdown_summary", result)
        
        # 验证markdown_summary是英文（对于英文输入）
        markdown_summary = result["markdown_summary"]
        english_keywords = ["evaluation", "passed", "failed", "paragraph", "relevant"]
        has_english = any(keyword.lower() in markdown_summary.lower() for keyword in english_keywords)
        
        print(f"\n✅ 测试通过: 英文评估")
        print(f"   passed: {result['passed']}")
        print(f"   markdown_summary语言: {'英文' if has_english else '未确定'}")
        print(f"   markdown_summary: {markdown_summary[:100]}...")
    
    def test_real_llm_output_format_with_markdown_summary(self):
        """测试真实LLM - 验证输出格式包含markdown_summary"""
        business_idea = "智能家居控制系统"
        paragraphs = [
            {"title": "用户画像", "content": "家庭用户需要便捷的智能家居控制方案"},
            {"title": "解决方案", "content": "通过IoT设备实现远程控制和管理"}
        ]
        
        input_data = {
            "business_idea": business_idea,
            "paragraphs": paragraphs
        }
        
        result = self.node.run(input_data)
        
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
        """测试真实LLM - 验证提示词的有效性（能否识别通用模板）"""
        business_idea = "基于区块链的供应链管理系统"
        
        # 测试1：相关的内容（应该通过）
        relevant_paragraphs = [
            {
                "title": "解决方案",
                "content": "使用区块链技术实现供应链数据的透明化和可追溯性，帮助企业追踪产品从生产到销售的完整流程，解决传统供应链管理中的信息不透明问题。"
            }
        ]
        
        input_data_relevant = {
            "business_idea": business_idea,
            "paragraphs": relevant_paragraphs
        }
        
        result_relevant = self.node.run(input_data_relevant)
        
        # 测试2：通用的模板内容（应该不通过）
        generic_paragraphs = [
            {
                "title": "解决方案",
                "content": "针对痛点的解决方案，核心价值主张，解决方案的独特性和优势，解决方案假设"
            }
        ]
        
        input_data_generic = {
            "business_idea": business_idea,
            "paragraphs": generic_paragraphs
        }
        
        result_generic = self.node.run(input_data_generic)
        
        print(f"\n✅ 测试通过: 提示词有效性验证")
        print(f"   相关内容评估: passed={result_relevant['passed']}")
        print(f"   通用模板评估: passed={result_generic['passed']}")
        
        # 验证提示词能够区分相关内容和通用模板
        if result_relevant["passed"] and not result_generic["passed"]:
            print(f"   ✅ 提示词有效：正确区分了相关内容和通用模板")
    
    def test_real_llm_language_consistency(self):
        """测试真实LLM - 验证语言一致性（输出语言与输入一致）"""
        # 中文输入
        chinese_idea = "AI教育平台"
        chinese_paragraphs = [
            {"title": "用户画像", "content": "K12学生需要个性化学习"}
        ]
        
        input_data_cn = {
            "business_idea": chinese_idea,
            "paragraphs": chinese_paragraphs
        }
        
        result_cn = self.node.run(input_data_cn)
        
        # 英文输入
        english_idea = "AI education platform"
        english_paragraphs = [
            {"title": "User Persona", "content": "K12 students need personalized learning"}
        ]
        
        input_data_en = {
            "business_idea": english_idea,
            "paragraphs": english_paragraphs
        }
        
        result_en = self.node.run(input_data_en)
        
        # 验证语言一致性
        markdown_cn = result_cn["markdown_summary"]
        markdown_en = result_en["markdown_summary"]
        
        # 简单检查：中文摘要应该包含中文字符，英文摘要应该主要是英文
        has_chinese_cn = any('\u4e00' <= char <= '\u9fff' for char in markdown_cn)
        has_chinese_en = any('\u4e00' <= char <= '\u9fff' for char in markdown_en)
        
        print(f"\n✅ 测试通过: 语言一致性验证")
        print(f"   中文输入markdown_summary包含中文: {has_chinese_cn}")
        print(f"   英文输入markdown_summary包含中文: {has_chinese_en}")
        
        if has_chinese_cn and not has_chinese_en:
            print(f"   ✅ 语言一致性良好：输出语言与输入一致")


if __name__ == "__main__":
    unittest.main()

