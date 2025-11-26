"""
BP Generation Agent API Server
提供REST API接口来调用BP生成功能
"""

import os
import sys
import uuid
import threading
import httpx
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
    callback_url: str = Field(..., description="状态更新回调URL，将接收POST请求包含状态更新和中间产物URL")


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
                    detail=f"Invalid session_id format: {session_id}. Must be a valid UUID format."
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
                message="Business plan generation failed",
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
                message="Business plan generation successful",
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
                    detail=f"Invalid session_id format: {session_id}. Must be a valid UUID format."
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
                "message": "Business plan generation failed",
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
                "message": "Business plan generation successful",
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


def _send_callback(callback_url: str, session_id: str, status: str, message: str, artifacts: Optional[Dict[str, Any]] = None, error: Optional[str] = None):
    """
    Send status update callback to the provided URL.
    
    Args:
        callback_url: URL to send the callback to
        session_id: Session ID
        status: Status string (e.g., "started", "input_check", "structure_gen", "completed", "error")
        message: Human-readable status message
        artifacts: Optional dict of artifact URLs
        error: Optional error message
    """
    try:
        payload = {
            "session_id": session_id,
            "status": status,
            "message": message,
            "timestamp": datetime.now().isoformat(),
        }
        if artifacts:
            payload["artifacts"] = artifacts
        if error:
            payload["error"] = error
        
        # Use httpx to send async HTTP request
        with httpx.Client(timeout=10.0) as client:
            response = client.post(callback_url, json=payload)
            response.raise_for_status()
    except Exception as e:
        # Log error but don't fail the generation
        print(f"Warning: Failed to send callback to {callback_url}: {e}")


