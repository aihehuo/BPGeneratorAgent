"""
BP Generation Agent API Server
提供REST API接口来调用BP生成功能
"""

import os
import sys
import uuid
from typing import Optional
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn

from src.bp_generation_agent import BPGenerationAgent, create_bp_agent
from src.utils.config import load_config


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


class GenerateBPResponse(BaseModel):
    """生成BP响应模型"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    session_id: str = Field(..., description="会话ID")
    data: Optional[dict] = Field(None, description="生成结果数据")
    error: Optional[str] = Field(None, description="错误信息（如果失败）")


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


@app.post("/api/v1/generate", response_model=GenerateBPResponse, tags=["BP Generation"])
async def generate_bp(request: GenerateBPRequest):
    """
    生成商业计划书
    
    Args:
        request: 生成BP请求，包含商业创意等参数
        
    Returns:
        生成结果，包括sessionID、文件路径、Markdown内容等
    """
    try:
        # 获取Agent实例
        agent = get_agent()
        
        # 如果提供了session_id，验证格式
        session_id = request.session_id
        if session_id:
            try:
                uuid.UUID(session_id)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"无效的session_id格式: {session_id}。必须是有效的UUID格式。"
                )
        # 如果没有提供session_id，传递None，让bp_agent自己生成
        
        # 调用generate_bp方法，传入session_id（可能为None）
        result = agent.generate_bp(
            business_idea=request.business_idea,
            output_file=request.output_file,
            save_report=request.save_report,
            session_id=session_id
        )
        
        # 构建响应数据
        markdown = result.get("markdown")
        bp_structure = result.get("bp_structure", [])
        
        response_data = {
            "output_file": result.get("output_file"),
            "markdown_length": len(markdown) if markdown else 0,
            "bp_structure_count": len(bp_structure) if bp_structure else 0,
            "has_evaluation": result.get("evaluation_result") is not None,
            "has_pitch": result.get("pitch_result") is not None,
            "has_ppt": result.get("ppt_result") is not None,
            "has_partner_search": result.get("partner_search_result") is not None,
            "partner_report_file": result.get("partner_report_file"),
        }
        
        # 如果生成失败（有错误），添加错误信息
        if result.get("error"):
            response_data["error"] = result.get("error")
            response_data["input_completeness"] = result.get("input_completeness")
        
        # 从result中获取session_id和session_dir（由bp_agent生成）
        session_id = result.get("session_id")
        session_dir = result.get("session_dir")
        
        # 检查是否有错误（输入不完整等情况）
        if result.get("error"):
            # 如果请求保存报告，包含文件路径信息
            if request.save_report and session_dir:
                response_data["session_dir"] = session_dir
            
            return GenerateBPResponse(
                success=False,
                message="商业计划书生成失败",
                session_id=session_id or "unknown",
                data=response_data,
                error=result.get("error")
            )
        
        # 如果请求保存报告，包含文件路径信息
        if request.save_report and session_dir:
            response_data["files"] = {
                "main_report": result.get("output_file"),
                "ppt_design": result.get("ppt_design_file"),
                "partner_report": result.get("partner_report_file"),
            }
            response_data["session_dir"] = session_dir
        
        return GenerateBPResponse(
            success=True,
            message="商业计划书生成成功",
            session_id=session_id or "unknown",
            data=response_data,
            error=None
        )
        
    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        import traceback
        error_msg = str(e)
        error_trace = traceback.format_exc()
        
        return GenerateBPResponse(
            success=False,
            message="商业计划书生成失败",
            session_id=request.session_id or "unknown",
            data=None,
            error=f"{error_msg}\n\n{error_trace}"
        )


@app.post("/api/v1/generate/preview", tags=["BP Generation"])
async def generate_bp_preview(request: GenerateBPRequest):
    """
    生成商业计划书预览（返回Markdown内容的前N个字符）
    
    Args:
        request: 生成BP请求
        
    Returns:
        包含Markdown预览的响应
    """
    try:
        agent = get_agent()
        
        # 如果提供了session_id，验证格式
        session_id = request.session_id
        if session_id:
            try:
                uuid.UUID(session_id)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"无效的session_id格式: {session_id}。必须是有效的UUID格式。"
                )
        # 如果没有提供session_id，传递None，让bp_agent自己生成
        
        result = agent.generate_bp(
            business_idea=request.business_idea,
            output_file=request.output_file,
            save_report=request.save_report,
            session_id=session_id
        )
        
        markdown_content = result.get("markdown") or ""
        preview_length = 2000  # 预览长度
        
        # 从result中获取session_id和session_dir（由bp_agent生成）
        session_id = result.get("session_id")
        session_dir = result.get("session_dir")
        
        # 检查是否有错误
        if result.get("error"):
            return {
                "success": False,
                "message": "商业计划书生成失败",
                "session_id": session_id or "unknown",
                "data": {
                    "error": result.get("error"),
                    "input_completeness": result.get("input_completeness"),
                    "session_dir": session_dir,
                },
                "error": result.get("error")
            }
        
        return {
            "success": True,
            "message": "商业计划书生成成功",
            "session_id": session_id or "unknown",
            "data": {
                "preview": markdown_content[:preview_length] if markdown_content else "",
                "full_length": len(markdown_content) if markdown_content else 0,
                "is_truncated": len(markdown_content) > preview_length if markdown_content else False,
                "output_file": result.get("output_file"),
                "session_dir": session_dir,
            }
        }
        
    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        import traceback
        return {
            "success": False,
            "message": "商业计划书生成失败",
            "session_id": request.session_id or "unknown",
            "error": str(e),
            "traceback": traceback.format_exc()
        }


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
            raise HTTPException(status_code=403, detail="访问被拒绝：文件路径不安全")
        
        if not os.path.exists(file_path_abs):
            # 提供更详细的错误信息用于调试
            import logging
            logging.error(f"文件不存在: filename={filename}, session_dir={session_dir_abs}, file_path={file_path_abs}, exists={os.path.exists(session_dir_abs)}")
            raise HTTPException(
                status_code=404, 
                detail=f"文件不存在: {filename}\nSession目录: {session_dir_abs}\n查找路径: {file_path_abs}\nSession目录存在: {os.path.exists(session_dir_abs)}"
            )
        
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
        # 确保内容以UTF-8编码的字节形式传递
        content_bytes = content.encode('utf-8')
        return Response(
            content=content_bytes,
            media_type=content_type,
            headers={
                "Content-Disposition": f'inline; filename="{os.path.basename(filename)}"'
            }
        )
    except HTTPException:
        raise
    except UnicodeDecodeError as e:
        # 处理编码错误
        raise HTTPException(
            status_code=500, 
            detail=f"文件编码错误: 无法使用UTF-8读取文件。请检查文件编码格式。错误详情: {str(e)}"
        )
    except Exception as e:
        # 确保错误消息可以正确编码
        error_msg = str(e)
        try:
            # 尝试编码错误消息以确保它可以被正确传输
            error_msg.encode('utf-8')
        except UnicodeEncodeError:
            error_msg = "读取文件失败: 编码错误"
        raise HTTPException(status_code=500, detail=error_msg)


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
            raise HTTPException(status_code=404, detail=f"Session 目录不存在: {session_id}")
        
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
        raise HTTPException(status_code=500, detail=f"列出文件失败: {str(e)}")


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

