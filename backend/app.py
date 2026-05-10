import os
import uuid
import shutil
import threading
import json
import requests
import re
import http.cookiejar
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

# Path to an optional netscape-format cookies.txt (user can export from browser)
COOKIES_FILE = os.path.join(os.path.dirname(os.path.abspath(__name__)), 'instagram_cookies.txt')

def base_ydl_opts():
    opts = {
        'quiet': True,
        'no_warnings': True,
    }
    if FFMPEG_LOCATION:
        opts['ffmpeg_location'] = FFMPEG_LOCATION
    return opts


def instagram_ydl_opts():
    """yt-dlp options for Instagram — tries cookies.txt first, then browser cookies."""
    opts = base_ydl_opts()
    if os.path.exists(COOKIES_FILE):
        opts['cookiefile'] = COOKIES_FILE
    # Note: we intentionally skip cookiesfrombrowser here because Chrome
    # keeps its SQLite DB locked while running, causing yt-dlp to error.
    # Users should export cookies to instagram_cookies.txt via a browser extension
    # like "Get cookies.txt LOCALLY" if they need auth for private content.
    return opts

def get_requests_cookies():
    """Load cookies.txt as a CookieJar for the requests library."""
    if os.path.exists(COOKIES_FILE):
        try:
            cj = http.cookiejar.MozillaCookieJar(COOKIES_FILE)
            cj.load(ignore_discard=True, ignore_expires=True)
            return cj
        except Exception:
            pass
    return None

# ══════════════════════════════════════════════════════════════════════════════
#  YOUTUBE ROUTES
# ══════════════════════════════════════════════════════════════════════════════

# ── GET INFO ────────────────────────────────────────────────────────────────────
@app.route('/api/get-info', methods=['POST'])
def get_info():
    data = request.json
    url = data.get('url')
    if not url:
        return jsonify({'error': 'URL is required'}), 400

    ydl_opts = {**base_ydl_opts(), 'skip_download': True}

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
        **base_ydl_opts(),
        'outtmpl':        outtmpl,
        'progress_hooks': [progress_hook],
    }

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


# ══════════════════════════════════════════════════════════════════════════════
#  INSTAGRAM ROUTES
# ══════════════════════════════════════════════════════════════════════════════

def classify_instagram_url(url):
    """Classify Instagram URL type."""
    url_lower = url.lower()
    if '/stories/' in url_lower:
        return 'story'
    elif '/reel/' in url_lower or '/reels/' in url_lower:
        return 'reel'
    elif '/p/' in url_lower:
        return 'post'
    elif 'instagram.com/' in url_lower and not any(x in url_lower for x in ['/p/', '/reel/', '/stories/', '/tv/']):
        # Likely a profile URL
        return 'profile'
    elif '/tv/' in url_lower:
        return 'igtv'
    return 'unknown'


# ── INSTAGRAM: GET INFO ─────────────────────────────────────────────────────────
def _pick_best_thumbnail(entry):
    """Return the highest-res thumbnail URL from an entry dict."""
    thumbs = entry.get('thumbnails', [])
    if thumbs:
        return thumbs[-1].get('url', '') or thumbs[0].get('url', '')
    return entry.get('thumbnail', '')


def _build_items_from_info(info, url):
    """Turn a yt-dlp info dict into a list of item dicts for the frontend."""
    entries = info.get('entries') or [info]
    items = []
    for idx, entry in enumerate(entries):
        if entry is None:
            continue

        formats = entry.get('formats', [])
        is_video = any(
            f.get('vcodec') not in (None, 'none') and f.get('vcodec')
            for f in formats
        )

        thumbnail = _pick_best_thumbnail(entry)

        # For image-only entries yt-dlp may store the image URL in 'url' field
        direct_url = ''
        if not is_video:
            # Prefer the raw image URL so we can download without yt-dlp
            direct_url = (
                entry.get('url')
                or entry.get('display_url')
                or thumbnail
            )

        items.append({
            'index':       idx,
            'title':       entry.get('title') or entry.get('description') or f'Item {idx + 1}',
            'thumbnail':   thumbnail,
            'is_video':    is_video,
            'duration':    entry.get('duration', 0),
            'uploader':    entry.get('uploader') or entry.get('channel') or 'Instagram',
            'webpage_url': entry.get('webpage_url') or url,
            'direct_url':  direct_url,
        })
    return items


