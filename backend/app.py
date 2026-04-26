import os
import uuid
from flask import Flask, request, jsonify, send_file, after_this_request
from flask_cors import CORS
import yt_dlp

app = Flask(__name__)
CORS(app)

DOWNLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__name__)), 'temp_downloads')
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

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

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # Extract relevant info
            title = info.get('title', 'Unknown Title')
            thumbnail = info.get('thumbnail', '')
            channel = info.get('uploader', 'Unknown Channel')
            duration = info.get('duration', 0) # in seconds
            
            # Extract formats
            formats = []
            
            # Simplify formats for the user
            available_formats = {
                '1080p': False,
                '720p': False,
                '480p': False,
                '360p': False,
            }
            
            for f in info.get('formats', []):
                height = f.get('height')
                vcodec = f.get('vcodec')
                if vcodec != 'none':
                    if height == 1080: available_formats['1080p'] = True
                    if height == 720: available_formats['720p'] = True
                    if height == 480: available_formats['480p'] = True
                    if height == 360: available_formats['360p'] = True

            # Format options to send back
            options = []
            if available_formats['1080p']: options.append({'id': '1080p', 'label': '1080p HD Video'})
            if available_formats['720p']: options.append({'id': '720p', 'label': '720p HD Video'})
            if available_formats['480p']: options.append({'id': '480p', 'label': '480p Video'})
            if available_formats['360p']: options.append({'id': '360p', 'label': '360p Video'})
            options.append({'id': 'mp3', 'label': 'MP3 Audio Only'})
            
            return jsonify({
                'title': title,
                'thumbnail': thumbnail,
                'channel': channel,
                'duration': duration,
                'options': options
            })
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/download', methods=['POST'])
def download():
    data = request.json
    url = data.get('url')
    quality = data.get('quality', '720p')
    
    if not url:
        return jsonify({'error': 'URL is required'}), 400
        
    filename_id = str(uuid.uuid4())
    outtmpl = os.path.join(DOWNLOAD_DIR, f'{filename_id}.%(ext)s')
    
    ydl_opts = {
        'outtmpl': outtmpl,
        'quiet': True,
        'no_warnings': True,
    }
    
    if quality == 'mp3':
        ydl_opts['format'] = 'bestaudio/best'
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]
    elif quality == '1080p':
        ydl_opts['format'] = 'bestvideo[height<=1080]+bestaudio/best'
        ydl_opts['merge_output_format'] = 'mp4'
    elif quality == '720p':
        ydl_opts['format'] = 'bestvideo[height<=720]+bestaudio/best'
        ydl_opts['merge_output_format'] = 'mp4'
    elif quality == '480p':
        ydl_opts['format'] = 'bestvideo[height<=480]+bestaudio/best'
        ydl_opts['merge_output_format'] = 'mp4'
    elif quality == '360p':
        ydl_opts['format'] = 'bestvideo[height<=360]+bestaudio/best'
        ydl_opts['merge_output_format'] = 'mp4'
    else:
        ydl_opts['format'] = 'best'
        
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            
            # The exact filename might change if it's merged or processed (like mp3)
            # So let's look for the file that starts with our filename_id in DOWNLOAD_DIR
            downloaded_file = None
            for f in os.listdir(DOWNLOAD_DIR):
                if f.startswith(filename_id):
                    downloaded_file = os.path.join(DOWNLOAD_DIR, f)
                    break
                    
            if not downloaded_file:
                return jsonify({'error': 'Download failed to produce a file'}), 500

            # Set up the file to be deleted after sending
            @after_this_request
            def remove_file(response):
                try:
                    os.remove(downloaded_file)
                except Exception as e:
                    print("Error removing file:", e)
                return response
                
            # Clean title for the downloaded file name
            safe_title = "".join([c for c in info.get('title', 'video') if c.isalpha() or c.isdigit() or c==' ']).rstrip()
            ext = os.path.splitext(downloaded_file)[1]
            download_name = f"{safe_title}{ext}"
            
            return send_file(downloaded_file, as_attachment=True, download_name=download_name)
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(port=5000, debug=True)
