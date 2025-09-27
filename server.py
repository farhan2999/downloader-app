# -*- coding: utf-8 -*-

# This MUST be the first thing to run to avoid errors.
import eventlet
eventlet.monkey_patch()

# Now we can import other modules
from flask import Flask, render_template, send_from_directory
from flask_socketio import SocketIO
from flask_cors import CORS
import yt_dlp
import os
import re

app = Flask(__name__, template_folder='templates', static_folder=None)
CORS(app)
# Initialize SocketIO for real-time communication
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

DOWNLOAD_FOLDER = os.path.join(os.getcwd(), "downloads")
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# Main route for the application
@app.route('/')
def index():
    return render_template('downloader.html')

# --- Add routes to serve PWA files from the root directory ---
@app.route('/manifest.json')
def serve_manifest():
    return send_from_directory(os.getcwd(), 'manifest.json')

@app.route('/sw.js')
def serve_sw():
    return send_from_directory(os.getcwd(), 'sw.js', mimetype='application/javascript')

@app.route('/<path:filename>')
def serve_root_files(filename):
    # This will serve the icon files
    if filename in ['icon-192x192.png', 'icon-512x512.png']:
        return send_from_directory(os.getcwd(), filename)
    return "Not Found", 404
# --- End of PWA routes ---

def clean_ansi(text):
    """Removes color codes from progress text to avoid NaN% errors."""
    if not isinstance(text, str): return text
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

def progress_hook(d):
    """Callback function called by yt-dlp to report progress."""
    status = d.get('status', 'processing')
    
    if status == 'downloading':
        percent_str = clean_ansi(d.get('_percent_str', '0.0%')).strip()
        speed_str = clean_ansi(d.get('_speed_str', 'N/A')).strip()
        total_bytes_str = clean_ansi(d.get('_total_bytes_str_na', 'N/A')).strip()
        
        task = "الفيديو" if d.get('info_dict', {}).get('vcodec', 'none') != 'none' else "الصوت"
        
        # Send progress update to the client via WebSocket
        socketio.emit('progress', {
            'status': f'جاري تحميل {task}...',
            'percent': percent_str,
            'speed': speed_str,
            'total_size': total_bytes_str
        })
    elif status == 'finished':
        # After downloads are finished, merging starts
        socketio.emit('progress', {
            'status': 'اكتمل التحميل، جاري دمج الملفات...',
            'percent': '100%'
        })

@socketio.on('start_download')
def handle_download(json_data):
    """Handles the download request received via WebSocket."""
    url = json_data.get('url')
    if not url:
        socketio.emit('error', {'error': 'URL is required'})
        return

    try:
        ydl_opts = {
            'quiet': True,
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': os.path.join(DOWNLOAD_FOLDER, '%(title)s - %(height)sp.%(ext)s'),
            'merge_output_format': 'mp4',
            'progress_hooks': [progress_hook], # Key for real-time updates
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            final_filename = ydl.prepare_filename(info)
            base_filename = os.path.basename(final_filename)

        # When done, send the final result to the client
        socketio.emit('finished', {
            'title': info.get('title'),
            'thumbnail': info.get('thumbnail'),
            'download_url': f'/files/{base_filename}',
            'filename': base_filename
        })

    except Exception as e:
        print(f"[SERVER ERROR] {e}")
        socketio.emit('error', {'error': 'حدث خطأ في الخادم. تأكد أن الرابط صحيح.'})

@app.route('/files/<path:filename>')
def serve_file(filename):
    """Serves the final downloaded file."""
    return send_from_directory(DOWNLOAD_FOLDER, filename, as_attachment=True)

if __name__ == '__main__':
    print("="*50)
    print("Starting YouTube Downloader Server with Real-time Progress...")
    print(f"Downloaded files will be saved in: {DOWNLOAD_FOLDER}")
    print("Open your browser and go to: http://127.0.0.1:5000")
    print("="*50)
    # Use socketio.run() to start the server
    socketio.run(app, port=5000, debug=True)

