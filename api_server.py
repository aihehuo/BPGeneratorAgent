"""
BP Generation Agent API Server
提供REST API接口来调用BP生成功能
"""

import os
import sys
import uuid
import time
import threading
import httpx
import re
from typing import Optional, Dict, Any
from datetime import datetime
from urllib.parse import urljoin

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn

from src.bp_generation_agent import BPGenerationAgent, create_bp_agent
from src.utils.config import load_config
from src.utils.i18n import translate_status_message


# 全局Agent实例
_agent: Optional[BPGenerationAgent] = None


def get_agent() -> BPGenerationAgent:
    """获取或创建Agent实例（单例模式）"""
    global _agent
    if _agent is None:
        config = load_config()
        _agent = BPGenerationAgent(config)
    return _agent


# FastAPI应用
app = FastAPI(
    title="BP Generation Agent API",
    description="商业计划书生成API服务",
    version="1.0.0",
)

# 添加 CORS 支持
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源（生产环境应限制为特定域名）
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 请求模型
class GenerateBPRequest(BaseModel):
    """生成BP请求模型"""
    business_idea: str = Field(..., description="商业创意", min_length=1)
    output_file: Optional[str] = Field(None, description="指定输出文件路径（可选）")
    save_report: bool = Field(True, description="是否保存报告到文件")
    session_id: Optional[str] = Field(None, description="Session ID（可选，如果提供则使用该Session，否则创建新的）")


class GenerateBPAsyncRequest(BaseModel):
    """异步生成BP请求模型"""
    business_idea: str = Field(..., description="商业创意", min_length=1)
    output_file: Optional[str] = Field(None, description="指定输出文件路径（可选）")
    save_report: bool = Field(True, description="是否保存报告到文件")
    session_id: Optional[str] = Field(None, description="Session ID（可选，如果提供则使用该Session，否则创建新的）")
    callback_url: str = Field(..., description="状态更新回调URL，将接收POST请求包含状态更新、markdown摘要和中间产物URL")


class GenerateBPResponse(BaseModel):
    """生成BP响应模型"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    session_id: str = Field(..., description="会话ID")
    data: Optional[dict] = Field(None, description="生成结果数据")
    error: Optional[str] = Field(None, description="错误信息（如果失败）")


class GenerateBPAsyncResponse(BaseModel):
    """异步生成BP响应模型"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    session_id: str = Field(..., description="会话ID，用于查询状态和获取文件")


class HealthResponse(BaseModel):
    """健康检查响应模型"""
    status: str = Field(..., description="服务状态")
    timestamp: str = Field(..., description="时间戳")
    agent_initialized: bool = Field(..., description="Agent是否已初始化")


