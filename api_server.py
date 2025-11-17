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

from src.bp_agent import BPGenerationAgent, create_bp_agent
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
        if request.session_id:
            try:
                uuid.UUID(request.session_id)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"无效的session_id格式: {request.session_id}。必须是有效的UUID格式。"
                )
            # 构建session_dir（如果提供了session_id）
            config = load_config()
            session_dir = os.path.join(config.output_dir, request.session_id)
        else:
            # 如果没有提供session_id，传递None，让bp_agent自己生成
            session_dir = None
        
        # 调用generate_bp方法，传入session_dir（可能为None）
        result = agent.generate_bp(
            business_idea=request.business_idea,
            output_file=request.output_file,
            save_report=request.save_report,
            session_dir=session_dir
        )
        
        # 构建响应数据
        response_data = {
            "output_file": result.get("output_file"),
            "markdown_length": len(result.get("markdown", "")),
            "bp_structure_count": len(result.get("bp_structure", [])),
            "has_evaluation": result.get("evaluation_result") is not None,
            "has_pitch": result.get("pitch_result") is not None,
            "has_ppt": result.get("ppt_result") is not None,
            "has_partner_search": result.get("partner_search_result") is not None,
            "partner_report_file": result.get("partner_report_file"),
        }
        
        # 从result中获取session_id和session_dir（由bp_agent生成）
        session_id = result.get("session_id")
        session_dir = result.get("session_dir")
        
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
        if request.session_id:
            try:
                uuid.UUID(request.session_id)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"无效的session_id格式: {request.session_id}。必须是有效的UUID格式。"
                )
            # 构建session_dir（如果提供了session_id）
            config = load_config()
            session_dir = os.path.join(config.output_dir, request.session_id)
        else:
            # 如果没有提供session_id，传递None，让bp_agent自己生成
            session_dir = None
        
        result = agent.generate_bp(
            business_idea=request.business_idea,
            output_file=request.output_file,
            save_report=request.save_report,
            session_dir=session_dir
        )
        
        markdown_content = result.get("markdown", "")
        preview_length = 2000  # 预览长度
        
        # 从result中获取session_id和session_dir（由bp_agent生成）
        session_id = result.get("session_id")
        session_dir = result.get("session_dir")
        
        return {
            "success": True,
            "message": "商业计划书生成成功",
            "session_id": session_id or "unknown",
            "data": {
                "preview": markdown_content[:preview_length],
                "full_length": len(markdown_content),
                "is_truncated": len(markdown_content) > preview_length,
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

