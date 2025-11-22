"""
BP生成示例
演示如何使用BP Generation Agent生成商业计划书
"""

import os
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.bp_generation_agent import BPGenerationAgent, create_bp_agent
from src.utils.config import load_config, print_config


def bp_generation_example():
    """BP生成基本示例"""
    print("=" * 60)
    print("BP Generation Agent - 商业计划书生成示例")
    print("=" * 60)
    
    try:
        # 加载配置
        print("\n正在加载配置...")
        config = load_config()
        print_config(config)
        
        # 创建Agent
        print("\n正在初始化BP Generation Agent...")
        agent = BPGenerationAgent(config)
        
        # 定义商业创意
        business_idea = """
        我想创建一个基于AI的在线教育平台，主要面向K12学生。
        平台将提供个性化的学习路径推荐，利用AI分析学生的学习习惯和知识薄弱点，
        为学生推荐最适合的学习内容和练习题。同时，平台还会为家长提供详细的学习报告，
        帮助家长了解孩子的学习进度和需要改进的地方。
        """
        
        print(f"\n商业创意: {business_idea.strip()[:100]}...")
        print("\n开始生成商业计划书...")
        
        # 生成商业计划书
        final_report = agent.generate_bp(business_idea, save_report=True)
        
        # 显示结果
        print("\n" + "=" * 60)
        print("商业计划书生成完成！")
        print("=" * 60)
        
        # Extract results from the returned dictionary
        markdown = final_report.get("markdown", "")
        bp_structure = final_report.get("bp_structure", [])
        output_file = final_report.get("output_file", "")
        
        if markdown:
            print("最终报告预览:")
            print(markdown[:1000] + "..." if len(markdown) > 1000 else markdown)
        
        if output_file:
            print(f"\n报告已保存到: {output_file}")
        
        if bp_structure:
            print(f"\n生成的段落数: {len(bp_structure)}")
            print("段落标题:")
            for i, section in enumerate(bp_structure, 1):
                print(f"  {i}. {section.get('title', 'N/A')}")
        
    except Exception as e:
        print(f"示例运行失败: {str(e)}")
        import traceback
        traceback.print_exc()
        print("\n请检查：")
        print("1. 是否安装了所有依赖：pip install -r requirements.txt")
        print("2. 是否设置了必要的API密钥")
        print("3. 网络连接是否正常")
        print("4. 配置文件是否正确")


def bp_generation_simple_example():
    """使用便捷函数创建Agent的简单示例"""
    print("=" * 60)
    print("BP Generation Agent - 简单使用示例")
    print("=" * 60)
    
    try:
        # 使用便捷函数创建Agent
        print("\n正在创建BP Generation Agent...")
        agent = create_bp_agent()
        
        # 定义商业创意
        business_idea = "一个帮助老年人使用智能手机的AI助手应用"
        
        print(f"\n商业创意: {business_idea}")
        print("\n开始生成商业计划书...")
        
        # 生成商业计划书
        final_report = agent.generate_bp(business_idea, save_report=True)
        
        # 显示结果摘要
        print("\n" + "=" * 60)
        print("商业计划书生成完成！")
        print("=" * 60)
        
        # Extract results from the returned dictionary
        markdown = final_report.get("markdown", "")
        bp_structure = final_report.get("bp_structure", [])
        output_file = final_report.get("output_file", "")
        
        if markdown:
            print(f"报告长度: {len(markdown)} 字符")
        
        if output_file:
            print(f"报告已保存到: {output_file}")
        
        if bp_structure:
            print(f"报告段落数: {len(bp_structure)}")
            print("\n生成的段落:")
            for i, section in enumerate(bp_structure, 1):
                print(f"  {i}. {section.get('title', 'N/A')}")
        
    except Exception as e:
        print(f"示例运行失败: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="BP Generation Agent 示例")
    parser.add_argument(
        "--simple",
        action="store_true",
        help="运行简单示例（使用便捷函数）"
    )
    
    args = parser.parse_args()
    
    if args.simple:
        bp_generation_simple_example()
    else:
        bp_generation_example()

