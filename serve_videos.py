"""
serve_videos.py
===============
Simple HTTP server with Range-request support for smooth video streaming and downloads.
Serves on http://localhost:8080 with a modern, dark-mode preview and download interface.
"""

import http.server
import socketserver
import os
import urllib.parse
from pathlib import Path

PORT = 8080
BASE_DIR = Path(__file__).resolve().parent

class VideoHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(BASE_DIR), **kwargs)

    def do_GET(self):
        # If accessing root or index, serve a rich UI
        parsed_path = urllib.parse.urlparse(self.path).path
        if parsed_path in ("/", "/index.html"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            html = self.render_index()
            encoded = html.encode("utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)
            return

        # Normal file serving with range requests supported by parent
        super().do_GET()

    def render_index(self) -> str:
        runs_dir = BASE_DIR / "workspace" / "runs"
        videos = []
        if runs_dir.exists():
            for p in runs_dir.rglob("*.mp4"):
                # Skip small segments in temp_render
                if "temp_render" in str(p) or "temp" in str(p).split(os.sep):
                    continue
                size_mb = p.stat().st_size / (1024 * 1024)
                rel = p.relative_to(BASE_DIR).as_posix()
                videos.append({
                    "name": p.name,
                    "path": rel,
                    "size": f"{size_mb:.1f} MB",
                    "mtime": p.stat().st_mtime,
                    "parent": p.parent.name,
                })
        
        # Sort newest first
        videos.sort(key=lambda x: x["mtime"], reverse=True)
        latest = videos[0] if videos else None

        cards_html = ""
        for v in videos:
            is_latest = (v == latest)
            badge = '<span class="badge">LATEST</span>' if is_latest else ''
            cards_html += f"""
            <div class="video-card {'active-card' if is_latest else ''}">
                <div class="card-header">
                    <h3>{v['name']} {badge}</h3>
                    <span class="meta">{v['parent']} • {v['size']}</span>
                </div>
                <div class="card-actions">
                    <a href="/{v['path']}" target="_blank" class="btn btn-secondary">▶ Play in Tab</a>
                    <a href="/{v['path']}" download class="btn btn-primary">⬇ Download</a>
                </div>
            </div>
            """

        latest_player = ""
        if latest:
            latest_player = f"""
            <div class="hero-player">
                <div class="player-wrapper">
                    <video controls autoplay muted playsinline poster="">
                        <source src="/{latest['path']}" type="video/mp4">
                        Your browser does not support the video tag.
                    </video>
                </div>
                <div class="hero-info">
                    <h2>{latest['name']}</h2>
                    <p class="meta">Location: <code>{latest['path']}</code> • Size: <strong>{latest['size']}</strong></p>
                    <div class="action-row">
                        <a href="/{latest['path']}" download class="btn btn-primary btn-large">⬇ Download Latest Video ({latest['size']})</a>
                        <a href="/{latest['path']}" target="_blank" class="btn btn-secondary btn-large">↗ Open Direct Stream</a>
                    </div>
                </div>
            </div>
            """

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DocStudio — Video Delivery & Download Center</title>
    <style>
        :root {{
            --bg: #0b0f19;
            --surface: #131b2e;
            --border: #233152;
            --primary: #00e676;
            --primary-hover: #00c853;
            --accent: #3b82f6;
            --text: #f1f5f9;
            --text-muted: #94a3b8;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            background: var(--bg);
            color: var(--text);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", sans-serif;
            min-height: 100vh;
            padding: 32px 20px;
        }}
        .container {{
            max-width: 900px;
            margin: 0 auto;
        }}
        header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 28px;
            padding-bottom: 20px;
            border-bottom: 1px solid var(--border);
        }}
        h1 {{
            font-size: 24px;
            font-weight: 700;
            letter-spacing: -0.5px;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .status-dot {{
            width: 10px;
            height: 10px;
            background: var(--primary);
            border-radius: 50%;
            box-shadow: 0 0 12px var(--primary);
        }}
        .hero-player {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 32px;
            box-shadow: 0 16px 36px rgba(0,0,0,0.4);
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 20px;
        }}
        .player-wrapper {{
            width: 100%;
            max-width: 380px;
            background: #000;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 8px 24px rgba(0,0,0,0.6);
        }}
        video {{
            width: 100%;
            display: block;
            max-height: 560px;
            background: #000;
        }}
        .hero-info {{
            text-align: center;
            width: 100%;
        }}
        .hero-info h2 {{
            font-size: 20px;
            margin-bottom: 8px;
        }}
        .meta {{
            color: var(--text-muted);
            font-size: 14px;
            margin-bottom: 16px;
        }}
        code {{
            background: rgba(255,255,255,0.06);
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 12px;
        }}
        .action-row {{
            display: flex;
            justify-content: center;
            gap: 12px;
            flex-wrap: wrap;
        }}
        .btn {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 10px 18px;
            border-radius: 8px;
            text-decoration: none;
            font-weight: 600;
            font-size: 14px;
            transition: all 0.2s ease;
        }}
        .btn-primary {{
            background: var(--primary);
            color: #000;
        }}
        .btn-primary:hover {{
            background: var(--primary-hover);
            transform: translateY(-1px);
        }}
        .btn-secondary {{
            background: rgba(255,255,255,0.08);
            color: var(--text);
            border: 1px solid var(--border);
        }}
        .btn-secondary:hover {{
            background: rgba(255,255,255,0.14);
        }}
        .btn-large {{
            padding: 14px 26px;
            font-size: 16px;
        }}
        .section-title {{
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 16px;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.8px;
        }}
        .video-card {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 16px 20px;
            margin-bottom: 12px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 16px;
            transition: border-color 0.2s;
        }}
        .video-card:hover {{
            border-color: #384d7a;
        }}
        .active-card {{
            border-color: rgba(0, 230, 118, 0.4);
            background: linear-gradient(90deg, rgba(0, 230, 118, 0.04), var(--surface));
        }}
        .card-header h3 {{
            font-size: 16px;
            margin-bottom: 4px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .badge {{
            background: rgba(0, 230, 118, 0.2);
            color: var(--primary);
            font-size: 11px;
            padding: 2px 8px;
            border-radius: 999px;
            font-weight: 700;
            letter-spacing: 0.5px;
        }}
        .card-actions {{
            display: flex;
            gap: 8px;
            flex-shrink: 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1><span class="status-dot"></span> DocStudio Video Delivery</h1>
            <span class="meta">Server running on port 8080</span>
        </header>

        {latest_player}

        <h2 class="section-title">All Generated Videos</h2>
        <div class="video-list">
            {cards_html}
        </div>
    </div>
</body>
</html>
"""

if __name__ == "__main__":
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), VideoHandler) as httpd:
        print(f"[DocStudio] Serving videos at http://localhost:{PORT}")
        print(f"[DocStudio] Open http://localhost:{PORT} in your browser to preview and download.")
        httpd.serve_forever()
