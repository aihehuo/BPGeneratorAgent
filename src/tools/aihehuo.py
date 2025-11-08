"""
爱合伙平台工具实现
提供爱合伙平台成员搜索和用户信息查询功能
直接调用爱合伙API
"""

import os
import requests
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


def _load_config_value(key: str, default: Optional[str] = None) -> Optional[str]:
    """
    从环境变量或config.py加载配置值
    
    Args:
        key: 配置键名
        default: 默认值
        
    Returns:
        配置值
    """
    # 首先尝试从环境变量读取
    value = os.getenv(key)
    if value:
        return value
    
    # 如果环境变量不存在，尝试从config.py读取
    try:
        import sys
        import importlib.util
        
        # 查找config.py文件
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config.py")
        if os.path.exists(config_path):
            spec = importlib.util.spec_from_file_location("config", config_path)
            config_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(config_module)
            value = getattr(config_module, key, None)
            if value:
                return value
    except Exception:
        pass
    
    return default


@dataclass
class MemberResult:
    """成员搜索结果数据类"""
    user_id: str
    name: str
    bio: Optional[str] = None
    goal: Optional[str] = None
    tags: Optional[List[str]] = None
    wechat_reachable: Optional[bool] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "user_id": self.user_id,
            "name": self.name,
            "bio": self.bio,
            "goal": self.goal,
            "tags": self.tags,
            "wechat_reachable": self.wechat_reachable
        }


@dataclass
class UserInfo:
    """用户详细信息数据类"""
    user_id: str
    name: str
    bio: Optional[str] = None
    goal: Optional[str] = None
    tags: Optional[List[str]] = None
    wechat_data: Optional[Dict[str, Any]] = None
    ideas: Optional[List[Dict[str, Any]]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "user_id": self.user_id,
            "name": self.name,
            "bio": self.bio,
            "goal": self.goal,
            "tags": self.tags,
            "wechat_data": self.wechat_data,
            "ideas": self.ideas
        }


@dataclass
class IdeaResult:
    """创业想法/项目搜索结果数据类"""
    idea_id: str
    title: str
    city: Optional[str] = None
    cover: Optional[str] = None
    team_members: Optional[str] = None
    investment: Optional[str] = None
    vertical: Optional[str] = None
    sub_vertical: Optional[str] = None
    created_at: Optional[str] = None
    last_accessed_at: Optional[str] = None
    popscore: Optional[float] = None
    total_comments: Optional[int] = None
    vip: Optional[bool] = None
    hiring: Optional[bool] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "idea_id": self.idea_id,
            "title": self.title,
            "city": self.city,
            "cover": self.cover,
            "team_members": self.team_members,
            "investment": self.investment,
            "vertical": self.vertical,
            "sub_vertical": self.sub_vertical,
            "created_at": self.created_at,
            "last_accessed_at": self.last_accessed_at,
            "popscore": self.popscore,
            "total_comments": self.total_comments,
            "vip": self.vip,
            "hiring": self.hiring
        }


@dataclass
class IdeaDetails:
    """创业想法/项目详细信息数据类"""
    idea_id: str
    title: str
    description: Optional[str] = None
    city: Optional[str] = None
    province: Optional[str] = None
    cover: Optional[str] = None
    team_members: Optional[str] = None
    partners_count: Optional[str] = None
    investment: Optional[str] = None
    skills: Optional[List[str]] = None
    all_skills: Optional[List[Dict[str, Any]]] = None
    vertical: Optional[str] = None
    sub_vertical: Optional[str] = None
    created_at: Optional[str] = None
    last_accessed_at: Optional[str] = None
    popscore: Optional[float] = None
    total_comments: Optional[int] = None
    vip: Optional[bool] = None
    hiring: Optional[bool] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "idea_id": self.idea_id,
            "title": self.title,
            "description": self.description,
            "city": self.city,
            "province": self.province,
            "cover": self.cover,
            "team_members": self.team_members,
            "partners_count": self.partners_count,
            "investment": self.investment,
            "skills": self.skills,
            "all_skills": self.all_skills,
            "vertical": self.vertical,
            "sub_vertical": self.sub_vertical,
            "created_at": self.created_at,
            "last_accessed_at": self.last_accessed_at,
            "popscore": self.popscore,
            "total_comments": self.total_comments,
            "vip": self.vip,
            "hiring": self.hiring
        }