@app.route('/api/instagram/get-info', methods=['POST'])
def instagram_get_info():
    data = request.json
    url = data.get('url', '').strip()
    if not url:
        return jsonify({'error': 'URL is required'}), 400

    content_type = classify_instagram_url(url)

    # Profile picture is handled separately
    if content_type == 'profile':
        return jsonify({
            'type': 'profile',
            'url': url,
            'title': 'Instagram Profile Picture',
            'thumbnail': '',
            'items': [],
        })

    ydl_opts = {
        **instagram_ydl_opts(),
        'skip_download': True,
        'extract_flat': False,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        items = _build_items_from_info(info, url)
        top_thumb = _pick_best_thumbnail(info)

        return jsonify({
            'type':      content_type,
            'url':       url,
            'title':     info.get('title') or info.get('description') or 'Instagram Content',
            'thumbnail': top_thumb,
            'uploader':  info.get('uploader') or info.get('channel') or 'Instagram',
            'items':     items,
        })

    except Exception as first_err:
        err_msg = str(first_err)

        # ── Photo-only post fallback ─────────────────────────────────────────
        # yt-dlp often fails on photo-only posts or due to transient API blocks.
        # We retry with extract_flat=True to at least get metadata + thumbnail.
        low_err = err_msg.lower()
        if any(x in low_err for x in ['no video', 'photo', 'empty media', 'not granting access']):
            try:
                flat_opts = {
                    **instagram_ydl_opts(),
                    'skip_download': True,
                    'extract_flat': True,
                }
                with yt_dlp.YoutubeDL(flat_opts) as ydl:
                    flat_info = ydl.extract_info(url, download=False)

                thumbnail = _pick_best_thumbnail(flat_info)
                # For flat extraction, 'url' on the entry IS the image CDN link
                direct_url = flat_info.get('url') or thumbnail

                entries = flat_info.get('entries') or [flat_info]
                items = []
                for idx, entry in enumerate(entries):
                    if entry is None:
                        continue
                    # Use the CDN thumbnail URL — that's the actual image.
                    # entry.get('url') is the post page URL, NOT the image CDN.
                    th = _pick_best_thumbnail(entry) or thumbnail
                    d_url = th  # CDN image URL for direct download
                    items.append({
                        'index':       idx,
                        'title':       entry.get('title') or entry.get('description') or f'Photo {idx + 1}',
                        'thumbnail':   th,
                        'is_video':    False,
                        'duration':    0,
                        'uploader':    entry.get('uploader') or flat_info.get('uploader') or 'Instagram',
                        'webpage_url': entry.get('webpage_url') or url,
                        'direct_url':  d_url,
                    })

                if not items:
                    items = [{
                        'index':      0,
                        'title':      flat_info.get('title') or 'Instagram Photo',
                        'thumbnail':  thumbnail,
                        'is_video':   False,
                        'duration':   0,
                        'uploader':   flat_info.get('uploader') or 'Instagram',
                        'webpage_url': url,
                        'direct_url': thumbnail,  # CDN URL — always use thumbnail for photos
                    }]

                return jsonify({
                    'type':      content_type,
                    'url':       url,
                    'title':     flat_info.get('title') or flat_info.get('description') or 'Instagram Photo Post',
                    'thumbnail': thumbnail,
                    'uploader':  flat_info.get('uploader') or 'Instagram',
                    'items':     items,
                })

            except Exception:
                pass  # Fall through to original error

        return jsonify({'error': err_msg}), 500


# ── INSTAGRAM: BACKGROUND DOWNLOAD WORKER ──────────────────────────────────────
def _is_cdn_image_url(url):
    """Return True if url looks like a direct CDN image (not a webpage)."""
    cdn_hints = [
        'cdninstagram.com', 'fbcdn.net', 'scontent', 'instagram.f',
        '.jpg', '.jpeg', '.png', '.webp',
    ]
    return any(h in url for h in cdn_hints)


def _direct_image_download(job_id, cdn_url, custom_filename):
    """
    Download an Instagram photo directly from its CDN URL.
    Validates that the response is actually an image (not HTML).
    """
    if not cdn_url or not _is_cdn_image_url(cdn_url):
        progress_store[job_id] = {
            'status': 'error',
            'error': 'No direct image URL available. Try adding instagram_cookies.txt for authenticated access.',
        }
        return

    progress_store[job_id].update({'status': 'downloading', 'percent': 20})
    headers = {
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/124.0.0.0 Safari/537.36'
        ),
        'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://www.instagram.com/',
        'Sec-Fetch-Dest': 'image',
        'Sec-Fetch-Mode': 'no-cors',
        'Sec-Fetch-Site': 'cross-site',
    }
    try:
        r = requests.get(cdn_url, headers=headers, cookies=get_requests_cookies(), timeout=30, stream=True)
        r.raise_for_status()

        ct = r.headers.get('Content-Type', '')
        # Guard: reject HTML/text responses (happens when CDN URL has expired)
        if 'html' in ct or 'text/plain' in ct:
            progress_store[job_id] = {
                'status': 'error',
                'error': 'Image URL has expired. Please re-fetch the post and try again.',
            }
            return

        ext = (
            '.jpg'  if 'jpeg' in ct or 'jpg' in ct else
            '.png'  if 'png'  in ct else
            '.webp' if 'webp' in ct else
            '.jpg'
        )

        img_path = os.path.join(DOWNLOAD_DIR, f'{job_id}_img{ext}')
        total = int(r.headers.get('Content-Length', 0))
        downloaded = 0
        with open(img_path, 'wb') as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)
                downloaded += len(chunk)
                if total > 0:
                    pct = min(90, 20 + int(70 * downloaded / total))
                    progress_store[job_id].update({'percent': pct})

        filename = sanitize_filename(custom_filename or 'instagram_photo') + ext
        progress_store[job_id].update({
            'status':   'done',
            'percent':  100,
            'filepath': img_path,
            'filename': filename,
        })
    except Exception as e:
        progress_store[job_id] = {'status': 'error', 'error': str(e)}


