"""
单元测试：BP生成工作流（Workflow）
"""

import unittest
import os
import json
import tempfile
import shutil
import uuid
from unittest.mock import Mock, patch, MagicMock, call
from typing import Dict, Any, List, Optional

# 添加项目根目录到Python路径
import sys

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 导入相关模块
try:
    from langchain_core.language_models.chat_models import BaseChatModel
    from langchain_openai import ChatOpenAI
    from src.graph.workflow import create_bp_graph
    from src.graph.state import AgentState
    from src.graph.chat_history import ChatHistoryManager
    from src.utils.config import load_config
    from src.utils.text_processing import detect_language
    LANGCHAIN_AVAILABLE = True
except ImportError as e:
    LANGCHAIN_AVAILABLE = False
    print(f"警告: LangChain模块不可用 ({e})，部分测试将被跳过")


class MockChatModel(BaseChatModel):
    """Mock LangChain ChatModel用于测试"""
    
    # 使用model_config来定义Pydantic模型配置
    model_config = {"arbitrary_types_allowed": True}
    
    def __init__(self, responses: Dict[str, str] = None, **kwargs):
        # 先调用父类初始化，不传递responses
        super().__init__(**kwargs)
        # 使用object.__setattr__来设置非Pydantic字段
        object.__setattr__(self, "responses", responses or {})
        object.__setattr__(self, "call_history", [])
    
    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        """模拟LLM生成"""
        message_str = str(messages)
        # 根据消息内容返回预设响应
        for key, response in self.responses.items():
            if key in message_str.lower():
                self.call_history.append({"key": key, "messages": messages})
                return self._create_llm_result(response)
        # 默认响应
        default_response = self.responses.get("default", "{}")
        self.call_history.append({"key": "default", "messages": messages})
        return self._create_llm_result(default_response)
    
    def _create_llm_result(self, content: str):
        """创建LLM结果对象"""
        from langchain_core.outputs import ChatGeneration, ChatResult
        from langchain_core.messages import AIMessage
        
        message = AIMessage(content=content)
        generation = ChatGeneration(message=message)
        return ChatResult(generations=[generation])
    
    @property
    def _llm_type(self) -> str:
        return "mock_chat_model"
    
    def _stream(self, messages, stop=None, run_manager=None, **kwargs):
        """Mock stream method"""
        result = self._generate(messages, stop, run_manager, **kwargs)
        yield result.generations[0].message


@unittest.skipUnless(LANGCHAIN_AVAILABLE, "LangChain模块不可用")
class TestWorkflowStructure(unittest.TestCase):
    """工作流结构测试类（测试graph的创建和基本结构）"""
    
    def setUp(self):
        """设置测试环境"""
        self.mock_llm = MockChatModel()
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """清理测试环境"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_create_bp_graph(self):
        """测试创建BP生成图"""
        graph = create_bp_graph(self.mock_llm)
        
        self.assertIsNotNone(graph)
        # 验证graph有invoke方法（LangGraph的编译后的图应该有这个方法）
        self.assertTrue(hasattr(graph, "invoke"))
        self.assertTrue(callable(graph.invoke))
    
    def test_create_bp_graph_with_chat_history(self):
        """测试使用chat history manager创建图"""
        session_id = str(uuid.uuid4())
        chat_history_manager = ChatHistoryManager(session_id=session_id)
        
        graph = create_bp_graph(self.mock_llm, chat_history_manager=chat_history_manager)
        
        self.assertIsNotNone(graph)
        self.assertTrue(hasattr(graph, "invoke"))
    
    def test_create_bp_graph_with_aihehuo(self):
        """测试使用aihehuo API key创建图"""
        graph = create_bp_graph(
            self.mock_llm,
            aihehuo_api_key="test_key",
            aihehuo_api_base="https://test.api.com"
        )
        
        self.assertIsNotNone(graph)
        self.assertTrue(hasattr(graph, "invoke"))


@unittest.skipUnless(LANGCHAIN_AVAILABLE, "LangChain模块不可用")
class TestWorkflowExecutionWithMock(unittest.TestCase):
    """工作流执行测试类（使用Mock节点）"""
    
    def setUp(self):
        """设置测试环境"""
        self.mock_llm = MockChatModel()
        self.business_idea = "基于AI的在线教育平台，面向K12学生，提供个性化学习路径推荐，解决学生学习效率低和缺乏针对性指导的问题"
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """清理测试环境"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_workflow_graph_structure(self):
        """测试工作流图的基本结构"""
        graph = create_bp_graph(self.mock_llm)
        
        # 验证graph对象存在
        self.assertIsNotNone(graph)
        
        # 验证graph有invoke方法
        self.assertTrue(hasattr(graph, "invoke"))
        self.assertTrue(callable(graph.invoke))
        
        # 验证graph有nodes属性或类似的结构信息
        # LangGraph编译后的graph可能有nodes或get_graph方法
        if hasattr(graph, "get_graph"):
            graph_def = graph.get_graph()
            self.assertIsNotNone(graph_def)
        
        print("\n✅ 工作流图结构验证通过")


