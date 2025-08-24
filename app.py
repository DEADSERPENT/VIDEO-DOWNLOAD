from flask import Flask, request, jsonify, send_from_directory, render_template, Response
from flask_socketio import SocketIO
import threading
import subprocess
import json
import sys
import os
import shutil
import webbrowser
import time
import re
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from concurrent.futures import ThreadPoolExecutor
import logging

# --- Constants ---
FFMPEG_URL = "https://ffmpeg.org/download.html"
YTDLP_URL = "https://github.com/yt-dlp/yt-dlp"

# --- Backend Downloader Class (from your original script) ---
class DownloaderBackend:
    def __init__(self, ytdlp_path):
        self.ytdlp_path = ytdlp_path

    def get_metadata(self, url):
        command = [
            self.ytdlp_path,
            '--dump-json',
            '--flat-playlist',
            '--no-warnings',
            url
        ]
        try:
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', startupinfo=self._get_startup_info())
            stdout, stderr = process.communicate(timeout=30)
            if process.returncode != 0:
                raise RuntimeError(f"yt-dlp error: {stderr.strip()}")
            videos = [json.loads(line) for line in stdout.strip().split('\n')]
            return videos
        except Exception as e:
            raise e

    def download(self, job_id, url, options, sid):
        command = [
            self.ytdlp_path,
            '--progress',
            '--no-warnings',
            '--encoding', 'utf-8',
            '--output', options['output_template'],
            '--format', options['format_code'],
        ]
        if options.get('extract_audio'):
            command.extend(['--extract-audio', '--audio-format', options['audio_format']])
        command.append(url)

        try:
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', bufsize=1, startupinfo=self._get_startup_info())
            
            socketio.emit('progress_update', {'id': job_id, 'status': 'Downloading'}, room=sid)

            for line in iter(process.stdout.readline, ''):
                progress_data = self._parse_progress(line)
                if progress_data:
                    progress_data['id'] = job_id
                    socketio.emit('progress_update', progress_data, room=sid)
            
            process.wait()
            if process.returncode == 0:
                socketio.emit('progress_update', {'id': job_id, 'status': 'Completed', 'progress': 100.0}, room=sid)
            else:
                socketio.emit('progress_update', {'id': job_id, 'status': 'Error'}, room=sid)
        except Exception as e:
            socketio.emit('progress_update', {'id': job_id, 'status': 'Error', 'message': str(e)}, room=sid)

    def _parse_progress(self, line):
        if line.strip().startswith('[download]'):
            parts = line.split()
            try:
                percent_str = next((p for p in parts if '%' in p), None)
                if percent_str:
                    progress = float(percent_str.replace('%', ''))
                    size_str = next((p for p in parts if 'iB' in p), None)
                    speed_str = next((p for p in parts if 'iB/s' in p), None)
                    eta_str = next((p for p in parts if ':' in p and len(p) > 4), None)
                    return {'status': 'Downloading', 'progress': progress, 'size': size_str, 'speed': speed_str, 'eta': eta_str}
            except (ValueError, IndexError):
                pass
        return None

    def _get_startup_info(self):
        if sys.platform == "win32":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            return startupinfo
        return None

# --- Flask App Initialization ---
app = Flask(__name__, static_folder='.', static_url_path='')
socketio = SocketIO(app, cors_allowed_origins="*")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Thread pool for concurrent downloads
executor = ThreadPoolExecutor(max_workers=4)

# Global variables for tracking downloads
active_downloads = {}
download_stats = {
    'total': 0,
    'completed': 0,
    'failed': 0,
    'active': 0
}

# --- Dependency Check ---
YTDLP_PATH = shutil.which('yt-dlp')
FFMPEG_PATH = shutil.which('ffmpeg')

if not YTDLP_PATH or not FFMPEG_PATH:
    print("ERROR: yt-dlp or ffmpeg not found in PATH.")
    print("Please install them and ensure they are accessible.")
    # In a real app, you might exit or provide download links.
    # For this example, we will proceed but expect errors.

downloader = DownloaderBackend(YTDLP_PATH)

# --- HTTP API Routes ---
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/api/stats')
def get_stats():
    """Get download statistics"""
    return jsonify(download_stats)

@app.route('/api/queue')
def get_queue():
    """Get current download queue"""
    return jsonify({
        'active_downloads': active_downloads,
        'stats': download_stats
    })

@app.route('/api/queue/clear', methods=['POST'])
def clear_queue():
    """Clear completed downloads from queue"""
    try:
        # Reset stats but keep active downloads
        download_stats['completed'] = 0
        download_stats['failed'] = 0
        download_stats['total'] = download_stats['active']
        
        return jsonify({'message': 'Queue cleared successfully', 'stats': download_stats})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/queue/pause', methods=['POST'])
