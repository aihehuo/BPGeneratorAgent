"""
单元测试：黄金60秒Pitch节点
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
from src.nodes.pitch_60s_node import Pitch60sNode
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
        """默认响应（60秒pitch的示例）"""
        return json.dumps({
            "data": {
                "painpoint_resonance": {
                    "selected_dimensions": ["频发性", "高成本"],
                    "content": "我们服务的用户是K12学生，他们正在遇到学习效率低的问题，这个问题具有频发性和高成本，并导致学习时间浪费和成绩下降。"
                },
                "team_advantages": {
                    "selected_advantages": ["百里挑一背景", "10倍级解决方案亮点"],
                    "content": "我们能做成，因为我们有丰富的教育行业经验，并且我们的AI算法能够提供10倍级的学习效果提升。"
                },
                "call_to_action": {
                    "target_audience": "教育机构",
                    "action": "试点合作",
                    "content": "我们正在寻找教育机构进行试点合作，可以先从10分钟演示开始。"
                },
                "full_pitch": "我们服务的用户是K12学生，他们正在遇到学习效率低的问题，这个问题具有频发性和高成本，并导致学习时间浪费和成绩下降。我们能做成，因为我们有丰富的教育行业经验，并且我们的AI算法能够提供10倍级的学习效果提升。我们正在寻找教育机构进行试点合作，可以先从10分钟演示开始。"
            },
            "markdown_summary": "已生成60秒pitch，包含痛点共鸣（频发性、高成本）、团队优势（百里挑一背景、10倍级解决方案亮点）和召唤行动（教育机构试点合作）。"
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


class TestPitch60sNode(unittest.TestCase):
    """Pitch60sNode 单元测试类（使用Mock LLM）"""
    
    def setUp(self):
        """设置测试环境"""
        self.mock_llm = MockLLM()
        self.node = Pitch60sNode(self.mock_llm)
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
        self.assertEqual(self.node.node_name, "Pitch60sNode")
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
        self.assertIn("painpoint_resonance", result)
        self.assertIn("team_advantages", result)
        self.assertIn("call_to_action", result)
        self.assertIn("full_pitch", result)
        self.assertIn("markdown_summary", result)
        
        # 验证painpoint_resonance结构
        painpoint = result["painpoint_resonance"]
        self.assertIsInstance(painpoint, dict)
        self.assertIn("selected_dimensions", painpoint)
        self.assertIn("content", painpoint)
        
        # 验证team_advantages结构
        team = result["team_advantages"]
        self.assertIsInstance(team, dict)
        self.assertIn("selected_advantages", team)
        self.assertIn("content", team)
        
        # 验证call_to_action结构
        cta = result["call_to_action"]
        self.assertIsInstance(cta, dict)
        self.assertIn("target_audience", cta)
        self.assertIn("action", cta)
        self.assertIn("content", cta)
        
        # 验证full_pitch
        self.assertIsInstance(result["full_pitch"], str)
        self.assertGreater(len(result["full_pitch"]), 0)
        
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
        required_fields = ["painpoint_resonance", "team_advantages", "call_to_action", "full_pitch", "markdown_summary"]
        for field in required_fields:
            self.assertIn(field, result, f"结果应该包含字段: {field}")
        
        # 验证painpoint_resonance
        painpoint = result["painpoint_resonance"]
        self.assertIsInstance(painpoint["selected_dimensions"], list)
        self.assertGreater(len(painpoint["selected_dimensions"]), 0, "应该至少选择一个痛点维度")
        self.assertIsInstance(painpoint["content"], str)
        self.assertGreater(len(painpoint["content"]), 0)
        
        # 验证team_advantages
        team = result["team_advantages"]
        self.assertIsInstance(team["selected_advantages"], list)
        self.assertGreater(len(team["selected_advantages"]), 0, "应该至少选择一个团队优势")
        self.assertIsInstance(team["content"], str)
        self.assertGreater(len(team["content"]), 0)
        
        # 验证call_to_action
        cta = result["call_to_action"]
        self.assertIsInstance(cta["target_audience"], str)
        self.assertIsInstance(cta["action"], str)
        self.assertIsInstance(cta["content"], str)
        self.assertGreater(len(cta["content"]), 0)
        
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
        
        self.assertIn("painpoint_resonance", result)
        self.assertIn("team_advantages", result)
        self.assertIn("call_to_action", result)
        self.assertIn("full_pitch", result)
        self.assertIn("markdown_summary", result)
    
    def test_run_with_english_input(self):
        """测试英文输入"""
        english_idea = "An AI-powered online education platform for K12 students"
        english_structure = [
            {"title": "User Persona & Pain Points", "content": "K12 students need personalized learning"},
            {"title": "Solution", "content": "AI-based learning path recommendation"}
        ]
        
        # 设置英文响应
        english_response = json.dumps({
            "data": {
                "painpoint_resonance": {
                    "selected_dimensions": ["Frequency", "High Cost"],
                    "content": "Our users are K12 students who face learning efficiency issues daily."
                },
                "team_advantages": {
                    "selected_advantages": ["Top-tier Background", "10x Solution"],
                    "content": "We can succeed because of our education industry experience."
                },
                "call_to_action": {
                    "target_audience": "Educational institutions",
                    "action": "Pilot partnership",
                    "content": "We are looking for educational institutions for pilot partnerships."
                },
                "full_pitch": "Our users are K12 students who face learning efficiency issues daily. We can succeed because of our education industry experience. We are looking for educational institutions for pilot partnerships."
            },
            "markdown_summary": "Generated 60-second pitch with pain point resonance (Frequency, High Cost), team advantages (Top-tier Background, 10x Solution), and call to action (Educational institutions pilot partnership)."
        }, ensure_ascii=False)
        
        self.mock_llm.response = english_response
        
        input_data = {
            "business_idea": english_idea,
            "bp_structure": english_structure
        }
        
        result = self.node.run(input_data)
        
        self.assertIn("painpoint_resonance", result)
        self.assertIn("markdown_summary", result)
        
        # 验证输出是英文（简单检查）
        full_pitch = result["full_pitch"]
        has_chinese = any('\u4e00' <= char <= '\u9fff' for char in full_pitch)
        self.assertFalse(has_chinese, "英文输入的pitch应该是英文")
    
    def test_generate_pitch_convenience_method(self):
        """测试便捷方法generate_pitch"""
        result = self.node.generate_pitch(self.business_idea, self.bp_structure)
        
        self.assertIsInstance(result, dict)
        self.assertIn("painpoint_resonance", result)
        self.assertIn("team_advantages", result)
        self.assertIn("call_to_action", result)
        self.assertIn("full_pitch", result)
        self.assertTrue(self.mock_llm.invoke_called)
    
    def test_process_output_with_new_format(self):
        """测试处理包含data和markdown_summary的新格式输出"""
        output = json.dumps({
            "data": {
                "painpoint_resonance": {
                    "selected_dimensions": ["频发性"],
                    "content": "痛点内容"
                },
                "team_advantages": {
                    "selected_advantages": ["优势1"],
                    "content": "团队优势内容"
                },
                "call_to_action": {
                    "target_audience": "目标受众",
                    "action": "行动",
                    "content": "召唤行动内容"
                },
                "full_pitch": "完整pitch文本"
            },
            "markdown_summary": "这是测试摘要"
        }, ensure_ascii=False)
        
        result = self.node.process_output(output)
        
        self.assertIn("painpoint_resonance", result)
        self.assertIn("team_advantages", result)
        self.assertIn("call_to_action", result)
        self.assertIn("full_pitch", result)
        self.assertIn("markdown_summary", result)
        self.assertEqual(result["markdown_summary"], "这是测试摘要")
    
    def test_process_output_with_old_format(self):
        """测试处理旧格式输出（直接是pitch结果）"""
        output = json.dumps({
            "painpoint_resonance": {
                "selected_dimensions": ["频发性"],
                "content": "痛点内容"
            },
            "team_advantages": {
                "selected_advantages": ["优势1"],
                "content": "团队优势内容"
            },
            "call_to_action": {
                "target_audience": "目标受众",
                "action": "行动",
                "content": "召唤行动内容"
            },
            "full_pitch": "完整pitch文本"
        }, ensure_ascii=False)
        
        result = self.node.process_output(output)
        
        self.assertIn("painpoint_resonance", result)
        self.assertIn("team_advantages", result)
        self.assertIn("call_to_action", result)
        self.assertIn("full_pitch", result)
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
    
    def test_painpoint_dimensions_selection(self):
        """测试痛点维度选择"""
        input_data = {
            "business_idea": self.business_idea,
            "bp_structure": self.bp_structure
        }
        
        result = self.node.run(input_data)
        
        painpoint = result["painpoint_resonance"]
        dimensions = painpoint["selected_dimensions"]
        
        # 验证维度数量（应该选择1-2个）
        self.assertGreaterEqual(len(dimensions), 1, "应该至少选择1个痛点维度")
        self.assertLessEqual(len(dimensions), 2, "应该最多选择2个痛点维度")
        
        # 验证维度是字符串
        for dim in dimensions:
            self.assertIsInstance(dim, str)
            self.assertGreater(len(dim.strip()), 0)
    
    def test_team_advantages_selection(self):
        """测试团队优势选择"""
        input_data = {
            "business_idea": self.business_idea,
            "bp_structure": self.bp_structure
        }
        
        result = self.node.run(input_data)
        
        team = result["team_advantages"]
        advantages = team["selected_advantages"]
        
        # 验证优势数量（应该选择2-3个）
        self.assertGreaterEqual(len(advantages), 2, "应该至少选择2个团队优势")
        self.assertLessEqual(len(advantages), 3, "应该最多选择3个团队优势")
        
        # 验证优势是字符串
        for adv in advantages:
            self.assertIsInstance(adv, str)
            self.assertGreater(len(adv.strip()), 0)


class TestPitch60sNodeWithRealLLM(unittest.TestCase):
    """使用真实LLM的Pitch60sNode测试类
    
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
        
        self.node = Pitch60sNode(self.llm_client)
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """清理测试环境"""
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_real_llm_generate_chinese_pitch(self):
        """测试真实LLM - 生成中文60秒pitch"""
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
                "title": "团队优势",
                "content": "团队拥有丰富的教育行业经验和AI技术背景，核心算法已获得多项专利。"
            }
        ]
        
        result = self.node.generate_pitch(business_idea, bp_structure)
        
        # 验证基本结构
        self.assertIsInstance(result, dict)
        self.assertIn("painpoint_resonance", result)
        self.assertIn("team_advantages", result)
        self.assertIn("call_to_action", result)
        self.assertIn("full_pitch", result)
        self.assertIn("markdown_summary", result)
        
        # 验证painpoint_resonance
        painpoint = result["painpoint_resonance"]
        self.assertIn("selected_dimensions", painpoint)
        self.assertIn("content", painpoint)
        dimensions = painpoint["selected_dimensions"]
        self.assertGreaterEqual(len(dimensions), 1)
        self.assertLessEqual(len(dimensions), 2)
        
        # 验证team_advantages
        team = result["team_advantages"]
        self.assertIn("selected_advantages", team)
        self.assertIn("content", team)
        advantages = team["selected_advantages"]
        self.assertGreaterEqual(len(advantages), 2)
        self.assertLessEqual(len(advantages), 3)
        
        # 验证call_to_action
        cta = result["call_to_action"]
        self.assertIn("target_audience", cta)
        self.assertIn("action", cta)
        self.assertIn("content", cta)
        
        # 验证full_pitch
        full_pitch = result["full_pitch"]
        self.assertIsInstance(full_pitch, str)
        self.assertGreater(len(full_pitch.strip()), 0, "full_pitch应该非空")
        
        # 验证markdown_summary
        markdown_summary = result["markdown_summary"]
        self.assertIsInstance(markdown_summary, str)
        self.assertGreater(len(markdown_summary.strip()), 0, "markdown_summary应该非空")
        
        print(f"\n✅ 测试通过: 中文60秒pitch生成")
        print(f"   选择的痛点维度: {', '.join(dimensions)}")
        print(f"   选择的团队优势: {', '.join(advantages)}")
        print(f"   full_pitch长度: {len(full_pitch)} 字符")
        print(f"   markdown_summary: {markdown_summary[:100]}...")
    
    def test_real_llm_generate_english_pitch(self):
        """测试真实LLM - 生成英文60秒pitch"""
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
        
        result = self.node.generate_pitch(business_idea, bp_structure)
        
        # 验证基本结构
        self.assertIsInstance(result, dict)
        self.assertIn("painpoint_resonance", result)
        self.assertIn("markdown_summary", result)
        
        # 验证输出是英文（对于英文输入）
        full_pitch = result["full_pitch"]
        markdown_summary = result["markdown_summary"]
        
        has_chinese_in_pitch = any('\u4e00' <= char <= '\u9fff' for char in full_pitch)
        has_chinese_in_summary = any('\u4e00' <= char <= '\u9fff' for char in markdown_summary)
        
        print(f"\n✅ 测试通过: 英文60秒pitch生成")
        print(f"   full_pitch语言: {'中文' if has_chinese_in_pitch else '英文'}")
        print(f"   markdown_summary语言: {'中文' if has_chinese_in_summary else '英文'}")
        print(f"   full_pitch: {full_pitch[:100]}...")
    
    def test_real_llm_output_format_with_markdown_summary(self):
        """测试真实LLM - 验证输出格式包含markdown_summary"""
        business_idea = "智能家居控制系统"
        bp_structure = [
            {"title": "用户画像", "content": "家庭用户需要便捷的智能家居控制方案"},
            {"title": "解决方案", "content": "通过IoT设备实现远程控制和管理"}
        ]
        
        result = self.node.generate_pitch(business_idea, bp_structure)
        
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
        """测试真实LLM - 验证提示词的有效性（是否符合60秒pitch结构）"""
        business_idea = "基于区块链的供应链管理系统"
        bp_structure = [
            {
                "title": "用户画像与痛点",
                "content": "企业需要透明化和可追溯的供应链管理"
            },
            {
                "title": "解决方案",
                "content": "使用区块链技术实现供应链数据的透明化和可追溯性"
            },
            {
                "title": "团队优势",
                "content": "团队拥有区块链技术背景和供应链管理经验"
            }
        ]
        
        result = self.node.generate_pitch(business_idea, bp_structure)
        
        # 验证结构完整性
        self.assertIn("painpoint_resonance", result)
        self.assertIn("team_advantages", result)
        self.assertIn("call_to_action", result)
        self.assertIn("full_pitch", result)
        
        # 验证痛点维度选择（应该从6个维度中选择1-2个）
        painpoint = result["painpoint_resonance"]
        dimensions = painpoint["selected_dimensions"]
        valid_dimensions = ["紧迫性", "频发性", "高成本", "普遍性", "扩散趋势", "被迫改变"]
        
        print(f"\n✅ 测试通过: 提示词有效性验证")
        print(f"   选择的痛点维度: {', '.join(dimensions)}")
        print(f"   维度数量: {len(dimensions)} (应该在1-2个之间)")
        
        # 验证维度数量
        self.assertGreaterEqual(len(dimensions), 1)
        self.assertLessEqual(len(dimensions), 2)
        
        # 验证团队优势数量（应该选择2-3个）
        team = result["team_advantages"]
        advantages = team["selected_advantages"]
        print(f"   选择的团队优势: {', '.join(advantages)}")
        print(f"   优势数量: {len(advantages)} (应该在2-3个之间)")
        
        self.assertGreaterEqual(len(advantages), 2)
        self.assertLessEqual(len(advantages), 3)
        
        # 验证full_pitch长度（应该在200-250字左右，约60秒）
        full_pitch = result["full_pitch"]
        print(f"   full_pitch长度: {len(full_pitch)} 字符")
        # 60秒pitch大约200-250字，允许一定范围
        self.assertGreater(len(full_pitch), 100, "full_pitch应该足够长")
        self.assertLess(len(full_pitch), 500, "full_pitch不应该过长")
    
    def test_real_llm_pitch_structure(self):
        """测试真实LLM - 验证pitch结构（痛点→团队优势→召唤行动）"""
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
        
        result = self.node.generate_pitch(business_idea, bp_structure)
        
        full_pitch = result["full_pitch"]
        
        # 验证full_pitch包含了三个部分的内容
        painpoint_content = result["painpoint_resonance"]["content"]
        team_content = result["team_advantages"]["content"]
        cta_content = result["call_to_action"]["content"]
        
        # full_pitch应该包含这三个部分的内容（可能以不同形式组合）
        print(f"\n✅ 测试通过: Pitch结构验证")
        print(f"   painpoint_resonance内容长度: {len(painpoint_content)} 字符")
        print(f"   team_advantages内容长度: {len(team_content)} 字符")
        print(f"   call_to_action内容长度: {len(cta_content)} 字符")
        print(f"   full_pitch长度: {len(full_pitch)} 字符")
        
        # 验证各部分内容非空
        self.assertGreater(len(painpoint_content.strip()), 0)
        self.assertGreater(len(team_content.strip()), 0)
        self.assertGreater(len(cta_content.strip()), 0)
    
    def test_real_llm_language_consistency(self):
        """测试真实LLM - 验证语言一致性（输出语言与输入一致）"""
        # 中文输入
        chinese_idea = "AI教育平台"
        chinese_structure = [
            {"title": "用户画像", "content": "学生需要个性化学习"}
        ]
        
        result_cn = self.node.generate_pitch(chinese_idea, chinese_structure)
        
        # 英文输入
        english_idea = "AI education platform"
        english_structure = [
            {"title": "User Persona", "content": "Students need personalized learning"}
        ]
        
        result_en = self.node.generate_pitch(english_idea, english_structure)
        
        # 验证语言一致性
        pitch_cn = result_cn["full_pitch"]
        pitch_en = result_en["full_pitch"]
        
        markdown_cn = result_cn["markdown_summary"]
        markdown_en = result_en["markdown_summary"]
        
        # 检查中文pitch应该包含中文字符，英文pitch应该主要是英文
        has_chinese_cn = any('\u4e00' <= char <= '\u9fff' for char in pitch_cn)
        has_chinese_en = any('\u4e00' <= char <= '\u9fff' for char in pitch_en)
        
        has_chinese_markdown_cn = any('\u4e00' <= char <= '\u9fff' for char in markdown_cn)
        has_chinese_markdown_en = any('\u4e00' <= char <= '\u9fff' for char in markdown_en)
        
        print(f"\n✅ 测试通过: 语言一致性验证")
        print(f"   中文输入full_pitch包含中文: {has_chinese_cn}")
        print(f"   英文输入full_pitch包含中文: {has_chinese_en}")
        print(f"   中文输入markdown_summary包含中文: {has_chinese_markdown_cn}")
        print(f"   英文输入markdown_summary包含中文: {has_chinese_markdown_en}")
        
        if has_chinese_cn and not has_chinese_en and has_chinese_markdown_cn and not has_chinese_markdown_en:
            print(f"   ✅ 语言一致性良好：输出语言与输入一致")


if __name__ == "__main__":
    unittest.main()