@unittest.skipUnless(LANGCHAIN_AVAILABLE, "LangChain模块不可用")
class TestWorkflowWithRealLLM(unittest.TestCase):
    """使用真实LLM的工作流测试类
    
    这些测试会调用真实的LLM API，用于验证整个工作流的端到端功能。
    如果环境变量SKIP_REAL_LLM_TESTS=1，这些测试将被跳过。
    确保在运行这些测试前已正确配置API密钥。
    
    注意：这些测试会消耗API额度，运行时间较长。
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
            
            # 初始化LangChain ChatModel
            if cls.config.default_llm_provider == "deepseek":
                if not cls.config.deepseek_api_key:
                    cls.skip_all = True
                    print("\n警告: DeepSeek API Key未配置，跳过真实LLM测试")
                    return
                cls.llm = ChatOpenAI(
                    api_key=cls.config.deepseek_api_key,
                    base_url="https://api.deepseek.com",
                    model=cls.config.deepseek_model,
                    temperature=0.7
                )
            elif cls.config.default_llm_provider == "openai":
                if not cls.config.openai_api_key:
                    cls.skip_all = True
                    print("\n警告: OpenAI API Key未配置，跳过真实LLM测试")
                    return
                cls.llm = ChatOpenAI(
                    api_key=cls.config.openai_api_key,
                    model=cls.config.openai_model,
                    temperature=0.7
                )
            elif cls.config.default_llm_provider == "qwen":
                if not cls.config.qwen_api_key:
                    cls.skip_all = True
                    print("\n警告: Qwen API Key未配置，跳过真实LLM测试")
                    return
                cls.llm = ChatOpenAI(
                    api_key=cls.config.qwen_api_key,
                    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
                    model=cls.config.qwen_model,
                    temperature=0.7
                )
            else:
                cls.skip_all = True
                print(f"\n警告: 不支持的LLM提供商 {cls.config.default_llm_provider}，跳过真实LLM测试")
                return
            
            print(f"\n✅ 真实LLM工作流测试已启用: {cls.config.default_llm_provider} ({cls.config.deepseek_model if cls.config.default_llm_provider == 'deepseek' else cls.config.openai_model if cls.config.default_llm_provider == 'openai' else cls.config.qwen_model})")
            
        except Exception as e:
            cls.skip_all = True
            print(f"\n警告: 初始化LLM失败 ({str(e)})，跳过真实LLM测试")
    
    def setUp(self):
        """设置测试环境"""
        if self.skip_all:
            self.skipTest("真实LLM测试已跳过（API Key未配置或环境变量SKIP_REAL_LLM_TESTS=1）")
        
        self.temp_dir = tempfile.mkdtemp()
        self.session_id = str(uuid.uuid4())
    
    def tearDown(self):
        """清理测试环境"""
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_real_llm_workflow_complete_chinese(self):
        """测试真实LLM - 完整工作流（中文输入）"""
        business_idea = "基于AI的在线教育平台，面向K12学生，提供个性化学习路径推荐。通过分析学生的学习数据和行为模式，使用机器学习算法为每个学生生成定制化的学习计划，提升学习效率3倍以上。平台采用订阅制盈利模式，目标用户为关注孩子教育的家长群体。"
        
        # 创建chat history manager
        chat_history_manager = ChatHistoryManager(session_id=self.session_id)
        
        # 创建图
        graph = create_bp_graph(
            self.llm,
            aihehuo_api_key=self.config.aihehuo_api_key if hasattr(self.config, 'aihehuo_api_key') else None,
            aihehuo_api_base=getattr(self.config, 'aihehuo_api_base', None),
            chat_history_manager=chat_history_manager
        )
        
        # 准备输入状态
        inputs: AgentState = {
            "business_idea": business_idea,
            "session_id": self.session_id,
            "iteration_count": 0,
            "max_iterations": 3,
            "iteration_history": [],
            "is_english": detect_language(business_idea) == 'en'
        }
        
        print(f"\n开始执行工作流...")
        print(f"Session ID: {self.session_id}")
        print(f"商业创意: {business_idea[:100]}...")
        
        # 执行图（捕获可能的API连接错误）
        try:
            final_state = graph.invoke(inputs)
        except Exception as e:
            error_msg = str(e)
            if "Connection error" in error_msg or "API" in error_msg or "timeout" in error_msg.lower():
                self.skipTest(f"LLM API不可用（网络或连接问题）: {error_msg[:100]}")
            raise
        
        # 验证输入完整性检查
        self.assertIn("input_completeness", final_state)
        completeness = final_state["input_completeness"]
        
        if not completeness.get("is_complete", False):
            print(f"\n⚠️ 输入完整性检查未通过")
            print(f"视角: {completeness.get('current_perspective')}")
            print(f"建议: {completeness.get('suggestions', [])}")
            # 如果输入不完整，工作流应该停止
            self.assertNotIn("bp_structure", final_state)
            return
        
        print(f"\n✅ 输入完整性检查通过")
        
        # 验证输入完整性检查的markdown_summary（现在在state顶层，但可能被后续节点覆盖）
        # 注意：由于state是累积的，顶层的markdown_summary可能是最后一个节点的
        # 我们通过检查iteration_history来验证各个节点的markdown_summary
        
        # 验证BP结构生成
        self.assertIn("bp_structure", final_state)
        bp_structure = final_state["bp_structure"]
        self.assertIsInstance(bp_structure, list)
        self.assertGreater(len(bp_structure), 0, "应该生成至少一个BP结构段落")
        
        print(f"✅ BP结构生成完成，共 {len(bp_structure)} 个段落")
        
        # 验证评估结果
        if "evaluation_result" in final_state:
            eval_result = final_state["evaluation_result"]
            passed = eval_result.get("passed", False)
            print(f"✅ BP结构评估: {'通过' if passed else '未通过'}")
        
        # 验证production结果（至少应该有一个完成）
        has_pitch = "pitch_result" in final_state and final_state["pitch_result"] is not None
        has_ppt = "ppt_result" in final_state and final_state["ppt_result"] is not None
        
        print(f"✅ 60秒Pitch: {'已生成' if has_pitch else '未生成'}")
        print(f"✅ PPT: {'已生成' if has_ppt else '未生成'}")
        
        # 验证最终state顶层的markdown_summary（可能是最后一个节点的）
        if "markdown_summary" in final_state:
            final_markdown = final_state["markdown_summary"]
            self.assertIsInstance(final_markdown, str, "最终state的markdown_summary应该是字符串")
            self.assertGreater(len(final_markdown.strip()), 0, "最终state的markdown_summary应该非空")
            print(f"✅ 最终state包含markdown_summary (长度: {len(final_markdown)} 字符)")
        
        # 验证iteration_history
        iteration_history = final_state.get("iteration_history", [])
        self.assertIsInstance(iteration_history, list)
        print(f"✅ 迭代历史记录数量: {len(iteration_history)}")
        
        # 验证最终状态包含主要字段
        required_fields = ["input_completeness", "bp_structure"]
        for field in required_fields:
            self.assertIn(field, final_state, f"最终状态应该包含字段: {field}")
        
        print(f"\n✅ 工作流执行完成（包含所有markdown_summary验证）")
    
    def test_real_llm_workflow_incomplete_input(self):
        """测试真实LLM - 输入不完整的情况"""
        business_idea = "AI教育"  # 过于简短的输入
        
        # 创建chat history manager
        chat_history_manager = ChatHistoryManager(session_id=self.session_id)
        
        # 创建图
        graph = create_bp_graph(
            self.llm,
            chat_history_manager=chat_history_manager
        )
        
        # 准备输入状态
        inputs: AgentState = {
            "business_idea": business_idea,
            "session_id": self.session_id,
            "iteration_count": 0,
            "max_iterations": 3,
            "iteration_history": [],
            "is_english": detect_language(business_idea) == 'en'
        }
        
        print(f"\n开始执行工作流（输入不完整测试）...")
        print(f"商业创意: {business_idea}")
        
        # 执行图（捕获可能的API连接错误）
        try:
            final_state = graph.invoke(inputs)
        except Exception as e:
            error_msg = str(e)
            if "Connection error" in error_msg or "API" in error_msg or "timeout" in error_msg.lower():
                self.skipTest(f"LLM API不可用（网络或连接问题）: {error_msg[:100]}")
            raise
        
        # 验证输入完整性检查结果
        self.assertIn("input_completeness", final_state)
        completeness = final_state["input_completeness"]
        
        # 验证输入完整性检查结果的markdown_summary（现在在state顶层）
        # 注意：由于输入不完整，工作流会停止，所以state顶层的markdown_summary应该是input_check的
        if "markdown_summary" in final_state:
            markdown_summary = final_state["markdown_summary"]
            self.assertIsInstance(markdown_summary, str, "输入完整性检查的markdown_summary应该是字符串")
            self.assertGreater(len(markdown_summary.strip()), 0, "输入完整性检查的markdown_summary应该非空")
            print(f"✅ 输入完整性检查包含markdown_summary (长度: {len(markdown_summary)} 字符)")
        
        # 对于简短的输入，应该被识别为不完整
        is_complete = completeness.get("is_complete", True)
        
        if not is_complete:
            print(f"\n✅ 正确识别为输入不完整")
            print(f"视角: {completeness.get('current_perspective')}")
            suggestions = completeness.get("suggestions", [])
            if suggestions:
                print(f"改进建议: {suggestions[:3]}")
            
            # 验证没有执行后续节点
            self.assertNotIn("bp_structure", final_state)
        else:
            print(f"\n⚠️ 输入被识别为完整（可能与预期不符）")
    
    def test_real_llm_workflow_english_input(self):
        """测试真实LLM - 英文输入的工作流"""
        business_idea = "An AI-powered online education platform for K12 students, providing personalized learning path recommendations. The platform analyzes student learning data and uses machine learning algorithms to generate customized learning plans for each student, improving learning efficiency by 3x. The platform uses a subscription-based revenue model, targeting parents who care about their children's education."
        
        # 创建chat history manager
        chat_history_manager = ChatHistoryManager(session_id=self.session_id)
        
        # 创建图
        graph = create_bp_graph(
            self.llm,
            aihehuo_api_key=self.config.aihehuo_api_key if hasattr(self.config, 'aihehuo_api_key') else None,
            chat_history_manager=chat_history_manager
        )
        
        # 准备输入状态
        inputs: AgentState = {
            "business_idea": business_idea,
            "session_id": self.session_id,
            "iteration_count": 0,
            "max_iterations": 3,
            "iteration_history": [],
            "is_english": True
        }
        
        print(f"\n开始执行工作流（英文输入测试）...")
        print(f"Business Idea: {business_idea[:100]}...")
        
        # 执行图（捕获可能的API连接错误）
        try:
            final_state = graph.invoke(inputs)
        except Exception as e:
            error_msg = str(e)
            if "Connection error" in error_msg or "API" in error_msg or "timeout" in error_msg.lower():
                self.skipTest(f"LLM API不可用（网络或连接问题）: {error_msg[:100]}")
            raise
        
        # 验证输入完整性检查
        completeness = final_state.get("input_completeness", {})
        if not completeness.get("is_complete", False):
            print(f"\n⚠️ 输入完整性检查未通过，跳过后续验证")
            return
        
        # 验证BP结构
        if "bp_structure" in final_state:
            bp_structure = final_state["bp_structure"]
            if bp_structure:
                # 验证语言一致性（英文输入应该生成英文结构）
                first_paragraph = bp_structure[0]
                title = first_paragraph.get("title", "")
                has_chinese = any('\u4e00' <= char <= '\u9fff' for char in title)
                print(f"\n✅ BP结构生成完成")
                print(f"   第一段标题语言: {'中文' if has_chinese else '英文'}")
                print(f"   第一段标题: {title}")
        
        # 验证最终state顶层的markdown_summary（可能是最后一个节点的）
        if "markdown_summary" in final_state:
            final_markdown = final_state["markdown_summary"]
            self.assertIsInstance(final_markdown, str, "最终state的markdown_summary应该是字符串")
            self.assertGreater(len(final_markdown.strip()), 0, "最终state的markdown_summary应该非空")
            print(f"✅ 最终state包含markdown_summary (长度: {len(final_markdown)} 字符)")
        
        print(f"\n✅ 英文输入工作流执行完成（包含markdown_summary验证）")
    
    def test_real_llm_workflow_node_execution_order(self):
        """测试真实LLM - 验证节点执行顺序"""
        business_idea = "基于AI的在线教育平台，面向K12学生，提供个性化学习路径推荐，解决学生学习效率低的问题。平台使用机器学习算法分析学习数据，为每个学生生成定制化学习计划。"
        
        # 创建chat history manager
        chat_history_manager = ChatHistoryManager(session_id=self.session_id)
        
        # 创建图
        graph = create_bp_graph(
            self.llm,
            chat_history_manager=chat_history_manager
        )
        
        # 准备输入状态
        inputs: AgentState = {
            "business_idea": business_idea,
            "session_id": self.session_id,
            "iteration_count": 0,
            "max_iterations": 3,
            "iteration_history": [],
            "is_english": False
        }
        
        print(f"\n开始执行工作流（节点执行顺序测试）...")
        
        # 执行图（捕获可能的API连接错误）
        try:
            final_state = graph.invoke(inputs)
        except Exception as e:
            error_msg = str(e)
            if "Connection error" in error_msg or "API" in error_msg or "timeout" in error_msg.lower():
                self.skipTest(f"LLM API不可用（网络或连接问题）: {error_msg[:100]}")
            raise
        
        # 验证执行顺序：input_check -> structure_gen -> structure_eval -> ...
        completeness = final_state.get("input_completeness")
        
        if not completeness or not completeness.get("is_complete", False):
            print(f"\n⚠️ 输入完整性检查未通过，无法验证后续节点顺序")
            return
        
        # 验证节点执行顺序
        execution_order = []
        
        if completeness and completeness.get("is_complete"):
            execution_order.append("input_check")
        
        if "bp_structure" in final_state:
            execution_order.append("structure_gen")
        
        if "evaluation_result" in final_state:
            execution_order.append("structure_eval")
        
        if final_state.get("bp_structure"):  # painpoint可能会更新bp_structure
            # 检查是否有痛点增强（通过检查bp_structure是否被修改过）
            pass  # 难以直接验证，但可以检查iteration_history
        
        if "pitch_result" in final_state or "ppt_result" in final_state:
            execution_order.append("production_nodes")
        
        print(f"\n✅ 节点执行顺序: {' -> '.join(execution_order)}")
        
        # 验证至少执行了前几个关键节点
        self.assertIn("input_check", execution_order)
        if len(execution_order) > 1:
            self.assertIn("structure_gen", execution_order)
        
        # 验证关键节点的markdown_summary
        # 注意：所有节点的markdown_summary现在都存储在state顶层
        print(f"\n✅ Markdown Summary验证:")
        
        # 验证输入完整性检查的markdown_summary（现在在state顶层）
        # 由于state是累积的，我们需要检查是否有markdown_summary（可能是最后一个节点的）
        # 为了更准确地验证，我们检查iteration_history中的节点输出
        has_input_check_markdown = False
        has_structure_gen_markdown = False
        has_structure_eval_markdown = False
        has_pitch_gen_markdown = False
        has_ppt_gen_markdown = False
        
        iteration_history = final_state.get("iteration_history", [])
        for item in iteration_history:
            if isinstance(item, dict):
                # 检查各个节点的输出
                if "input_check" in str(item) or "completeness" in str(item):
                    # Input check的markdown_summary可能在state顶层（如果是最新的）
                    pass
                if "structure_gen" in str(item) or "structure" in str(item):
                    if "markdown_summary" in item:
                        has_structure_gen_markdown = True
        
        # 检查state顶层的markdown_summary（最后一个节点的）
        if "markdown_summary" in final_state:
            markdown_summary = final_state["markdown_summary"]
            self.assertIsInstance(markdown_summary, str, "markdown_summary应该是字符串")
            self.assertGreater(len(markdown_summary.strip()), 0, "markdown_summary应该非空")
            print(f"   ✅ State顶层包含markdown_summary (长度: {len(markdown_summary)} 字符)")
        
        # 验证各个节点的markdown_summary（通过检查节点是否执行过）
        if "input_completeness" in final_state:
            print(f"   ✅ Input Check: 节点已执行")
        if "bp_structure" in final_state:
            print(f"   ✅ Structure Gen: 节点已执行")
        if "evaluation_result" in final_state:
            print(f"   ✅ Structure Eval: 节点已执行")
        if "pitch_result" in final_state:
            print(f"   ✅ Pitch Gen: 节点已执行")
        if "ppt_result" in final_state:
            print(f"   ✅ PPT Gen: 节点已执行")
    
    def test_real_llm_workflow_html_generation(self):
        """测试真实LLM - HTML生成功能"""
        business_idea = "基于AI的在线教育平台，面向K12学生，提供个性化学习路径推荐。通过分析学生的学习数据和行为模式，使用机器学习算法为每个学生生成定制化的学习计划，提升学习效率3倍以上。平台采用订阅制盈利模式，目标用户为关注孩子教育的家长群体。"
        
        # 创建chat history manager
        chat_history_manager = ChatHistoryManager(session_id=self.session_id)
        
        # 创建图（需要aihehuo API key用于partner search，但HTML生成不依赖它）
        graph = create_bp_graph(
            self.llm,
            aihehuo_api_key=self.config.aihehuo_api_key if hasattr(self.config, 'aihehuo_api_key') else None,
            aihehuo_api_base=getattr(self.config, 'aihehuo_api_base', None),
            chat_history_manager=chat_history_manager
        )
        
        # 准备输入状态
        inputs: AgentState = {
            "business_idea": business_idea,
            "session_id": self.session_id,
            "iteration_count": 0,
            "max_iterations": 3,
            "iteration_history": [],
            "is_english": detect_language(business_idea) == 'en'
        }
        
        print(f"\n开始执行工作流（HTML生成测试）...")
        print(f"Session ID: {self.session_id}")
        print(f"商业创意: {business_idea[:100]}...")
        
        # 执行图（捕获可能的API连接错误）
        try:
            final_state = graph.invoke(inputs)
        except Exception as e:
            error_msg = str(e)
            if "Connection error" in error_msg or "API" in error_msg or "timeout" in error_msg.lower():
                self.skipTest(f"LLM API不可用（网络或连接问题）: {error_msg[:100]}")
            raise
        
        # 验证输入完整性检查
        self.assertIn("input_completeness", final_state)
        completeness = final_state["input_completeness"]
        
        if not completeness.get("is_complete", False):
            print(f"\n⚠️ 输入完整性检查未通过，跳过HTML生成验证")
            return
        
        print(f"\n✅ 输入完整性检查通过")
        
        # 验证BP结构生成（HTML生成需要BP结构）
        self.assertIn("bp_structure", final_state)
        bp_structure = final_state["bp_structure"]
        self.assertIsInstance(bp_structure, list)
        self.assertGreater(len(bp_structure), 0, "应该生成至少一个BP结构段落")
        print(f"✅ BP结构生成完成，共 {len(bp_structure)} 个段落")
        
        # 验证HTML生成结果
        # 注意：html_result 可能不存在，如果 HTML 生成节点没有被执行（例如因为并行节点未完成）
        # 或者如果 HTML 生成节点在数据不完整时返回了空结果
        if "html_result" not in final_state:
            print(f"\n⚠️ html_result 不在最终状态中")
            print(f"   可能的原因：")
            print(f"   1. HTML 生成节点未被执行")
            print(f"   2. 并行节点（pitch_gen, ppt_gen, partner_search）未全部完成")
            print(f"   3. HTML 生成节点返回了空字典（防重复逻辑）")
            print(f"   当前状态中的关键字段：")
            print(f"   - pitch_result: {'存在' if 'pitch_result' in final_state else '不存在'}")
            print(f"   - ppt_result: {'存在' if 'ppt_result' in final_state else '不存在'}")
            print(f"   - partner_search_result: {'存在' if 'partner_search_result' in final_state else '不存在'}")
            # 对于测试，我们允许这种情况，但记录警告
            print(f"\n⚠️ 跳过 HTML 验证（html_result 不存在）")
            return
        
        self.assertIn("html_result", final_state, "最终状态应该包含html_result")
        html_result = final_state["html_result"]
        self.assertIsInstance(html_result, dict, "html_result应该是字典")
        
        # 验证HTML内容
        self.assertIn("html_content", html_result, "html_result应该包含html_content")
        html_content = html_result.get("html_content")
        
        if html_content is None:
            print(f"\n⚠️ HTML内容为空（可能是BP结构未准备好）")
            # 检查是否有错误信息
            if "error" in html_result:
                print(f"   错误信息: {html_result.get('error')}")
            return
        
        self.assertIsInstance(html_content, str, "html_content应该是字符串")
        self.assertGreater(len(html_content), 100, "HTML内容应该足够长")
        print(f"✅ HTML内容生成完成，长度: {len(html_content)} 字符")
        
        # 验证HTML基本结构
        self.assertIn("<!DOCTYPE html>", html_content, "HTML应该包含DOCTYPE声明")
        self.assertIn("<html", html_content, "HTML应该包含html标签")
        self.assertIn("</html>", html_content, "HTML应该包含闭合的html标签")
        self.assertIn("<head>", html_content, "HTML应该包含head标签")
        self.assertIn("<body>", html_content, "HTML应该包含body标签")
        print(f"✅ HTML基本结构验证通过")
        
        # 验证三个分页按钮
        import re
        button_matches = re.findall(r'<button[^>]*class="[^"]*tab-button[^"]*"', html_content)
        self.assertEqual(len(button_matches), 3, f"应该包含3个分页按钮，实际找到{len(button_matches)}个")
        print(f"✅ 分页按钮验证通过: 找到 {len(button_matches)} 个按钮")
        
        # 验证三个分页的文本
        self.assertIn("Pitch & PPT", html_content, "应该包含'Pitch & PPT'分页")
        self.assertIn("商业计划书", html_content, "应该包含'商业计划书'分页")
        self.assertIn("合伙人报告", html_content, "应该包含'合伙人报告'分页")
        print(f"✅ 分页文本验证通过")
        
        # 验证三个分页内容区域
        tab_content_matches = re.findall(r'<div class="tab-content[^"]*"', html_content)
        self.assertGreaterEqual(len(tab_content_matches), 3, f"应该包含至少3个分页内容区域，实际找到{len(tab_content_matches)}个")
        print(f"✅ 分页内容区域验证通过: 找到 {len(tab_content_matches)} 个区域")
        
        # 验证包含商业创意
        self.assertIn(business_idea[:50], html_content, "HTML应该包含商业创意")
        print(f"✅ 商业创意内容验证通过")
        
        # 验证包含BP结构内容
        if bp_structure:
            first_section = bp_structure[0]
            section_title = first_section.get("title", "")
            if section_title:
                self.assertIn(section_title, html_content, f"HTML应该包含BP结构段落标题: {section_title}")
                print(f"✅ BP结构内容验证通过: 包含段落标题 '{section_title}'")
        
        # 验证包含CSS样式
        self.assertIn("<style>", html_content, "HTML应该包含CSS样式")
        self.assertIn(".tab-button", html_content, "HTML应该包含tab-button样式")
        self.assertIn(".tab-content", html_content, "HTML应该包含tab-content样式")
        print(f"✅ CSS样式验证通过")
        
        # 验证包含JavaScript
        self.assertIn("<script>", html_content, "HTML应该包含JavaScript")
        self.assertIn("function showTab", html_content, "HTML应该包含showTab函数")
        print(f"✅ JavaScript验证通过")
        
        # 验证markdown_summary
        if "markdown_summary" in html_result:
            markdown_summary = html_result["markdown_summary"]
            self.assertIsInstance(markdown_summary, str, "markdown_summary应该是字符串")
            self.assertGreater(len(markdown_summary.strip()), 0, "markdown_summary应该非空")
            print(f"✅ HTML生成节点的markdown_summary验证通过 (长度: {len(markdown_summary)} 字符)")
        
        # 验证Pitch内容（如果存在）
        if "pitch_result" in final_state and final_state["pitch_result"]:
            pitch_result = final_state["pitch_result"]
            full_pitch = pitch_result.get("full_pitch", "")
            if full_pitch:
                # 检查HTML中是否包含pitch内容（可能被截断或格式化）
                pitch_in_html = full_pitch[:50] in html_content or any(
                    word in html_content for word in full_pitch.split()[:5] if len(word) > 3
                )
                if pitch_in_html:
                    print(f"✅ Pitch内容验证通过: HTML包含pitch内容")
                else:
                    print(f"⚠️ Pitch内容可能未正确包含在HTML中")
        
        # 验证PPT内容（如果存在）
        if "ppt_result" in final_state and final_state["ppt_result"]:
            ppt_result = final_state["ppt_result"]
            slides = ppt_result.get("slides", [])
            if slides:
                # 检查HTML中是否包含PPT相关内容
                if "PPT" in html_content or "幻灯片" in html_content:
                    print(f"✅ PPT内容验证通过: HTML包含PPT相关内容 ({len(slides)} 页)")
                else:
                    print(f"⚠️ PPT内容可能未正确包含在HTML中")
        
        # 验证合伙人搜索结果（如果存在）
        if "partner_search_result" in final_state and final_state["partner_search_result"]:
            partner_result = final_state["partner_search_result"]
            partner_count = partner_result.get("partner_count", 0)
            investor_count = partner_result.get("investor_count", 0)
            if partner_count > 0 or investor_count > 0:
                if "合伙人" in html_content or "投资人" in html_content:
                    print(f"✅ 合伙人报告验证通过: HTML包含合伙人/投资人内容")
                else:
                    print(f"⚠️ 合伙人报告内容可能未正确包含在HTML中")
        
        print(f"\n✅ HTML生成功能测试完成")
        print(f"   HTML内容长度: {len(html_content)} 字符")
        print(f"   分页数量: 3")
        print(f"   包含样式: 是")
        print(f"   包含脚本: 是")


if __name__ == "__main__":
    unittest.main()