class AihehuoClient:
    """爱合伙平台客户端封装"""
    
    def __init__(self, api_key: Optional[str] = None, api_base: Optional[str] = None):
        """
        初始化爱合伙平台客户端
        
        Args:
            api_key: 爱合伙API密钥，如果不提供则从环境变量读取
            api_base: API基础URL，如果不提供则从环境变量读取或使用默认值
        """
        if api_key is None:
            api_key = _load_config_value("AIHEHUO_API_KEY")
            if not api_key:
                raise ValueError("爱合伙API Key未找到！请设置AIHEHUO_API_KEY环境变量或在config.py中配置")
        
        if api_base is None:
            api_base = _load_config_value("AIHEHUO_API_BASE", "https://new-api.aihehuo.com")
        
        self.api_key = api_key
        self.api_base = api_base.rstrip('/')
        
        # 设置默认请求头
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "LLM_AGENT"
        }
    
    def search_members(
        self,
        query: str,
        page: int = 1,
        per_page: int = 10,
        wechat_reachable_only: bool = False,
        investor: bool = False,
        excluded_ids: Optional[List[str]] = None,
        timeout: int = 15
    ) -> List[MemberResult]:
        """
        搜索成员
        
        Args:
            query: 搜索查询（语义搜索，长度必须大于5个字符）
            page: 页码，从1开始
            per_page: 每页结果数
            wechat_reachable_only: 是否只返回微信上能直接触达的用户
            investor: 是否只搜索投资人
            excluded_ids: 要排除的用户ID列表
            timeout: 请求超时时间（秒）
            
        Returns:
            成员搜索结果列表
        """
        try:
            # 验证查询长度
            if len(query.strip()) <= 5:
                print(f"搜索错误: 查询关键词长度必须大于5个字符，当前长度: {len(query.strip())}")
                return []
            
            # 构建请求负载
            # API expects paginate as nested object: {"page": 1, "per_page": 10}
            # Note: The actual API uses "per_page" not "per"
            payload = {
                "query": query,
                "paginate": {
                    "page": page,
                    "per_page": per_page
                },
                "vector_search": True,
                "wechat_reachable_only": wechat_reachable_only
            }
            
            # 添加可选参数
            if investor is not None:
                payload["investor"] = investor
            if excluded_ids:
                payload["excluded_ids"] = excluded_ids
            
            # 调用API - 使用GET方法，与MCP实现保持一致
            # Note: Some APIs accept JSON body with GET, though it's non-standard
            url = f"{self.api_base}/users/search"
            resp = requests.get(url, json=payload, headers=self.headers, timeout=timeout)
            resp.raise_for_status()
            resp.encoding = 'utf-8'
            response_data = resp.json()
            
            # API返回格式: {"data": "text formatted data", "meta": "..."}
            # data字段包含文本格式的用户信息，用"---"分隔
            text_data = response_data.get("data", "")
            
            # 解析文本格式的结果
            results = []
            if text_data:
                # 按"---"分割不同的用户记录
                user_blocks = text_data.split("---")
                
                for block in user_blocks:
                    block = block.strip()
                    if not block:
                        continue
                    
                    # 解析文本块提取用户信息
                    user_info = {}
                    lines = block.split("\n")
                    
                    for line in lines:
                        line = line.strip()
                        if not line:
                            continue
                        
                        # 解析键值对格式: "键: 值"
                        if ":" in line:
                            key, value = line.split(":", 1)
                            key = key.strip()
                            value = value.strip()
                            
                            if key == "用户ID":
                                user_info["user_id"] = value
                            elif key == "用户名":
                                user_info["name"] = value
                            elif key == "个人简介" or key.startswith("个人简介"):
                                # 个人简介可能跨多行，需要特殊处理
                                user_info["bio"] = value
                            elif key == "AI印象标签":
                                # 标签可能是逗号分隔的
                                user_info["tags"] = [t.strip() for t in value.split(",") if t.strip()]
                    
                    # 如果提取到了基本信息，创建结果对象
                    if user_info.get("user_id") or user_info.get("name"):
                        result = MemberResult(
                            user_id=str(user_info.get("user_id", "")),
                            name=user_info.get("name", ""),
                            bio=user_info.get("bio"),
                            tags=user_info.get("tags")
                        )
                        results.append(result)
            
            return results
            
        except requests.exceptions.RequestException as e:
            print(f"搜索成员错误: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    print(f"错误详情: {error_data}")
                except:
                    print(f"响应内容: {e.response.text[:200]}")
            return []
        except Exception as e:
            print(f"搜索成员错误: {str(e)}")
            return []
    
    def get_user_info(self, user_id: str, timeout: int = 15) -> Optional[UserInfo]:
        """
        获取用户详细信息
        
        Args:
            user_id: 用户ID
            timeout: 请求超时时间（秒）
            
        Returns:
            用户信息对象，如果未找到则返回None
        """
        try:
            # 调用API
            url = f"{self.api_base}/users/{user_id}"
            resp = requests.get(url, headers=self.headers, timeout=timeout)
            resp.raise_for_status()
            resp.encoding = 'utf-8'
            response_data = resp.json()
            
            # API返回格式: {"data": {"id": int, "user_profile_text": "text", ...}}
            user_data = response_data.get("data", {})
            
            if not user_data:
                return None
            
            # 解析user_profile_text提取信息
            profile_text = user_data.get("user_profile_text", "")
            user_info_dict = {}
            
            # 提取基本信息
            user_info_dict["user_id"] = str(user_data.get("id", user_id))
            
            # 解析profile_text提取姓名等信息
            if profile_text:
                lines = profile_text.split("\n")
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    if "用户名" in line and "：" in line:
                        # 格式: "用户名：章宇辰（创业号：100045）"
                        parts = line.split("：", 1)
                        if len(parts) > 1:
                            name_part = parts[1].split("（")[0].strip()
                            user_info_dict["name"] = name_part
                    elif "个人简介" in line and "：" in line:
                        parts = line.split("：", 1)
                        if len(parts) > 1:
                            user_info_dict["bio"] = parts[1].strip()
                    elif "AI印象标签" in line and "：" in line:
                        parts = line.split("：", 1)
                        if len(parts) > 1:
                            tags_str = parts[1].strip()
                            user_info_dict["tags"] = [t.strip() for t in tags_str.split("、") if t.strip()]
            
            # 创建UserInfo对象
            user_info = UserInfo(
                user_id=user_info_dict.get("user_id", str(user_id)),
                name=user_info_dict.get("name", ""),
                bio=user_info_dict.get("bio"),
                tags=user_info_dict.get("tags"),
                wechat_data={"reachable": "微信是否可达：是" in profile_text} if profile_text else None
            )
            
            return user_info
            
        except requests.exceptions.RequestException as e:
            print(f"获取用户信息错误: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    print(f"错误详情: {error_data}")
                except:
                    print(f"响应内容: {e.response.text[:200]}")
            return None
        except Exception as e:
            print(f"获取用户信息错误: {str(e)}")
            return None
    
    def search_ideas(
        self,
        query: str,
        page: int = 1,
        per_page: int = 10,
        timeout: int = 15
    ) -> List[IdeaResult]:
        """
        搜索创业想法/项目
        
        Args:
            query: 搜索查询（语义搜索，建议使用完整句子描述）
            page: 页码，从1开始
            per_page: 每页结果数
            timeout: 请求超时时间（秒）
            
        Returns:
            创业想法/项目搜索结果列表
        """
        try:
            # 构建请求负载
            payload = {
                "query": query,
                "paginate": {
                    "page": page,
                    "per_page": per_page
                },
                "vector_search": True
            }
            
            # 调用API
            url = f"{self.api_base}/ideas/search"
            resp = requests.get(url, json=payload, headers=self.headers, timeout=timeout)
            resp.raise_for_status()
            resp.encoding = 'utf-8'
            response_data = resp.json()
            
            # API返回格式: {"data": [...], "meta": "..."}
            # data字段包含项目列表（JSON格式，不是文本）
            ideas_data = response_data.get("data", [])
            
            # 解析结果
            results = []
            if isinstance(ideas_data, list):
                for item in ideas_data:
                    result = IdeaResult(
                        idea_id=str(item.get("id", "")),
                        title=item.get("title", ""),
                        city=item.get("city"),
                        cover=item.get("cover"),
                        team_members=item.get("team_members"),
                        investment=item.get("investment"),
                        vertical=item.get("vertical"),
                        sub_vertical=item.get("sub_vertical"),
                        created_at=item.get("created_at"),
                        last_accessed_at=item.get("last_accessed_at"),
                        popscore=item.get("popscore"),
                        total_comments=item.get("total_comments"),
                        vip=item.get("vip"),
                        hiring=item.get("hiring")
                    )
                    results.append(result)
            
            return results
            
        except requests.exceptions.RequestException as e:
            print(f"搜索创业想法错误: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    print(f"错误详情: {error_data}")
                except:
                    print(f"响应内容: {e.response.text[:200]}")
            return []
        except Exception as e:
            print(f"搜索创业想法错误: {str(e)}")
            return []
    
    def get_idea_details(self, idea_id: str, timeout: int = 15) -> Optional[IdeaDetails]:
        """
        获取创业想法/项目的详细信息
        
        Args:
            idea_id: 想法/项目ID
            timeout: 请求超时时间（秒）
            
        Returns:
            想法/项目详细信息对象，如果未找到则返回None
        """
        try:
            # 调用API
            url = f"{self.api_base}/ideas/{idea_id}"
            resp = requests.get(url, headers=self.headers, timeout=timeout)
            resp.raise_for_status()
            resp.encoding = 'utf-8'
            response_data = resp.json()
            
            # API返回格式: {"data": {"detail": {...}}}
            data = response_data.get("data", {})
            detail = data.get("detail", {})
            
            if not detail:
                return None
            
            # 提取技能列表
            skills = detail.get("skills", [])
            all_skills = detail.get("all_skills", [])
            
            # 创建IdeaDetails对象
            idea_details = IdeaDetails(
                idea_id=str(detail.get("id", idea_id)),
                title=detail.get("title", ""),
                description=detail.get("description"),
                city=detail.get("city"),
                province=detail.get("province"),
                cover=detail.get("cover"),
                team_members=detail.get("team_members"),
                partners_count=detail.get("partners_count"),
                investment=detail.get("investment"),
                skills=[s if isinstance(s, str) else str(s) for s in skills] if skills else None,
                all_skills=all_skills if all_skills else None,
                vertical=detail.get("vertical"),
                sub_vertical=detail.get("sub_vertical"),
                created_at=detail.get("created_at"),
                last_accessed_at=detail.get("last_accessed_at"),
                popscore=detail.get("popscore"),
                total_comments=detail.get("total_comments"),
                vip=detail.get("vip"),
                hiring=detail.get("hiring")
            )
            
            return idea_details
            
        except requests.exceptions.RequestException as e:
            print(f"获取想法详情错误: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    print(f"错误详情: {error_data}")
                except:
                    print(f"响应内容: {e.response.text[:200]}")
            return None
        except Exception as e:
            print(f"获取想法详情错误: {str(e)}")
            return None


# 全局客户端实例
_aihehuo_client = None


def get_aihehuo_client(api_key: Optional[str] = None, api_base: Optional[str] = None) -> AihehuoClient:
    """
    获取全局爱合伙客户端实例
    
    Args:
        api_key: API密钥，仅在首次调用时使用
        api_base: API基础URL，仅在首次调用时使用
        
    Returns:
        爱合伙客户端实例
    """
    global _aihehuo_client
    if _aihehuo_client is None:
        _aihehuo_client = AihehuoClient(api_key, api_base)
    return _aihehuo_client


def search_members(
    query: str,
    page: int = 1,
    per_page: int = 10,
    wechat_reachable_only: bool = False,
    investor: bool = False,
    excluded_ids: Optional[List[str]] = None,
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
    timeout: int = 15
) -> List[Dict[str, Any]]:
    """
    便捷的成员搜索函数
    
    Args:
        query: 搜索查询（语义搜索，长度必须大于5个字符）
        page: 页码，从1开始
        per_page: 每页结果数
        wechat_reachable_only: 是否只返回微信上能直接触达的用户
        investor: 是否只搜索投资人
        excluded_ids: 要排除的用户ID列表
        api_key: API密钥，如果提供则使用此密钥，否则使用全局客户端
        api_base: API基础URL，如果提供则使用此URL，否则使用全局客户端
        timeout: 请求超时时间（秒）
        
    Returns:
        成员搜索结果字典列表
    """
    try:
        if api_key or api_base:
            # 使用提供的API密钥或URL创建临时客户端
            client = AihehuoClient(api_key, api_base)
        else:
            # 使用全局客户端
            client = get_aihehuo_client()
        
        results = client.search_members(
            query=query,
            page=page,
            per_page=per_page,
            wechat_reachable_only=wechat_reachable_only,
            investor=investor,
            excluded_ids=excluded_ids,
            timeout=timeout
        )
        
        # 转换为字典格式以保持兼容性
        return [result.to_dict() for result in results]
        
    except Exception as e:
        print(f"搜索成员功能调用错误: {str(e)}")
        return []


def get_user_info(
    user_id: str,
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
    timeout: int = 15
) -> Optional[Dict[str, Any]]:
    """
    便捷的用户信息查询函数
    
    Args:
        user_id: 用户ID
        api_key: API密钥，如果提供则使用此密钥，否则使用全局客户端
        api_base: API基础URL，如果提供则使用此URL，否则使用全局客户端
        timeout: 请求超时时间（秒）
        
    Returns:
        用户信息字典，如果未找到则返回None
    """
    try:
        if api_key or api_base:
            # 使用提供的API密钥或URL创建临时客户端
            client = AihehuoClient(api_key, api_base)
        else:
            # 使用全局客户端
            client = get_aihehuo_client()
        
        user_info = client.get_user_info(user_id, timeout=timeout)
        
        if user_info:
            return user_info.to_dict()
        return None
        
    except Exception as e:
        print(f"获取用户信息功能调用错误: {str(e)}")
        return None


def test_search_members(query: str = "寻找有创业经验的AI技术专家", per_page: int = 5):
    """
    测试成员搜索功能
    
    Args:
        query: 测试查询
        per_page: 每页结果数
    """
    print(f"\n=== 测试爱合伙成员搜索功能 ===")
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
        else:
            print("未找到搜索结果")
            
    except Exception as e:
        print(f"搜索测试失败: {str(e)}")


def get_idea_details(
    idea_id: str,
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
    timeout: int = 15
) -> Optional[Dict[str, Any]]:
    """
    便捷的想法/项目详情查询函数
    
    Args:
        idea_id: 想法/项目ID
        api_key: API密钥，如果提供则使用此密钥，否则使用全局客户端
        api_base: API基础URL，如果提供则使用此URL，否则使用全局客户端
        timeout: 请求超时时间（秒）
        
    Returns:
        想法/项目详细信息字典，如果未找到则返回None
    """
    try:
        if api_key or api_base:
            # 使用提供的API密钥或URL创建临时客户端
            client = AihehuoClient(api_key, api_base)
        else:
            # 使用全局客户端
            client = get_aihehuo_client()
        
        idea_details = client.get_idea_details(idea_id, timeout=timeout)
        
        if idea_details:
            return idea_details.to_dict()
        return None
        
    except Exception as e:
        print(f"获取想法详情功能调用错误: {str(e)}")
        return None


def test_get_idea_details(idea_id: str = "31009"):
    """
    测试想法/项目详情查询功能
    
    Args:
        idea_id: 测试想法/项目ID
    """
    print(f"\n=== 测试爱合伙想法/项目详情查询功能 ===")
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
        else:
            print("未找到想法/项目详情")
            
    except Exception as e:
        print(f"想法/项目详情查询测试失败: {str(e)}")


def test_get_user_info(user_id: str = "1"):
    """
    测试用户信息查询功能
    
    Args:
        user_id: 测试用户ID
    """
    print(f"\n=== 测试爱合伙用户信息查询功能 ===")
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
        else:
            print("未找到用户信息")
            
    except Exception as e:
        print(f"用户信息查询测试失败: {str(e)}")


def search_ideas(
    query: str,
    page: int = 1,
    per_page: int = 10,
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
    timeout: int = 15
) -> List[Dict[str, Any]]:
    """
    便捷的创业想法/项目搜索函数
    
    Args:
        query: 搜索查询（语义搜索，建议使用完整句子描述）
        page: 页码，从1开始
        per_page: 每页结果数
        api_key: API密钥，如果提供则使用此密钥，否则使用全局客户端
        api_base: API基础URL，如果提供则使用此URL，否则使用全局客户端
        timeout: 请求超时时间（秒）
        
    Returns:
        创业想法/项目搜索结果字典列表
    """
    try:
        if api_key or api_base:
            # 使用提供的API密钥或URL创建临时客户端
            client = AihehuoClient(api_key, api_base)
        else:
            # 使用全局客户端
            client = get_aihehuo_client()
        
        results = client.search_ideas(
            query=query,
            page=page,
            per_page=per_page,
            timeout=timeout
        )
        
        # 转换为字典格式以保持兼容性
        return [result.to_dict() for result in results]
        
    except Exception as e:
        print(f"搜索创业想法功能调用错误: {str(e)}")
        return []


def test_search_ideas(query: str = "AI创业项目", per_page: int = 5):
    """
    测试创业想法搜索功能
    
    Args:
        query: 测试查询
        per_page: 每页结果数
    """
    print(f"\n=== 测试爱合伙创业想法搜索功能 ===")
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
        else:
            print("未找到搜索结果")
            
    except Exception as e:
        print(f"搜索测试失败: {str(e)}")


if __name__ == "__main__":
    # 运行测试
    test_search_members()
    test_get_user_info()
    test_search_ideas()
    test_get_idea_details()
