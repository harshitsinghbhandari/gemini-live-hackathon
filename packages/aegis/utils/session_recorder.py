import os
import time
import base64
import logging
import subprocess
import tempfile
from pathlib import Path
from aegis.utils.latency import checkpoint
from configs.agent import config

logger = logging.getLogger("aegis.recorder")

class SessionRecorder:
    def __init__(self):
        self.session_id = int(time.time())
        self.data_dir = Path("data")
        self.audio_dir = self.data_dir / "audio"
        self.image_dir = self.data_dir / "images"
        
        # Subfolders for raw chunks
        self.sent_dir = self.audio_dir / "sent"
        self.received_dir = self.audio_dir / "received"
        
        self.image_count = 0
        self.sent_chunk_count = 0
        self.received_chunk_count = 0
        
        self._ensure_dirs()
        self._generate_index_html() # Generate initial index

    def _ensure_dirs(self):
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        self.image_dir.mkdir(parents=True, exist_ok=True)
        self.sent_dir.mkdir(parents=True, exist_ok=True)
        self.received_dir.mkdir(parents=True, exist_ok=True)

    def record_sent_audio(self, pcm_data):
        if not pcm_data: return
        self.sent_chunk_count += 1
        timestamp = int(time.time() * 1000)
        filename = f"sent_{timestamp}_{self.sent_chunk_count:05d}.raw"
        filepath = self.sent_dir / filename
        
        with open(filepath, "wb") as f:
            f.write(pcm_data)
            
        if self.sent_chunk_count == 1:
            checkpoint("recorder", "sent_audio_first_chunk")
        if self.sent_chunk_count % 500 == 0:
            checkpoint("recorder", f"sent_audio_chunks_{self.sent_chunk_count}")

    def record_received_audio(self, pcm_data):
        if not pcm_data: return
        self.received_chunk_count += 1
        timestamp = int(time.time() * 1000)
        filename = f"recv_{timestamp}_{self.received_chunk_count:05d}.raw"
        filepath = self.received_dir / filename
        
        with open(filepath, "wb") as f:
            f.write(pcm_data)
            
        if self.received_chunk_count == 1:
            checkpoint("recorder", "received_audio_first_chunk")
        if self.received_chunk_count % 500 == 0:
            checkpoint("recorder", f"received_audio_chunks_{self.received_chunk_count}")

    def record_image(self, image_blob):
        if not image_blob: return
        self.image_count += 1
        timestamp = int(time.time() * 1000)
        filename = f"img_{timestamp}_{self.image_count:05d}.jpg"
        filepath = self.image_dir / filename
        
        with open(filepath, "wb") as f:
            f.write(image_blob)
            
        if self.image_count % 5 == 0:
            self._generate_index_html()
            
        if self.image_count % 50 == 0:
            checkpoint("recorder", f"saved_images_count_{self.image_count}")

    def finalize(self):
        checkpoint("recorder", "session_end_finalize_start")
        # Generate the final HTML with current file lists
        self._generate_index_html()
        checkpoint("recorder", "session_end_finalize_done")

    def _generate_index_html(self):
        # Scan for existing recordings
        sent_chunks = sorted([f.name for f in self.sent_dir.glob("*.raw")])
        received_chunks = sorted([f.name for f in self.received_dir.glob("*.raw")])
        image_files = sorted([f.name for f in self.image_dir.glob("*.jpg")], reverse=True)
        
        sent_mp3s = sorted([f.name for f in self.audio_dir.glob("sent_combined_*.mp3")], reverse=True)
        recv_mp3s = sorted([f.name for f in self.audio_dir.glob("received_combined_*.mp3")], reverse=True)

        # Image tags snippet
        image_tags = " ".join([f'<img src="images/{f}" title="{f}" loading="lazy" onclick="zoom(this)" />' for f in image_files[:500]])

        # Stats for UI
        s_count = len(sent_chunks)
        r_count = len(received_chunks)
        i_count = len(image_files)
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Aegis Session Analytics</title>
    <style>
        :root {{
            --bg: #0e0f11;
            --bg2: #141518;
            --accent: #7c6af7;
            --text: #e8e9ec;
            --text-dim: #8b8d94;
            --border: #1c1d21;
        }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: var(--bg); color: var(--text); padding: 2rem; margin: 0; }}
        .header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border); padding-bottom: 1rem; margin-bottom: 2rem; }}
        .btn {{ background: var(--accent); color: white; border: none; padding: 0.6rem 1.2rem; border-radius: 6px; cursor: pointer; font-weight: 600; transition: opacity 0.2s; }}
        .btn:hover {{ opacity: 0.9; }}
        .btn:disabled {{ background: #333; cursor: not-allowed; }}
        .section {{ margin-bottom: 3rem; }}
        h2 {{ font-size: 1rem; text-transform: uppercase; letter-spacing: 0.1em; color: var(--text-dim); margin-bottom: 1rem; }}
        .stats {{ display: flex; gap: 2rem; margin-bottom: 2rem; }}
        .stat-card {{ background: var(--bg2); padding: 1.5rem; border-radius: 12px; border: 1px solid var(--border); flex: 1; }}
        .stat-val {{ font-size: 1.5rem; font-weight: 700; color: var(--accent); }}
        .gallery {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 1rem; background: var(--bg2); padding: 1.5rem; border-radius: 12px; border: 1px solid var(--border); max-height: 500px; overflow-y: auto; }}
        .gallery img {{ width: 100%; border-radius: 6px; cursor: pointer; transition: transform 0.2s; }}
        .gallery img:hover {{ transform: scale(1.03); }}
        .logs-control {{ background: var(--bg2); padding: 1.5rem; border-radius: 12px; border: 1px solid var(--border); }}
        #status {{ font-family: monospace; color: var(--accent); margin-top: 1rem; font-size: 0.9rem; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Aegis — Session Recorder</h1>
        <button id="combineBtn" class="btn">Combine Audio Chunks</button>
    </div>

    <div class="section">
        <div class="stats">
            <div class="stat-card">
                <div class="stat-label">Sent Chunks</div>
                <div class="stat-val">{s_count}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Received Chunks</div>
                <div class="stat-val">{r_count}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Images Saved</div>
                <div class="stat-val">{i_count}</div>
            </div>
        </div>
    </div>

    <div class="section">
        <h2>Visual Archive</h2>
        <div class="gallery" id="imageGallery">
            {image_tags}
        </div>
    </div>

    <div class="section">
        <h2>Audio Processing</h2>
        <div class="logs-control">
            <p>Every small audio packet sent to or received from Gemini is saved as a <code>.raw</code> file. Click to stitch them into high-quality MP3s.</p>
            <div id="status">Ready</div>
            <div id="audioResults" style="margin-top: 1rem; display: none;">
                <h3>Combined Results:</h3>
                <div style="display: flex; gap: 1rem; align-items: center;">
                    <span>Sent:</span> <audio id="sentAudio" controls></audio>
                </div>
                <div style="display: flex; gap: 1rem; align-items: center; margin-top: 0.5rem;">
                    <span>Received:</span> <audio id="recvAudio" controls></audio>
                </div>
            </div>
        </div>
    </div>

    <script>
        const statusEl = document.getElementById('status');
        const combineBtn = document.getElementById('combineBtn');

        function zoom(img) {{
            if (img.style.transform === "scale(2.5)") {{
                img.style.transform = "";
                img.style.zIndex = "";
                img.style.position = "";
                img.style.boxShadow = "";
            }} else {{
                img.style.transform = "scale(2.5)";
                img.style.zIndex = "1000";
                img.style.position = "relative";
                img.style.boxShadow = "0 20px 50px rgba(0,0,0,0.5)";
            }}
        }}

        combineBtn.onclick = async () => {{
            statusEl.textContent = "Requesting combination from helper server...";
            combineBtn.disabled = true;
            try {{
                const resp = await fetch('http://localhost:8766/combine', {{ method: 'POST' }});
                const data = await resp.json();
                if (data.success) {{
                    statusEl.textContent = "Success! Combined files: " + data.sent + ", " + data.received;
                    document.getElementById('audioResults').style.display = 'block';
                    document.getElementById('sentAudio').src = 'audio/' + data.sent + '?t=' + Date.now();
                    document.getElementById('recvAudio').src = 'audio/' + data.received + '?t=' + Date.now();
                }} else {{
                    statusEl.textContent = "Error: " + data.error;
                }}
            }} catch (err) {{
                statusEl.textContent = "Failed to connect to helper server (localhost:8766). Is it running?";
            }}
            combineBtn.disabled = false;
        }};
    </script>
</body>
</html>"""
        (self.data_dir / "index.html").write_text(html_content)

# Singleton
recorder = SessionRecorder()