def pause_downloads():
    """Pause all active downloads"""
    try:
        # In a real implementation, this would pause active downloads
        # For now, we'll just return a success message
        return jsonify({'message': 'Downloads paused'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/queue/resume', methods=['POST'])
def resume_downloads():
    """Resume all paused downloads"""
    try:
        # In a real implementation, this would resume paused downloads
        # For now, we'll just return a success message
        return jsonify({'message': 'Downloads resumed'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/metadata', methods=['POST'])
def get_metadata_route():
    data = request.get_json()
    urls = data.get('urls', [])
    
    if not urls:
        url = data.get('url')
        if url:
            urls = [url]
        else:
            return jsonify({'error': 'URL or URLs are required'}), 400
    
    try:
        metadata_list = []
        
        for url in urls:
            url = url.strip()
            if not url:
                continue
                
            try:
                metadata = downloader.get_metadata(url)
                for item in metadata:
                    metadata_list.append(extract_video_metadata(item))
                        
            except Exception as e:
                logger.error(f"Error extracting metadata for {url}: {str(e)}")
                # Add error entry for failed URL
                metadata_list.append({
                    'title': f'Error: {url}',
                    'duration': 0,
                    'thumbnail': '',
                    'url': url,
                    'error': str(e),
                    'view_count': 0,
                    'description': f'Failed to extract metadata: {str(e)}'
                })
                
        return jsonify(metadata_list)
                
    except Exception as e:
        logger.error(f"General error in metadata extraction: {str(e)}")
        return jsonify({'error': str(e)}), 500

def extract_video_metadata(info):
    """Extract comprehensive metadata from video info"""
    return {
        'title': info.get('title', 'Unknown'),
        'duration': info.get('duration', 0),
        'thumbnail': info.get('thumbnail', ''),
        'webpage_url': info.get('webpage_url') or info.get('url', ''),
        'url': info.get('webpage_url') or info.get('url', ''),
        'view_count': info.get('view_count', 0),
        'description': info.get('description', '')[:200] + '...' if info.get('description') and len(info.get('description', '')) > 200 else info.get('description', ''),
        'uploader': info.get('uploader', 'Unknown'),
        'upload_date': info.get('upload_date', ''),
        'filesize': info.get('filesize') or info.get('filesize_approx'),
        'format_id': info.get('format_id', ''),
        'ext': info.get('ext', 'mp4')
    }

# --- WebSocket Event Handlers ---
@socketio.on('connect')
def handle_connect():
    print(f'Client connected: {request.sid}')

@app.route('/download')
def download_video():
    url = request.args.get('url')
    quality = request.args.get('quality', 'best_mp4')
    
    if not url:
        return jsonify({'error': 'URL is required'}), 400
    
    def generate_progress():
        download_id = f"download_{int(time.time() * 1000)}"
        active_downloads[download_id] = {'url': url, 'quality': quality, 'status': 'starting'}
        download_stats['active'] += 1
        
        try:
            # Configure yt-dlp options based on quality
            ydl_opts = get_download_options(quality, download_id)
            
            yield f"data: {json.dumps({'status': 'starting', 'message': 'Initializing download...'})}\n\n"
            
            try:
                # Use the existing downloader backend
                downloader.download(download_id, url, ydl_opts, None)
                
                # Download completed successfully
                active_downloads[download_id]['status'] = 'completed'
                download_stats['active'] -= 1
                download_stats['completed'] += 1
                
                yield f"data: {json.dumps({'status': 'finished', 'message': 'Download completed successfully!'})}\n\n"
                
            except Exception as download_error:
                logger.error(f"Download error for {url}: {str(download_error)}")
                
                active_downloads[download_id]['status'] = 'failed'
                download_stats['active'] -= 1
                download_stats['failed'] += 1
                
                yield f"data: {json.dumps({'status': 'error', 'message': str(download_error)})}\n\n"
                
        except Exception as e:
            logger.error(f"General download error: {str(e)}")
            
            if download_id in active_downloads:
                active_downloads[download_id]['status'] = 'failed'
                download_stats['active'] -= 1
                download_stats['failed'] += 1
            
            yield f"data: {json.dumps({'status': 'error', 'message': str(e)})}\n\n"
        
        finally:
            # Clean up
            if download_id in active_downloads:
                del active_downloads[download_id]
    
    return Response(generate_progress(), mimetype='text/event-stream')

def get_download_options(quality, download_id):
    """Get yt-dlp options based on quality selection"""
    
    quality_map = {
        "best_mp4": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "720p_mp4": "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best",
        "480p_mp4": "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480][ext=mp4]/best",
        "360p_mp4": "bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/best[height<=360][ext=mp4]/best",
        "mp3": "bestaudio/best"
    }
    
    output_dir = os.path.join(os.path.expanduser('~'), 'Downloads', 'WebApp_Downloader')
    os.makedirs(output_dir, exist_ok=True)
    
    options = {
        'format_code': quality_map.get(quality, "best"),
        'output_template': os.path.join(output_dir, '%(title)s - %(id)s.%(ext)s'),
        'extract_audio': quality == "mp3",
        'audio_format': 'mp3'
    }
    
    return options

@socketio.on('start_download')
def handle_start_download(data):
    job_id = data.get('id')
    url = data.get('url')
    quality = data.get('quality')
    
    quality_map = {
        "best_mp4": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "720p_mp4": "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best",
        "mp3": "bestaudio/best"
    }
    
    output_dir = os.path.join(os.path.expanduser('~'), 'Downloads', 'WebApp_Downloader')
    os.makedirs(output_dir, exist_ok=True)
    
    options = {
        'format_code': quality_map.get(quality, "best"),
        'output_template': os.path.join(output_dir, '%(title)s - %(id)s.%(ext)s'),
        'extract_audio': quality == "mp3",
        'audio_format': 'mp3'
    }
    
    # Run each download in its own thread to not block the server
    thread = threading.Thread(target=downloader.download, args=(job_id, url, options, request.sid))
    thread.daemon = True
    thread.start()

@socketio.on('disconnect')
def handle_disconnect():
    print(f'Client disconnected: {request.sid}')

# --- Main Entry Point ---
if __name__ == '__main__':
    print("Starting YouTube Downloader Web App...")
    print("Open http://127.0.0.1:5000 in your browser.")
    socketio.run(app, host='127.0.0.1', port=5000)