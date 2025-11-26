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
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
import sys


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


def start_callback_server(port=8888):
    """Start a simple callback server"""
    server = HTTPServer(('localhost', port), CallbackHandler)
    print(f"✅ Callback server started on http://localhost:{port}")
    
    def run_server():
        server.serve_forever()
    
    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    return server, thread


def test_async_api(business_idea: str, callback_url: str, api_url: str = "http://localhost:8000"):
    """Test the async API endpoint"""
    
    print("=" * 60)
    print("Testing Async BP Generation API")
    print("=" * 60)
    print(f"API URL: {api_url}/api/v1/generate-async")
    print(f"Callback URL: {callback_url}")
    print(f"Business Idea: {business_idea[:50]}...")
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


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test async BP generation API")
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
        "--business-idea",
        default="一个基于AI的在线教育平台，主要面向K12学生，提供个性化学习路径推荐",
        help="Business idea to test"
    )
    
    args = parser.parse_args()
    
    # Setup callback URL
    if args.callback_url:
        callback_url = args.callback_url
        print(f"Using custom callback URL: {callback_url}")
    else:
        # Start local callback server
        callback_port = args.callback_port
        try:
            server, thread = start_callback_server(callback_port)
            callback_url = f"http://localhost:{callback_port}"
            time.sleep(0.5)  # Give server time to start
        except OSError as e:
            print(f"❌ Could not start callback server on port {callback_port}: {e}")
            print("Try a different port with --callback-port")
            sys.exit(1)
    
    # Test the async API
    test_async_api(
        business_idea=args.business_idea,
        callback_url=callback_url,
        api_url=args.api_url
    )
    
    # Print summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Total callbacks received: {len(CallbackHandler.callbacks_received)}")
    if CallbackHandler.callbacks_received:
        print("\nCallback statuses:")
        for i, cb in enumerate(CallbackHandler.callbacks_received, 1):
            status = cb.get("status", "unknown")
            message = cb.get("message", "")[:50]
            print(f"  {i}. {status}: {message}")


if __name__ == "__main__":
    main()

