import os
import uuid
import shutil
import threading
import json
from flask import Flask, request, jsonify, send_file, after_this_request
from flask_cors import CORS
import yt_dlp

# ── FFmpeg Detection ────────────────────────────────────────────────────────────
def get_ffmpeg_location():
    env_path = os.environ.get('FFMPEG_PATH')
    if env_path and os.path.exists(env_path):
        return env_path
    system_ffmpeg = shutil.which('ffmpeg')
    if system_ffmpeg:
        return os.path.dirname(system_ffmpeg)
    local_path = r'C:\Users\hp\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1-full_build\bin'
    if os.path.exists(local_path):
        return local_path
    return None

FFMPEG_LOCATION = get_ffmpeg_location()

app = Flask(__name__)
CORS(app)

DOWNLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__name__)), 'temp_downloads')
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# ── In-memory progress store ────────────────────────────────────────────────────
# { job_id: { status, percent, speed, eta, filepath, filename, error } }
progress_store = {}

# ── Helpers ─────────────────────────────────────────────────────────────────────
def sanitize_filename(name):
    keepchars = (' ', '.', '_', '-')
    return "".join(c for c in name if c.isalnum() or c in keepchars).strip() or 'download'

# ── GET INFO ────────────────────────────────────────────────────────────────────
@app.route('/api/get-info', methods=['POST'])
def get_info():
    data = request.json
    url = data.get('url')
    if not url:
        return jsonify({'error': 'URL is required'}), 400

    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
    }
    if FFMPEG_LOCATION:
        ydl_opts['ffmpeg_location'] = FFMPEG_LOCATION

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

            available_formats = {'1080p': False, '720p': False, '480p': False, '360p': False}
            for f in info.get('formats', []):
                height = f.get('height')
                vcodec = f.get('vcodec')
                if vcodec != 'none':
                    if height == 1080: available_formats['1080p'] = True
                    if height == 720:  available_formats['720p'] = True
                    if height == 480:  available_formats['480p'] = True
                    if height == 360:  available_formats['360p'] = True

            options = []
            if available_formats['1080p']: options.append({'id': '1080p', 'label': '1080p HD Video'})
            if available_formats['720p']:  options.append({'id': '720p',  'label': '720p HD Video'})
            if available_formats['480p']:  options.append({'id': '480p',  'label': '480p Video'})
            if available_formats['360p']:  options.append({'id': '360p',  'label': '360p Video'})
            options.append({'id': 'mp3', 'label': 'MP3 Audio Only'})

            return jsonify({
                'title':     info.get('title', 'Unknown Title'),
                'thumbnail': info.get('thumbnail', ''),
                'channel':   info.get('uploader', 'Unknown Channel'),
                'duration':  info.get('duration', 0),
                'options':   options,
            })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ── Background download worker ──────────────────────────────────────────────────
