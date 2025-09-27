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
    return render_template('downloader.html')

@app.route('/download', methods=['POST'])
def download_video():
    ffmpeg_path = shutil.which('ffmpeg')
    if not ffmpeg_path:
        error_msg = 'FATAL ERROR: ffmpeg could not be found on the server.'
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
            'ffmpeg_location': ffmpeg_path,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
                'Accept-Language': 'en-US,en;q=0.9',
            },
            # THE FIX: Force extraction from a different client to bypass bot detection
            'extractor_args': {
                'youtube': {
                    'player_client': ['web'],
                    'skip': ['hls', 'dash']
                }
            }
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
        return jsonify({'error': 'An error occurred. The link might be invalid or YouTube is blocking requests from this server.'}), 500

@app.route('/files/<path:filename>')
def serve_file(filename):
    return send_from_directory(DOWNLOAD_FOLDER, filename, as_attachment=True)

# PWA File Routes
@app.route('/manifest.json')
def serve_manifest():
    return send_from_directory(os.getcwd(), 'manifest.json')

@app.route('/sw.js')
def serve_sw():
    return send_from_directory(os.getcwd(), 'sw.js', mimetype='application/javascript')

@app.route('/<path:icon>')
def serve_icons(icon):
    if icon in ['icon-192x192.png', 'icon-512x512.png']:
        return send_from_directory(os.getcwd(), icon)
    return "Not Found", 404

if __name__ == '__main__':
    app.run(port=5000, debug=True)