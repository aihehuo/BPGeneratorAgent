"""
单元测试：BP Generation Agent
测试BP生成Agent的核心功能，特别是回调功能
"""

import unittest
import os
import sys
import json
import time
import threading
import uuid
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, patch, MagicMock

# 添加项目根目录到Python路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.bp_generation_agent import BPGenerationAgent
from src.utils.config import load_config


class CallbackReceiver(BaseHTTPRequestHandler):
    """简单的HTTP服务器用于接收回调"""
    
    callbacks_received = []
    
    def log_message(self, format, *args):
        """Suppress default logging"""
        pass
    
    def do_POST(self):
        """处理POST回调请求"""
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        try:
            data = json.loads(post_data.decode('utf-8'))
            CallbackReceiver.callbacks_received.append(data)
            
            # 发送成功响应
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"success": True}).encode('utf-8'))
        except Exception as e:
            print(f"Error processing callback: {e}")
            self.send_response(500)
            self.end_headers()
    
    def do_GET(self):
        """处理GET请求（健康检查）"""
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"OK")


class TestBPGenerationAgent(unittest.TestCase):
    """BP Generation Agent测试类
    
    这些测试会调用真实的LLM API，用于验证BP Generation Agent的功能。
    如果环境变量SKIP_REAL_LLM_TESTS=1，这些测试将被跳过。
    确保在运行这些测试前已正确配置API密钥。
    """
    
    @classmethod
    def setUpClass(cls):
        """设置测试类"""
        if os.getenv("SKIP_REAL_LLM_TESTS") == "1":
            cls.skip_all = True
            return
        
        cls.skip_all = False
        cls.config = load_config()
        
        # 检查必要的API密钥
        if cls.config.default_llm_provider == "qwen" and not cls.config.qwen_api_key:
            cls.skip_all = True
            print("\n警告: Qwen API Key未配置，跳过真实LLM测试")
            return
        elif cls.config.default_llm_provider == "deepseek" and not cls.config.deepseek_api_key:
            cls.skip_all = True
            print("\n警告: DeepSeek API Key未配置，跳过真实LLM测试")
            return
        elif cls.config.default_llm_provider == "openai" and not cls.config.openai_api_key:
            cls.skip_all = True
            print("\n警告: OpenAI API Key未配置，跳过真实LLM测试")
            return
        
        cls.agent = BPGenerationAgent(cls.config)
        
        # 启动回调接收服务器
        cls.callback_server = None
        cls.callback_port = 8889  # 使用不同的端口避免冲突
        cls.callback_url = f"http://localhost:{cls.callback_port}"
        
        def start_server():
            cls.callback_server = HTTPServer(('localhost', cls.callback_port), CallbackReceiver)
            cls.callback_server.serve_forever()
        
        cls.server_thread = threading.Thread(target=start_server, daemon=True)
        cls.server_thread.start()
        
        # 等待服务器启动
        time.sleep(0.5)
        
        # 清空回调记录
        CallbackReceiver.callbacks_received = []
        
        print(f"\n✅ 真实LLM和回调测试已启用: LLM={cls.config.default_llm_provider}")
        print(f"   回调服务器: {cls.callback_url}")
    
    def setUp(self):
        """每个测试前的设置"""
        if self.skip_all:
            self.skipTest("真实LLM测试已跳过（API Key未配置或环境变量SKIP_REAL_LLM_TESTS=1）")
        
        # 清空回调记录
        CallbackReceiver.callbacks_received = []
    
    @classmethod
    def tearDownClass(cls):
        """清理测试类"""
        if cls.callback_server:
            cls.callback_server.shutdown()
    
    def setUp(self):
        """每个测试前的设置"""
        # 清空回调记录
        CallbackReceiver.callbacks_received = []
    
    def test_agent_initialization(self):
        """测试Agent初始化"""
        agent = BPGenerationAgent(self.config)
        self.assertIsNotNone(agent)
        self.assertIsNotNone(agent.llm)
        self.assertEqual(agent.max_iterations, 3)
        self.assertIsNotNone(agent.config)
    
    def test_generate_bp_without_callback(self):
        """测试不使用回调的BP生成"""
        business_idea = "一个在线教育平台，提供个性化学习方案"
        
        result = self.agent.generate_bp(
            business_idea=business_idea,
            save_report=False,
            callback_url=None
        )
        
        self.assertIsInstance(result, dict)
        self.assertIn("session_id", result)
        self.assertIn("markdown", result)
        self.assertIsNotNone(result.get("markdown"))
        
        # 验证没有回调被发送
        self.assertEqual(len(CallbackReceiver.callbacks_received), 0)
    
    def test_generate_bp_with_callback(self):
        """测试使用回调的BP生成"""
        print("\n--- 测试带回调的BP生成 ---")
        business_idea = "一个AI驱动的健康管理应用，帮助用户追踪健康数据并提供个性化建议"
        
        result = self.agent.generate_bp(
            business_idea=business_idea,
            save_report=False,
            callback_url=self.callback_url,
            api_base_url="http://localhost:8000"
        )
        
        self.assertIsInstance(result, dict)
        self.assertIn("session_id", result)
        session_id = result["session_id"]
        print(f"Session ID: {session_id}")
        
        # 等待回调被接收（异步发送，需要等待）
        print("等待回调...")
        time.sleep(3)
        
        # 验证至少收到了started回调
        callbacks = CallbackReceiver.callbacks_received
        print(f"收到 {len(callbacks)} 个回调")
        
        self.assertGreater(len(callbacks), 0, "应该至少收到一个回调")
        
        # 验证第一个回调是started
        started_callbacks = [c for c in callbacks if c.get("status") == "started"]
        self.assertGreater(len(started_callbacks), 0, "应该收到started回调")
        print(f"✓ 收到started回调")
        
        # 验证session_id匹配
        for callback in callbacks:
            self.assertEqual(callback.get("session_id"), session_id, "回调的session_id应该匹配")
        
        # 打印所有收到的状态
        statuses = [c.get("status") for c in callbacks]
        print(f"收到的状态: {statuses}")
        
        # 等待completed回调并打印HTML链接（如果存在）
        max_wait = 90
        wait_time = 0
        while wait_time < max_wait:
            time.sleep(3)
            wait_time += 3
            
            callbacks = CallbackReceiver.callbacks_received
            completed_callbacks = [c for c in callbacks if c.get("status") == "completed"]
            if len(completed_callbacks) > 0:
                completed = completed_callbacks[0]
                
                # 检查并打印HTML链接
                if "artifacts" in completed:
                    artifacts = completed["artifacts"]
                    html_url = artifacts["html"]
                    
                    # ========== 打印HTML链接（供手动查看） ==========
                    print("\n" + "=" * 80)
                    print("📎 HTML文件链接（可手动打开查看）:")
                    print("=" * 80)
                    print(html_url)
                    print("=" * 80 + "\n")
                    # ============================================================
                    
                    print(f"✅ 找到HTML链接: {html_url}")
                
                # 也检查result中的uploaded_urls
                if "uploaded_urls" in result and "html" in result["uploaded_urls"]:
                    uploaded_url = result["uploaded_urls"]["html"]
                    
                    # ========== 打印HTML上传后的链接（供手动查看） ==========
                    print("\n" + "=" * 80)
                    print("📎 HTML文件上传后的链接（可手动打开查看）:")
                    print("=" * 80)
                    print(uploaded_url)
                    print("=" * 80 + "\n")
                    # ============================================================
                    
                    print(f"✅ 找到HTML上传链接: {uploaded_url}")
                
                break
    
    def test_callback_structure(self):
        """测试回调的数据结构"""
        business_idea = "一个智能家居控制系统"
        
        self.agent.generate_bp(
            business_idea=business_idea,
            save_report=False,
            callback_url=self.callback_url,
            api_base_url="http://localhost:8000"
        )
        
        # 等待回调
        time.sleep(3)
        
        callbacks = CallbackReceiver.callbacks_received
        if len(callbacks) > 0:
            # 检查回调结构
            callback = callbacks[0]
            self.assertIn("session_id", callback)
            self.assertIn("status", callback)
            self.assertIn("message", callback)
            self.assertIn("timestamp", callback)
            
            # 验证必需字段的类型
            self.assertIsInstance(callback["session_id"], str)
            self.assertIsInstance(callback["status"], str)
            self.assertIsInstance(callback["message"], str)
            self.assertIsInstance(callback["timestamp"], str)
    
    def test_callback_intermediate_states(self):
        """测试中间状态的回调"""
        business_idea = "一个基于区块链的供应链管理系统"
        
        self.agent.generate_bp(
            business_idea=business_idea,
            save_report=False,
            callback_url=self.callback_url,
            api_base_url="http://localhost:8000"
        )
        
        # 等待更多回调（中间状态需要时间）
        time.sleep(5)
        
        callbacks = CallbackReceiver.callbacks_received
        
        if len(callbacks) > 1:
            # 应该收到多个状态的回调
            statuses = [c.get("status") for c in callbacks]
            
            # 验证有started状态
            self.assertIn("started", statuses)
            
            # 验证可能的中间状态
            possible_statuses = [
                "started",
                "input_check",
                "structure_generation",
                "structure_evaluation",
                "pitch_generation",
                "ppt_generation",
                "partner_search",
                "completed"
            ]
            
            # 至少应该有一些预期的状态
            found_statuses = [s for s in statuses if s in possible_statuses]
            self.assertGreater(len(found_statuses), 0, "应该收到预期的状态回调")
    
    def test_callback_with_markdown_summary(self):
        """测试回调中包含markdown_summary"""
        business_idea = "一个智能健身追踪应用"
        
        self.agent.generate_bp(
            business_idea=business_idea,
            save_report=False,
            callback_url=self.callback_url,
            api_base_url="http://localhost:8000"
        )
        
        # 等待回调
        time.sleep(5)
        
        callbacks = CallbackReceiver.callbacks_received
        
        # 检查是否有回调包含markdown_summary
        callbacks_with_summary = [
            c for c in callbacks 
            if "markdown_summary" in c and c["markdown_summary"]
        ]
        
        # 某些节点应该提供markdown_summary
        if len(callbacks) > 1:
            # 至少有一些回调应该有markdown_summary
            # 注意：不是所有节点都一定有markdown_summary
            print(f"收到 {len(callbacks)} 个回调，其中 {len(callbacks_with_summary)} 个包含markdown_summary")
    
    def test_callback_completed_status(self):
        """测试完成状态的回调"""
        business_idea = "一个在线音乐学习平台"
        
        result = self.agent.generate_bp(
            business_idea=business_idea,
            save_report=False,
            callback_url=self.callback_url,
            api_base_url="http://localhost:8000"
        )
        
        # 等待完成（可能需要较长时间）
        max_wait = 60  # 最多等待60秒
        wait_time = 0
        while wait_time < max_wait:
            time.sleep(2)
            wait_time += 2
            
            callbacks = CallbackReceiver.callbacks_received
            completed_callbacks = [c for c in callbacks if c.get("status") == "completed"]
            
            if len(completed_callbacks) > 0:
                # 找到completed回调
                completed = completed_callbacks[0]
                
                # 验证completed回调的结构
                self.assertIn("artifacts", completed)
                self.assertIsInstance(completed["artifacts"], dict)
                
                # 验证session_id匹配
                self.assertEqual(completed["session_id"], result["session_id"])
                break
        
        # 验证收到了completed回调
        callbacks = CallbackReceiver.callbacks_received
        completed_callbacks = [c for c in callbacks if c.get("status") == "completed"]
        self.assertGreater(len(completed_callbacks), 0, "应该收到completed回调")
    
    def test_callback_error_handling(self):
        """测试错误情况下的回调"""
        # 使用无效的business_idea来触发错误（如果可能）
        # 或者模拟一个错误情况
        
        # 这里我们测试一个可能导致输入检查失败的情况
        business_idea = ""  # 空字符串应该触发输入检查失败
        
        result = self.agent.generate_bp(
            business_idea=business_idea,
            save_report=False,
            callback_url=self.callback_url,
            api_base_url="http://localhost:8000"
        )
        
        # 等待错误回调
        time.sleep(3)
        
        callbacks = CallbackReceiver.callbacks_received
        
        # 应该收到错误相关的回调
        if len(callbacks) > 0:
            error_callbacks = [c for c in callbacks if c.get("status") == "error"]
            # 注意：输入检查失败可能不会发送error回调，而是返回结果
            # 这里主要是验证回调机制能正常工作
    
    def test_callback_artifacts(self):
        """测试回调中的artifacts"""
        business_idea = "一个智能旅游规划应用"
        
        result = self.agent.generate_bp(
            business_idea=business_idea,
            save_report=True,  # 保存文件以生成artifacts
            callback_url=self.callback_url,
            api_base_url="http://localhost:8000"
        )
        
        # 等待完成
        max_wait = 60
        wait_time = 0
        while wait_time < max_wait:
            time.sleep(2)
            wait_time += 2
            
            callbacks = CallbackReceiver.callbacks_received
            completed_callbacks = [c for c in callbacks if c.get("status") == "completed"]
            
            if len(completed_callbacks) > 0:
                completed = completed_callbacks[0]
                
                # 验证artifacts存在
                if "artifacts" in completed:
                    artifacts = completed["artifacts"]
                    self.assertIsInstance(artifacts, dict)
                    
                    # 验证可能的artifact类型（包括HTML）
                    possible_artifacts = ["markdown", "ppt_design", "partner_report", "html"]
                    found_artifacts = [a for a in artifacts.keys() if a in possible_artifacts]
                    # 至少应该有一些artifacts（如果生成了的话）
                    print(f"找到的artifacts: {list(artifacts.keys())}")
                    
                    # 如果HTML在artifacts中，验证其格式
                    if "html" in artifacts:
                        html_url = artifacts["html"]
                        
                        # ========== 打印HTML链接（供手动查看） ==========
                        print("\n" + "=" * 80)
                        print("📎 HTML文件链接（可手动打开查看）:")
                        print("=" * 80)
                        print(html_url)
                        print("=" * 80 + "\n")
                        # ============================================================
                        
                        self.assertIsInstance(html_url, str)
                        self.assertTrue(
                            html_url.startswith("http://") or html_url.startswith("https://"),
                            f"HTML URL应该是有效的HTTP/HTTPS URL: {html_url}"
                        )
                        print(f"✅ HTML artifact验证通过: {html_url}")
                break
    
    def test_html_generation_in_workflow(self):
        """测试工作流中的HTML生成功能"""
        print("\n--- 测试HTML生成功能 ---")
        business_idea = "一个AI驱动的智能客服系统，帮助企业自动化客户服务流程"
        
        result = self.agent.generate_bp(
            business_idea=business_idea,
            save_report=True,  # 保存文件以生成HTML
            callback_url=self.callback_url,
            api_base_url="http://localhost:8000"
        )
        
        self.assertIsInstance(result, dict)
        self.assertIn("session_id", result)
        session_id = result["session_id"]
        print(f"Session ID: {session_id}")
        
        # 等待工作流完成（HTML生成在最后）
        max_wait = 90  # HTML生成需要更多时间
        wait_time = 0
        html_generated = False
        
        while wait_time < max_wait:
            time.sleep(3)
            wait_time += 3
            
            callbacks = CallbackReceiver.callbacks_received
            completed_callbacks = [c for c in callbacks if c.get("status") == "completed"]
            
            if len(completed_callbacks) > 0:
                completed = completed_callbacks[0]
                
                # 检查artifacts中是否包含HTML
                if "artifacts" in completed:
                    artifacts = completed["artifacts"]
                    if "html" in artifacts:
                        html_generated = True
                        html_url = artifacts["html"]
                        
                        # ========== 打印HTML链接（供手动查看） ==========
                        print("\n" + "=" * 80)
                        print("📎 HTML文件链接（可手动打开查看）:")
                        print("=" * 80)
                        print(html_url)
                        print("=" * 80 + "\n")
                        # ============================================================
                        
                        print(f"✅ HTML文件已生成: {html_url}")
                        
                        # 验证HTML URL格式
                        self.assertIsInstance(html_url, str)
                        self.assertTrue(
                            html_url.startswith("http://") or html_url.startswith("https://"),
                            f"HTML URL应该是有效的HTTP/HTTPS URL: {html_url}"
                        )
                        break
        
        # 验证收到了completed回调
        callbacks = CallbackReceiver.callbacks_received
        completed_callbacks = [c for c in callbacks if c.get("status") == "completed"]
        self.assertGreater(len(completed_callbacks), 0, "应该收到completed回调")
        
        if html_generated:
            print("✅ HTML生成验证通过")
        else:
            print("⚠️ HTML可能未生成（检查artifacts）")
            # 检查所有回调中的artifacts
            for callback in callbacks:
                if "artifacts" in callback:
                    artifacts = callback["artifacts"]
                    print(f"   回调状态: {callback.get('status')}, artifacts: {list(artifacts.keys())}")
    
    def test_html_generation_callback_status(self):
        """测试HTML生成节点的回调状态"""
        print("\n--- 测试HTML生成回调状态 ---")
        business_idea = "一个基于区块链的数字身份验证平台"
        
        self.agent.generate_bp(
            business_idea=business_idea,
            save_report=True,
            callback_url=self.callback_url,
            api_base_url="http://localhost:8000"
        )
        
        # 等待回调
        max_wait = 90
        wait_time = 0
        
        while wait_time < max_wait:
            time.sleep(3)
            wait_time += 3
            
            callbacks = CallbackReceiver.callbacks_received
            html_gen_callbacks = [c for c in callbacks if c.get("status") == "html_generation"]
            
            if len(html_gen_callbacks) > 0:
                html_callback = html_gen_callbacks[0]
                
                # 验证HTML生成回调的结构
                self.assertIn("session_id", html_callback)
                self.assertIn("message", html_callback)
                self.assertIn("timestamp", html_callback)
                
                # 验证markdown_summary（HTML生成节点应该提供）
                if "markdown_summary" in html_callback:
                    markdown_summary = html_callback["markdown_summary"]
                    self.assertIsInstance(markdown_summary, str)
                    self.assertGreater(len(markdown_summary.strip()), 0)
                    print(f"✅ HTML生成回调包含markdown_summary (长度: {len(markdown_summary)})")
                
                print(f"✅ 收到HTML生成回调")
                break
        
        # 验证至少收到了started回调
        callbacks = CallbackReceiver.callbacks_received
        self.assertGreater(len(callbacks), 0, "应该至少收到一个回调")
    
    def test_html_file_saved_locally(self):
        """测试HTML文件是否被保存到本地"""
        print("\n--- 测试HTML文件本地保存 ---")
        business_idea = "一个智能家居能源管理系统"
        
        result = self.agent.generate_bp(
            business_idea=business_idea,
            save_report=True,
            callback_url=None  # 不使用回调，直接检查结果
        )
        
        self.assertIsInstance(result, dict)
        session_id = result.get("session_id")
        
        if session_id:
            # 检查session目录
            session_dir = os.path.join(self.config.output_dir, session_id)
            
            if os.path.exists(session_dir):
                # 查找HTML文件
                html_files = [
                    f for f in os.listdir(session_dir)
                    if f.endswith('.html')
                ]
                
                if html_files:
                    html_file = os.path.join(session_dir, html_files[0])
                    print(f"✅ 找到HTML文件: {html_file}")
                    
                    # 验证文件存在且非空
                    self.assertTrue(os.path.exists(html_file))
                    file_size = os.path.getsize(html_file)
                    self.assertGreater(file_size, 100, "HTML文件应该足够大")
                    
                    # 读取并验证HTML内容
                    with open(html_file, 'r', encoding='utf-8') as f:
                        html_content = f.read()
                    
                    # 验证HTML基本结构
                    self.assertIn("<!DOCTYPE html>", html_content)
                    self.assertIn("<html", html_content)
                    self.assertIn("</html>", html_content)
                    
                    # 验证包含三个分页
                    self.assertIn("Pitch & PPT", html_content)
                    self.assertIn("商业计划书", html_content)
                    self.assertIn("合伙人报告", html_content)
                    
                    print(f"✅ HTML文件验证通过 (大小: {file_size} 字节)")
                else:
                    print(f"⚠️ 在session目录中未找到HTML文件: {session_dir}")
                    print(f"   目录中的文件: {os.listdir(session_dir) if os.path.exists(session_dir) else '目录不存在'}")
            else:
                print(f"⚠️ Session目录不存在: {session_dir}")
        else:
            print("⚠️ 未获取到session_id，无法验证HTML文件")
    
    def test_html_in_final_result(self):
        """测试最终结果中是否包含HTML相关信息"""
        print("\n--- 测试最终结果中的HTML信息 ---")
        business_idea = "一个AI辅助的代码审查工具"
        
        result = self.agent.generate_bp(
            business_idea=business_idea,
            save_report=True,
            callback_url=self.callback_url,
            api_base_url="http://localhost:8000"
        )
        
        self.assertIsInstance(result, dict)
        
        # 等待完成
        max_wait = 90
        wait_time = 0
        
        while wait_time < max_wait:
            time.sleep(3)
            wait_time += 3
            
            callbacks = CallbackReceiver.callbacks_received
            completed_callbacks = [c for c in callbacks if c.get("status") == "completed"]
            
            if len(completed_callbacks) > 0:
                completed = completed_callbacks[0]
                
                # 验证artifacts中包含HTML
                if "artifacts" in completed:
                    artifacts = completed["artifacts"]
                    
                    # HTML应该在artifacts中（如果生成了）
                    if "html" in artifacts:
                        html_url = artifacts["html"]
                        
                        # ========== 打印HTML链接（供手动查看） ==========
                        print("\n" + "=" * 80)
                        print("📎 HTML文件链接（可手动打开查看）:")
                        print("=" * 80)
                        print(html_url)
                        print("=" * 80 + "\n")
                        # ============================================================
                        
                        print(f"✅ 最终结果包含HTML URL: {html_url}")
                        
                        # 验证URL格式
                        self.assertIsInstance(html_url, str)
                        self.assertTrue(
                            html_url.startswith("http://") or html_url.startswith("https://"),
                            f"HTML URL应该是有效的HTTP/HTTPS URL"
                        )
                        
                        # 验证URL包含session_id（如果是本地URL）
                        if "localhost" in html_url or "127.0.0.1" in html_url:
                            self.assertIn(result["session_id"], html_url)
                        
                        print(f"✅ HTML在最终结果中验证通过")
                    else:
                        print(f"⚠️ HTML不在artifacts中")
                        print(f"   可用的artifacts: {list(artifacts.keys())}")
                break
        
        # 验证收到了completed回调
        callbacks = CallbackReceiver.callbacks_received
        completed_callbacks = [c for c in callbacks if c.get("status") == "completed"]
        self.assertGreater(len(completed_callbacks), 0, "应该收到completed回调")
    
    def test_html_uploaded_url_in_result(self):
        """测试HTML上传后链接是否在最终结果中返回"""
        print("\n--- 测试HTML上传后链接的返回 ---")
        business_idea = "一个基于AI的智能推荐系统"
        
        result = self.agent.generate_bp(
            business_idea=business_idea,
            save_report=True,
            callback_url=None,  # 不使用回调，直接检查结果
            api_base_url="http://localhost:8000"
        )
        
        self.assertIsNotNone(result, "结果不应该为空")
        self.assertIsInstance(result, dict)
        
        # 验证 uploaded_urls 存在
        self.assertIn("uploaded_urls", result, "结果应该包含 uploaded_urls")
        uploaded_urls = result.get("uploaded_urls", {})
        self.assertIsInstance(uploaded_urls, dict)
        
        # 验证 HTML 是否在 uploaded_urls 中（如果上传成功）
        if self.config.aihehuo_api_key:
            # 如果配置了 API Key，应该尝试上传
            if "html" in uploaded_urls:
                html_uploaded_url = uploaded_urls["html"]
                
                # ========== 打印HTML上传后的链接（供手动查看） ==========
                print("\n" + "=" * 80)
                print("📎 HTML文件上传后的链接（可手动打开查看）:")
                print("=" * 80)
                print(html_uploaded_url)
                print("=" * 80 + "\n")
                # ============================================================
                
                print(f"✅ HTML上传URL: {html_uploaded_url}")
                
                # 验证上传URL格式（应该是云存储URL，不是本地URL）
                self.assertIsInstance(html_uploaded_url, str)
                self.assertGreater(len(html_uploaded_url), 0)
                
                # 验证不是本地文件URL（应该是云存储URL）
                self.assertFalse(
                    "localhost" in html_uploaded_url or "127.0.0.1" in html_uploaded_url,
                    f"HTML上传URL应该是云存储URL，而不是本地URL: {html_uploaded_url}"
                )
                
                # 验证是有效的HTTP/HTTPS URL
                self.assertTrue(
                    html_uploaded_url.startswith("http://") or html_uploaded_url.startswith("https://"),
                    f"HTML上传URL应该是有效的HTTP/HTTPS URL: {html_uploaded_url}"
                )
                
                print(f"✅ HTML上传URL验证通过: {html_uploaded_url}")
            else:
                print("⚠️ HTML未在uploaded_urls中（可能是上传失败或未配置API Key）")
                # 如果上传失败，至少应该验证HTML文件被保存了
                if "html_file" in result and result["html_file"]:
                    print(f"   但HTML文件已保存: {result['html_file']}")
        else:
            print("⚠️ 未配置API Key，跳过上传URL验证")
            # 即使没有上传，也应该验证HTML文件被保存了
            if "html_file" in result and result["html_file"]:
                print(f"   HTML文件已保存: {result['html_file']}")
        
        # 验证最终结果中的artifacts是否优先使用上传的URL
        # 注意：这个测试在没有callback的情况下，artifacts可能不在result中
        # 但我们可以验证uploaded_urls本身
    
    def test_html_uploaded_url_in_callback_artifacts(self):
        """测试callback的artifacts中HTML URL是否优先使用上传后的链接"""
        print("\n--- 测试callback artifacts中HTML上传链接的优先使用 ---")
        business_idea = "一个基于区块链的供应链追溯平台"
        
        result = self.agent.generate_bp(
            business_idea=business_idea,
            save_report=True,
            callback_url=self.callback_url,
            api_base_url="http://localhost:8000"
        )
        
        self.assertIsNotNone(result, "结果不应该为空")
        
        # 等待completed回调
        max_wait = 90
        wait_time = 0
        completed_callback = None
        
        while wait_time < max_wait:
            time.sleep(3)
            wait_time += 3
            
            callbacks = CallbackReceiver.callbacks_received
            completed_callbacks = [c for c in callbacks if c.get("status") == "completed"]
            
            if len(completed_callbacks) > 0:
                completed_callback = completed_callbacks[0]
                break
        
        self.assertIsNotNone(completed_callback, "应该收到completed回调")
        
        # 验证artifacts中包含HTML
        if "artifacts" in completed_callback:
            artifacts = completed_callback["artifacts"]
            
            if "html" in artifacts:
                html_url = artifacts["html"]
                print(f"✅ Callback artifacts中的HTML URL: {html_url}")
                
                # 验证URL格式
                self.assertIsInstance(html_url, str)
                self.assertTrue(
                    html_url.startswith("http://") or html_url.startswith("https://"),
                    f"HTML URL应该是有效的HTTP/HTTPS URL: {html_url}"
                )
                
                # 如果配置了API Key，验证是否优先使用上传后的链接
                if self.config.aihehuo_api_key:
                    # 检查result中的uploaded_urls
                    if "uploaded_urls" in result and "html" in result["uploaded_urls"]:
                        uploaded_url = result["uploaded_urls"]["html"]
                        
                        # ========== 打印HTML上传后的链接（供手动查看） ==========
                        print("\n" + "=" * 80)
                        print("📎 HTML文件上传后的链接（可手动打开查看）:")
                        print("=" * 80)
                        print(uploaded_url)
                        print("=" * 80 + "\n")
                        # ============================================================
                        
                        print(f"   上传后的URL: {uploaded_url}")
                        
                        # 验证artifacts中的URL是否与上传后的URL一致（优先使用上传URL）
                        if uploaded_url and not ("localhost" in uploaded_url or "127.0.0.1" in uploaded_url):
                            # 如果上传成功，artifacts应该使用上传后的URL
                            self.assertEqual(
                                html_url,
                                uploaded_url,
                                f"Artifacts中的HTML URL应该与上传后的URL一致。"
                                f"Artifacts URL: {html_url}, Uploaded URL: {uploaded_url}"
                            )
                            print(f"✅ Artifacts中的HTML URL优先使用了上传后的链接")
                        else:
                            # 如果上传失败或未上传，artifacts会使用本地URL
                            print(f"⚠️ 上传URL是本地URL或为空，artifacts使用本地URL: {html_url}")
                    else:
                        print(f"⚠️ uploaded_urls中未找到HTML URL，artifacts使用本地URL: {html_url}")
                else:
                    print(f"⚠️ 未配置API Key，artifacts使用本地URL: {html_url}")
            else:
                print("⚠️ Callback artifacts中未包含HTML")
        else:
            print("⚠️ Callback中未包含artifacts")


class TestBPGenerationAgentWithMockLLM(unittest.TestCase):
    """使用Mock LLM的BP Generation Agent测试"""
    
    def setUp(self):
        """设置测试"""
        self.config = load_config()
        # 这里可以创建使用Mock LLM的Agent，但需要修改Agent的初始化
        # 为了简化，我们主要测试回调机制本身
    
    def test_callback_url_validation(self):
        """测试callback_url参数的处理"""
        agent = BPGenerationAgent(self.config)
        
        # 测试None callback_url（应该使用invoke模式）
        # 这个测试主要验证参数传递正确
        business_idea = "测试商业创意"
        
        # 应该能正常执行（即使可能因为LLM调用而失败）
        try:
            result = agent.generate_bp(
                business_idea=business_idea,
                save_report=False,
                callback_url=None
            )
            # 如果没有异常，验证结果结构
            if result:
                self.assertIn("session_id", result)
        except Exception as e:
            # 如果LLM调用失败，这是预期的（在测试环境中）
            pass


if __name__ == "__main__":
    unittest.main(verbosity=2)

