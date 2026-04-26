# OmniSave (NexusFetch)
A premium, full-stack video downloader for YouTube built with React, Vite, and Python (Flask + yt-dlp).

## Features
- **High-Quality Downloads**: Supports 1080p, 720p, 480p, 360p, and MP3 audio extraction.
- **Premium UI/UX**: Dark mode, glassmorphism, and smooth Framer Motion animations.
- **Robust Backend**: Powered by `yt-dlp` for reliable extraction and downloading.

## Prerequisites
- **Node.js** (v16+)
- **Python** (3.8+)
- **FFmpeg**: Required by `yt-dlp` to merge video and audio for high-quality downloads (1080p) and MP3 conversion.
  - *Windows*: Download from [gyan.dev](https://www.gyan.dev/ffmpeg/builds/) or use `winget install ffmpeg`. Make sure it's added to your system PATH.
  - *Mac*: `brew install ffmpeg`
  - *Linux*: `sudo apt install ffmpeg`

## Setup Instructions

### 1. Backend Setup
The backend is built with Python and Flask.

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create a virtual environment (optional but recommended):
   ```bash
   python -m venv venv
   # Activate it:
   # Windows: venv\Scripts\activate
   # Mac/Linux: source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the Flask server:
   ```bash
   python app.py
   ```
   *The backend will run on `http://localhost:5000`*

### 2. Frontend Setup
The frontend is a React application built with Vite.

1. Open a new terminal and navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Run the development server:
   ```bash
   npm run dev
   ```
   *The frontend will run on `http://localhost:5173` (or similar, check terminal output).*

## Future Roadmap
- Support for Instagram Reels/Posts downloading.
- Support for TikTok (without watermark) downloading.
- Download progress tracking.
