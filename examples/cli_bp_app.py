#!/usr/bin/env python3
"""
CLI Interactive BP Generation Program
为BP Generation Agent提供友好的命令行交互界面
"""

import os
import sys
import argparse
from datetime import datetime
from typing import Optional, Tuple

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.bp_generation_agent import BPGenerationAgent, create_bp_agent
from src.utils.config import Config, load_config, print_config
from src.utils.text_processing import detect_language

# Graph-based imports (optional)
try:
    from langchain_openai import ChatOpenAI
    from src.graph.workflow import create_bp_graph
    from src.graph.chat_history import ChatHistoryManager
    GRAPH_AVAILABLE = True
except ImportError:
    GRAPH_AVAILABLE = False


def get_input(prompt: str, default: Optional[str] = None, password: bool = False) -> str:
    """获取用户输入，支持默认值和密码输入"""
    if default:
        prompt_text = f"{prompt} [{default}]: "
    else:
        prompt_text = f"{prompt}: "
    
    if password:
        import getpass
        value = getpass.getpass(prompt_text)
    else:
        value = input(prompt_text).strip()
    
    return value if value else (default or "")


def get_choice(prompt: str, choices: list, default: Optional[str] = None) -> str:
    """获取用户选择"""
    print(f"\n{prompt}")
    for i, choice in enumerate(choices, 1):
        marker = " (默认)" if choice == default else ""
        print(f"  {i}. {choice}{marker}")
    
    while True:
        try:
            choice_input = input(f"\n请选择 [1-{len(choices)}]: ").strip()
            if not choice_input and default:
                return default
            
            choice_idx = int(choice_input) - 1
            if 0 <= choice_idx < len(choices):
                return choices[choice_idx]
            else:
                print(f"无效选择，请输入 1-{len(choices)} 之间的数字")
        except ValueError:
            print("请输入有效的数字")


def get_number(prompt: str, min_val: int, max_val: int, default: int) -> int:
    """获取数字输入"""
    while True:
        try:
            value_input = input(f"{prompt} [{default}]: ").strip()
            if not value_input:
                return default
            
            value = int(value_input)
            if min_val <= value <= max_val:
                return value
            else:
                print(f"请输入 {min_val}-{max_val} 之间的数字")
        except ValueError:
            print("请输入有效的数字")


def configure_agent_interactive() -> Tuple[Config, bool]:
    """交互式配置Agent"""
    print("\n" + "=" * 60)
    print("BP Generation Agent - 配置向导")
    print("=" * 60)
    
    # 尝试加载现有配置
    try:
        existing_config = load_config()
        print("\n检测到现有配置文件")
        use_existing = get_input("是否使用现有配置？", default="y").lower()
        if use_existing in ['y', 'yes', '是']:
            # 仍然询问实现方式
            if GRAPH_AVAILABLE:
                implementation_choice = get_choice(
                    "选择实现方式",
                    ["传统实现 (Traditional)", "LangGraph实现 (Graph-based)"],
                    default="传统实现 (Traditional)"
                )
                use_graph = "LangGraph" in implementation_choice
                return existing_config, use_graph
            else:
                return existing_config, False
    except:
        pass
    
    print("\n开始配置...")
    
    # LLM提供商选择
    llm_provider = get_choice(
        "选择LLM提供商",
        ["deepseek", "openai", "qwen"],
        default="qwen"
    )
    
    # API密钥配置
    print("\n" + "-" * 60)
    print("API密钥配置")
    print("-" * 60)
    
    deepseek_key = None
    openai_key = None
    qwen_key = None
    
    if llm_provider == "deepseek":
        deepseek_key = get_input("DeepSeek API Key", password=True)
    elif llm_provider == "openai":
        openai_key = get_input("OpenAI API Key", password=True)
    elif llm_provider == "qwen":
        qwen_key = get_input("Qwen API Key", password=True)
    
    # 模型选择
    print("\n" + "-" * 60)
    print("模型配置")
    print("-" * 60)
    
    if llm_provider == "deepseek":
        model_name = get_choice(
            "选择DeepSeek模型",
            ["deepseek-chat"],
            default="deepseek-chat"
        )
        deepseek_model = model_name
        openai_model = "gpt-4o-mini"
        qwen_model = "qwen-turbo"
    elif llm_provider == "openai":
        model_name = get_choice(
            "选择OpenAI模型",
            ["gpt-4o-mini", "gpt-4o"],
            default="gpt-4o-mini"
        )
        deepseek_model = "deepseek-chat"
        openai_model = model_name
        qwen_model = "qwen-turbo"
    else:  # qwen
        model_name = get_choice(
            "选择Qwen模型",
            ["qwen-turbo", "qwen-flash", "qwen-plus"],
            default="qwen-flash"
        )
        deepseek_model = "deepseek-chat"
        openai_model = "gpt-4o-mini"
        qwen_model = model_name
    
    # 高级配置
    print("\n" + "-" * 60)
    print("高级配置")
    print("-" * 60)
    
    max_iterations = get_number("最大迭代次数", 1, 5, 3)
    output_dir = get_input("输出目录", default="reports")
    
    # 实现方式选择
    print("\n" + "-" * 60)
    print("实现方式")
    print("-" * 60)
    
    if GRAPH_AVAILABLE:
        implementation_choice = get_choice(
            "选择实现方式",
            ["传统实现 (Traditional)", "LangGraph实现 (Graph-based)"],
            default="传统实现 (Traditional)"
        )
        use_graph = "LangGraph" in implementation_choice
        if use_graph:
            print("\n提示: LangGraph实现使用状态图工作流，提供更好的状态管理和可扩展性")
    else:
        print("提示: LangGraph未安装，只能使用传统实现")
        print("安装命令: pip install langgraph langchain-openai")
        use_graph = False
    
    # 创建配置对象
    config = Config(
        deepseek_api_key=deepseek_key,
        openai_api_key=openai_key,
        qwen_api_key=qwen_key,
        default_llm_provider=llm_provider,
        deepseek_model=deepseek_model,
        openai_model=openai_model,
        qwen_model=qwen_model,
        output_dir=output_dir,
    )
    
    # 验证配置
    if not config.validate():
        print("\n配置验证失败，请检查API密钥")
        sys.exit(1)
    
    # Return config and use_graph flag as a tuple
    return config, use_graph