def do_instagram_download(job_id, url, media_type, custom_filename, direct_url=''):
    """Download a single Instagram media item (video or image)."""

    # ── Fast path: image with a direct CDN URL ───────────────────────────────
    if media_type == 'image' and direct_url:
        _direct_image_download(job_id, direct_url, custom_filename)
        return

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

    if media_type == 'image':
        ydl_opts = {
            **instagram_ydl_opts(),
            'outtmpl': outtmpl,
            'progress_hooks': [progress_hook],
            'format': 'best',
        }
    else:
        # video / reel / story
        ydl_opts = {
            **instagram_ydl_opts(),
            'outtmpl': outtmpl,
            'progress_hooks': [progress_hook],
            'format': 'bestvideo+bestaudio/best',
            'merge_output_format': 'mp4',
        }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

        downloaded_file = None
        if 'requested_downloads' in info and info['requested_downloads']:
            downloaded_file = info['requested_downloads'][0].get('filepath')
        elif 'filepath' in info:
            downloaded_file = info.get('filepath')

        # Fallback: scan temp dir
        if not downloaded_file or not os.path.exists(downloaded_file):
            for f in os.listdir(DOWNLOAD_DIR):
                if f.startswith(filename_id):
                    downloaded_file = os.path.join(DOWNLOAD_DIR, f)
                    break

        if not downloaded_file or not os.path.exists(downloaded_file):
            progress_store[job_id] = {'status': 'error', 'error': 'Download failed to produce a file'}
            return

        ext = os.path.splitext(downloaded_file)[1]
        base_name = custom_filename if custom_filename else info.get('title', 'instagram_media')
        download_name = sanitize_filename(base_name) + ext

        progress_store[job_id].update({
            'status':   'done',
            'percent':  100,
            'filepath': downloaded_file,
            'filename': download_name,
        })

    except Exception as outer_err:
        # ── Fallback chain for image posts ───────────────────────────────────
        if media_type == 'image':
            # Step 1: Try yt-dlp's writethumbnail (downloads image via yt-dlp natively)
            try:
                wt_id   = str(uuid.uuid4())
                wt_tmpl = os.path.join(DOWNLOAD_DIR, f'{wt_id}.%(ext)s')
                wt_opts = {
                    **instagram_ydl_opts(),
                    'outtmpl':        wt_tmpl,
                    'skip_download':  True,
                    'writethumbnail': True,
                    'postprocessors': [{'key': 'FFmpegThumbnailsConvertor', 'format': 'jpg'}]
                    if FFMPEG_LOCATION else [],
                }
                with yt_dlp.YoutubeDL(wt_opts) as ydl:
                    wt_info = ydl.extract_info(url, download=True)

                # Find the thumbnail file written to disk
                for fname in os.listdir(DOWNLOAD_DIR):
                    if fname.startswith(wt_id):
                        wt_path = os.path.join(DOWNLOAD_DIR, fname)
                        ext = os.path.splitext(wt_path)[1] or '.jpg'
                        dl_name = sanitize_filename(custom_filename or 'instagram_photo') + ext
                        progress_store[job_id].update({
                            'status':   'done',
                            'percent':  100,
                            'filepath': wt_path,
                            'filename': dl_name,
                        })
                        return
            except Exception:
                pass

            # Step 2: Re-fetch the CDN thumbnail URL and download via HTTP
            try:
                flat_opts = {
                    **instagram_ydl_opts(),
                    'skip_download': True,
                    'extract_flat': True,
                }
                with yt_dlp.YoutubeDL(flat_opts) as ydl:
                    flat_info = ydl.extract_info(url, download=False)
                cdn = _pick_best_thumbnail(flat_info)
                if cdn and _is_cdn_image_url(cdn):
                    _direct_image_download(job_id, cdn, custom_filename)
                    return
            except Exception:
                pass

            progress_store[job_id] = {
                'status': 'error',
                'error': (
                    'Could not download this photo. '
                    'Add instagram_cookies.txt for authenticated access, '
                    'or the CDN URL may have expired — try re-fetching.'
                ),
            }
        else:
            progress_store[job_id] = {'status': 'error', 'error': str(outer_err)}


