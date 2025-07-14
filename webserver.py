import os
import http.server
import socketserver
import urllib.parse

def create_folder(folder_name):
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)
        print(f"Folder '{folder_name}' created successfully.")
    else:
        print(f"Folder '{folder_name}' already exists.")
    return folder_name

# Set the Inspections folder
INSPECTIONS_ROOT = os.path.abspath("Inspections")
create_folder(INSPECTIONS_ROOT)

# Verify that Inspections is accessible
if not os.path.isdir(INSPECTIONS_ROOT):
    print(f"Error: '{INSPECTIONS_ROOT}' is not a directory or is inaccessible.")
    exit(1)

class DirectoryHandler(http.server.SimpleHTTPRequestHandler):
    # Supported image extensions
    IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp'}

    def do_GET(self):
        try:
            # Get the requested path from the URL
            requested_path = urllib.parse.unquote(self.path.lstrip('/'))
            print(f"Requested path: {self.path}")
            print(f"Decoded requested path: {requested_path}")
            
            # Construct the full path
            full_path = INSPECTIONS_ROOT if not requested_path else os.path.join(INSPECTIONS_ROOT, requested_path)
            full_path = os.path.normpath(full_path)  # Normalize path for Windows
            print(f"Resolved full path: {full_path}")
            
            # Prevent directory traversal outside Inspections
            abs_inspections_root = os.path.abspath(INSPECTIONS_ROOT)
            abs_full_path = os.path.abspath(full_path)
            print(f"Absolute Inspections root: {abs_inspections_root}")
            print(f"Absolute full path: {abs_full_path}")
            
            if not abs_full_path.startswith(abs_inspections_root):
                print("403: Attempted access outside Inspections directory")
                self.send_response(403)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(b"<h1>403 Forbidden</h1><p>Access outside Inspections directory is not allowed.</p>")
                return
            
            if not os.path.exists(full_path):
                print(f"404: Path does not exist: {full_path}")
                self.send_response(404)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(b"<h1>404 Not Found</h1><p>The requested path does not exist.</p>")
                return
            
            if os.path.isdir(full_path):
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                html = f"""
                <html>
                <head>
                    <title>IBM MVI Inspections Thai Summit Workcenters</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; margin: 20px; display: flex; flex-direction: column; align-items: flex-start; }}
                        .logo {{ width: 100px; height: auto; margin-bottom: 20px; }}
                        h1 {{ color: #333; margin: 0 0 20px 0; }}
                        ul {{ list-style: none; padding: 0; }}
                        li {{ margin: 10px 0; }}
                        a {{ text-decoration: none; color: #0066cc; }}
                        a:hover {{ text-decoration: underline; }}
                        .image-list {{ display: flex; flex-wrap: wrap; gap: 10px; }}
                        .image-item {{ max-width: 200px; text-align: center; }}
                        img:not(.logo) {{ max-width: 100%; height: auto; border: 1px solid #ddd; border-radius: 4px; cursor: pointer; }}
                        .fullscreen {{ position: fixed; top: 0; left: 0; width: 100%; height: 100%; object-fit: contain; background: rgba(0,0,0,0.9); z-index: 1000; }}
                    </style>
                    <script>
                        function toggleFullScreen(img) {{
                            if (!document.fullscreenElement) {{
                                img.requestFullscreen().catch(err => console.error('Fullscreen error:', err));
                                img.classList.add('fullscreen');
                            }} else {{
                                document.exitFullscreen();
                                img.classList.remove('fullscreen');
                            }}
                        }}
                        document.addEventListener('fullscreenchange', () => {{
                            document.querySelectorAll('img:not(.logo)').forEach(img => {{
                                if (!document.fullscreenElement) {{
                                    img.classList.remove('fullscreen');
                                }}
                            }});
                        }});
                    </script>
                </head>
                <body>
                    <img src="/Logo.png" alt="Logo" class="logo">
                    <h1>Workcenters</h1>
                    <ul>
                """
                if requested_path:
                    parent_path = os.path.dirname(requested_path)
                    html += f'<li><a href="/{parent_path}">.. (Parent Directory)</a></li>'
                
                # List only directories
                for item in sorted(os.listdir(full_path)):
                    item_path = os.path.join(full_path, item)
                    rel_path = os.path.join(requested_path, item).replace('\\', '/')
                    if os.path.isdir(item_path):
                        html += f'<li><a href="/{rel_path}">{item}/</a></li>'
                
                # Only show images section for subdirectories
                if requested_path:
                    html += "</ul><h2>Most Recent Inspections</h2><div class='image-list'>"
                    for item in sorted(os.listdir(full_path)):
                        item_path = os.path.join(full_path, item)
                        rel_path = os.path.join(requested_path, item).replace('\\', '/')
                        if os.path.isfile(item_path) and os.path.splitext(item)[1].lower() in self.IMAGE_EXTENSIONS:
                            html += f"""
                            <div class='image-item'>
                                <a href='javascript:void(0)' onclick='toggleFullScreen(document.getElementById("img-{item}"))'>
                                    <img id='img-{item}' src='/{rel_path}' alt='{item}'>
                                </a>
                                <p>{item}</p>
                            </div>
                            """
                    html += "</div>"
                
                html += "</body></html>"
                self.wfile.write(html.encode('utf-8'))
            else:
                # Serve only image files or Logo.png
                if os.path.splitext(full_path)[1].lower() in self.IMAGE_EXTENSIONS or os.path.basename(full_path).lower() == 'logo.png':
                    print(f"Serving file: {full_path}")
                    super().do_GET()
                else:
                    print(f"403: File type not allowed: {full_path}")
                    self.send_response(403)
                    self.send_header("Content-type", "text/html")
                    self.end_headers()
                    self.wfile.write(b"<h1>403 Forbidden</h1><p>Only images and directories can be accessed.</p>")
                
        except Exception as e:
            print(f"500: Server error: {str(e)}")
            self.send_response(500)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(f"<h1>500 Internal Server Error</h1><p>{str(e)}</p>".encode('utf-8'))

def run_server(port=8000):
    try:
        os.chdir(INSPECTIONS_ROOT)
        print(f"Changed working directory to: {os.getcwd()}")
    except Exception as e:
        print(f"Error changing to Inspections directory: {e}")
        exit(1)
    server_address = ('10.11.2.62', port)
    httpd = socketserver.TCPServer(server_address, DirectoryHandler)
    print(f"Server running at http://localhost:{port}/")
    print(f"Serving files from: {os.path.abspath(INSPECTIONS_ROOT)}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        httpd.server_close()

if __name__ == "__main__":
    run_server()