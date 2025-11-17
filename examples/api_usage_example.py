"""
BP Generation Agent API 使用示例
演示如何通过HTTP API调用BP生成功能
"""

import requests
import json


def example_generate_bp():
    """示例：调用生成BP接口"""
    api_url = "http://localhost:8000/api/v1/generate"
    
    # 请求数据
    request_data = {
        "business_idea": "我想创建一个基于AI的在线教育平台，主要面向K12学生，提供个性化学习路径推荐",
        "save_report": True
    }
    
    print("=" * 60)
    print("调用BP生成API")
    print("=" * 60)
    print(f"API地址: {api_url}")
    print(f"商业创意: {request_data['business_idea'][:50]}...")
    print("\n正在发送请求...")
    
    try:
        # 发送POST请求
        response = requests.post(api_url, json=request_data, timeout=600)
        
        # 检查响应状态
        if response.status_code == 200:
            result = response.json()
            
            if result.get("success"):
                print("\n✓ 生成成功！")
                print(f"消息: {result.get('message')}")
                
                data = result.get("data", {})
                print(f"\n生成结果:")
                print(f"  - 输出文件: {data.get('output_file')}")
                print(f"  - Markdown长度: {data.get('markdown_length')} 字符")
                print(f"  - BP结构段落数: {data.get('bp_structure_count')}")
                print(f"  - 包含评估: {data.get('has_evaluation')}")
                print(f"  - 包含Pitch: {data.get('has_pitch')}")
                print(f"  - 包含PPT: {data.get('has_ppt')}")
                print(f"  - 包含合伙人搜索: {data.get('has_partner_search')}")
                
                if data.get("files"):
                    files = data.get("files", {})
                    print(f"\n生成的文件:")
                    if files.get("main_report"):
                        print(f"  - 主报告: {files['main_report']}")
                    if files.get("partner_report"):
                        print(f"  - 人脉报告: {files['partner_report']}")
            else:
                print(f"\n✗ 生成失败: {result.get('message')}")
                if result.get("error"):
                    print(f"错误信息: {result.get('error')[:500]}...")
        else:
            print(f"\n✗ HTTP错误: {response.status_code}")
            print(f"响应内容: {response.text[:500]}")
            
    except requests.exceptions.RequestException as e:
        print(f"\n✗ 请求失败: {str(e)}")
        print("\n请确保API服务器正在运行:")
        print("  python api_server.py")


def example_generate_preview():
    """示例：调用生成BP预览接口（返回Markdown预览）"""
    api_url = "http://localhost:8000/api/v1/generate/preview"
    
    request_data = {
        "business_idea": "一个帮助老年人使用智能手机的AI助手应用",
        "save_report": False  # 预览模式可以不保存文件
    }
    
    print("=" * 60)
    print("调用BP生成预览API")
    print("=" * 60)
    
    try:
        response = requests.post(api_url, json=request_data, timeout=600)
        
        if response.status_code == 200:
            result = response.json()
            
            if result.get("success"):
                data = result.get("data", {})
                print("\n✓ 预览生成成功！")
                print(f"Markdown总长度: {data.get('full_length')} 字符")
                print(f"预览长度: {len(data.get('preview', ''))} 字符")
                print(f"是否截断: {data.get('is_truncated')}")
                print(f"\n预览内容（前500字符）:")
                print("-" * 60)
                print(data.get('preview', '')[:500])
                print("-" * 60)
            else:
                print(f"\n✗ 生成失败: {result.get('message')}")
        else:
            print(f"\n✗ HTTP错误: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"\n✗ 请求失败: {str(e)}")


def example_health_check():
    """示例：健康检查"""
    api_url = "http://localhost:8000/health"
    
    print("=" * 60)
    print("健康检查")
    print("=" * 60)
    
    try:
        response = requests.get(api_url, timeout=5)
        
        if response.status_code == 200:
            result = response.json()
            print(f"状态: {result.get('status')}")
            print(f"时间戳: {result.get('timestamp')}")
            print(f"Agent已初始化: {result.get('agent_initialized')}")
        else:
            print(f"✗ HTTP错误: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"✗ 请求失败: {str(e)}")
        print("API服务器可能未运行")


def example_get_config():
    """示例：获取配置信息"""
    api_url = "http://localhost:8000/api/v1/config"
    
    print("=" * 60)
    print("获取配置信息")
    print("=" * 60)
    
    try:
        response = requests.get(api_url, timeout=5)
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                data = result.get("data", {})
                print(f"LLM提供商: {data.get('default_llm_provider')}")
                print(f"输出目录: {data.get('output_dir')}")
                print(f"爱合伙API可用: {data.get('aihehuo_available')}")
            else:
                print(f"✗ 获取配置失败: {result.get('error')}")
        else:
            print(f"✗ HTTP错误: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"✗ 请求失败: {str(e)}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="BP Generation Agent API 使用示例")
    parser.add_argument(
        "--example",
        type=str,
        choices=["generate", "preview", "health", "config", "all"],
        default="all",
        help="要运行的示例（默认: all）"
    )
    
    args = parser.parse_args()
    
    if args.example == "generate" or args.example == "all":
        example_generate_bp()
        print("\n")
    
    if args.example == "preview" or args.example == "all":
        example_generate_preview()
        print("\n")
    
    if args.example == "health" or args.example == "all":
        example_health_check()
        print("\n")
    
    if args.example == "config" or args.example == "all":
        example_get_config()
        print("\n")

