"""
合伙人员搜索示例
演示如何使用PartnerSearchNode搜索符合需求的人员
"""

import os
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.nodes.partner_search_node import PartnerSearchNode
from src.utils.config import load_config
from src.llms import DeepSeekLLM, OpenAILLM, QwenLLM


def partner_search_example():
    """合伙人员搜索基本示例"""
    print("=" * 60)
    print("PartnerSearchNode - 合伙人员搜索示例")
    print("=" * 60)
    
    try:
        # 加载配置
        print("\n正在加载配置...")
        config = load_config()
        
        # 初始化LLM客户端（可选，用于优化搜索查询）
        print("正在初始化LLM客户端...")
        if config.default_llm_provider == "deepseek":
            llm_client = DeepSeekLLM(
                api_key=config.deepseek_api_key,
                model_name=config.deepseek_model
            )
        elif config.default_llm_provider == "openai":
            llm_client = OpenAILLM(
                api_key=config.openai_api_key,
                model_name=config.openai_model
            )
        elif config.default_llm_provider == "qwen":
            llm_client = QwenLLM(
                api_key=config.qwen_api_key,
                model_name=config.qwen_model
            )
        else:
            llm_client = None
            print("警告: 未配置LLM，将跳过查询优化功能")
        
        # 从config.py读取爱合伙API配置
        import importlib.util
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config.py')
        aihehuo_api_key = None
        aihehuo_api_base = None
        if os.path.exists(config_path):
            spec = importlib.util.spec_from_file_location("config", config_path)
            config_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(config_module)
            aihehuo_api_key = getattr(config_module, "AIHEHUO_API_KEY", None)
            aihehuo_api_base = getattr(config_module, "AIHEHUO_API_BASE", None)
        
        # 创建PartnerSearchNode
        print("正在初始化PartnerSearchNode...")
        search_node = PartnerSearchNode(
            llm_client=llm_client,
            api_key=aihehuo_api_key,
            api_base=aihehuo_api_base
        )
        
        # 示例1: 基本搜索
        print("\n" + "=" * 60)
        print("示例1: 基本合伙人员搜索")
        print("=" * 60)
        
        requirement = "寻找有AI技术背景和创业经验的合伙人"
        print(f"\n合伙需求: {requirement}")
        
        result = search_node.run(
            input_data={"requirement": requirement},
            per_page=5
        )
        
        print(f"\n搜索结果:")
        print(f"- 搜索查询: {result.get('query')}")
        print(f"- 找到 {result.get('total_count', 0)} 个结果")
        
        for i, person in enumerate(result.get('results', [])[:3], 1):
            print(f"\n结果 {i}:")
            print(f"  用户ID: {person.get('user_id')}")
            print(f"  姓名: {person.get('name')}")
            if person.get('bio'):
                print(f"  简介: {person.get('bio', '')[:100]}...")
            if person.get('tags'):
                print(f"  标签: {', '.join(person.get('tags', [])[:5])}")
        
        # 示例2: 使用LLM优化搜索查询
        if llm_client:
            print("\n" + "=" * 60)
            print("示例2: 使用LLM优化搜索查询")
            print("=" * 60)
            
            business_idea = "我想创建一个基于AI的在线教育平台，主要面向K12学生"
            partner_requirement = "需要技术合伙人，熟悉AI和教育领域"
            
            print(f"\n商业创意: {business_idea}")
            print(f"合伙需求: {partner_requirement}")
            
            result = search_node.search_with_llm_optimization(
                business_idea=business_idea,
                partner_requirement=partner_requirement,
                per_page=5
            )
            
            print(f"\n搜索结果:")
            print(f"- 优化后的搜索查询: {result.get('query')}")
            print(f"- 找到 {result.get('total_count', 0)} 个结果")
            
            for i, person in enumerate(result.get('results', [])[:3], 1):
                print(f"\n结果 {i}:")
                print(f"  用户ID: {person.get('user_id')}")
                print(f"  姓名: {person.get('name')}")
                if person.get('bio'):
                    print(f"  简介: {person.get('bio', '')[:100]}...")
        
        # 示例3: 搜索投资人
        print("\n" + "=" * 60)
        print("示例3: 搜索投资人")
        print("=" * 60)
        
        requirement = "寻找早期投资人或天使投资人"
        print(f"\n合伙需求: {requirement}")
        
        result = search_node.run(
            input_data={"requirement": requirement},
            investor=True,
            per_page=5
        )
        
        print(f"\n搜索结果:")
        print(f"- 搜索查询: {result.get('query')}")
        print(f"- 找到 {result.get('total_count', 0)} 个投资人")
        
        for i, person in enumerate(result.get('results', [])[:3], 1):
            print(f"\n结果 {i}:")
            print(f"  用户ID: {person.get('user_id')}")
            print(f"  姓名: {person.get('name')}")
            if person.get('bio'):
                print(f"  简介: {person.get('bio', '')[:100]}...")
        
    except Exception as e:
        print(f"示例运行失败: {str(e)}")
        import traceback
        traceback.print_exc()
        print("\n请检查：")
        print("1. 是否安装了所有依赖：pip install -r requirements.txt")
        print("2. 是否设置了必要的API密钥（爱合伙API Key）")
        print("3. 网络连接是否正常")
        print("4. 配置文件是否正确")


if __name__ == "__main__":
    partner_search_example()