# ── INSTAGRAM: START DOWNLOAD ───────────────────────────────────────────────────
@app.route('/api/instagram/download', methods=['POST'])
def instagram_download():
    data = request.json
    url = data.get('url', '').strip()
    media_type      = data.get('media_type', 'video')   # 'video' | 'image'
    custom_filename = data.get('filename', '').strip()
    direct_url      = data.get('direct_url', '').strip() # CDN URL for photo posts

    if not url:
        return jsonify({'error': 'URL is required'}), 400

    job_id = str(uuid.uuid4())
    progress_store[job_id] = {'status': 'starting', 'percent': 0, 'speed': '', 'eta': ''}

    t = threading.Thread(
        target=do_instagram_download,
        args=(job_id, url, media_type, custom_filename, direct_url),
        daemon=True,
    )
    t.start()

    return jsonify({'job_id': job_id})


# ── INSTAGRAM: PROFILE PICTURE DOWNLOAD ────────────────────────────────────────
@app.route('/api/instagram/profile-pic', methods=['POST'])
def instagram_profile_pic():
    """
    Fetch Instagram profile picture for a username.
    Strategy:
      1. Try Instagram's public JSON endpoint (?__a=1&__d=dis)
      2. Fall back to yt-dlp flat extraction
    """
    data = request.json
    username_or_url = data.get('username', '').strip()
    if not username_or_url:
        return jsonify({'error': 'Username or URL is required'}), 400

    # Normalise to plain username
    username = username_or_url.lstrip('@').rstrip('/')
    if username.startswith('http'):
        # Extract username from URL like https://www.instagram.com/nasa/
        parts = [p for p in username.split('/') if p and 'instagram' not in p and 'http' not in p]
        username = parts[0] if parts else username

    username = username.split('?')[0].split('&')[0]

    profile_url = f'https://www.instagram.com/{username}/'

    # ── Strategy 0: Instagram Search API (Best for Cookies) ───────────────────
    avatar = ''
    bio    = ''
    followers = 0
    display_name = username

    api_headers = {
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/124.0.0.0 Safari/537.36'
        ),
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'en-US,en;q=0.9',
        'X-Requested-With': 'XMLHttpRequest',
        'Referer': 'https://www.instagram.com/',
    }

    try:
        search_resp = requests.get(
            f'https://www.instagram.com/web/search/topsearch/?context=blended&query={username}',
            headers=api_headers,
            cookies=get_requests_cookies(),
            timeout=15
        )
        if search_resp.status_code == 200:
            for u in search_resp.json().get('users', []):
                user_obj = u.get('user', {})
                if user_obj.get('username') == username:
                    avatar = user_obj.get('profile_pic_url', '')
                    display_name = user_obj.get('full_name') or username
                    # The search API doesn't return bio/followers, but the avatar is the most critical part
                    break
    except Exception:
        pass

    # ── Strategy 1: Instagram public JSON API ────────────────────────────────
    if not avatar:
        try:
            resp = requests.get(
                f'https://www.instagram.com/api/v1/users/web_profile_info/?username={username}',
                headers={**api_headers, 'X-IG-App-ID': '936619743392459'},
                cookies=get_requests_cookies(),
                timeout=15,
            )
            if resp.status_code == 200:
                jd = resp.json()
                user = jd.get('data', {}).get('user', {})
                avatar        = user.get('profile_pic_url_hd') or user.get('profile_pic_url', '')
                bio           = user.get('biography', '')
                followers     = user.get('edge_followed_by', {}).get('count', 0)
                display_name  = user.get('username') or username
        except Exception:
            pass

    # ── Strategy 2: yt-dlp flat extraction (fallback) ───────────────────────
    if not avatar:
        try:
            ydl_opts = {
                **instagram_ydl_opts(),
                'skip_download': True,
                'extract_flat': True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(profile_url, download=False)

            avatar = (
                info.get('thumbnail')
                or info.get('avatar')
                or info.get('profile_picture')
                or _pick_best_thumbnail(info)
                or ''
            )
            bio          = info.get('description', '')
            followers    = info.get('channel_follower_count', 0)
            display_name = info.get('uploader') or username
        except Exception:
            pass

    # ── Strategy 3: Parse HTML meta tags (fallback) ─────────────────────────
    if not avatar:
        try:
            resp = requests.get(profile_url, headers=api_headers, cookies=get_requests_cookies(), timeout=15)
            if resp.status_code == 200:
                html = resp.text
                match = re.search(r'<meta property="og:image" content="([^"]+)"', html)
                if match:
                    avatar = match.group(1).replace('&amp;', '&')
                else:
                    # If logged in, og:image is often missing, but the data is embedded in JS
                    match_hd = re.search(r'profile_pic_url_hd":"([^"]+)"', html)
                    if match_hd:
                        avatar = match_hd.group(1).replace(r'\u0026', '&').replace(r'\/', '/')
                    else:
                        match_std = re.search(r'profile_pic_url":"([^"]+)"', html)
                        if match_std:
                            avatar = match_std.group(1).replace(r'\u0026', '&').replace(r'\/', '/')
                
                desc_match = re.search(r'<meta property="og:description" content="([^"]+)"', html)
                if desc_match:
                    desc_content = desc_match.group(1)
                    if 'Followers' in desc_content:
                        f_part = desc_content.split('Followers')[0].strip()
                        followers = f_part
        except Exception:
            pass

    if not avatar:
        return jsonify({
            'error': (
                'Could not retrieve profile picture. '
                'Instagram may require authentication. '
                'Add instagram_cookies.txt and try again.'
            )
        }), 404

    # ── Download the profile pic to temp dir ─────────────────────────────────
    try:
        job_id   = str(uuid.uuid4())
        img_path = os.path.join(DOWNLOAD_DIR, f'{job_id}_profile.jpg')
        r = requests.get(avatar, headers=api_headers, cookies=get_requests_cookies(), timeout=30)
        r.raise_for_status()

        with open(img_path, 'wb') as f:
            f.write(r.content)

        progress_store[job_id] = {
            'status':   'done',
            'percent':  100,
            'filepath': img_path,
            'filename': f'{sanitize_filename(display_name)}_profile.jpg',
        }

        return jsonify({
            'job_id':    job_id,
            'username':  display_name,
            'avatar':    avatar,
            'bio':       bio,
            'followers': followers,
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(port=5000, debug=True)