def display_examples():
    """显示示例商业创意"""
    examples = [
        "一个基于AI的在线教育平台，主要面向K12学生，提供个性化学习路径推荐",
        "帮助老年人使用智能手机的AI助手应用",
        "基于区块链的供应链溯源平台",
        "智能健身教练应用，提供个性化训练计划",
        "面向中小企业的AI客服解决方案"
    ]
    
    print("\n" + "-" * 60)
    print("示例商业创意")
    print("-" * 60)
    for i, example in enumerate(examples, 1):
        print(f"{i}. {example}")
    print("-" * 60)


def get_business_idea() -> str:
    """获取商业创意输入"""
    print("\n" + "=" * 60)
    print("商业创意输入")
    print("=" * 60)
    
    show_examples = get_input("是否查看示例？", default="y").lower()
    if show_examples in ['y', 'yes', '是']:
        display_examples()
    
    print("\n请输入您的商业创意（可以多行，输入空行结束）:")
    print("提示: 描述越详细，生成的商业计划书越准确")
    
    lines = []
    while True:
        line = input()
        if not line.strip() and lines:
            break
        if line.strip():
            lines.append(line)
    
    business_idea = "\n".join(lines).strip()
    
    if not business_idea:
        print("错误: 商业创意不能为空")
        sys.exit(1)
    
    return business_idea


def get_llm_for_graph(config):
    """Initialize LangChain Chat Model based on config."""
    if config.default_llm_provider == "deepseek":
        return ChatOpenAI(
            api_key=config.deepseek_api_key,
            base_url="https://api.deepseek.com",
            model=config.deepseek_model,
            temperature=0.7
        )
    elif config.default_llm_provider == "openai":
        return ChatOpenAI(
            api_key=config.openai_api_key,
            model=config.openai_model,
            temperature=0.7
        )
    elif config.default_llm_provider == "qwen":
        return ChatOpenAI(
            api_key=config.qwen_api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            model=config.qwen_model,
            temperature=0.7
        )
    else:
        raise ValueError(f"Unsupported LLM provider: {config.default_llm_provider}")


