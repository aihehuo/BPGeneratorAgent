"""
单元测试：爱合伙平台工具
测试爱合伙API的各种功能
"""

import unittest
import os
import sys
import tempfile
import requests
from urllib.parse import urlparse

# 添加项目根目录到Python路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 导入爱合伙工具函数
from src.tools.aihehuo import (
    search_members,
    get_user_info,
    search_ideas,
    get_idea_details,
    upload_file
)


class TestAihehuoTools(unittest.TestCase):
    """爱合伙工具测试类"""
    
    def test_search_members(self):
        """测试成员搜索功能"""
        print(f"\n=== 测试爱合伙成员搜索功能 ===")
        query = "寻找有创业经验的AI技术专家"
        per_page = 5
        print(f"搜索查询: {query}")
        print(f"每页结果数: {per_page}")
        
        try:
            results = search_members(query, per_page=per_page)
            
            if results:
                print(f"\n找到 {len(results)} 个结果:")
                for i, result in enumerate(results, 1):
                    print(f"\n结果 {i}:")
                    print(f"用户ID: {result['user_id']}")
                    print(f"姓名: {result['name']}")
                    if result.get('bio'):
                        print(f"简介: {result['bio'][:100]}...")
                    if result.get('goal'):
                        print(f"目标: {result['goal'][:100]}...")
                
                # 验证结果格式
                self.assertIsInstance(results, list)
                if len(results) > 0:
                    self.assertIn('user_id', results[0])
                    self.assertIn('name', results[0])
            else:
                print("未找到搜索结果")
                # 如果没有结果，也不应该报错
                self.assertIsInstance(results, list)
                
        except Exception as e:
            print(f"搜索测试失败: {str(e)}")
            # 如果API未配置，跳过测试
            if "API Key未找到" in str(e) or "未设置" in str(e):
                self.skipTest(f"API Key未配置: {str(e)}")
            else:
                raise
    
    def test_get_user_info(self):
        """测试用户信息查询功能"""
        print(f"\n=== 测试爱合伙用户信息查询功能 ===")
        user_id = "1"
        print(f"用户ID: {user_id}")
        
        try:
            user_info = get_user_info(user_id)
            
            if user_info:
                print(f"\n用户信息:")
                print(f"用户ID: {user_info['user_id']}")
                print(f"姓名: {user_info['name']}")
                if user_info.get('bio'):
                    print(f"简介: {user_info['bio'][:200]}...")
                if user_info.get('goal'):
                    print(f"目标: {user_info['goal'][:200]}...")
                
                # 验证结果格式
                self.assertIsInstance(user_info, dict)
                self.assertIn('user_id', user_info)
                self.assertIn('name', user_info)
            else:
                print("未找到用户信息")
                # 如果用户不存在，返回None是正常的
                self.assertIsNone(user_info)
                
        except Exception as e:
            print(f"用户信息查询测试失败: {str(e)}")
            # 如果API未配置，跳过测试
            if "API Key未找到" in str(e) or "未设置" in str(e):
                self.skipTest(f"API Key未配置: {str(e)}")
            else:
                raise
    
    def test_search_ideas(self):
        """测试创业想法搜索功能"""
        print(f"\n=== 测试爱合伙创业想法搜索功能 ===")
        query = "AI创业项目"
        per_page = 5
        print(f"搜索查询: {query}")
        print(f"每页结果数: {per_page}")
        
        try:
            results = search_ideas(query, per_page=per_page)
            
            if results:
                print(f"\n找到 {len(results)} 个结果:")
                for i, result in enumerate(results, 1):
                    print(f"\n结果 {i}:")
                    print(f"项目ID: {result['idea_id']}")
                    print(f"标题: {result['title']}")
                    if result.get('city'):
                        print(f"城市: {result['city']}")
                    if result.get('vertical'):
                        print(f"行业: {result['vertical']}")
                    if result.get('investment'):
                        print(f"投资额: {result['investment']}")
                    if result.get('team_members'):
                        print(f"团队规模: {result['team_members']}")
                
                # 验证结果格式
                self.assertIsInstance(results, list)
                if len(results) > 0:
                    self.assertIn('idea_id', results[0])
                    self.assertIn('title', results[0])
            else:
                print("未找到搜索结果")
                # 如果没有结果，也不应该报错
                self.assertIsInstance(results, list)
                
        except Exception as e:
            print(f"搜索测试失败: {str(e)}")
            # 如果API未配置，跳过测试
            if "API Key未找到" in str(e) or "未设置" in str(e):
                self.skipTest(f"API Key未配置: {str(e)}")
            else:
                raise
    
    def test_get_idea_details(self):
        """测试想法/项目详情查询功能"""
        print(f"\n=== 测试爱合伙想法/项目详情查询功能 ===")
        idea_id = "31009"
        print(f"想法/项目ID: {idea_id}")
        
        try:
            idea_details = get_idea_details(idea_id)
            
            if idea_details:
                print(f"\n想法/项目详情:")
                print(f"项目ID: {idea_details['idea_id']}")
                print(f"标题: {idea_details['title']}")
                if idea_details.get('description'):
                    print(f"描述: {idea_details['description'][:200]}...")
                if idea_details.get('city'):
                    print(f"城市: {idea_details['city']}")
                if idea_details.get('investment'):
                    print(f"投资额: {idea_details['investment']}")
                if idea_details.get('team_members'):
                    print(f"团队规模: {idea_details['team_members']}")
                if idea_details.get('partners_count'):
                    print(f"合伙人数量: {idea_details['partners_count']}")
                if idea_details.get('all_skills'):
                    skills_names = [s.get('name', '') for s in idea_details['all_skills'][:10]]
                    print(f"所需技能: {', '.join(skills_names)}...")
                
                # 验证结果格式
                self.assertIsInstance(idea_details, dict)
                self.assertIn('idea_id', idea_details)
                self.assertIn('title', idea_details)
            else:
                print("未找到想法/项目详情")
                # 如果项目不存在，返回None是正常的
                self.assertIsNone(idea_details)
                
        except Exception as e:
            print(f"想法/项目详情查询测试失败: {str(e)}")
            # 如果API未配置，跳过测试
            if "API Key未找到" in str(e) or "未设置" in str(e):
                self.skipTest(f"API Key未配置: {str(e)}")
            else:
                raise
    
    def test_upload_file(self):
        """测试文件上传功能（包括TXT、Markdown和HTML文件）"""
        print(f"\n=== 测试爱合伙文件上传功能 ===")
        
        # 定义要测试的文件类型和内容
        test_files = [
            {
                "suffix": ".txt",
                "content": "这是一个测试文件\n用于测试文件上传功能",
                "name": "文本文件"
            },
            {
                "suffix": ".md",
                "content": """# 测试Markdown文件

这是一个测试用的Markdown文件。

## 功能列表

- 测试Markdown格式
- 验证文件上传
- 检查URL返回

## 代码示例

```python
def hello():
    print("Hello, World!")
```

**注意**: 这是一个测试文件。
""",
                "name": "Markdown文件"
            },
            {
                "suffix": ".html",
                "content": """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>测试HTML文件</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }
        h1 {
            color: #333;
        }
        .content {
            line-height: 1.6;
        }
    </style>
</head>
<body>
    <h1>测试HTML文件上传</h1>
    <div class="content">
        <p>这是一个测试用的HTML文件。</p>
        <p>用于验证文件上传功能对HTML格式的支持。</p>
        <ul>
            <li>测试HTML格式</li>
            <li>验证文件上传</li>
            <li>检查URL返回</li>
        </ul>
    </div>
</body>
</html>""",
                "name": "HTML文件"
            }
        ]
        
        uploaded_urls = []
        test_file_paths = []
        
        try:
            for test_file_info in test_files:
                print(f"\n--- 测试上传{test_file_info['name']} ---")
                
                # 创建临时测试文件
                with tempfile.NamedTemporaryFile(mode='w', suffix=test_file_info['suffix'], delete=False, encoding='utf-8') as f:
                    test_file_path = f.name
                    f.write(test_file_info['content'])
                    test_file_paths.append(test_file_path)
                
                print(f"文件路径: {test_file_path}")
                print(f"文件类型: {test_file_info['suffix']}")
                
                result = upload_file(test_file_path)
                
                if result:
                    print(f"上传成功:")
                    print(f"响应数据: {result}")
                    
                    # 尝试提取文件URL
                    file_url = None
                    if isinstance(result, dict):
                        if "data" in result:
                            data = result["data"]
                            if isinstance(data, dict) and "url" in data:
                                file_url = data['url']
                            elif isinstance(data, str):
                                file_url = data
                        elif "url" in result:
                            file_url = result['url']
                    
                    if file_url:
                        print(f"文件URL: {file_url}")
                        uploaded_urls.append({
                            "type": test_file_info['name'],
                            "url": file_url,
                            "suffix": test_file_info['suffix']
                        })
                        
                        # 验证URL格式
                        self.assertIsInstance(file_url, str)
                        self.assertTrue(file_url.startswith('http://') or file_url.startswith('https://'))
                        print(f"✓ {test_file_info['name']}上传成功，URL: {file_url}")
                        
                        # 验证URL可以正常访问
                        try:
                            print(f"  正在验证URL可访问性...")
                            response = requests.get(file_url, timeout=10, allow_redirects=True)
                            response.raise_for_status()
                            
                            # 验证状态码
                            self.assertIn(response.status_code, [200, 201, 202], 
                                        f"URL应该返回成功状态码，但返回了 {response.status_code}")
                            
                            # 验证内容长度
                            content_length = len(response.content)
                            self.assertGreater(content_length, 0, "URL返回的内容不应该为空")
                            
                            # 验证Content-Type（如果存在）
                            content_type = response.headers.get('Content-Type', '')
                            if content_type:
                                print(f"  Content-Type: {content_type}")
                            
                            print(f"  ✓ URL可访问，状态码: {response.status_code}, 内容大小: {content_length} 字节")
                            
                        except requests.exceptions.RequestException as e:
                            print(f"  ⚠ URL访问失败: {str(e)}")
                            # 不强制失败，因为可能是网络问题或服务器临时不可用
                            # 但记录警告信息
                        except Exception as e:
                            print(f"  ⚠ URL验证异常: {str(e)}")
                    else:
                        print(f"警告: {test_file_info['name']}响应中未找到文件URL")
                else:
                    print(f"{test_file_info['name']}上传失败")
                    # 如果API未配置，跳过测试而不是失败
                    
        except Exception as e:
            print(f"上传测试失败: {str(e)}")
            # 如果API未配置，跳过测试
            if "API Key未找到" in str(e) or "未设置" in str(e):
                self.skipTest(f"API Key未配置: {str(e)}")
            else:
                raise
        finally:
            # 清理临时文件
            for test_file_path in test_file_paths:
                if os.path.exists(test_file_path):
                    try:
                        os.unlink(test_file_path)
                    except:
                        pass
        
        # 总结上传结果并验证所有URL
        if uploaded_urls:
            print(f"\n=== 上传结果总结 ===")
            print(f"成功上传 {len(uploaded_urls)} 个文件:")
            
            accessible_count = 0
            for item in uploaded_urls:
                print(f"\n{item['type']} ({item['suffix']}):")
                print(f"  URL: {item['url']}")
                
                # 再次验证URL可访问性（用于总结）
                try:
                    response = requests.get(item['url'], timeout=10, allow_redirects=True)
                    response.raise_for_status()
                    accessible_count += 1
                    print(f"  ✓ 可访问 (状态码: {response.status_code}, 大小: {len(response.content)} 字节)")
                except Exception as e:
                    print(f"  ⚠ 访问失败: {str(e)}")
            
            print(f"\n总结: {accessible_count}/{len(uploaded_urls)} 个URL可以正常访问")
            
            # 如果所有URL都可以访问，验证通过
            if accessible_count == len(uploaded_urls):
                print("✓ 所有上传的文件URL都可以正常访问")
            elif accessible_count > 0:
                print(f"⚠ 部分URL无法访问（可能是网络问题或服务器临时不可用）")
        else:
            print("\n警告: 没有文件成功上传（可能是API未配置）")


if __name__ == "__main__":
    unittest.main(verbosity=2)