@app.get("/", tags=["Root"])
async def root():
    """根路径，返回API信息"""
    return {
        "name": "BP Generation Agent API",
        "version": "1.0.0",
        "description": "商业计划书生成API服务",
        "endpoints": {
            "health": "/health",
            "generate": "/api/v1/generate",
            "generate_async": "/api/v1/generate-async",
            "docs": "/docs",
        }
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """健康检查端点"""
    try:
        agent = get_agent()
        return HealthResponse(
            status="healthy",
            timestamp=datetime.now().isoformat(),
            agent_initialized=agent is not None
        )
    except Exception as e:
        return HealthResponse(
            status="unhealthy",
            timestamp=datetime.now().isoformat(),
            agent_initialized=False
        )



# ==============================================================================
# Synchronous BP generation endpoints removed
# ==============================================================================
# The following synchronous endpoints have been removed:
# - POST /api/v1/generate - Synchronous BP generation
# - POST /api/v1/generate/preview - Synchronous BP preview
#
# Only async generation is supported now via:
# - POST /api/v1/generate-async - Asynchronous BP generation with callbacks
# ==============================================================================


@app.get("/api/v1/config", tags=["Config"])
async def get_config():
    """获取当前配置信息"""
    try:
        config = load_config()
        return {
            "success": True,
            "data": {
                "default_llm_provider": config.default_llm_provider,
                "output_dir": config.output_dir,
                "aihehuo_available": bool(config.aihehuo_api_key),
            }
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@app.get("/api/v1/files/{session_id}/{filename:path}", tags=["Files"])
async def get_file(session_id: str, filename: str):
    """
    获取生成的文件内容
    
    Args:
        session_id: Session ID
        filename: 文件名（支持路径，如 subfolder/file.md）
        
    Returns:
        文件内容
    """
    try:
        config = load_config()
        session_dir = os.path.join(config.output_dir, session_id)
        
        # 规范化文件名路径（处理 URL 编码等）
        filename = filename.lstrip('/')
        file_path = os.path.join(session_dir, filename)
        
        # 规范化路径，处理 .. 等相对路径
        session_dir_abs = os.path.abspath(session_dir)
        file_path_abs = os.path.abspath(file_path)
        file_path_abs = os.path.normpath(file_path_abs)
        session_dir_abs = os.path.normpath(session_dir_abs)
        
        # 安全检查：确保文件在 session_dir 内
        if not file_path_abs.startswith(session_dir_abs):
            raise HTTPException(status_code=403, detail="Access denied: File path is not secure")
        
        if not os.path.exists(file_path_abs):
            # 提供更详细的错误信息用于调试
            import logging
            logging.error(f"File not found: filename={filename}, session_dir={session_dir_abs}, file_path={file_path_abs}, exists={os.path.exists(session_dir_abs)}")
            error_detail = (
                f"File not found: {filename}\n"
                f"Session directory: {session_dir_abs}\n"
                f"Requested path: {file_path_abs}\n"
                f"Session directory exists: {os.path.exists(session_dir_abs)}"
            )
            raise HTTPException(status_code=404, detail=error_detail)
        
        # 读取文件内容（使用绝对路径）
        with open(file_path_abs, "r", encoding="utf-8") as f:
            content = f.read()
        
        # 根据文件类型设置 Content-Type (确保包含UTF-8编码)
        content_type = "text/plain; charset=utf-8"
        if filename.endswith(".md"):
            content_type = "text/markdown; charset=utf-8"
        elif filename.endswith(".html"):
            content_type = "text/html; charset=utf-8"
        elif filename.endswith(".json"):
            content_type = "application/json; charset=utf-8"
        
        from fastapi.responses import Response
        from urllib.parse import quote
        
        # 确保内容以UTF-8编码的字节形式传递
        try:
            content_bytes = content.encode('utf-8')
        except (UnicodeEncodeError, UnicodeDecodeError) as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to encode file content: {str(e)}"
            )
        
        # 处理文件名，使用RFC 5987格式支持UTF-8（避免latin-1编码问题）
        safe_filename = os.path.basename(filename)
        try:
            # URL编码文件名（UTF-8字节）
            encoded_filename = quote(safe_filename.encode('utf-8'), safe='')
            # 只使用RFC 5987格式，不包含latin-1兼容的filename参数
            content_disposition = f'inline; filename*=UTF-8\'\'{encoded_filename}'
        except (UnicodeEncodeError, UnicodeDecodeError):
            # 如果文件名编码失败，使用ASCII安全的版本
            safe_ascii_filename = safe_filename.encode('ascii', errors='ignore').decode('ascii') or 'file'
            encoded_filename = quote(safe_ascii_filename, safe='')
            content_disposition = f'inline; filename*=UTF-8\'\'{encoded_filename}'
        
        return Response(
            content=content_bytes,
            media_type=content_type,
            headers={
                "Content-Disposition": content_disposition
            }
        )
    except HTTPException:
        raise
    except UnicodeDecodeError as e:
        # 处理编码错误
        raise HTTPException(
            status_code=500, 
            detail=f"File encoding error: Cannot read file with UTF-8 encoding. Please check file encoding format. Error: {str(e)}"
        )
    except Exception as e:
        # 确保错误消息可以正确编码
        error_msg = str(e)
        try:
            # 尝试编码错误消息以确保它可以被正确传输
            error_msg.encode('utf-8')
        except UnicodeEncodeError:
            error_msg = "Failed to read file: encoding error"
        raise HTTPException(status_code=500, detail=error_msg)



# ==============================================================================
# Note: Old callback and translation helper functions have been removed
# ==============================================================================
# The following functions have been moved to other modules:
# - _send_callback, _extract_markdown_summary, _build_artifact_urls
#   -> Moved to BPGenerationAgent (src/bp_generation_agent.py)
# - _detect_language, _translate_status_message, _STATUS_TRANSLATIONS
#   -> Moved to i18n module (src/utils/i18n.py)
#
# API Server now only handles high-level orchestration.
# All workflow execution and callback logic is handled by BPGenerationAgent.
# ==============================================================================


def _run_async_generation(
    agent: BPGenerationAgent,
    business_idea: str,
    output_file: Optional[str],
    save_report: bool,
    session_id: str,
    callback_url: str,
    base_url: str = "http://localhost:8000"
):
    """
    Run BP generation in a background thread with callback support.

    High-level orchestration: delegates workflow execution and callbacks to BPGenerationAgent.

    Args:
        agent: BPGenerationAgent instance
        business_idea: Business idea
        output_file: Optional output file path
        save_report: Whether to save report
        session_id: Session ID
        callback_url: Callback URL for status updates
        base_url: Base URL for artifact URLs
    """
    try:
        # Delegate to BPGenerationAgent - it handles all workflow execution and callbacks
        result = agent.generate_bp(
            business_idea=business_idea,
            output_file=output_file,
            save_report=save_report,
            session_id=session_id,
            callback_url=callback_url,
            api_base_url=base_url
        )

        # Log success
        if result.get("output_file"):
            print(f"✓ BP generation completed successfully")
            print(f"  Output file: {result['output_file']}")
            print(f"  Session ID: {result['session_id']}")

    except Exception as e:
        # Agent already sent error callback, just log here
        import traceback
        print(f"✗ BP generation failed: {str(e)}")
        traceback.print_exc()


@app.post("/api/v1/generate-async", response_model=GenerateBPAsyncResponse, tags=["BP Generation"])
async def generate_bp_async(request: GenerateBPAsyncRequest, http_request: Request):
    """
    Asynchronously generate business plan with callback support.
    
    This endpoint immediately returns a session_id and executes the generation
    in a background thread. Status updates and intermediate artifacts are sent
    to the provided callback URL via POST requests.
    
    Args:
        request: Async generation request with callback URL
        http_request: FastAPI request object for getting base URL
        
    Returns:
        Response with session_id
    """
    try:
        agent = get_agent()
        config = load_config()
        
        # Validate session_id if provided
        session_id = request.session_id
        if session_id:
            try:
                uuid.UUID(session_id)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid session_id format: {session_id}. Must be a valid UUID format."
                )
            
            # Check if session already exists (has history)
            # Check both session directory and chat history file
            session_dir = os.path.join(config.output_dir, session_id)
            chat_history_base_dir = "/tmp/bp_agent_sessions"  # Default base dir for chat history
            chat_history_dir = os.path.join(chat_history_base_dir, session_id)
            chat_history_file = os.path.join(chat_history_dir, "chat_history.jsonl")
            
            session_exists = (
                os.path.exists(session_dir) or 
                os.path.exists(chat_history_file)
            )
            
            if session_exists:
                print(f"[Session Check] Session {session_id} already exists (has history), will continue with existing session")
            else:
                print(f"[Session Check] Session {session_id} is new, will create new session")
        else:
            # Generate new session_id
            session_id = str(uuid.uuid4())
        
        # Get base URL from request or environment variable
        base_url = os.getenv("API_BASE_URL")
        if not base_url:
            # Construct from request
            base_url = f"{http_request.url.scheme}://{http_request.url.netloc}"
        
        # Start generation in background thread
        thread = threading.Thread(
            target=_run_async_generation,
            args=(
                agent,
                request.business_idea,
                request.output_file,
                request.save_report,
                session_id,
                request.callback_url,
                base_url
            ),
            daemon=True
        )
        thread.start()
        
        # Translate the initial response message to match user's language
        initial_message = translate_status_message(
            request.business_idea, 
            "started"
        )
        
        return GenerateBPAsyncResponse(
            success=True,
            message=initial_message,
            session_id=session_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        return GenerateBPAsyncResponse(
            success=False,
            message=f"Failed to start async generation: {str(e)}",
            session_id=request.session_id or "unknown"
        )


@app.get("/api/v1/files/{session_id}", tags=["Files"])
async def list_files(session_id: str):
    """
    列出 Session 目录下的所有文件
    
    Args:
        session_id: Session ID
        
    Returns:
        文件列表
    """
    try:
        config = load_config()
        session_dir = os.path.join(config.output_dir, session_id)
        
        if not os.path.exists(session_dir):
            raise HTTPException(status_code=404, detail=f"Session directory does not exist: {session_id}")
        
        files = []
        for root, dirs, filenames in os.walk(session_dir):
            for filename in filenames:
                file_path = os.path.join(root, filename)
                rel_path = os.path.relpath(file_path, session_dir)
                file_stat = os.stat(file_path)
                files.append({
                    "name": filename,
                    "path": rel_path,
                    "size": file_stat.st_size,
                    "modified": datetime.fromtimestamp(file_stat.st_mtime).isoformat()
                })
        
        return {
            "success": True,
            "session_id": session_id,
            "files": files
        }
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        try:
            error_msg.encode('utf-8')
        except (UnicodeEncodeError, UnicodeDecodeError):
            error_msg = "Failed to list files: encoding error"
        raise HTTPException(status_code=500, detail=error_msg)


def main():
    """启动API服务器"""
    import argparse
    
    parser = argparse.ArgumentParser(description="BP Generation Agent API Server")
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="服务器主机地址（默认: 0.0.0.0）"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="服务器端口（默认: 8000）"
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="启用自动重载（开发模式）"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="工作进程数（默认: 1）"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("BP Generation Agent API Server")
    print("=" * 60)
    print(f"启动服务器: http://{args.host}:{args.port}")
    print(f"API文档: http://{args.host}:{args.port}/docs")
    print(f"健康检查: http://{args.host}:{args.port}/health")
    print("=" * 60)
    
    uvicorn.run(
        "api_server:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        workers=args.workers if not args.reload else 1,
    )


if __name__ == "__main__":
    main()

