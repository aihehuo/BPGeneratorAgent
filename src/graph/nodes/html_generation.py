"""
HTML Report Generation Node

Generates a comprehensive HTML report with three tabs:
1. Pitch & PPT: 60-second pitch + 10-page PPT slides
2. Business Plan: Complete BP content with rich formatting
3. Partner Report: Partner and investor search results
"""

from typing import Dict, Any, Optional
from ..state import AgentState
from ..chat_history import ChatHistoryManager
try:
    import markdown
    MARKDOWN_AVAILABLE = True
except ImportError:
    MARKDOWN_AVAILABLE = False
    print("[HTML Generation] Warning: markdown library not available. Markdown content will be displayed as plain text.")


class HTMLGenerationNode:
    """Node for generating HTML report from all generated content"""
    
    def __init__(self, chat_history_manager: Optional[ChatHistoryManager] = None):
        self.chat_history_manager = chat_history_manager
    
    def __call__(self, state: AgentState) -> Dict[str, Any]:
        """
        Generate HTML report from all generated content
        
        Args:
            state: Current agent state containing all generated content
            
        Returns:
            Dictionary with html_result containing HTML content and file path
        """
        # Check if HTML has already been generated (to avoid duplicate generation
        # when this node is called multiple times from parallel production nodes)
        existing_html_result = state.get("html_result")
        if existing_html_result and existing_html_result.get("html_content"):
            print("[HTML Generation] HTML already generated, skipping...")
            return {}  # Return empty dict to avoid overwriting existing result
        
        try:
            business_idea = state.get("business_idea", "")
            bp_structure = state.get("bp_structure", [])
            pitch_result = state.get("pitch_result", {})
            ppt_result = state.get("ppt_result", {})
            partner_search_result = state.get("partner_search_result", {})
            
            # Check if we have minimum required data (at least BP structure)
            if not bp_structure:
                print("[HTML Generation] BP structure not ready, skipping HTML generation...")
                return {
                    "html_result": {
                        "html_content": None,
                        "markdown_summary": "等待BP结构生成完成..."
                    }
                }
            
            # Generate HTML content
            # Note: In LangGraph, when multiple parallel nodes (pitch_gen, ppt_gen, partner_search)
            # all point to html_gen, html_gen will be executed multiple times (once per predecessor completion).
            # However, the state is cumulative, so each execution sees all completed nodes' results.
            # We generate HTML as soon as we have BP structure, and include whatever production
            # results are available at that time. The duplicate prevention logic above ensures
            # we only generate HTML once.
            html_content = self._generate_html(
                business_idea,
                bp_structure,
                pitch_result,
                ppt_result,
                partner_search_result
            )
            
            result = {
                "html_result": {
                    "html_content": html_content,
                    "markdown_summary": "已生成包含三个分页的HTML报告：Pitch与PPT、商业计划书、合伙人报告"
                }
            }
            
            # Persist node output to chat history
            if self.chat_history_manager:
                self.chat_history_manager.persist_node_output("html_gen", result)
            
            print("[HTML Generation] HTML report generated successfully")
            return result
            
        except Exception as e:
            error_msg = f"HTML生成失败: {str(e)}"
            print(f"[HTML Generation Error] {error_msg}")
            import traceback
            traceback.print_exc()
            return {
                "html_result": {
                    "html_content": None,
                    "error": error_msg,
                    "markdown_summary": f"HTML生成失败: {error_msg}"
                }
            }
    
    def _generate_html(
        self,
        business_idea: str,
        bp_structure: list,
        pitch_result: dict,
        ppt_result: dict,
        partner_search_result: dict
    ) -> str:
        """Generate complete HTML with three tabs"""
        
        # Tab 1: Pitch & PPT
        tab1_content = self._generate_pitch_ppt_tab(pitch_result, ppt_result)
        
        # Tab 2: Business Plan
        tab2_content = self._generate_bp_tab(business_idea, bp_structure)
        
        # Tab 3: Partner Report
        tab3_content = self._generate_partner_tab(partner_search_result)
        
        # Combine into complete HTML
        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>商业计划书 - {business_idea[:50]}...</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        
        .header h1 {{
            font-size: 28px;
            margin-bottom: 10px;
        }}
        
        .header p {{
            opacity: 0.9;
            font-size: 16px;
        }}
        
        .tabs {{
            display: flex;
            background: white;
            border-radius: 10px 10px 0 0;
            overflow: hidden;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        
        .tab-button {{
            flex: 1;
            padding: 15px 20px;
            background: #f8f9fa;
            border: none;
            cursor: pointer;
            font-size: 16px;
            font-weight: 500;
            color: #666;
            transition: all 0.3s;
            border-bottom: 3px solid transparent;
        }}
        
        .tab-button:hover {{
            background: #e9ecef;
        }}
        
        .tab-button.active {{
            background: white;
            color: #667eea;
            border-bottom-color: #667eea;
        }}
        
        .tab-content {{
            display: none;
            background: white;
            padding: 30px;
            border-radius: 0 0 10px 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            min-height: 500px;
        }}
        
        .tab-content.active {{
            display: block;
        }}
        
        .tab-content h2 {{
            color: #667eea;
            margin-bottom: 20px;
            font-size: 24px;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }}
        
        .tab-content h3 {{
            color: #555;
            margin-top: 25px;
            margin-bottom: 15px;
            font-size: 20px;
        }}
        
        .tab-content h4 {{
            color: #666;
            margin-top: 20px;
            margin-bottom: 10px;
            font-size: 18px;
        }}
        
        .tab-content p {{
            margin-bottom: 15px;
            text-align: justify;
        }}
        
        .tab-content ul, .tab-content ol {{
            margin-left: 20px;
            margin-bottom: 15px;
        }}
        
        .tab-content li {{
            margin-bottom: 8px;
        }}
        
        .slide-card {{
            background: #f8f9fa;
            border-left: 4px solid #667eea;
            padding: 20px;
            margin-bottom: 20px;
            border-radius: 5px;
        }}
        
        .slide-card h4 {{
            color: #667eea;
            margin-top: 0;
        }}
        
        .pitch-box {{
            background: linear-gradient(135deg, #667eea15 0%, #764ba215 100%);
            border: 2px solid #667eea;
            border-radius: 10px;
            padding: 25px;
            margin-bottom: 25px;
        }}
        
        .pitch-box h3 {{
            color: #667eea;
            margin-top: 0;
        }}
        
        .partner-card {{
            background: white;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 15px;
            transition: box-shadow 0.3s;
        }}
        
        .partner-card:hover {{
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }}
        
        .partner-name {{
            font-weight: bold;
            color: #667eea;
            font-size: 18px;
            margin-bottom: 8px;
        }}
        
        .partner-info {{
            color: #666;
            font-size: 14px;
            margin-bottom: 5px;
        }}
        
        .section-divider {{
            height: 2px;
            background: linear-gradient(to right, #667eea, transparent);
            margin: 30px 0;
        }}
        
        code {{
            background: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
            font-size: 14px;
        }}
        
        pre {{
            background: #f4f4f4;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
            margin-bottom: 15px;
        }}
        
        blockquote {{
            border-left: 4px solid #667eea;
            padding-left: 20px;
            margin: 20px 0;
            color: #666;
            font-style: italic;
        }}
        
        @media (max-width: 768px) {{
            .tabs {{
                flex-direction: column;
            }}
            
            .tab-button {{
                border-bottom: 1px solid #e0e0e0;
                border-right: none;
            }}
            
            .tab-button.active {{
                border-bottom-color: #e0e0e0;
                border-left: 3px solid #667eea;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>商业计划书</h1>
            <p>{business_idea[:100]}{'...' if len(business_idea) > 100 else ''}</p>
        </div>
        
        <div class="tabs">
            <button class="tab-button active" onclick="showTab(0)">Pitch & PPT</button>
            <button class="tab-button" onclick="showTab(1)">商业计划书</button>
            <button class="tab-button" onclick="showTab(2)">合伙人报告</button>
        </div>
        
        <div class="tab-content active">
            {tab1_content}
        </div>
        
        <div class="tab-content">
            {tab2_content}
        </div>
        
        <div class="tab-content">
            {tab3_content}
        </div>
    </div>
    
    <script>
        function showTab(index) {{
            const tabs = document.querySelectorAll('.tab-content');
            const buttons = document.querySelectorAll('.tab-button');
            
            tabs.forEach(tab => tab.classList.remove('active'));
            buttons.forEach(button => button.classList.remove('active'));
            
            tabs[index].classList.add('active');
            buttons[index].classList.add('active');
        }}
    </script>
</body>
</html>"""
        
        return html
    
    def _generate_pitch_ppt_tab(self, pitch_result: dict, ppt_result: dict) -> str:
        """Generate Tab 1: Pitch & PPT content"""
        content = "<h2>60秒路演 & PPT设计</h2>\n"
        
        # Pitch content
        if pitch_result:
            content += '<div class="pitch-box">\n'
            content += "<h3>60秒路演</h3>\n"
            
            full_pitch = pitch_result.get("full_pitch", "")
            if full_pitch:
                content += f'<blockquote>{full_pitch}</blockquote>\n'
            
            painpoint = pitch_result.get("painpoint_resonance", {})
            if painpoint.get("content"):
                content += "<h4>痛点共鸣</h4>\n"
                content += f'<p>{painpoint.get("content")}</p>\n'
            
            team = pitch_result.get("team_advantages", {})
            if team.get("content"):
                content += "<h4>团队优势</h4>\n"
                content += f'<p>{team.get("content")}</p>\n'
            
            cta = pitch_result.get("call_to_action", {})
            if cta.get("content"):
                content += "<h4>行动号召</h4>\n"
                content += f'<p>{cta.get("content")}</p>\n'
            
            content += "</div>\n"
        
        # PPT slides
        slides = ppt_result.get("slides", []) if ppt_result else []
        if slides:
            content += "<h3>PPT幻灯片设计</h3>\n"
            content += f'<p>共 {len(slides)} 页幻灯片</p>\n'
            
            for slide in slides:
                slide_no = slide.get("slide_number", "?")
                slide_title = slide.get("slide_title", "")
                slide_point = slide.get("point", "")
                slide_line = slide.get("line", "")
                slide_reserved = slide.get("reserved", "")
                
                content += '<div class="slide-card">\n'
                content += f'<h4>第 {slide_no} 页：{slide_title}</h4>\n'
                
                if slide_point:
                    content += f'<p><strong>要点：</strong>{slide_point}</p>\n'
                if slide_line:
                    content += f'<p><strong>支持文字：</strong>{slide_line}</p>\n'
                if slide_reserved:
                    content += f'<p><strong>预留钩子：</strong>{slide_reserved}</p>\n'
                
                content += "</div>\n"
        else:
            content += "<p>暂无PPT内容</p>\n"
        
        return content
    
    def _generate_bp_tab(self, business_idea: str, bp_structure: list) -> str:
        """Generate Tab 2: Business Plan content"""
        content = "<h2>商业计划书</h2>\n"
        content += f'<div class="pitch-box">\n'
        content += "<h3>商业创意</h3>\n"
        content += f'<p>{business_idea}</p>\n'
        content += "</div>\n"
        
        if bp_structure:
            content += "<h3>计划书结构</h3>\n"
            for idx, section in enumerate(bp_structure, 1):
                title = section.get("title", f"段落 {idx}")
                section_content = section.get("content", "")
                
                content += f'<h4>{idx}. {title}</h4>\n'
                
                # Convert markdown to HTML
                if section_content:
                    if MARKDOWN_AVAILABLE:
                        try:
                            html_section = markdown.markdown(
                                section_content,
                                extensions=['codehilite', 'tables', 'fenced_code']
                            )
                        except Exception:
                            # Fallback to plain text if markdown conversion fails
                            html_section = f"<pre>{section_content}</pre>"
                    else:
                        # Fallback to plain text if markdown library not available
                        html_section = f"<pre>{section_content}</pre>"
                    content += html_section + "\n"
                
                content += '<div class="section-divider"></div>\n'
        else:
            content += "<p>暂无商业计划书内容</p>\n"
        
        return content
    
    def _generate_partner_tab(self, partner_search_result: dict) -> str:
        """Generate Tab 3: Partner & Investor report"""
        content = "<h2>合伙人 & 投资人报告</h2>\n"
        
        if not partner_search_result:
            content += "<p>暂无合伙人搜索结果</p>\n"
            return content
        
        # Partner results
        partner_results = partner_search_result.get("partner_results", [])
        partner_count = partner_search_result.get("partner_count", 0)
        
        if partner_count > 0:
            content += f'<h3>潜在合伙人 ({partner_count} 位)</h3>\n'
            
            for partner in partner_results[:20]:  # Show top 20
                name = partner.get("name", "未知")
                bio = partner.get("bio", "")
                goal = partner.get("goal", "")
                profile_url = partner.get("profile_url", "")
                
                content += '<div class="partner-card">\n'
                # 显示姓名，如果有个人主页链接则添加链接
                if profile_url:
                    content += f'<div class="partner-name"><a href="{profile_url}" target="_blank">{name}</a></div>\n'
                else:
                    content += f'<div class="partner-name">{name}</div>\n'
                if bio:
                    # 处理换行：将换行符转换为HTML的<br>标签
                    bio_escaped = bio.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    bio_with_breaks = bio_escaped.replace('\n', '<br>')
                    bio_display = bio_with_breaks[:200] + ("..." if len(bio) > 200 else "")
                    content += f'<div class="partner-info"><strong>简介：</strong>{bio_display}</div>\n'
                if goal:
                    # 处理换行：将换行符转换为HTML的<br>标签
                    goal_escaped = goal.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    goal_with_breaks = goal_escaped.replace('\n', '<br>')
                    goal_display = goal_with_breaks[:200] + ("..." if len(goal) > 200 else "")
                    content += f'<div class="partner-info"><strong>目标：</strong>{goal_display}</div>\n'
                content += "</div>\n"
        else:
            content += "<p>未找到潜在合伙人</p>\n"
        
        content += '<div class="section-divider"></div>\n'
        
        # Investor results
        investor_results = partner_search_result.get("investor_results", [])
        investor_count = partner_search_result.get("investor_count", 0)
        
        if investor_count > 0:
            content += f'<h3>潜在投资人 ({investor_count} 位)</h3>\n'
            
            for investor in investor_results[:20]:  # Show top 20
                name = investor.get("name", "未知")
                bio = investor.get("bio", "")
                goal = investor.get("goal", "")
                profile_url = investor.get("profile_url", "")
                
                content += '<div class="partner-card">\n'
                # 显示姓名，如果有个人主页链接则添加链接
                if profile_url:
                    content += f'<div class="partner-name"><a href="{profile_url}" target="_blank">{name}</a></div>\n'
                else:
                    content += f'<div class="partner-name">{name}</div>\n'
                if bio:
                    # 处理换行：将换行符转换为HTML的<br>标签
                    bio_escaped = bio.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    bio_with_breaks = bio_escaped.replace('\n', '<br>')
                    bio_display = bio_with_breaks[:200] + ("..." if len(bio) > 200 else "")
                    content += f'<div class="partner-info"><strong>简介：</strong>{bio_display}</div>\n'
                if goal:
                    # 处理换行：将换行符转换为HTML的<br>标签
                    goal_escaped = goal.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    goal_with_breaks = goal_escaped.replace('\n', '<br>')
                    goal_display = goal_with_breaks[:200] + ("..." if len(goal) > 200 else "")
                    content += f'<div class="partner-info"><strong>目标：</strong>{goal_display}</div>\n'
                content += "</div>\n"
        else:
            content += "<p>未找到潜在投资人</p>\n"
        
        # Search summary
        markdown_summary = partner_search_result.get("markdown_summary", "")
        if markdown_summary:
            content += '<div class="section-divider"></div>\n'
            content += "<h3>搜索总结</h3>\n"
            if MARKDOWN_AVAILABLE:
                try:
                    html_summary = markdown.markdown(
                        markdown_summary,
                        extensions=['codehilite', 'tables', 'fenced_code']
                    )
                except Exception:
                    # Fallback to plain text if markdown conversion fails
                    html_summary = f"<pre>{markdown_summary}</pre>"
            else:
                # Fallback to plain text if markdown library not available
                html_summary = f"<pre>{markdown_summary}</pre>"
            content += html_summary + "\n"
        
        return content