def generate_bp_with_graph(
    business_idea: str,
    config: Config,
    session_id: Optional[str],
    save_report: bool = True
) -> dict:
    """Generate BP using LangGraph implementation."""
    import uuid
    
    # Setup session
    if not session_id:
        session_id = str(uuid.uuid4())
    else:
        # Validate session_id format
        try:
            uuid.UUID(session_id)
        except (ValueError, AttributeError):
            print(f"警告: 提供的session_id不是有效UUID格式，将生成新的Session ID")
            session_id = str(uuid.uuid4())
    
    # Convert session_id to session_dir (filesystem-based implementation)
    # TODO: In the future, this can be changed to Redis or other storage backends
    session_dir = os.path.join(config.output_dir, session_id) if save_report else None
    if session_dir:
        os.makedirs(session_dir, exist_ok=True)
    
    # Initialize LLM
    llm = get_llm_for_graph(config)
    
    # Initialize workflow-level chat history manager
    chat_history_manager = ChatHistoryManager(session_id=session_id)
    
    # Create Graph with chat history manager
    graph = create_bp_graph(llm, config.aihehuo_api_key, config.aihehuo_api_base, chat_history_manager=chat_history_manager)
    
    # Initial State (use session_id as primary identifier)
    inputs = {
        "business_idea": business_idea,
        "session_id": session_id,
        "iteration_count": 0,
        "max_iterations": 3,
        "iteration_history": [],
        "is_english": detect_language(business_idea) == 'en'
    }
    
    # Run Graph
    final_state = graph.invoke(inputs)
    
    # Determine where workflow stopped and persist final state
    stop_node = None
    completeness = final_state.get("input_completeness", {})
    if completeness and not completeness.get("is_complete", False):
        stop_node = "input_check"
    else:
        # Determine the last completed node based on state
        if final_state.get("partner_search_result"):
            stop_node = "partner_search"
        elif final_state.get("ppt_result"):
            stop_node = "ppt_gen"
        elif final_state.get("pitch_result"):
            stop_node = "pitch_gen"
        elif final_state.get("bp_structure"):
            stop_node = "investor_eval"
        elif final_state.get("evaluation_result"):
            stop_node = "structure_eval"
        else:
            stop_node = "end"
    
    # Persist final workflow state to chat history
    if chat_history_manager:
        chat_history_manager.persist_workflow_state(final_state, stop_node=stop_node)
    
    # Check completion
    if completeness and not completeness.get("is_complete", False):
        return {
            "output_file": None,
            "markdown": None,
            "bp_structure": None,
            "iteration_history": [],
            "evaluation_result": None,
            "pitch_result": None,
            "ppt_result": None,
            "partner_search_result": None,
            "partner_report_file": None,
            "ppt_design_file": None,
            "session_id": session_id,
            "session_dir": session_dir if save_report else None,
            "input_completeness": completeness,
            "error": "Input completeness check failed"
        }
    
    # Post-processing (Markdown & Files)
    agent_helper = BPGenerationAgent(config)
    
    # Build Markdown
    markdown_content = agent_helper._build_markdown(
        business_idea,
        final_state.get("bp_structure", []),
        final_state.get("iteration_history", []),
        final_state.get("evaluation_result", {}),
        final_state.get("partner_search_result")
    )
    
    # Save files if requested
    output_path = None
    partner_report_path = None
    ppt_design_file = None
    
    if save_report:
        output_path = agent_helper._build_default_filename(business_idea, session_id=session_id, session_dir=session_dir)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)
        
        # Save PPT Design
        ppt_result = final_state.get("ppt_result")
        if ppt_result and ppt_result.get("slides"):
            ppt_design_file = agent_helper._save_ppt_design_file(
                business_idea,
                final_state.get("bp_structure", []),
                ppt_result,
                output_path
            )
        
        # Save Partner Report
        partner_result = final_state.get("partner_search_result")
        if partner_result:
            partner_report_path = agent_helper._save_partner_report(
                business_idea,
                partner_result,
                output_path
            )
    
    return {
        "output_file": output_path,
        "markdown": markdown_content,
        "bp_structure": final_state.get("bp_structure"),
        "iteration_history": final_state.get("iteration_history", []),
        "evaluation_result": final_state.get("evaluation_result"),
        "pitch_result": final_state.get("pitch_result"),
        "ppt_result": final_state.get("ppt_result"),
        "partner_search_result": final_state.get("partner_search_result"),
        "partner_report_file": partner_report_path,
        "ppt_design_file": ppt_design_file,
        "session_id": session_id,
        "session_dir": session_dir if save_report else None,
        "input_completeness": completeness,
    }


