"""
Simple callback server for testing the async BP generation API.

This server receives status update callbacks from the async API endpoint
and displays them in the console.

Usage:
    python simple_callback_server.py [--port PORT]
    
Example:
    python simple_callback_server.py --port 8888
    
Then use the callback URL: http://localhost:8888
"""

import json
import argparse
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime


class CallbackHandler(BaseHTTPRequestHandler):
    """HTTP request handler for receiving callback updates"""
    
    def log_message(self, format, *args):
        """Override to suppress default logging"""
        pass
    
    def do_POST(self):
        """Handle POST requests from the async API"""
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        try:
            data = json.loads(post_data.decode('utf-8'))
            
            # Print callback data with formatting
            print("\n" + "=" * 70)
            timestamp = data.get('timestamp', datetime.now().isoformat())
            status = data.get('status', 'unknown')
            message = data.get('message', '')
            
            # Status emoji mapping
            status_emoji = {
                'started': '🚀',
                'input_check': '🔍',
                'structure_generation': '📋',
                'structure_regeneration': '🔄',
                'structure_evaluation': '✅',
                'painpoint_enhancement': '💡',
                'investor_evaluation': '💰',
                'pitch_generation': '🎤',
                'ppt_generation': '📊',
                'partner_search': '👥',
                'completed': '🎉',
                'error': '❌'
            }
            emoji = status_emoji.get(status, '📨')
            
            print(f"{emoji} {status.upper()}")
            print(f"Time: {timestamp}")
            print(f"Session ID: {data.get('session_id', 'N/A')}")
            print(f"Message: {message}")
            
            # Show artifacts if available
            artifacts = data.get('artifacts')
            if artifacts:
                print("\nArtifacts:")
                for artifact_type, artifact_url in artifacts.items():
                    print(f"  - {artifact_type}: {artifact_url}")
            
            # Show error if present
            error = data.get('error')
            if error:
                print(f"\n❌ Error:\n{error}")
            
            print("=" * 70)
            
            # Send response
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"success": True, "received": True}).encode('utf-8'))
            
        except Exception as e:
            print(f"\n❌ Error processing callback: {e}")
            import traceback
            traceback.print_exc()
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode('utf-8'))
    
    def do_GET(self):
        """Handle GET requests (for health checks)"""
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        html = """
        <html>
        <head><title>Callback Server</title></head>
        <body>
            <h1>✅ Callback Server is Running</h1>
            <p>This server is ready to receive callbacks from the async BP generation API.</p>
            <p>Use this URL as your callback_url: <code>http://localhost:{port}</code></p>
        </body>
        </html>
        """.format(port=self.server.server_port)
        self.wfile.write(html.encode('utf-8'))


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="Simple callback server for testing async BP generation API"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8888,
        help="Port to listen on (default: 8888)"
    )
    parser.add_argument(
        "--host",
        default="localhost",
        help="Host to bind to (default: localhost)"
    )
    
    args = parser.parse_args()
    
    server_address = (args.host, args.port)
    httpd = HTTPServer(server_address, CallbackHandler)
    
    print("=" * 70)
    print("📡 Callback Server Started")
    print("=" * 70)
    print(f"Listening on: http://{args.host}:{args.port}")
    print(f"\nUse this URL as your callback_url:")
    print(f"  http://{args.host}:{args.port}")
    print("\nWaiting for callbacks...")
    print("(Press Ctrl+C to stop)")
    print("=" * 70)
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\n⏹️  Stopping callback server...")
        httpd.shutdown()
        print("✅ Callback server stopped")


if __name__ == "__main__":
    main()

