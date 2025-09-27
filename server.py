# -*- coding: utf-8 -*-
from flask import Flask, request, jsonify, send_from_directory, render_template
from flask_cors import CORS
import yt_dlp
import os
import shutil

app = Flask(__name__, template_folder='templates')
CORS(app)

DOWNLOAD_FOLDER = os.path.join(os.getcwd(), "downloads")
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

@app.route('/')
def index():
    """Serves the main HTML page."""
    return render_template('downloader.html')

@app.route('/download', methods=['POST'])
def download_video():
    """Handles the download and merge process."""
    ffmpeg_path = shutil.which('ffmpeg')
    if not ffmpeg_path:
        error_msg = 'FATAL ERROR: ffmpeg.exe not found. Please place it in the same folder as server.py.'
        print(error_msg)
        return jsonify({'error': error_msg}), 500
    
    data = request.get_json()
    url = data.get('url')
    if not url:
        return jsonify({'error': 'URL is required'}), 400

    try:
        ydl_opts = {
            'quiet': True,
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': os.path.join(DOWNLOAD_FOLDER, '%(title)s - %(height)sp.%(ext)s'),
            'merge_output_format': 'mp4',
            'ffmpeg_location': ffmpeg_path
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            final_filename = ydl.prepare_filename(info)
            base_filename = os.path.basename(final_filename)

        response_data = {
            'title': info.get('title'),
            'thumbnail': info.get('thumbnail'),
            'download_url': f'/files/{base_filename}',
            'filename': base_filename
        }
        return jsonify(response_data), 200

    except Exception as e:
        print(f"[SERVER ERROR] {e}")
        return jsonify({'error': 'An error occurred. The link might be invalid or a download error occurred.'}), 500

@app.route('/files/<path:filename>')
def serve_file(filename):
    """Serves the downloaded file to the user."""
    return send_from_directory(DOWNLOAD_FOLDER, filename, as_attachment=True)

if __name__ == '__main__':
    print("="*50)
    print("Starting YouTube Downloader Server...")
    print(f"Downloaded files will be saved in: {DOWNLOAD_FOLDER}")
    print("Open your browser and go to: http://127.0.0.1:5000")
    print("="*50)
    app.run(port=5000, debug=True)