def display_results(result: dict, agent: BPGenerationAgent):
    """显示生成结果"""
    print("\n" + "=" * 60)
    print("生成结果")
    print("=" * 60)
    
    # 检查是否有错误（输入不完整等情况）
    if result.get('error'):
        print("\n" + "=" * 60)
        print("生成失败")
        print("=" * 60)
        print(result.get('error'))
        
        # 显示输入完整性检查结果
        input_completeness = result.get('input_completeness')
        if input_completeness:
            print("\n" + "-" * 60)
            print("输入完整性检查结果:")
            print("-" * 60)
            current_perspective = input_completeness.get('current_perspective', 'none')
            perspective_names = {
                "technical": "技术视角",
                "user_painpoint": "用户痛点视角（需求视角）",
                "market": "市场视角",
                "mixed": "混合视角",
                "none": "无法确定"
            }
            print(f"当前视角: {perspective_names.get(current_perspective, current_perspective)}")
            
            perspective_details = input_completeness.get('perspective_details', {})
            if perspective_details:
                print("\n各视角完整性评估:")
                for perspective, details in perspective_details.items():
                    perspective_cn = {
                        "technical": "技术视角",
                        "user_painpoint": "用户痛点视角",
                        "market": "市场视角"
                    }.get(perspective, perspective)
                    completeness = details.get('completeness', 'missing')
                    completeness_cn = {
                        "complete": "完整",
                        "partial": "部分",
                        "missing": "缺失"
                    }.get(completeness, completeness)
                    print(f"  - {perspective_cn}: {completeness_cn}")
                    
                    # 使用节点返回的格式化信息
                    formatted_checklist = input_completeness.get('formatted_checklist', {})
                    if perspective in formatted_checklist:
                        formatted = formatted_checklist[perspective]
                        
                        # 显示缺失的检查点
                        missing_checkpoints = formatted.get('missing_checkpoints', [])
                        if missing_checkpoints:
                            print(f"    缺失的检查点:")
                            for checkpoint in missing_checkpoints:
                                print(f"      - {checkpoint}")
                        
                        # 显示检查清单状态
                        checklist_status = formatted.get('checklist_status', [])
                        if checklist_status:
                            print(f"    检查清单状态:")
                            for item in checklist_status:
                                print(f"      {item['status']} {item['name']}")
            
            suggestions = input_completeness.get('suggestions', [])
            if suggestions:
                print("\n改进建议:")
                for i, suggestion in enumerate(suggestions, 1):
                    print(f"  {i}. {suggestion}")
        
        # 显示保存的用户输入文件路径
        input_completeness = result.get('input_completeness')
        if input_completeness and input_completeness.get('saved_input_file'):
            print(f"\n用户输入已保存到: {input_completeness.get('saved_input_file')}")
        
        # 显示Session信息（即使失败也可能有session_id）
        session_id = result.get('session_id')
        session_dir = result.get('session_dir')
        if session_id:
            print("\n" + "=" * 60)
            print("Session 信息")
            print("=" * 60)
            print(f"Session ID: {session_id}")
            if session_dir:
                print(f"Session目录: {session_dir}")
            
            # 提供下次调用的示例
            print("\n下次继续使用此Session的方法:")
            print("-" * 60)
            print(f"1. 使用此Session ID继续生成（修正输入后）:")
            print(f"   python cli_bp_app.py --session-id {session_id} --idea \"修正后的商业创意\"")
            print(f"\n2. 查看之前保存的用户输入:")
            print(f"   python cli_bp_app.py --session-id {session_id}")
            print(f"   (然后选择查看之前的用户输入)")
            print("=" * 60)
        
        return
    
    # 基本信息
    print(f"\n输出文件: {result.get('output_file', 'N/A')}")
    
    # 明确显示Session信息
    session_id = result.get('session_id')
    session_dir = result.get('session_dir')
    if session_id:
        print("\n" + "=" * 60)
        print("Session 信息")
        print("=" * 60)
        print(f"Session ID: {session_id}")
        if session_dir:
            print(f"Session目录: {session_dir}")
        
        # 提供下次调用的示例
        print("\n下次继续使用此Session的方法:")
        print("-" * 60)
        print(f"1. 继续在当前Session中生成新的商业计划书:")
        print(f"   python cli_bp_app.py --session-id {session_id} --idea \"你的新商业创意\"")
        print(f"\n2. 查看之前保存的用户输入:")
        print(f"   python cli_bp_app.py --session-id {session_id}")
        print(f"   (然后选择查看之前的用户输入)")
        print(f"\n3. 在指定Session中生成（不指定idea，将交互式输入）:")
        print(f"   python cli_bp_app.py --session-id {session_id}")
        print("=" * 60)
    else:
        print(f"\nSession ID: 未生成")
    markdown = result.get('markdown')
    if markdown:
        print(f"Markdown长度: {len(markdown)} 字符")
    else:
        print("Markdown: 未生成")
    
    # BP结构
    bp_structure = result.get('bp_structure', [])
    if bp_structure:
        print(f"\n生成的BP结构（共 {len(bp_structure)} 个段落）:")
        for i, section in enumerate(bp_structure, 1):
            title = section.get('title', f'段落 {i}')
            print(f"  {i}. {title}")
    
    # 迭代历史
    iteration_history = result.get('iteration_history', [])
    if iteration_history:
        iterations = [h for h in iteration_history if isinstance(h.get('iteration'), int)]
        print(f"\n迭代次数: {len(iterations)}")
    
    # 评估结果
    evaluation_result = result.get('evaluation_result', {})
    if evaluation_result:
        status = "✓ 通过" if evaluation_result.get('passed') else "✗ 不通过"
        print(f"评估状态: {status}")
    
    # Pitch结果
    pitch_result = result.get('pitch_result')
    if pitch_result:
        print("\n✓ 60秒Pitch已生成")
    
    # PPT结果
    ppt_result = result.get('ppt_result')
    if ppt_result:
        slides = ppt_result.get('slides', [])
        print(f"✓ PPT草稿已生成（共 {len(slides)} 页）")
    
    # 预览Markdown
    markdown = result.get('markdown')
    if markdown:
        print("\n" + "-" * 60)
        print("Markdown预览（前500字符）:")
        print("-" * 60)
        print(markdown[:500] + "..." if len(markdown) > 500 else markdown)
        print("-" * 60)
    
    # 询问是否查看完整报告
    view_full = get_input("\n是否查看完整Markdown报告？", default="n").lower()
    if view_full in ['y', 'yes', '是']:
        print("\n" + "=" * 60)
        print("完整Markdown报告")
        print("=" * 60)
        print(markdown)
    
    # 询问是否打开文件
    output_file = result.get('output_file')
    if output_file:
        open_file = get_input(f"\n是否打开输出文件？", default="n").lower()
        if open_file in ['y', 'yes', '是']:
            try:
                if sys.platform == "win32":
                    os.startfile(output_file)
                elif sys.platform == "darwin":
                    os.system(f"open '{output_file}'")
                else:
                    os.system(f"xdg-open '{output_file}'")
            except Exception as e:
                print(f"无法打开文件: {e}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="BP Generation Agent - 命令行交互界面",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python cli_bp_app.py                                    # 交互式运行
  python cli_bp_app.py --config config.py                # 使用指定配置文件
  python cli_bp_app.py --idea "我的商业创意"              # 直接指定商业创意
  python cli_bp_app.py --session-id <session_id>         # 使用指定Session ID
  python cli_bp_app.py --session-id <session_id> --idea "新的商业创意"  # 在指定Session中生成
  python cli_bp_app.py --use-graph --idea "我的商业创意"  # 使用LangGraph实现
        """
    )
    
    parser.add_argument(
        '--config',
        type=str,
        help='配置文件路径（可选）'
    )
    
    parser.add_argument(
        '--idea',
        type=str,
        help='商业创意（可选，如果不提供将交互式输入）'
    )
    
    parser.add_argument(
        '--output-dir',
        type=str,
        help='输出目录（可选）'
    )
    
    parser.add_argument(
        '--no-save',
        action='store_true',
        help='不保存报告到文件'
    )
    
    parser.add_argument(
        '--session-id',
        type=str,
        help='Session ID（可选，用于继续某个session或查看结果）'
    )
    
    parser.add_argument(
        '--use-graph',
        action='store_true',
        help='使用LangGraph实现（实验性功能）'
    )
    
    args = parser.parse_args()
    
    # 显示欢迎信息
    print("\n" + "=" * 60)
    print("BP Generation Agent")
    print("商业计划书生成工具")
    print("=" * 60)
    
    try:
        # 加载或配置Agent
        use_graph_from_interactive = False
        if args.config:
            print(f"\n正在加载配置文件: {args.config}")
            config = load_config(args.config)
            print_config(config)
        else:
            config_result = configure_agent_interactive()
            if isinstance(config_result, tuple):
                config, use_graph_from_interactive = config_result
            else:
                config = config_result
            print_config(config)
        
        # 如果指定了输出目录，更新配置
        if args.output_dir:
            config.output_dir = args.output_dir
        
        # 选择实现方式 (命令行参数优先，否则使用交互式选择)
        use_graph = args.use_graph or use_graph_from_interactive
        if use_graph and not GRAPH_AVAILABLE:
            print("\n警告: LangGraph未安装，将使用传统实现")
            print("安装命令: pip install langgraph langchain-openai")
            use_graph = False
        
        # 创建Agent或Graph
        if use_graph:
            print("\n正在初始化BP Generation Agent (LangGraph版本)...")
            agent = None  # We'll use graph directly
        else:
        print("\n正在初始化BP Generation Agent...")
        agent = BPGenerationAgent(config)
        
        # 处理Session ID
        session_id = args.session_id
        if session_id:
            # Validate session_id format
            import uuid
            try:
                uuid.UUID(session_id)
            except (ValueError, AttributeError):
                print(f"\n警告: Session ID格式无效: {session_id}")
                create_new = get_input("是否生成新的Session ID？", default="y").lower()
                if create_new not in ['y', 'yes', '是']:
                    print("已取消")
                    sys.exit(0)
                session_id = str(uuid.uuid4())
                print(f"已生成新的Session ID: {session_id}")
            
            # Check if session exists (filesystem-based check for now)
            # TODO: In the future, this can check Redis or other storage backends
            session_dir = os.path.join(config.output_dir, session_id)
            if not os.path.exists(session_dir):
                print(f"\n警告: Session不存在: {session_id}")
                create_new = get_input("是否创建新的Session？", default="y").lower()
                if create_new not in ['y', 'yes', '是']:
                    print("已取消")
                    sys.exit(0)
                os.makedirs(session_dir, exist_ok=True)
                print(f"已创建新的Session: {session_id}")
            else:
                print(f"\n使用现有Session: {session_id}")
                
                # 检查是否有previous_user_inputs文件（文件系统实现）
                previous_inputs_file = os.path.join(session_dir, "previous_user_inputs.md")
                if os.path.exists(previous_inputs_file):
                    view_previous = get_input("是否查看之前的用户输入？", default="n").lower()
                    if view_previous in ['y', 'yes', '是']:
                        print("\n" + "-" * 60)
                        print("之前的用户输入:")
                        print("-" * 60)
                        with open(previous_inputs_file, "r", encoding="utf-8") as f:
                            print(f.read())
                        print("-" * 60)
        
        # 获取商业创意
        if args.idea:
            business_idea = args.idea
            print(f"\n使用命令行提供的商业创意: {business_idea[:80]}...")
        else:
            business_idea = get_business_idea()
        
        # 确认开始生成
        print("\n" + "=" * 60)
        print("准备生成商业计划书")
        print("=" * 60)
        print(f"商业创意: {business_idea[:100]}...")
        print(f"LLM提供商: {config.default_llm_provider}")
        print(f"实现方式: {'LangGraph' if use_graph else '传统实现'}")
        print(f"输出目录: {config.output_dir}")
        if session_id:
            print(f"Session ID: {session_id}")
            # Only show session_dir if it exists (filesystem implementation detail)
            session_dir = os.path.join(config.output_dir, session_id)
            if os.path.exists(session_dir):
            print(f"Session目录: {session_dir}")
        
        confirm = get_input("\n确认开始生成？", default="y").lower()
        if confirm not in ['y', 'yes', '是']:
            print("已取消")
            sys.exit(0)
        
        # 生成BP
        print("\n" + "=" * 60)
        print("开始生成商业计划书...")
        print("=" * 60)
        
        if use_graph:
            result = generate_bp_with_graph(
                business_idea=business_idea,
                config=config,
                session_id=session_id,
                save_report=not args.no_save
            )
            # Create agent instance for display_results helper methods
            agent = BPGenerationAgent(config)
        else:
        result = agent.generate_bp(
            business_idea=business_idea,
            save_report=not args.no_save,
                session_id=session_id
        )
        
        # 显示结果
        display_results(result, agent)
        
        # 再次显示Session信息（如果成功生成）
        session_id = result.get('session_id')
        if session_id and not result.get('error'):
            print("\n" + "=" * 60)
            print("完成！")
            print("=" * 60)
            print(f"\n所有文件已保存到Session: {session_id}")
            print(f"\n快速命令参考:")
            print(f"  继续使用此Session: python cli_bp_app.py --session-id {session_id}")
            print("=" * 60)
        else:
            print("\n" + "=" * 60)
            print("完成！")
            print("=" * 60)
        
    except KeyboardInterrupt:
        print("\n\n用户中断")
        sys.exit(0)
    except Exception as e:
        print(f"\n错误: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

