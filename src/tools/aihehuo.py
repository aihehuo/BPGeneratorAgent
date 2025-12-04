"""
爱合伙平台工具实现
提供爱合伙平台成员搜索和用户信息查询功能
直接调用爱合伙API
"""

import os
import re
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
    age: Optional[int] = None
    age_range: Optional[str] = None
    profile_url: Optional[str] = None  # 个人主页链接
    user_number: Optional[str] = None  # 创业号
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "user_id": self.user_id,
            "name": self.name,
            "bio": self.bio,
            "goal": self.goal,
            "tags": self.tags,
            "wechat_reachable": self.wechat_reachable,
            "age": self.age,
            "age_range": self.age_range,
            "profile_url": self.profile_url,
            "user_number": self.user_number
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
            "Accept": "application/json"
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
            
            # API现在直接返回JSON格式的数据
            # 响应格式: {"data": [{"id": 320650, "number": 9520650, "name": "...", ...}, ...], "meta": {...}}
            data = response_data.get("data", [])
            
            # 如果data是字符串（向后兼容旧格式），返回空列表
            if isinstance(data, str):
                print("警告: API返回了文本格式的数据，但期望JSON格式")
                return []
            
            # 解析JSON格式的结果
            results = []
            if isinstance(data, list):
                for user_data in data:
                    if not isinstance(user_data, dict):
                        continue
                    
                    # 直接从JSON中提取字段
                    user_id = str(user_data.get("id", ""))
                    user_number = str(user_data.get("number", "")) if user_data.get("number") else None
                    name = user_data.get("name", "")
                    
                    # 如果用户名为空，跳过
                    if not name and not user_id:
                        continue
                    
                    # 提取bio（简介）
                    bio = user_data.get("bio", "")
                    
                    # 提取tags（从skills数组中提取name字段）
                    tags = []
                    skills = user_data.get("skills", [])
                    if isinstance(skills, list):
                        tags = [skill.get("name", "") for skill in skills if isinstance(skill, dict) and skill.get("name")]
                    
                    # 提取年龄段（从skills中查找包含"后"的标签，如"80后"、"90后"）
                    age_range = None
                    for skill in skills:
                        if isinstance(skill, dict):
                            skill_name = skill.get("name", "")
                            # 使用正则表达式匹配"数字+后"格式，如"80后"、"90后"
                            if skill_name and re.match(r'^\d+[后年代]', skill_name):
                                age_range = skill_name
                                break
                    
                    # 提取年龄（如果description中包含年龄信息，可以尝试提取，但通常从skills中获取年龄段更准确）
                    age = None
                    # 暂时不提取具体年龄，因为JSON中没有直接提供
                    
                    # 构建个人主页链接（基于user_id）
                    profile_url = None
                    if user_number:
                        profile_url = f"https://www.aihehuo.com/users/{user_number}"
                    
                    result = MemberResult(
                        user_id=user_id,
                        name=name,
                        bio=bio,
                        tags=tags if tags else None,
                        age=age,
                        age_range=age_range,
                        profile_url=profile_url,
                        user_number=user_number
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
    
    def _extract_age(self, value: str) -> Optional[int]:
        """
        从字符串中提取年龄
        
        Args:
            value: 包含年龄信息的字符串
            
        Returns:
            年龄（整数），如果无法提取则返回None
        """
        import re
        # 尝试提取数字年龄，如 "25岁", "年龄: 25", "age: 25" 等
        # 优先匹配明确的年龄格式
        patterns = [
            (r'(\d+)岁', True),  # "25岁" - 明确格式，直接返回
            (r'年龄[：:]?\s*(\d+)', True),  # "年龄: 25" 或 "年龄：25" - 明确格式
            (r'age[：:]?\s*(\d+)', True),  # "age: 25" - 明确格式
            (r'(\d{1,2})\s*岁', True),  # "25 岁" - 明确格式
        ]
        
        # 先尝试明确的年龄格式
        for pattern, strict in patterns:
            match = re.search(pattern, value, re.IGNORECASE)
            if match:
                age = int(match.group(1))
                # 年龄合理性检查：通常在18-100岁之间
                if 18 <= age <= 100:
                    return age
        
        # 如果没有找到明确的年龄格式，尝试提取可能包含年龄的数字
        # 但需要更谨慎，避免误匹配年份或其他数字
        # 只在值很短（可能是单独的数字）时才尝试
        if len(value.strip()) <= 3:  # 只有很短的值才可能是单独的数字
            match = re.search(r'^(\d{2})$', value.strip())
            if match:
                age = int(match.group(1))
                # 更保守的范围，避免误匹配
                if 20 <= age <= 65:  # 创业人群常见年龄段
                    return age
        
        return None
    
    def _extract_age_from_bio(self, bio: str) -> Optional[int]:
        """
        从个人简介中提取年龄信息
        
        Args:
            bio: 个人简介文本
            
        Returns:
            年龄（整数），如果无法提取则返回None
        """
        if not bio:
            return None
        
        # 先尝试直接提取年龄
        age = self._extract_age(bio)
        if age:
            return age
        
        # 尝试提取出生年份
        import re
        from datetime import datetime
        year_patterns = [
            r'(\d{4})年.*出生',  # "1990年出生"
            r'出生于[：:]?\s*(\d{4})',  # "出生于1990" 或 "出生于：1990"
            r'birth[：:]?\s*(\d{4})',  # "birth: 1990"
            r'(\d{4})年生',  # "1990年生"
        ]
        
        current_year = datetime.now().year
        for pattern in year_patterns:
            match = re.search(pattern, bio, re.IGNORECASE)
            if match:
                birth_year = int(match.group(1))
                # 出生年份合理性检查：通常在1950-2006之间（对应18-74岁）
                # 创业人群通常在18-70岁之间
                if 1950 <= birth_year <= current_year - 18:
                    age = current_year - birth_year
                    if 18 <= age <= 100:
                        return age
        
        return None
    
    def _calculate_age_range(self, age: int) -> str:
        """
        根据年龄计算年龄段
        
        Args:
            age: 年龄
            
        Returns:
            年龄段字符串
        """
        if age < 25:
            return "20-24岁"
        elif age < 30:
            return "25-29岁"
        elif age < 35:
            return "30-34岁"
        elif age < 40:
            return "35-39岁"
        elif age < 45:
            return "40-44岁"
        elif age < 50:
            return "45-49岁"
        elif age < 55:
            return "50-54岁"
        elif age < 60:
            return "55-59岁"
        else:
            return "60岁以上"
    
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
    
    def upload_file(
        self,
        file_path: str,
        timeout: int = 60
    ) -> Optional[Dict[str, Any]]:
        """
        上传文件到云存储
        
        Args:
            file_path: 要上传的文件的本地绝对路径
            timeout: 请求超时时间（秒），默认60秒
            
        Returns:
            上传结果字典，包含文件URL等信息，如果失败则返回None
        """
        try:
            # 验证文件是否存在
            if not os.path.exists(file_path):
                print(f"上传文件错误: 文件不存在 - {file_path}")
                return None
            
            # 构建上传URL
            url = f"{self.api_base}/micro/upload"
            
            # 获取文件名
            filename = os.path.basename(file_path)
            
            # 确定MIME类型
            import mimetypes
            mime_type, _ = mimetypes.guess_type(file_path)
            
            # 处理mimetypes无法识别的文件类型
            if mime_type is None:
                # 根据文件扩展名手动设置MIME类型
                file_ext = os.path.splitext(file_path)[1].lower()
                mime_type_map = {
                    '.md': 'text/markdown',
                    '.markdown': 'text/markdown',
                    '.txt': 'text/plain',
                    '.html': 'text/html',
                    '.htm': 'text/html',
                    '.json': 'application/json',
                    '.xml': 'application/xml',
                    '.pdf': 'application/pdf',
                    '.png': 'image/png',
                    '.jpg': 'image/jpeg',
                    '.jpeg': 'image/jpeg',
                    '.gif': 'image/gif',
                    '.svg': 'image/svg+xml',
                }
                mime_type = mime_type_map.get(file_ext, 'application/octet-stream')
            
            # 准备上传请求头（注意：multipart/form-data不需要Content-Type头，requests会自动设置）
            upload_headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Accept": "application/json"
            }
            
            # 使用multipart/form-data上传文件
            with open(file_path, 'rb') as f:
                files = {
                    'file': (filename, f, mime_type)
                }
                
                resp = requests.post(url, headers=upload_headers, files=files, timeout=timeout)
            
            resp.raise_for_status()
            resp.encoding = 'utf-8'
            response_data = resp.json()
            
            return response_data
            
        except requests.exceptions.RequestException as e:
            print(f"上传文件错误: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    print(f"错误详情: {error_data}")
                except:
                    print(f"响应内容: {e.response.text[:200]}")
            return None
        except Exception as e:
            print(f"上传文件错误: {str(e)}")
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


def upload_file(
    file_path: str,
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
    timeout: int = 60
) -> Optional[Dict[str, Any]]:
    """
    便捷的文件上传函数
    
    Args:
        file_path: 要上传的文件的本地绝对路径
        api_key: API密钥，如果提供则使用此密钥，否则使用全局客户端
        api_base: API基础URL，如果提供则使用此URL，否则使用全局客户端
        timeout: 请求超时时间（秒），默认60秒
        
    Returns:
        上传结果字典，包含文件URL等信息，如果失败则返回None
    """
    try:
        if api_key or api_base:
            # 使用提供的API密钥或URL创建临时客户端
            client = AihehuoClient(api_key, api_base)
        else:
            # 使用全局客户端
            client = get_aihehuo_client()
        
        result = client.upload_file(file_path, timeout=timeout)
        return result
        
    except Exception as e:
        print(f"上传文件功能调用错误: {str(e)}")
        return None


