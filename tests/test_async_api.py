"""
Test script for the async BP generation API endpoint.

This script:
1. Starts a simple callback server to receive status updates
2. Calls the async API endpoint
3. Displays all callback updates in real-time

Usage:
    python test_async_api.py
"""

import requests
import json
import threading
import time
import socket
import platform
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
import sys
import re


class CallbackHandler(BaseHTTPRequestHandler):
    """HTTP request handler for receiving callback updates"""
    
    callbacks_received = []
    
    def log_message(self, format, *args):
        """Override to suppress default logging"""
        pass
    
    def do_POST(self):
        """Handle POST requests from the async API"""
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        try:
            data = json.loads(post_data.decode('utf-8'))
            CallbackHandler.callbacks_received.append(data)
            
            # Print callback data
            print("\n" + "=" * 60)
            print(f"📨 Callback received: {data.get('status', 'unknown')}")
            print("=" * 60)
            print(json.dumps(data, indent=2, ensure_ascii=False))
            
            # Validate markdown_summary if present
            markdown_summary = data.get('markdown_summary')
            status = data.get('status', 'unknown')
            
            if markdown_summary:
                # Determine node name from status
                node_name = status  # Status typically matches node name
                
                # Validate markdown_summary format
                validation_result = validate_markdown_summary(
                    markdown_summary, 
                    status,
                    node_name
                )
                if validation_result['valid']:
                    print(f"\n✅ Markdown Summary Validation: PASSED")
                    print(f"   Status: {status}")
                    print(f"   Length: {len(markdown_summary)} characters")
                    if validation_result.get('preview'):
                        print(f"   Preview: {validation_result['preview']}")
                else:
                    print(f"\n⚠️  Markdown Summary Validation: FAILED")
                    print(f"   Status: {status}")
                    print(f"   Issues: {', '.join(validation_result.get('issues', []))}")
            else:
                # Check if this status should have markdown_summary
                if status in NODES_WITH_MARKDOWN_SUMMARY:
                    print(f"\n⚠️  Markdown Summary Missing")
                    print(f"   Status: {status} should have markdown_summary but it's missing")
            
            # Send response
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"success": True}).encode('utf-8'))
            
        except Exception as e:
            print(f"Error processing callback: {e}")
            self.send_response(500)
            self.end_headers()
    
    def do_GET(self):
        """Handle GET requests (for health checks)"""
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Callback server is running")


# Nodes that should return markdown_summary in their intermediate results
NODES_WITH_MARKDOWN_SUMMARY = {
    "input_check",
    "structure_gen",
    "structure_regenerate",
    "structure_eval",
    "painpoint_enhancement",
    "investor_eval",
    "pitch_gen",
    "ppt_gen"
}


def validate_markdown_summary(markdown_summary: str, status: str, node_name: str) -> dict:
    """
    Validate markdown_summary format and content.
    
    Args:
        markdown_summary: The markdown summary string to validate
        status: Callback status
        node_name: Name of the node that generated this summary
        
    Returns:
        Dictionary with validation results:
        {
            "valid": bool,
            "issues": list of issue descriptions,
            "preview": str (first 150 chars)
        }
    """
    issues = []
    
    # Check if it's a string
    if not isinstance(markdown_summary, str):
        issues.append(f"markdown_summary is not a string (type: {type(markdown_summary).__name__})")
        return {"valid": False, "issues": issues}
    
    # Check if it's not empty
    if not markdown_summary or not markdown_summary.strip():
        issues.append("markdown_summary is empty or whitespace only")
        return {"valid": False, "issues": issues}
    
    # Check minimum length (should have some content)
    if len(markdown_summary.strip()) < 10:
        issues.append(f"markdown_summary is too short ({len(markdown_summary.strip())} chars, minimum 10)")
    
    # Check if it contains some actual content (not just whitespace or special chars)
    content_chars = re.sub(r'[\s\*#\[\]()]', '', markdown_summary)
    if len(content_chars) < 5:
        issues.append("markdown_summary appears to contain only formatting characters")
    
    # Note: We don't require markdown formatting - plain text is acceptable
    # The summary just needs to be human-readable text
    
    # Generate preview
    preview = markdown_summary[:150].replace('\n', ' ') if len(markdown_summary) > 150 else markdown_summary.replace('\n', ' ')
    if len(markdown_summary) > 150:
        preview += "..."
    
    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "preview": preview
    }


