#!/usr/bin/env python3
"""
CLI Interactive BP Generation Program
为BP Generation Agent提供友好的命令行交互界面
"""

import os
import sys
import argparse
from datetime import datetime
from typing import Optional

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.bp_agent import BPGenerationAgent, create_bp_agent
from src.utils.config import Config, load_config, print_config


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


def configure_agent_interactive() -> Config:
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
            return existing_config
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
    
    return config


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


def display_results(result: dict, agent: BPGenerationAgent):
    """显示生成结果"""
    print("\n" + "=" * 60)
    print("生成结果")
    print("=" * 60)
    
    # 基本信息
    print(f"\n输出文件: {result.get('output_file', 'N/A')}")
    print(f"Markdown长度: {len(result.get('markdown', ''))} 字符")
    
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
    markdown = result.get('markdown', '')
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
  python cli_bp_app.py                    # 交互式运行
  python cli_bp_app.py --config config.py # 使用指定配置文件
  python cli_bp_app.py --idea "我的商业创意" # 直接指定商业创意
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
    
    args = parser.parse_args()
    
    # 显示欢迎信息
    print("\n" + "=" * 60)
    print("BP Generation Agent")
    print("商业计划书生成工具")
    print("=" * 60)
    
    try:
        # 加载或配置Agent
        if args.config:
            print(f"\n正在加载配置文件: {args.config}")
            config = load_config(args.config)
            print_config(config)
        else:
            config = configure_agent_interactive()
            print_config(config)
        
        # 如果指定了输出目录，更新配置
        if args.output_dir:
            config.output_dir = args.output_dir
        
        # 创建Agent
        print("\n正在初始化BP Generation Agent...")
        agent = BPGenerationAgent(config)
        
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
        print(f"输出目录: {config.output_dir}")
        
        confirm = get_input("\n确认开始生成？", default="y").lower()
        if confirm not in ['y', 'yes', '是']:
            print("已取消")
            sys.exit(0)
        
        # 生成BP
        print("\n" + "=" * 60)
        print("开始生成商业计划书...")
        print("=" * 60)
        
        result = agent.generate_bp(
            business_idea=business_idea,
            save_report=not args.no_save
        )
        
        # 显示结果
        display_results(result, agent)
        
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

