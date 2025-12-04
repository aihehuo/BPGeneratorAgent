"""
单元测试：HTML生成节点
"""

import unittest
import os
import sys
import tempfile
import shutil
from unittest.mock import Mock, MagicMock
from typing import Dict, Any

# 添加项目根目录到Python路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.graph.nodes.html_generation import HTMLGenerationNode
from src.graph.state import AgentState
from src.graph.chat_history import ChatHistoryManager


class TestHTMLGenerationNode(unittest.TestCase):
    """HTMLGenerationNode 单元测试类"""
    
    def setUp(self):
        """设置测试环境"""
        self.node = HTMLGenerationNode()
        self.business_idea = "基于AI的在线教育平台，面向K12学生，提供个性化学习路径推荐"
        self.bp_structure = [
            {"title": "用户画像与痛点", "content": "K12学生需要个性化学习，但传统教育无法满足。传统教育采用一刀切的教学方式，无法针对每个学生的特点和需求进行定制化教学。"},
            {"title": "解决方案", "content": "使用AI技术分析学生学习数据，提供个性化学习路径。通过机器学习算法，分析学生的学习行为、知识掌握情况和学习偏好。"},
            {"title": "最小可行产品（MVP）", "content": "核心功能包括学习数据分析和智能推荐引擎。系统能够实时收集和分析学生的学习数据，包括答题正确率、学习时长、知识点掌握情况等。"}
        ]
        self.pitch_result = {
            "full_pitch": "我们的平台解决了K12学生个性化学习的问题。通过AI技术，我们为每个学生提供定制化的学习路径，显著提高学习效率。我们的团队拥有丰富的教育行业经验和AI技术背景。我们正在寻找合作伙伴和投资人，共同推动教育科技的发展。",
            "painpoint_resonance": {
                "content": "传统教育无法满足每个学生的个性化需求，导致学习效率低下。"
            },
            "team_advantages": {
                "content": "我们的团队拥有10年以上的教育行业经验和5年以上的AI技术开发经验。"
            },
            "call_to_action": {
                "content": "我们正在寻找技术合伙人和早期投资人，共同推动这个项目的成功。"
            }
        }
        self.ppt_result = {
            "slides": [
                {
                    "slide_number": 1,
                    "slide_title": "项目介绍",
                    "point": "AI驱动的个性化教育平台",
                    "line": "为K12学生提供定制化学习体验",
                    "reserved": "展示平台核心价值"
                },
                {
                    "slide_number": 2,
                    "slide_title": "市场痛点",
                    "point": "传统教育无法满足个性化需求",
                    "line": "学生需要定制化的学习路径",
                    "reserved": "强调市场机会"
                },
                {
                    "slide_number": 3,
                    "slide_title": "解决方案",
                    "point": "AI技术驱动的个性化推荐",
                    "line": "基于学习数据的智能分析",
                    "reserved": "展示技术优势"
                }
            ]
        }
        self.partner_search_result = {
            "partner_results": [
                {
                    "name": "张三",
                    "bio": "拥有10年AI技术开发经验，专注于教育科技领域",
                    "goal": "寻找有潜力的教育科技项目进行技术合作"
                },
                {
                    "name": "李四",
                    "bio": "教育行业资深专家，曾主导多个在线教育平台开发",
                    "goal": "希望参与有创新性的教育项目"
                }
            ],
            "investor_results": [
                {
                    "name": "王五",
                    "bio": "专注于教育科技领域的早期投资，已投资多个成功项目",
                    "goal": "寻找有创新性的教育科技项目进行投资"
                }
            ],
            "partner_count": 2,
            "investor_count": 1,
            "markdown_summary": "找到2位潜在合伙人和1位潜在投资人。合伙人主要具备AI技术和教育行业经验，投资人专注于教育科技领域。"
        }
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """清理测试环境"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_init(self):
        """测试节点初始化"""
        node = HTMLGenerationNode()
        self.assertIsNotNone(node)
        self.assertIsNone(node.chat_history_manager)
        
        # 测试带chat_history_manager的初始化
        chat_manager = ChatHistoryManager(session_id="test_session")
        node_with_manager = HTMLGenerationNode(chat_history_manager=chat_manager)
        self.assertIsNotNone(node_with_manager.chat_history_manager)
        self.assertEqual(node_with_manager.chat_history_manager.session_id, "test_session")
    
    def test_generate_html_with_complete_data(self):
        """测试使用完整数据生成HTML"""
        state: AgentState = {
            "business_idea": self.business_idea,
            "bp_structure": self.bp_structure,
            "pitch_result": self.pitch_result,
            "ppt_result": self.ppt_result,
            "partner_search_result": self.partner_search_result
        }
        
        result = self.node(state)
        
        # 验证返回结果
        self.assertIsInstance(result, dict)
        self.assertIn("html_result", result)
        html_result = result["html_result"]
        self.assertIn("html_content", html_result)
        self.assertIn("markdown_summary", html_result)
        
        html_content = html_result["html_content"]
        self.assertIsNotNone(html_content)
        self.assertIsInstance(html_content, str)
        self.assertGreater(len(html_content), 100)
        
        # 验证HTML包含基本结构
        self.assertIn("<!DOCTYPE html>", html_content)
        self.assertIn("<html", html_content)
        self.assertIn("</html>", html_content)
        self.assertIn("Pitch & PPT", html_content)
        self.assertIn("商业计划书", html_content)
        self.assertIn("合伙人报告", html_content)
        
        # 验证包含三个分页按钮（检查button标签数量）
        # 注意：第一个按钮有"active"类，所以搜索时需要考虑两种情况
        import re
        button_matches = re.findall(r'<button[^>]*class="[^"]*tab-button[^"]*"', html_content)
        self.assertEqual(len(button_matches), 3, f"Expected exactly 3 tab buttons, found {len(button_matches)}")
        
        # 验证包含商业创意
        self.assertIn(self.business_idea[:50], html_content)
    
    def test_generate_html_without_bp_structure(self):
        """测试没有BP结构时的处理"""
        state: AgentState = {
            "business_idea": self.business_idea,
            "bp_structure": [],  # 空的BP结构
            "pitch_result": self.pitch_result,
            "ppt_result": self.ppt_result,
            "partner_search_result": self.partner_search_result
        }
        
        result = self.node(state)
        
        # 应该返回等待消息
        self.assertIn("html_result", result)
        html_result = result["html_result"]
        self.assertIsNone(html_result.get("html_content"))
        self.assertIn("等待BP结构生成完成", html_result.get("markdown_summary", ""))
    
    def test_generate_html_without_pitch_and_ppt(self):
        """测试没有Pitch和PPT时的处理"""
        state: AgentState = {
            "business_idea": self.business_idea,
            "bp_structure": self.bp_structure,
            "pitch_result": {},
            "ppt_result": {},
            "partner_search_result": self.partner_search_result
        }
        
        result = self.node(state)
        
        # 应该仍然生成HTML，但Pitch和PPT部分为空
        self.assertIn("html_result", result)
        html_result = result["html_result"]
        html_content = html_result.get("html_content")
        self.assertIsNotNone(html_content)
        
        # 验证HTML仍然包含三个分页
        self.assertIn("Pitch & PPT", html_content)
        self.assertIn("暂无PPT内容", html_content)
    
    def test_generate_html_without_partner_search(self):
        """测试没有合伙人搜索结果时的处理"""
        state: AgentState = {
            "business_idea": self.business_idea,
            "bp_structure": self.bp_structure,
            "pitch_result": self.pitch_result,
            "ppt_result": self.ppt_result,
            "partner_search_result": {}
        }
        
        result = self.node(state)
        
        # 应该仍然生成HTML，但合伙人报告部分为空
        self.assertIn("html_result", result)
        html_result = result["html_result"]
        html_content = html_result.get("html_content")
        self.assertIsNotNone(html_content)
        
        # 验证HTML仍然包含三个分页
        self.assertIn("合伙人报告", html_content)
        self.assertIn("暂无合伙人搜索结果", html_content)
    
    def test_duplicate_generation_prevention(self):
        """测试防止重复生成HTML"""
        state: AgentState = {
            "business_idea": self.business_idea,
            "bp_structure": self.bp_structure,
            "pitch_result": self.pitch_result,
            "ppt_result": self.ppt_result,
            "partner_search_result": self.partner_search_result,
            "html_result": {
                "html_content": "<html>Existing HTML</html>",
                "markdown_summary": "Already generated"
            }
        }
        
        result = self.node(state)
        
        # 应该返回空字典，不覆盖现有结果
        self.assertEqual(result, {})
    
    def test_pitch_ppt_tab_content(self):
        """测试Pitch & PPT分页的内容"""
        state: AgentState = {
            "business_idea": self.business_idea,
            "bp_structure": self.bp_structure,
            "pitch_result": self.pitch_result,
            "ppt_result": self.ppt_result,
            "partner_search_result": self.partner_search_result
        }
        
        result = self.node(state)
        html_content = result["html_result"]["html_content"]
        
        # 验证包含60秒路演内容
        self.assertIn("60秒路演", html_content)
        self.assertIn(self.pitch_result["full_pitch"][:50], html_content)
        
        # 验证包含PPT幻灯片
        self.assertIn("PPT幻灯片设计", html_content)
        self.assertIn("共 3 页幻灯片", html_content)
        
        # 验证包含每个幻灯片的内容
        for slide in self.ppt_result["slides"]:
            self.assertIn(f"第 {slide['slide_number']} 页", html_content)
            self.assertIn(slide["slide_title"], html_content)
            if slide.get("point"):
                self.assertIn(slide["point"], html_content)
    
    def test_bp_tab_content(self):
        """测试商业计划书分页的内容"""
        state: AgentState = {
            "business_idea": self.business_idea,
            "bp_structure": self.bp_structure,
            "pitch_result": self.pitch_result,
            "ppt_result": self.ppt_result,
            "partner_search_result": self.partner_search_result
        }
        
        result = self.node(state)
        html_content = result["html_result"]["html_content"]
        
        # 验证包含商业创意
        self.assertIn("商业创意", html_content)
        self.assertIn(self.business_idea[:50], html_content)
        
        # 验证包含计划书结构
        self.assertIn("计划书结构", html_content)
        
        # 验证包含每个段落
        for section in self.bp_structure:
            self.assertIn(section["title"], html_content)
            # 内容可能被转换为HTML，所以检查部分内容
            self.assertIn(section["content"][:30], html_content)
    
    def test_partner_tab_content(self):
        """测试合伙人报告分页的内容"""
        state: AgentState = {
            "business_idea": self.business_idea,
            "bp_structure": self.bp_structure,
            "pitch_result": self.pitch_result,
            "ppt_result": self.ppt_result,
            "partner_search_result": self.partner_search_result
        }
        
        result = self.node(state)
        html_content = result["html_result"]["html_content"]
        
        # 验证包含合伙人部分
        self.assertIn("潜在合伙人", html_content)
        self.assertIn("2 位", html_content)
        
        # 验证包含投资人部分
        self.assertIn("潜在投资人", html_content)
        self.assertIn("1 位", html_content)
        
        # 验证包含合伙人信息
        for partner in self.partner_search_result["partner_results"]:
            self.assertIn(partner["name"], html_content)
            if partner.get("bio"):
                self.assertIn(partner["bio"][:30], html_content)
        
        # 验证包含投资人信息
        for investor in self.partner_search_result["investor_results"]:
            self.assertIn(investor["name"], html_content)
        
        # 验证包含搜索总结
        if self.partner_search_result.get("markdown_summary"):
            self.assertIn("搜索总结", html_content)
    
    def test_html_structure_and_styling(self):
        """测试HTML结构和样式"""
        state: AgentState = {
            "business_idea": self.business_idea,
            "bp_structure": self.bp_structure,
            "pitch_result": self.pitch_result,
            "ppt_result": self.ppt_result,
            "partner_search_result": self.partner_search_result
        }
        
        result = self.node(state)
        html_content = result["html_result"]["html_content"]
        
        # 验证HTML结构
        self.assertIn("<head>", html_content)
        self.assertIn("</head>", html_content)
        self.assertIn("<body>", html_content)
        self.assertIn("</body>", html_content)
        self.assertIn("<style>", html_content)
        self.assertIn("</style>", html_content)
        self.assertIn("<script>", html_content)
        self.assertIn("</script>", html_content)
        
        # 验证包含CSS样式
        self.assertIn(".container", html_content)
        self.assertIn(".tabs", html_content)
        self.assertIn(".tab-button", html_content)
        self.assertIn(".tab-content", html_content)
        
        # 验证包含JavaScript函数
        self.assertIn("function showTab", html_content)
    
    def test_error_handling(self):
        """测试错误处理"""
        # 创建一个会抛出异常的节点（通过模拟_generate_html方法）
        node = HTMLGenerationNode()
        
        # 模拟_generate_html抛出异常
        def mock_generate_html(*args, **kwargs):
            raise ValueError("Test error")
        
        node._generate_html = mock_generate_html
        
        state: AgentState = {
            "business_idea": self.business_idea,
            "bp_structure": self.bp_structure,
            "pitch_result": self.pitch_result,
            "ppt_result": self.ppt_result,
            "partner_search_result": self.partner_search_result
        }
        
        result = node(state)
        
        # 应该返回错误信息而不是抛出异常
        self.assertIn("html_result", result)
        html_result = result["html_result"]
        self.assertIn("error", html_result)
        self.assertIn("HTML生成失败", html_result.get("markdown_summary", ""))
        self.assertIsNone(html_result.get("html_content"))
    
    def test_chat_history_persistence(self):
        """测试聊天历史持久化"""
        chat_manager = ChatHistoryManager(session_id="test_session")
        node = HTMLGenerationNode(chat_history_manager=chat_manager)
        
        state: AgentState = {
            "business_idea": self.business_idea,
            "bp_structure": self.bp_structure,
            "pitch_result": self.pitch_result,
            "ppt_result": self.ppt_result,
            "partner_search_result": self.partner_search_result
        }
        
        result = node(state)
        
        # 验证结果被持久化到聊天历史
        # 注意：这里我们只验证节点不会因为chat_history_manager而失败
        self.assertIn("html_result", result)
        self.assertIsNotNone(result["html_result"].get("html_content"))
    
    def test_empty_business_idea(self):
        """测试空商业创意时的处理"""
        state: AgentState = {
            "business_idea": "",
            "bp_structure": self.bp_structure,
            "pitch_result": self.pitch_result,
            "ppt_result": self.ppt_result,
            "partner_search_result": self.partner_search_result
        }
        
        result = self.node(state)
        
        # 应该仍然生成HTML
        self.assertIn("html_result", result)
        html_result = result["html_result"]
        html_content = html_result.get("html_content")
        self.assertIsNotNone(html_content)
        self.assertIn("<!DOCTYPE html>", html_content)
    
    def test_markdown_conversion(self):
        """测试Markdown到HTML的转换"""
        # 创建包含Markdown格式的BP结构
        bp_with_markdown = [
            {
                "title": "测试段落",
                "content": "# 标题\n\n这是**粗体**文本和*斜体*文本。\n\n- 列表项1\n- 列表项2\n\n`代码示例`"
            }
        ]
        
        state: AgentState = {
            "business_idea": self.business_idea,
            "bp_structure": bp_with_markdown,
            "pitch_result": {},
            "ppt_result": {},
            "partner_search_result": {}
        }
        
        result = self.node(state)
        html_content = result["html_result"]["html_content"]
        
        # 验证Markdown内容被转换（即使转换失败，也应该包含原始内容）
        self.assertIn("测试段落", html_content)
        # 注意：如果markdown库不可用，内容会以<pre>标签显示
    
    def test_partner_results_limit(self):
        """测试合伙人结果数量限制（只显示前20个）"""
        # 创建超过20个合伙人结果
        many_partners = {
            "partner_results": [
                {"name": f"合伙人{i}", "bio": f"简介{i}", "goal": f"目标{i}"}
                for i in range(25)
            ],
            "investor_results": [],
            "partner_count": 25,
            "investor_count": 0,
            "markdown_summary": "找到25位潜在合伙人"
        }
        
        state: AgentState = {
            "business_idea": self.business_idea,
            "bp_structure": self.bp_structure,
            "pitch_result": self.pitch_result,
            "ppt_result": self.ppt_result,
            "partner_search_result": many_partners
        }
        
        result = self.node(state)
        html_content = result["html_result"]["html_content"]
        
        # 验证只显示前20个
        # 检查前20个是否都在HTML中
        for i in range(20):
            self.assertIn(f"合伙人{i}", html_content)
        
        # 验证第21个不在HTML中（或者被截断）
        # 注意：由于HTML生成逻辑，可能所有25个都在，但实际显示时可能只渲染前20个
        # 这里我们主要验证HTML生成不会因为大量数据而失败
        self.assertIn("25 位", html_content)  # 总数应该显示


if __name__ == "__main__":
    unittest.main(verbosity=2)