def get_host_ip_for_docker():
    """
    Get the host IP address that Docker containers can reach.
    
    Returns:
        str: Host IP address or special hostname for Docker
    """
    # On Docker Desktop (Mac/Windows), use host.docker.internal
    if platform.system() in ['Darwin', 'Windows']:
        return 'host.docker.internal'
    
    # On Linux, try to get the host IP from Docker bridge
    # First try to get the default gateway (Docker bridge)
    try:
        import subprocess
        result = subprocess.run(
            ['ip', 'route', 'show', 'default'],
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode == 0:
            # Extract IP from route output
            for line in result.stdout.split('\n'):
                if 'default via' in line:
                    parts = line.split()
                    if 'via' in parts:
                        idx = parts.index('via')
                        if idx + 1 < len(parts):
                            return parts[idx + 1]
    except Exception:
        pass
    
    # Fallback: try to get local IP address
    try:
        # Connect to a remote address to determine local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        pass
    
    # Last resort: return localhost (may not work from Docker)
    return 'localhost'


def start_callback_server(port=8888, bind_all=False):
    """
    Start a simple callback server
    
    Args:
        port: Port to listen on
        bind_all: If True, bind to 0.0.0.0 (accessible from Docker), 
                  otherwise bind to localhost only
    """
    host = '0.0.0.0' if bind_all else 'localhost'
    server = HTTPServer((host, port), CallbackHandler)
    
    display_host = 'localhost' if not bind_all else get_host_ip_for_docker()
    print(f"✅ Callback server started on http://{display_host}:{port}")
    if bind_all:
        print(f"   (Bound to 0.0.0.0:{port} - accessible from Docker containers)")
    
    def run_server():
        server.serve_forever()
    
    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    return server, thread


def test_async_api(business_idea: str, callback_url: str, api_url: str = "http://localhost:8000", expected_lang: str = None, lang_code: str = None, api_in_docker: bool = False):
    """Test the async API endpoint
    
    Args:
        business_idea: Business idea to test
        callback_url: URL for receiving callbacks (should be accessible from API server)
        api_url: API server URL
        expected_lang: Expected language code
        lang_code: Language code for display
        api_in_docker: If True, API server is running in Docker, so callback URL should use host.docker.internal
    """
    
    print("=" * 60)
    print("Testing Async BP Generation API")
    print("=" * 60)
    if expected_lang:
        print(f"🌐 Language: {LANGUAGE_NAMES.get(expected_lang, expected_lang)} ({expected_lang})")
    if api_in_docker:
        print(f"🐳 API Server is running in Docker container")
    print(f"API URL: {api_url}/api/v1/generate-async")
    print(f"Callback URL: {callback_url}")
    print(f"Business Idea: {business_idea[:80]}...")
    print()
    
    # Prepare request
    request_data = {
        "business_idea": business_idea,
        "callback_url": callback_url,
        "save_report": True
    }
    
    try:
        # Send async request
        print("🚀 Sending async request...")
        response = requests.post(
            f"{api_url}/api/v1/generate-async",
            json=request_data,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            session_id = result.get("session_id")
            
            print("\n✅ Request accepted!")
            print(f"Session ID: {session_id}")
            print(f"Message: {result.get('message')}")
            print("\n⏳ Waiting for callbacks...")
            print("(Press Ctrl+C to stop waiting)")
            print()
            
            # Wait for callbacks
            start_time = time.time()
            last_count = 0
            
            while True:
                current_count = len(CallbackHandler.callbacks_received)
                if current_count > last_count:
                    last_count = current_count
                
                # Check if we received a completion or error callback
                if CallbackHandler.callbacks_received:
                    last_callback = CallbackHandler.callbacks_received[-1]
                    status = last_callback.get("status")
                    if status in ["completed", "error"]:
                        print("\n" + "=" * 60)
                        print("🏁 Generation finished!")
                        print("=" * 60)
                        break
                
                time.sleep(1)
                
                # Timeout after 10 minutes
                if time.time() - start_time > 600:
                    print("\n⏱️  Timeout waiting for completion")
                    break
                
        else:
            print(f"❌ Request failed with status {response.status_code}")
            print(response.text)
            
    except requests.exceptions.ConnectionError:
        print(f"❌ Could not connect to API server at {api_url}")
        print("Make sure the API server is running:")
        print("  python api_server.py")
        sys.exit(1)
    except requests.exceptions.Timeout:
        print("❌ Request timed out")
    except KeyboardInterrupt:
        print("\n\n⏹️  Interrupted by user")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


# Predefined test business ideas in different languages
TEST_BUSINESS_IDEAS = {
    "en": "An AI-powered online education platform targeting K12 students, providing personalized learning path recommendations",
    "zh": "一个基于AI的在线教育平台，主要面向K12学生，提供个性化学习路径推荐",
    "zh-tw": "一個基於AI的線上教育平台，主要面向K12學生，提供個人化學習路徑推薦",
    "ja": "K12の学生向けのAIを活用したオンライン教育プラットフォームで、個別化された学習パス推奨を提供",
    "nl": "Een AI-aangedreven online onderwijsplatform voor K12-studenten, dat gepersonaliseerde leerpadaanbevelingen biedt",
    "fr": "Une plateforme d'éducation en ligne alimentée par l'IA, ciblant les élèves K12, offrant des recommandations de parcours d'apprentissage personnalisées",
    "de": "Eine KI-gestützte Online-Bildungsplattform für K12-Schüler, die personalisierte Lernpfadempfehlungen bietet",
    "es": "Una plataforma educativa en línea impulsada por IA dirigida a estudiantes K12, que ofrece recomendaciones de rutas de aprendizaje personalizadas",
    "it": "Una piattaforma educativa online alimentata dall'IA rivolta agli studenti K12, che offre raccomandazioni di percorsi di apprendimento personalizzati",
    "ru": "Образовательная онлайн-платформа на базе ИИ для учащихся K12, предоставляющая персонализированные рекомендации по учебным путям"
}

# Expected language names for display
LANGUAGE_NAMES = {
    "en": "English",
    "zh": "Simplified Chinese",
    "zh-tw": "Traditional Chinese",
    "ja": "Japanese",
    "nl": "Dutch",
    "fr": "French",
    "de": "German",
    "es": "Spanish",
    "it": "Italian",
    "ru": "Russian"
}


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Test async BP generation API with multi-language support",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Examples:
  # Test with English (default)
  python test_async_api.py
  
  # Test with Chinese
  python test_async_api.py --lang zh
  
  # Test with Japanese
  python test_async_api.py --lang ja
  
  # Test with Traditional Chinese
  python test_async_api.py --lang zh-tw
  
  # Test with German
  python test_async_api.py --lang de
  
  # Test against Docker container (API server in Docker)
  python test_async_api.py --lang fr --docker
  
  # Test with API server in Docker, explicit callback host
  python test_async_api.py --lang zh --api-in-docker --docker-host host.docker.internal
  
  # Test with custom business idea
  python test_async_api.py --business-idea "Your custom idea here" --lang es

Supported languages: {', '.join(TEST_BUSINESS_IDEAS.keys())}
        """
    )
    parser.add_argument(
        "--api-url",
        default="http://localhost:8000",
        help="API server URL (default: http://localhost:8000)"
    )
    parser.add_argument(
        "--callback-port",
        type=int,
        default=8888,
        help="Callback server port (default: 8888)"
    )
    parser.add_argument(
        "--callback-url",
        help="Custom callback URL (if not provided, will start local callback server)"
    )
    parser.add_argument(
        "--lang",
        choices=list(TEST_BUSINESS_IDEAS.keys()),
        default="zh",
        help=f"Language to test (default: zh). Available: {', '.join(TEST_BUSINESS_IDEAS.keys())}"
    )
    parser.add_argument(
        "--business-idea",
        help="Custom business idea to test (if not provided, uses predefined idea for selected language)"
    )
    parser.add_argument(
        "--docker",
        action="store_true",
        help="Enable Docker mode: bind callback server to 0.0.0.0 and use host IP for callback URL. Also assumes API server is in Docker."
    )
    parser.add_argument(
        "--docker-host",
        help="Explicit host IP/hostname for Docker containers to reach callback server (e.g., host.docker.internal or 192.168.1.100)"
    )
    parser.add_argument(
        "--api-in-docker",
        action="store_true",
        help="Indicate that the API server is running in a Docker container. Callback URL will use host.docker.internal (or --docker-host if provided)"
    )
    
    args = parser.parse_args()
    
    # Determine business idea
    if args.business_idea:
        business_idea = args.business_idea
        detected_lang = None  # User provided custom idea, don't assume language
    else:
        business_idea = TEST_BUSINESS_IDEAS.get(args.lang, TEST_BUSINESS_IDEAS["zh"])
        detected_lang = args.lang
    
    # Determine if we should use Docker mode
    use_docker = args.docker or args.docker_host is not None
    api_in_docker = args.api_in_docker or args.docker  # If --docker is used, assume API is also in Docker
    
    # Setup callback URL
    if args.callback_url:
        callback_url = args.callback_url
        print(f"Using custom callback URL: {callback_url}")
    else:
        # Start local callback server
        callback_port = args.callback_port
        
        # Determine callback host
        # If API is in Docker, callback URL must be accessible from Docker container
        if use_docker or api_in_docker:
            if args.docker_host:
                callback_host = args.docker_host
            else:
                # Use host.docker.internal for Docker containers to reach host
                callback_host = get_host_ip_for_docker()
            bind_all = True
            print(f"🐳 Docker mode enabled")
            if api_in_docker:
                print(f"   API Server is in Docker container")
            print(f"   Callback host for Docker: {callback_host}")
        else:
            callback_host = 'localhost'
            bind_all = False
        
        try:
            server, thread = start_callback_server(callback_port, bind_all=bind_all)
            callback_url = f"http://{callback_host}:{callback_port}"
            if use_docker or api_in_docker:
                print(f"   Callback URL for Docker containers: {callback_url}")
            time.sleep(0.5)  # Give server time to start
        except OSError as e:
            print(f"❌ Could not start callback server on port {callback_port}: {e}")
            print("Try a different port with --callback-port")
            sys.exit(1)
    
    # Test the async API
    test_async_api(
        business_idea=business_idea,
        callback_url=callback_url,
        api_url=args.api_url,
        expected_lang=detected_lang,
        lang_code=args.lang if args.business_idea else detected_lang,
        api_in_docker=api_in_docker
    )
    
    # Print summary
    print_summary(lang_code=args.lang if args.business_idea else detected_lang)


def print_summary(lang_code: str = None):
    """Print summary of received callbacks with language and markdown_summary validation"""
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Total callbacks received: {len(CallbackHandler.callbacks_received)}")
    if CallbackHandler.callbacks_received:
        print("\nCallback statuses and messages:")
        print("-" * 60)
        all_correct_language = True
        all_markdown_valid = True
        markdown_summary_count = 0
        markdown_summary_issues = []
        expected_lang_name = LANGUAGE_NAMES.get(lang_code, lang_code) if lang_code else None
        
        for i, cb in enumerate(CallbackHandler.callbacks_received, 1):
            status = cb.get("status", "unknown")
            message = cb.get("message", "")
            
            # Check if message is in expected language (basic check)
            lang_match = "✓" if expected_lang_name else "?"
            if expected_lang_name:
                # Simple validation: message should not be empty
                if not message or message.strip() == "":
                    lang_match = "✗"
                    all_correct_language = False
                # For non-English, check that message contains non-ASCII characters (rough check)
                elif lang_code != "en" and all(ord(c) < 128 for c in message):
                    # Might still be correct if it's an error message, but flag it
                    if status != "error":
                        lang_match = "⚠"
            
            print(f"  {i}. [{status:20s}] {lang_match}")
            print(f"      {message}")
            
            # Check markdown_summary (now at top level of callback data)
            markdown_summary = cb.get("markdown_summary")
            
            if markdown_summary:
                markdown_summary_count += 1
                validation = validate_markdown_summary(markdown_summary, status, status)
                if validation["valid"]:
                    print(f"      📝 Markdown Summary: ✅ Valid ({len(markdown_summary)} chars)")
                    if validation.get("preview"):
                        print(f"         Preview: {validation['preview']}")
                else:
                    all_markdown_valid = False
                    issues_str = ", ".join(validation["issues"])
                    print(f"      📝 Markdown Summary: ⚠️  Issues: {issues_str}")
                    markdown_summary_issues.append({
                        "callback": i,
                        "status": status,
                        "issues": validation["issues"]
                    })
            elif status in NODES_WITH_MARKDOWN_SUMMARY:
                # This status should have markdown_summary but doesn't
                all_markdown_valid = False
                print(f"      📝 Markdown Summary: ❌ Missing (expected for {status})")
                markdown_summary_issues.append({
                    "callback": i,
                    "status": status,
                    "issues": ["markdown_summary is missing"]
                })
            
            print()
        
        # Print language validation summary
        if expected_lang_name:
            print("-" * 60)
            if all_correct_language:
                print(f"✅ All status messages appear to be in {expected_lang_name}")
            else:
                print(f"⚠️  Some status messages may not be in {expected_lang_name}")
        
        # Print markdown_summary validation summary
        print("-" * 60)
        print(f"Markdown Summary Validation:")
        print(f"  Total callbacks with markdown_summary: {markdown_summary_count}")
        
        if all_markdown_valid and markdown_summary_count > 0:
            print(f"  ✅ All markdown_summary validations passed")
        elif markdown_summary_count == 0:
            print(f"  ⚠️  No markdown_summary found in any callback")
        else:
            print(f"  ⚠️  Found {len(markdown_summary_issues)} markdown_summary issues:")
            for issue in markdown_summary_issues:
                print(f"     - Callback #{issue['callback']} ({issue['node']}): {', '.join(issue['issues'])}")
        
        print()


if __name__ == "__main__":
    main()

