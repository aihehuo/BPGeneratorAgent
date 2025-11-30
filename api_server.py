"""
BP Generation Agent API Server
提供REST API接口来调用BP生成功能
"""

import os
import sys
import uuid
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


def _send_callback(callback_url: str, session_id: str, status: str, message: str, artifacts: Optional[Dict[str, Any]] = None, intermediate_result: Optional[Dict[str, Any]] = None, error: Optional[str] = None, max_retries: int = 2):
    """
    Send status update callback to the provided URL.
    Callbacks are sent in a separate thread to avoid blocking the main generation process.
    
    Args:
        callback_url: URL to send the callback to
        session_id: Session ID
        status: Status string (e.g., "started", "input_check", "structure_gen", "completed", "error")
        message: Human-readable status message
        artifacts: Optional dict of artifact URLs
        intermediate_result: Optional intermediate result from the node execution
        error: Optional error message
        max_retries: Maximum number of retry attempts (default: 2)
    """
    def _send_with_retry():
        """Send callback with retry logic in a separate thread"""
        payload = {
            "session_id": session_id,
            "status": status,
            "message": message,
            "timestamp": datetime.now().isoformat(),
        }
        if artifacts:
            payload["artifacts"] = artifacts
        if intermediate_result:
            payload["intermediate_result"] = intermediate_result
        if error:
            payload["error"] = error
        
        # Configure timeout: connect timeout (5s) + read timeout (10s)
        timeout = httpx.Timeout(5.0, read=10.0)
        
        for attempt in range(max_retries + 1):
            try:
                with httpx.Client(timeout=timeout, follow_redirects=True) as client:
                    response = client.post(callback_url, json=payload)
                    response.raise_for_status()
                    # Success - log only if not first attempt
                    if attempt > 0:
                        print(f"✓ Callback sent successfully to {callback_url} (after {attempt + 1} attempts)")
                    return
            except httpx.TimeoutException as e:
                error_msg = f"timeout after {timeout.connect_timeout + timeout.read_timeout}s"
                if attempt < max_retries:
                    wait_time = (attempt + 1) * 1  # Exponential backoff: 1s, 2s
                    print(f"⚠ Callback timeout to {callback_url} (attempt {attempt + 1}/{max_retries + 1}), retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"⚠ Failed to send callback to {callback_url}: {error_msg} (gave up after {max_retries + 1} attempts)")
            except httpx.ConnectError as e:
                error_msg = f"connection error: {str(e)}"
                if attempt < max_retries:
                    wait_time = (attempt + 1) * 1
                    print(f"⚠ Callback connection error to {callback_url} (attempt {attempt + 1}/{max_retries + 1}), retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"⚠ Failed to send callback to {callback_url}: {error_msg} (gave up after {max_retries + 1} attempts)")
            except httpx.HTTPStatusError as e:
                # HTTP error (4xx, 5xx) - don't retry
                print(f"⚠ Callback HTTP error {e.response.status_code} to {callback_url}: {e.response.text[:200]}")
                return
            except Exception as e:
                error_msg = str(e)
                if attempt < max_retries:
                    wait_time = (attempt + 1) * 1
                    print(f"⚠ Callback error to {callback_url} (attempt {attempt + 1}/{max_retries + 1}): {error_msg}, retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"⚠ Failed to send callback to {callback_url}: {error_msg} (gave up after {max_retries + 1} attempts)")
    
    # Send callback in a separate thread to avoid blocking
    callback_thread = threading.Thread(target=_send_with_retry, daemon=True)
    callback_thread.start()


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


def _generate_markdown_summary(llm, node_name: str, result_data: Dict[str, Any], business_idea: str) -> str:
    """
    Generate a human-readable Markdown summary of the node result using LLM.
    
    Args:
        llm: LangChain LLM instance
        node_name: Name of the node that executed
        result_data: The result data from the node
        business_idea: The business idea for context
        
    Returns:
        Markdown-formatted string summary
    """
    from langchain_core.messages import HumanMessage, SystemMessage
    import json
    
    # Node-specific prompts
    node_prompts = {
        "input_check": """Generate a brief, human-readable Markdown summary of the input completeness check result.
Focus on whether the input is complete and what suggestions were provided.""",
        "structure_gen": """Generate a brief, human-readable Markdown summary of the generated BP structure.
List the main sections/topics that were created.""",
        "structure_regenerate": """Generate a brief, human-readable Markdown summary of the regenerated BP structure.
Highlight what was improved or changed based on feedback.""",
        "structure_eval": """Generate a brief, human-readable Markdown summary of the BP structure evaluation.
Highlight the evaluation results, whether it passed, and key feedback points.""",
        "painpoint_enhancement": """Generate a brief, human-readable Markdown summary of the painpoint enhancement.
Describe what dimensions were selected and how the painpoint was enhanced.""",
        "investor_eval": """Generate a brief, human-readable Markdown summary of the investor evaluation.
Highlight key assessment points, concerns, and improvements made.""",
        "pitch_gen": """Generate a brief, human-readable Markdown summary of the 60-second pitch generation.
Summarize the key points of the pitch.""",
        "ppt_gen": """Generate a brief, human-readable Markdown summary of the PPT design generation.
List the main slides and their purposes.""",
        "partner_search": """Generate a brief, human-readable Markdown summary of the partner search results.
Mention how many partners were found and key characteristics.""",
    }
    
    prompt = node_prompts.get(node_name, "Generate a brief, human-readable Markdown summary of this result.")
    
    try:
        # Prepare the data for LLM (limit size to avoid token limits)
        data_str = json.dumps(result_data, ensure_ascii=False, indent=2)
        # Truncate if too long (keep first 2000 chars)
        if len(data_str) > 2000:
            data_str = data_str[:2000] + "... (truncated)"
        
        system_prompt = """You are a helpful assistant that generates concise, human-readable Markdown summaries.
Generate a brief summary in Markdown format that can be directly displayed to users.
Keep it concise (2-4 sentences or a short bullet list). Use the same language as the business idea if possible."""
        
        user_prompt = f"""{prompt}

Business Idea Context:
{business_idea[:200]}

Result Data:
{data_str}

Generate a Markdown summary:"""
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        response = llm.invoke(messages)
        return response.content.strip()
        
    except Exception as e:
        # Fallback: return a simple text summary
        print(f"Warning: Failed to generate Markdown summary for {node_name}: {e}")
        return f"**{node_name}** completed successfully."


def _extract_intermediate_result(node_name: str, node_state: Dict[str, Any], llm=None, business_idea: str = "") -> Optional[Dict[str, Any]]:
    """
    Extract the relevant intermediate result from node state based on the node that just executed.
    Extracts Markdown summary directly from node results (if available) instead of generating it.
    
    Each node returns different results that get merged into the state. This function extracts
    the relevant result for each node type and includes the Markdown summary if the node provided it.
    
    Args:
        node_name: Name of the node that just executed
        node_state: The state dictionary after node execution (contains merged state)
        llm: Optional LLM instance (not used anymore, kept for backward compatibility)
        business_idea: Business idea (not used anymore, kept for backward compatibility)
        
    Returns:
        Dictionary containing the intermediate result with node name, data, and Markdown summary (if available)
    """
    result_map = {
        "input_check": "input_completeness",
        "structure_gen": "bp_structure",
        "structure_regenerate": "bp_structure",
        "structure_eval": "evaluation_result",
        "painpoint_enhancement": "bp_structure",  # Returns updated bp_structure
        "investor_eval": "bp_structure",  # Returns updated bp_structure  
        "pitch_gen": "pitch_result",
        "ppt_gen": "ppt_result",
        "partner_search": "partner_search_result",
    }
    
    result_key = result_map.get(node_name)
    if result_key and result_key in node_state:
        result = node_state.get(result_key)
        if result is not None:
            # For nodes that also update iteration_history, include that too
            iteration_history = node_state.get("iteration_history")
            
            intermediate_result = {
                "node": node_name,
                "result_key": result_key,
                "data": result
            }
            
            # Include iteration_history if available (for structure_eval, painpoint_enhancement, investor_eval)
            if iteration_history and node_name in ["structure_eval", "painpoint_enhancement", "investor_eval"]:
                # Get the most recent iteration history entry
                if isinstance(iteration_history, list) and len(iteration_history) > 0:
                    intermediate_result["iteration_history"] = iteration_history[-1]
            
            # For structure_eval, also include iteration_count
            if node_name == "structure_eval":
                iteration_count = node_state.get("iteration_count")
                if iteration_count is not None:
                    intermediate_result["iteration_count"] = iteration_count
            
            # Extract Markdown summary from node state if available
            # Nodes that return markdown_summary: structure_gen, structure_regenerate, structure_eval
            markdown_summary = node_state.get("markdown_summary")
            if markdown_summary:
                intermediate_result["markdown_summary"] = markdown_summary
            
            return intermediate_result
    
    # If no specific result found, return None
    return None


# Translation dictionary for status messages
# Supported languages: en (English), zh (Simplified Chinese), zh-tw (Traditional Chinese), 
# ja (Japanese), nl (Dutch), fr (French), de (German), es (Spanish), it (Italian), ru (Russian)
_STATUS_TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "started": {
        "en": "BP generation started",
        "zh": "商业计划书生成已开始",
        "zh-tw": "商業計劃書生成已開始",
        "ja": "ビジネスプラン生成を開始しました",
        "nl": "BP-generatie gestart",
        "fr": "Génération du plan d'affaires démarrée",
        "de": "BP-Generierung gestartet",
        "es": "Generación del plan de negocio iniciada",
        "it": "Generazione del piano aziendale avviata",
        "ru": "Генерация бизнес-плана начата"
    },
    "input_check": {
        "en": "Checking input completeness...",
        "zh": "正在检查输入完整性...",
        "zh-tw": "正在檢查輸入完整性...",
        "ja": "入力の完全性を確認中...",
        "nl": "Invoer volledigheid controleren...",
        "fr": "Vérification de l'exhaustivité de la saisie...",
        "de": "Eingabevollständigkeit prüfen...",
        "es": "Verificando la integridad de la entrada...",
        "it": "Verifica della completezza dell'input...",
        "ru": "Проверка полноты ввода..."
    },
    "structure_generation": {
        "en": "Generating BP structure...",
        "zh": "正在生成商业计划书结构...",
        "zh-tw": "正在生成商業計劃書結構...",
        "ja": "ビジネスプラン構造を生成中...",
        "nl": "BP-structuur genereren...",
        "fr": "Génération de la structure du plan d'affaires...",
        "de": "BP-Struktur generieren...",
        "es": "Generando la estructura del plan de negocio...",
        "it": "Generazione della struttura del piano aziendale...",
        "ru": "Генерация структуры бизнес-плана..."
    },
    "structure_regeneration": {
        "en": "Regenerating BP structure...",
        "zh": "正在重新生成商业计划书结构...",
        "zh-tw": "正在重新生成商業計劃書結構...",
        "ja": "ビジネスプラン構造を再生成中...",
        "nl": "BP-structuur opnieuw genereren...",
        "fr": "Régénération de la structure du plan d'affaires...",
        "de": "BP-Struktur erneut generieren...",
        "es": "Regenerando la estructura del plan de negocio...",
        "it": "Rigenerazione della struttura del piano aziendale...",
        "ru": "Повторная генерация структуры бизнес-плана..."
    },
    "structure_evaluation": {
        "en": "Evaluating BP structure...",
        "zh": "正在评估商业计划书结构...",
        "zh-tw": "正在評估商業計劃書結構...",
        "ja": "ビジネスプラン構造を評価中...",
        "nl": "BP-structuur evalueren...",
        "fr": "Évaluation de la structure du plan d'affaires...",
        "de": "BP-Struktur bewerten...",
        "es": "Evaluando la estructura del plan de negocio...",
        "it": "Valutazione della struttura del piano aziendale...",
        "ru": "Оценка структуры бизнес-плана..."
    },
    "painpoint_enhancement": {
        "en": "Enhancing pain points...",
        "zh": "正在优化痛点分析...",
        "zh-tw": "正在優化痛點分析...",
        "ja": "ペインポイントを強化中...",
        "nl": "Pijnpunten verbeteren...",
        "fr": "Amélioration des points de douleur...",
        "de": "Schmerzpunkte verbessern...",
        "es": "Mejorando los puntos de dolor...",
        "it": "Miglioramento dei punti critici...",
        "ru": "Улучшение болевых точек..."
    },
    "investor_evaluation": {
        "en": "Evaluating investor perspective...",
        "zh": "正在评估投资者视角...",
        "zh-tw": "正在評估投資者視角...",
        "ja": "投資家の視点を評価中...",
        "nl": "Investeerderperspectief evalueren...",
        "fr": "Évaluation de la perspective des investisseurs...",
        "de": "Investorenperspektive bewerten...",
        "es": "Evaluando la perspectiva del inversor...",
        "it": "Valutazione della prospettiva dell'investitore...",
        "ru": "Оценка перспективы инвестора..."
    },
    "pitch_generation": {
        "en": "Generating 60-second pitch...",
        "zh": "正在生成60秒路演...",
        "zh-tw": "正在生成60秒路演...",
        "ja": "60秒ピッチを生成中...",
        "nl": "60-seconden pitch genereren...",
        "fr": "Génération du pitch de 60 secondes...",
        "de": "60-Sekunden-Pitch generieren...",
        "es": "Generando el pitch de 60 segundos...",
        "it": "Generazione del pitch di 60 secondi...",
        "ru": "Генерация 60-секундной презентации..."
    },
    "ppt_generation": {
        "en": "Generating PPT design...",
        "zh": "正在生成PPT设计...",
        "zh-tw": "正在生成PPT設計...",
        "ja": "PPTデザインを生成中...",
        "nl": "PPT-ontwerp genereren...",
        "fr": "Génération de la conception PPT...",
        "de": "PPT-Design generieren...",
        "es": "Generando el diseño de la presentación...",
        "it": "Generazione del design della presentazione...",
        "ru": "Генерация дизайна презентации..."
    },
    "partner_search": {
        "en": "Searching for partners...",
        "zh": "正在搜索合作伙伴...",
        "zh-tw": "正在搜尋合作夥伴...",
        "ja": "パートナーを検索中...",
        "nl": "Zoeken naar partners...",
        "fr": "Recherche de partenaires...",
        "de": "Suche nach Partnern...",
        "es": "Buscando socios...",
        "it": "Ricerca di partner...",
        "ru": "Поиск партнеров..."
    },
    "completed": {
        "en": "BP generation completed successfully",
        "zh": "商业计划书生成成功",
        "zh-tw": "商業計劃書生成成功",
        "ja": "ビジネスプラン生成が正常に完了しました",
        "nl": "BP-generatie succesvol voltooid",
        "fr": "Génération du plan d'affaires terminée avec succès",
        "de": "BP-Generierung erfolgreich abgeschlossen",
        "es": "Generación del plan de negocio completada con éxito",
        "it": "Generazione del piano aziendale completata con successo",
        "ru": "Генерация бизнес-плана успешно завершена"
    },
    "input_check_failed": {
        "en": "Input completeness check failed",
        "zh": "输入完整性检查失败",
        "zh-tw": "輸入完整性檢查失敗",
        "ja": "入力完全性チェックに失敗しました",
        "nl": "Invoer volledigheid controle mislukt",
        "fr": "Échec de la vérification de l'exhaustivité de la saisie",
        "de": "Eingabevollständigkeitsprüfung fehlgeschlagen",
        "es": "Verificación de la integridad de la entrada fallida",
        "it": "Verifica della completezza dell'input fallita",
        "ru": "Проверка полноты ввода не прошла"
    },
    "generation_failed": {
        "en": "BP generation failed",
        "zh": "商业计划书生成失败",
        "zh-tw": "商業計劃書生成失敗",
        "ja": "ビジネスプラン生成に失敗しました",
        "nl": "BP-generatie mislukt",
        "fr": "Échec de la génération du plan d'affaires",
        "de": "BP-Generierung fehlgeschlagen",
        "es": "Generación del plan de negocio fallida",
        "it": "Generazione del piano aziendale fallita",
        "ru": "Генерация бизнес-плана не удалась"
    },
    "async_started": {
        "en": "BP generation started. Status updates will be sent to the callback URL.",
        "zh": "商业计划书生成已开始。状态更新将发送到回调URL。",
        "zh-tw": "商業計劃書生成已開始。狀態更新將發送到回調URL。",
        "ja": "ビジネスプラン生成を開始しました。ステータス更新はコールバックURLに送信されます。",
        "nl": "BP-generatie gestart. Statusupdates worden naar de callback-URL verzonden.",
        "fr": "Génération du plan d'affaires démarrée. Les mises à jour de statut seront envoyées à l'URL de rappel.",
        "de": "BP-Generierung gestartet. Statusaktualisierungen werden an die Callback-URL gesendet.",
        "es": "Generación del plan de negocio iniciada. Las actualizaciones de estado se enviarán a la URL de callback.",
        "it": "Generazione del piano aziendale avviata. Gli aggiornamenti di stato verranno inviati all'URL di callback.",
        "ru": "Генерация бизнес-плана начата. Обновления статуса будут отправлены на URL обратного вызова."
    }
}


def _detect_language(text: str) -> str:
    """
    Detect language from text. Returns language code: 'en', 'zh' (Simplified), 'zh-tw' (Traditional), 
    'ja', 'nl', 'fr', 'de', 'es', 'it', 'ru', or 'en' as default.
    
    Args:
        text: Input text to detect language from
        
    Returns:
        Language code: 'en', 'zh', 'zh-tw', 'ja', 'nl', 'fr', 'de', 'es', 'it', 'ru'
    """
    if not text or not text.strip():
        return 'en'
    
    text = text.strip()
    
    # Chinese characters: \u4e00-\u9fff
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    
    # Japanese characters: Hiragana \u3040-\u309f, Katakana \u30a0-\u30ff, Kanji overlaps with Chinese
    # For Japanese, we look for hiragana/katakana which are unique to Japanese
    hiragana_chars = len(re.findall(r'[\u3040-\u309f]', text))
    katakana_chars = len(re.findall(r'[\u30a0-\u30ff]', text))
    japanese_chars = hiragana_chars + katakana_chars
    
    # Russian characters: Cyrillic \u0400-\u04ff
    russian_chars = len(re.findall(r'[\u0400-\u04ff]', text))
    
    # Count total characters for ratios
    total_chars = len(re.findall(r'[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\u0400-\u04ff\w]', text))
    
    if total_chars == 0:
        return 'en'
    
    # Prioritize detection order: Japanese (has unique characters) > Russian (Cyrillic) > Chinese > European languages > English
    if japanese_chars > 0:
        return 'ja'
    
    # Russian detection (Cyrillic script)
    russian_ratio = russian_chars / total_chars if total_chars > 0 else 0
    if russian_ratio > 0.3:
        return 'ru'
    
    chinese_ratio = chinese_chars / total_chars if total_chars > 0 else 0
    if chinese_ratio > 0.3:
        # Distinguish between Simplified and Traditional Chinese
        traditional_patterns = [
            '繁體', '系統', '資訊', '網路', '數據', '企業', '產品', '專業', '應用',
            '計畫', '評估', '設計', '優化', '搜尋', '檢查', '輸入', '開始', '失敗',
            '商業', '投資', '合作', '夥伴', '狀態', '更新', '回調', '成功'
        ]
        traditional_score = sum(1 for pattern in traditional_patterns if pattern in text)
        
        simplified_patterns = [
            '简体', '系统', '信息', '网络', '数据', '企业', '产品', '专业', '应用',
            '计划', '评估', '设计', '优化', '搜索', '检查', '输入', '开始', '失败',
            '商业', '投资', '合作', '伙伴', '状态', '更新', '回调', '成功'
        ]
        simplified_score = sum(1 for pattern in simplified_patterns if pattern in text)
        
        if traditional_score > simplified_score:
            return 'zh-tw'
        return 'zh'
    
    # European languages: Use common words and patterns
    # German common words
    german_patterns = [
        r'\bder\b', r'\bdie\b', r'\bdas\b', r'\bund\b', r'\bin\b', r'\bist\b', r'\bzur\b',
        r'\bfür\b', r'\bmit\b', r'\bvon\b', r'\bauf\b', r'\bzu\b', r'\bden\b', r'\bdes\b',
        r'\bwerden\b', r'\bsind\b', r'\bhaben\b', r'\bsein\b'
    ]
    german_score = sum(1 for pattern in german_patterns if re.search(pattern, text, re.IGNORECASE))
    
    # Spanish common words
    spanish_patterns = [
        r'\bel\b', r'\bla\b', r'\blos\b', r'\blas\b', r'\bde\b', r'\bque\b', r'\by\b',
        r'\ba\b', r'\ben\b', r'\bun\b', r'\buna\b', r'\bes\b', r'\bcon\b', r'\bpor\b',
        r'\bpara\b', r'\bser\b', r'\bhaber\b', r'\bestar\b'
    ]
    spanish_score = sum(1 for pattern in spanish_patterns if re.search(pattern, text, re.IGNORECASE))
    
    # Italian common words
    italian_patterns = [
        r'\bil\b', r'\bla\b', r'\blo\b', r'\bli\b', r'\ble\b', r'\bdi\b', r'\bche\b',
        r'\be\b', r'\ba\b', r'\bin\b', r'\bun\b', r'\buna\b', r'\bè\b', r'\bcon\b',
        r'\bper\b', r'\bessere\b', r'\bavere\b', r'\bfare\b'
    ]
    italian_score = sum(1 for pattern in italian_patterns if re.search(pattern, text, re.IGNORECASE))
    
    # French common words
    french_patterns = [
        r'\ble\b', r'\bla\b', r'\bles\b', r'\bde\b', r'\bet\b', r'\bun\b', r'\bune\b',
        r'\bdans\b', r'\bqui\b', r'\bque\b', r'\bà\b', r'\bavec\b', r'\bêtre\b', r'\bavoir\b'
    ]
    french_score = sum(1 for pattern in french_patterns if re.search(pattern, text, re.IGNORECASE))
    
    # Dutch common words - include more specific Dutch words
    dutch_patterns = [
        # Common Dutch words
        r'\bde\b', r'\bhet\b', r'\ben\b', r'\bvan\b', r'\bin\b', r'\bis\b', r'\bdat\b',
        r'\bop\b', r'\bvoor\b', r'\bmet\b', r'\bte\b', r'\bzijn\b', r'\bhebben\b', r'\bier\b',
        # More specific Dutch words
        r'\bdie\b', r'\bwat\b', r'\bwie\b', r'\bwaar\b', r'\bwanneer\b', r'\bwaarom\b', r'\bhoe\b',
        # Dutch-specific compound words and verbs
        r'\baangedreven\b', r'\bonderwijsplatform\b', r'\bstudenten\b', r'\bgepersonaliseerde\b',
        r'\bleerpadaanbevelingen\b', r'\bbiedt\b', r'\bworden\b', r'\bgeworden\b', r'\bgeweest\b'
    ]
    dutch_score = sum(1 for pattern in dutch_patterns if re.search(pattern, text, re.IGNORECASE))
    
    # Find the language with the highest score
    # Lower threshold to 2 for better detection, but prioritize higher scores
    lang_scores = {
        'de': german_score,
        'es': spanish_score,
        'it': italian_score,
        'fr': french_score,
        'nl': dutch_score
    }
    
    # Sort by score (descending) to find the best match
    sorted_langs = sorted(lang_scores.items(), key=lambda x: x[1], reverse=True)
    
    # If we have a clear winner (score >= 2 and at least 2 points higher than second place)
    if len(sorted_langs) >= 2:
        best_lang, best_score = sorted_langs[0]
        second_score = sorted_langs[1][1] if len(sorted_langs) > 1 else 0
        
        # If best score is >= 2 and significantly higher than second, use it
        if best_score >= 2 and (best_score - second_score) >= 2:
            return best_lang
        # If best score is >= 3, use it even if second is close
        elif best_score >= 3:
            return best_lang
    
    # If no clear winner but we have a score >= 2, use the best one
    if sorted_langs and sorted_langs[0][1] >= 2:
        return sorted_langs[0][0]
    
    # Default to English
    return 'en'


def _translate_status_message(user_input: str, english_message_key: str) -> str:
    """
    Get translated status message based on user's input language.
    
    Args:
        user_input: User's business idea (to detect language)
        english_message_key: Key for the message in _STATUS_TRANSLATIONS dict
        
    Returns:
        Translated message in the user's language, or English if not found
    """
    # Detect language
    lang = _detect_language(user_input)
    
    # Get translation, with fallback chain: detected_lang -> zh (if zh-tw not available) -> en
    translations = _STATUS_TRANSLATIONS.get(english_message_key, {})
    
    # Try detected language first
    if lang in translations:
        return translations[lang]
    
    # If zh-tw is detected but not available, fallback to zh
    if lang == 'zh-tw' and 'zh' in translations:
        return translations['zh']
    
    # Final fallback to English
    return translations.get("en", english_message_key)


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
        # Translate initial status message
        started_message = _translate_status_message(business_idea, "started")
        _send_callback(callback_url, session_id, "started", started_message)
        
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
                    
                    # Translate message to match user's language using status key
                    message = _translate_status_message(business_idea, status)
                    
                    # Extract intermediate result based on node name (with Markdown summary generation)
                    intermediate_result = _extract_intermediate_result(
                        node_name, 
                        node_state, 
                        llm=agent.llm, 
                        business_idea=business_idea
                    )
                    
                    # Build artifact URLs from current state (include intermediate artifacts)
                    artifacts = _build_artifact_urls(session_id, node_state, base_url, include_intermediate=True)
                    
                    # Send callback with intermediate result
                    _send_callback(callback_url, session_id, status, message, artifacts, intermediate_result=intermediate_result)
        
        # Ensure we have a final state
        if final_state is None:
            # Fallback: invoke if stream didn't work
            final_state = graph.invoke(inputs)
        
        # Check for errors
        completeness = final_state.get("input_completeness", {})
        if completeness and not completeness.get("is_complete", False):
            base_error_msg = _translate_status_message(business_idea, "input_check_failed")
            suggestions = completeness.get("suggestions", [])
            if suggestions:
                # Append suggestions in the same language (keep original format)
                error_msg = f"{base_error_msg}: {', '.join(suggestions[:3])}"
            else:
                error_msg = base_error_msg
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
        
        # Translate completion message
        completed_message = _translate_status_message(business_idea, "completed")
        
        # Send completion callback
        _send_callback(
            callback_url,
            session_id,
            "completed",
            completed_message,
            artifacts=final_artifacts
        )
        
    except Exception as e:
        import traceback
        error_msg = str(e)
        error_trace = traceback.format_exc()
        # Translate error message
        base_error = _translate_status_message(business_idea, "generation_failed")
        translated_error = f"{base_error}: {error_msg}"
        _send_callback(
            callback_url,
            session_id,
            "error",
            translated_error,
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
        
        # Translate the initial response message to match user's language
        initial_message = _translate_status_message(
            request.business_idea, 
            "async_started"
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