def _build_artifact_urls(session_id: str, state: Dict[str, Any], base_url: str = "http://localhost:8000", include_intermediate: bool = False) -> Dict[str, str]:
    """
    Build artifact URLs from the current state.
    
    Args:
        session_id: Session ID
        state: Current workflow state
        base_url: Base URL for the API server
        include_intermediate: Whether to include intermediate artifacts (may not be saved as files yet)
        
    Returns:
        Dict of artifact type to URL
    """
    artifacts = {}
    
    # Only include URLs for artifacts that are saved as files
    # For intermediate states, we include them if include_intermediate is True
    # but note that files may not exist yet
    
    if state.get("markdown_content") and state.get("output_file"):
        # Markdown file is saved, so URL is available
        output_file = state.get("output_file")
        filename = os.path.basename(output_file)
        artifacts["markdown"] = f"{base_url}/api/v1/files/{session_id}/{filename}"
    
    if state.get("partner_report_file"):
        # Partner report file path is available
        partner_file = state.get("partner_report_file")
        filename = os.path.basename(partner_file)
        artifacts["partner_report"] = f"{base_url}/api/v1/files/{session_id}/{filename}"
    
    if state.get("ppt_design_file"):
        # PPT design file path is available
        ppt_file = state.get("ppt_design_file")
        filename = os.path.basename(ppt_file)
        artifacts["ppt_design"] = f"{base_url}/api/v1/files/{session_id}/{filename}"
    
    # For intermediate artifacts that may not be saved as files yet,
    # include them only if include_intermediate is True
    # Note: These URLs may return 404 until files are actually saved
    if include_intermediate:
        if state.get("bp_structure"):
            artifacts["bp_structure"] = f"{base_url}/api/v1/files/{session_id}/bp_structure.json"
        
        if state.get("evaluation_result"):
            artifacts["evaluation"] = f"{base_url}/api/v1/files/{session_id}/evaluation.json"
        
        if state.get("pitch_result"):
            artifacts["pitch"] = f"{base_url}/api/v1/files/{session_id}/pitch.json"
        
        if state.get("ppt_result") and not state.get("ppt_design_file"):
            artifacts["ppt"] = f"{base_url}/api/v1/files/{session_id}/ppt_design.json"
        
        if state.get("partner_search_result") and not state.get("partner_report_file"):
            artifacts["partner_search"] = f"{base_url}/api/v1/files/{session_id}/partner_report.md"
    
    return artifacts


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
        # Send started callback
        _send_callback(callback_url, session_id, "started", "BP generation started")
        
        # Get the graph and chat history manager
        from src.graph.workflow import create_bp_graph
        from src.graph.chat_history import ChatHistoryManager
        from src.utils.text_processing import detect_language
        
        chat_history_manager = ChatHistoryManager(session_id=session_id)
        graph = create_bp_graph(
            agent.llm,
            agent.config.aihehuo_api_key,
            agent.config.aihehuo_api_base,
            chat_history_manager=chat_history_manager
        )
        
        # Initial state
        inputs = {
            "business_idea": business_idea,
            "session_id": session_id,
            "iteration_count": 0,
            "max_iterations": agent.max_iterations,
            "iteration_history": [],
            "is_english": detect_language(business_idea) == 'en'
        }
        
        # Use stream() to get intermediate states
        last_node = None
        final_state = None
        
        for event in graph.stream(inputs):
            # event is a dict with node names as keys
            for node_name, node_state in event.items():
                # Update final_state with the latest state
                if final_state is None:
                    final_state = node_state.copy()
                else:
                    final_state.update(node_state)
                
                if node_name != last_node:
                    last_node = node_name
                    
                    # Map node names to human-readable status
                    status_map = {
                        "input_check": "input_check",
                        "structure_gen": "structure_generation",
                        "structure_regenerate": "structure_regeneration",
                        "structure_eval": "structure_evaluation",
                        "painpoint_enhancement": "painpoint_enhancement",
                        "investor_eval": "investor_evaluation",
                        "pitch_gen": "pitch_generation",
                        "ppt_gen": "ppt_generation",
                        "partner_search": "partner_search"
                    }
                    
                    status = status_map.get(node_name, node_name)
                    message_map = {
                        "input_check": "Checking input completeness...",
                        "structure_generation": "Generating BP structure...",
                        "structure_regeneration": "Regenerating BP structure...",
                        "structure_evaluation": "Evaluating BP structure...",
                        "painpoint_enhancement": "Enhancing pain points...",
                        "investor_evaluation": "Evaluating investor perspective...",
                        "pitch_generation": "Generating 60-second pitch...",
                        "ppt_generation": "Generating PPT design...",
                        "partner_search": "Searching for partners..."
                    }
                    message = message_map.get(status, f"Processing {node_name}...")
                    
                    # Build artifact URLs from current state (include intermediate artifacts)
                    artifacts = _build_artifact_urls(session_id, node_state, base_url, include_intermediate=True)
                    
                    # Send callback
                    _send_callback(callback_url, session_id, status, message, artifacts)
        
        # Ensure we have a final state
        if final_state is None:
            # Fallback: invoke if stream didn't work
            final_state = graph.invoke(inputs)
        
        # Check for errors
        completeness = final_state.get("input_completeness", {})
        if completeness and not completeness.get("is_complete", False):
            error_msg = "Input completeness check failed"
            suggestions = completeness.get("suggestions", [])
            if suggestions:
                error_msg += f": {', '.join(suggestions[:3])}"
            _send_callback(
                callback_url, 
                session_id, 
                "error", 
                error_msg,
                error=error_msg
            )
            return
        
        # Continue with post-processing (markdown generation, file saving)
        # Use agent's helper methods to build markdown and save files
        bp_structure = final_state.get("bp_structure", [])
        iteration_history = final_state.get("iteration_history", [])
        evaluation_result = final_state.get("evaluation_result", {})
        partner_search_result = final_state.get("partner_search_result")
        
        # Build markdown
        markdown_content = agent._build_markdown(
            business_idea,
            bp_structure,
            iteration_history,
            evaluation_result,
            partner_search_result
        )
        
        # Save files if needed
        output_path = None
        if save_report:
            session_dir = agent._get_session_dir(session_id)
            os.makedirs(session_dir, exist_ok=True)
            
            output_path = output_file or agent._build_default_filename(business_idea, session_id=session_id)
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(markdown_content)
            
            # Save other artifacts and capture file paths
            ppt_result = final_state.get("ppt_result")
            if ppt_result and ppt_result.get("slides"):
                ppt_file_path = agent._save_ppt_design_file(business_idea, bp_structure, ppt_result, output_path)
                if ppt_file_path:
                    final_state["ppt_design_file"] = ppt_file_path
            
            if partner_search_result:
                partner_report_path = agent._save_partner_report(business_idea, partner_search_result, output_path)
                if partner_report_path:
                    final_state["partner_report_file"] = partner_report_path
        
        # Update final_state with file paths for artifact URL building
        final_state["output_file"] = output_path if save_report else None
        final_state["markdown_content"] = markdown_content
        
        # Build final artifact URLs (only include files that are actually saved)
        final_artifacts = _build_artifact_urls(session_id, final_state, base_url, include_intermediate=False)
        
        # Send completion callback
        _send_callback(
            callback_url,
            session_id,
            "completed",
            "BP generation completed successfully",
            artifacts=final_artifacts
        )
        
    except Exception as e:
        import traceback
        error_msg = str(e)
        error_trace = traceback.format_exc()
        _send_callback(
            callback_url,
            session_id,
            "error",
            f"BP generation failed: {error_msg}",
            error=error_trace
        )


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
        
        return GenerateBPAsyncResponse(
            success=True,
            message="BP generation started. Status updates will be sent to the callback URL.",
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

