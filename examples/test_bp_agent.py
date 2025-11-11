"""
BP Agent 测试程序
调用 BPGenerationAgent，根据商业创意生成完整的BP Markdown输出
"""

import os
import sys
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.bp_agent import BPGenerationAgent


def main():
    import argparse

    parser = argparse.ArgumentParser(description="BP Agent 测试程序")
    parser.add_argument(
        "--idea",
        type=str,
        default="一个基于AI的在线教育平台，主要面向K12学生，提供个性化学习路径推荐",
        help="商业创意（如果不提供则使用默认值）",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="输出文件路径（如果不提供则自动生成）",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="不保存Markdown，仅返回内容",
    )

    args = parser.parse_args()

    agent = BPGenerationAgent()
    result = agent.generate_bp(
        business_idea=args.idea,
        output_file=args.output,
        save_report=not args.no_save,
    )

    output_path = result.get("output_file")
    markdown_content = result.get("markdown", "")

    print("\n" + "=" * 60)
    print("BP Agent 测试完成")
    print("=" * 60)
    if output_path:
        print(f"输出文件: {output_path}")
        print(f"文件大小: {len(markdown_content)} 字符")
    else:
        print("未保存Markdown文件（--no-save）")

    preview = markdown_content[:500] + "..." if len(markdown_content) > 500 else markdown_content
    print("\nMarkdown预览（前500字符）:")
    print("-" * 60)
    print(preview)


if __name__ == "__main__":
    main()