def do_download(job_id, url, quality, custom_filename):
    filename_id = str(uuid.uuid4())
    outtmpl = os.path.join(DOWNLOAD_DIR, f'{filename_id}.%(ext)s')

    def progress_hook(d):
        if d['status'] == 'downloading':
            raw = d.get('_percent_str', '0%').strip().replace('%', '')
            try:
                pct = float(raw)
            except ValueError:
                pct = 0.0
            progress_store[job_id].update({
                'status':  'downloading',
                'percent': round(pct, 1),
                'speed':   d.get('_speed_str', '').strip(),
                'eta':     d.get('_eta_str', '').strip(),
            })
        elif d['status'] == 'finished':
            progress_store[job_id].update({'status': 'processing', 'percent': 99})

    ydl_opts = {
        'outtmpl':        outtmpl,
        'quiet':          True,
        'no_warnings':    True,
        'progress_hooks': [progress_hook],
    }
    if FFMPEG_LOCATION:
        ydl_opts['ffmpeg_location'] = FFMPEG_LOCATION

    aac_args = {'merger+ffmpeg': ['-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k']}

    if quality == 'mp3':
        ydl_opts['format'] = 'bestaudio/best'
        ydl_opts['postprocessors'] = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}]
    elif quality == '1080p':
        ydl_opts['format'] = 'bestvideo[height<=1080]+bestaudio/best'
        ydl_opts['merge_output_format'] = 'mp4'
        ydl_opts['postprocessor_args'] = aac_args
    elif quality == '720p':
        ydl_opts['format'] = 'bestvideo[height<=720]+bestaudio/best'
        ydl_opts['merge_output_format'] = 'mp4'
        ydl_opts['postprocessor_args'] = aac_args
    elif quality == '480p':
        ydl_opts['format'] = 'bestvideo[height<=480]+bestaudio/best'
        ydl_opts['merge_output_format'] = 'mp4'
        ydl_opts['postprocessor_args'] = aac_args
    elif quality == '360p':
        ydl_opts['format'] = 'bestvideo[height<=360]+bestaudio/best'
        ydl_opts['merge_output_format'] = 'mp4'
        ydl_opts['postprocessor_args'] = aac_args
    else:
        ydl_opts['format'] = 'best'

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

            downloaded_file = None
            if 'requested_downloads' in info and len(info['requested_downloads']) > 0:
                downloaded_file = info['requested_downloads'][0].get('filepath')
            elif 'filepath' in info:
                downloaded_file = info.get('filepath')

            if not downloaded_file or not os.path.exists(downloaded_file):
                progress_store[job_id] = {'status': 'error', 'error': 'Download failed to produce a file'}
                return

            ext = os.path.splitext(downloaded_file)[1]
            base_name = custom_filename if custom_filename else info.get('title', 'video')
            download_name = sanitize_filename(base_name) + ext

            progress_store[job_id].update({
                'status':   'done',
                'percent':  100,
                'filepath': downloaded_file,
                'filename': download_name,
            })
    except Exception as e:
        progress_store[job_id] = {'status': 'error', 'error': str(e)}

# ── START DOWNLOAD (returns job_id immediately) ─────────────────────────────────
@app.route('/api/download', methods=['POST'])
def download():
    data = request.json
    url = data.get('url')
    quality = data.get('quality', '720p')
    custom_filename = data.get('filename', '').strip()

    if not url:
        return jsonify({'error': 'URL is required'}), 400

    job_id = str(uuid.uuid4())
    progress_store[job_id] = {'status': 'starting', 'percent': 0, 'speed': '', 'eta': ''}

    t = threading.Thread(target=do_download, args=(job_id, url, quality, custom_filename), daemon=True)
    t.start()

    return jsonify({'job_id': job_id})

# ── POLL PROGRESS ───────────────────────────────────────────────────────────────
@app.route('/api/progress/<job_id>', methods=['GET'])
def get_progress(job_id):
    job = progress_store.get(job_id, {'status': 'not_found'})
    # Never expose server filepath to the client
    safe = {k: v for k, v in job.items() if k != 'filepath'}
    return jsonify(safe)

# ── SERVE FILE ──────────────────────────────────────────────────────────────────
@app.route('/api/get-file/<job_id>', methods=['GET'])
def get_file(job_id):
    job = progress_store.get(job_id)
    if not job or job.get('status') != 'done':
        return jsonify({'error': 'File not ready or not found'}), 404

    filepath = job.get('filepath')
    filename = job.get('filename', 'download')

    if not filepath or not os.path.exists(filepath):
        return jsonify({'error': 'File not found on server'}), 404

    @after_this_request
    def cleanup(response):
        try:
            os.remove(filepath)
        except Exception:
            pass
        try:
            del progress_store[job_id]
        except Exception:
            pass
        return response

    return send_file(filepath, as_attachment=True, download_name=filename)

if __name__ == '__main__':
    app.run(port=5000, debug=True)
