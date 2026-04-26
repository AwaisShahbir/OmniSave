import React, { useState, useEffect, useRef } from 'react';
import { Download, Loader2, Clock, User, Pencil, Check, X } from 'lucide-react';
import toast from 'react-hot-toast';
import axios from 'axios';

const API = 'http://localhost:5000';

const formatDuration = (seconds) => {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  if (h > 0) return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  return `${m}:${s.toString().padStart(2, '0')}`;
};

const PreviewCard = ({ video }) => {
  const [selectedQuality, setSelectedQuality] = useState(video.options?.[0]?.id || '720p');
  const [downloadState, setDownloadState] = useState('idle'); // idle | downloading | processing | done | error
  const [progress, setProgress] = useState(0);
  const [speed, setSpeed]       = useState('');
  const [eta, setEta]           = useState('');

  // ── Filename editing ──────────────────────────────────────────────────────
  const [isEditingName, setIsEditingName] = useState(false);
  const [customFilename, setCustomFilename] = useState(
    video.title.replace(/[^\w\s.-]/g, '').trim()
  );
  const [editDraft, setEditDraft] = useState(customFilename);
  const nameInputRef = useRef(null);

  useEffect(() => {
    if (isEditingName && nameInputRef.current) {
      nameInputRef.current.focus();
      nameInputRef.current.select();
    }
  }, [isEditingName]);

  const confirmRename = () => {
    const trimmed = editDraft.trim();
    if (trimmed) setCustomFilename(trimmed);
    else setEditDraft(customFilename); // revert if empty
    setIsEditingName(false);
  };

  const cancelRename = () => {
    setEditDraft(customFilename);
    setIsEditingName(false);
  };

  // ── Download flow ─────────────────────────────────────────────────────────
  const pollRef = useRef(null);

  const stopPolling = () => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  };

  const handleDownload = async () => {
    if (downloadState === 'downloading' || downloadState === 'processing') return;

    setDownloadState('downloading');
    setProgress(0);
    setSpeed('');
    setEta('');

    try {
      // 1. Kick off the download and get a job_id
      const { data } = await axios.post(`${API}/api/download`, {
        url:      video.originalUrl,
        quality:  selectedQuality,
        filename: customFilename,
      });

      const { job_id } = data;

      // 2. Poll progress every 600 ms
      pollRef.current = setInterval(async () => {
        try {
          const { data: prog } = await axios.get(`${API}/api/progress/${job_id}`);

          setProgress(prog.percent ?? 0);
          setSpeed(prog.speed  ?? '');
          setEta(prog.eta    ?? '');

          if (prog.status === 'processing') {
            setDownloadState('processing');
          }

          if (prog.status === 'done') {
            stopPolling();
            setProgress(100);
            setDownloadState('done');

            // 3. Trigger the actual file download
            const link = document.createElement('a');
            link.href = `${API}/api/get-file/${job_id}`;
            link.setAttribute('download', '');
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);

            toast.success('Download complete! 🎉');
            setTimeout(() => setDownloadState('idle'), 3000);
          }

          if (prog.status === 'error') {
            stopPolling();
            setDownloadState('error');
            toast.error(prog.error || 'Download failed. Please try again.');
            setTimeout(() => setDownloadState('idle'), 3000);
          }
        } catch {
          stopPolling();
          setDownloadState('error');
          toast.error('Lost connection to server.');
          setTimeout(() => setDownloadState('idle'), 3000);
        }
      }, 600);

    } catch (err) {
      setDownloadState('error');
      toast.error(err.response?.data?.error || 'Failed to start download.');
      setTimeout(() => setDownloadState('idle'), 3000);
    }
  };

  const isActive = downloadState === 'downloading' || downloadState === 'processing';

  // ── Label helpers ─────────────────────────────────────────────────────────
  const statusLabel = () => {
    if (downloadState === 'downloading') return `Downloading… ${progress.toFixed(0)}%`;
    if (downloadState === 'processing')  return 'Merging audio & video…';
    if (downloadState === 'done')        return 'Done! ✓';
    if (downloadState === 'error')       return 'Error — try again';
    return 'Download Now';
  };

  return (
    <div className="preview-card glass-panel">
      {/* Thumbnail */}
      <div className="preview-image-container">
        <img src={video.thumbnail} alt={video.title} className="preview-image" />
        <div className="preview-duration">
          <Clock size={12} style={{ display: 'inline', marginRight: '4px', verticalAlign: 'middle' }} />
          {formatDuration(video.duration)}
        </div>
      </div>

      <div className="preview-content">
        {/* Title */}
        <h3 className="preview-title" title={video.title}>{video.title}</h3>
        <div className="preview-channel">
          <User size={16} />
          <span>{video.channel}</span>
        </div>

        {/* ── Filename editor ─────────────────────────────────────────── */}
        <div className="filename-editor">
          <span className="filename-label">Save as</span>
          {isEditingName ? (
            <div className="filename-input-row">
              <input
                ref={nameInputRef}
                className="filename-input"
                value={editDraft}
                onChange={(e) => setEditDraft(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') confirmRename();
                  if (e.key === 'Escape') cancelRename();
                }}
                maxLength={120}
              />
              <button className="icon-btn confirm" onClick={confirmRename} title="Confirm"><Check size={15} /></button>
              <button className="icon-btn cancel"  onClick={cancelRename}  title="Cancel"><X    size={15} /></button>
            </div>
          ) : (
            <div className="filename-display" onClick={() => { setEditDraft(customFilename); setIsEditingName(true); }}>
              <span className="filename-text">{customFilename}</span>
              <Pencil size={13} className="pencil-icon" />
            </div>
          )}
        </div>

        {/* ── Progress bar ────────────────────────────────────────────── */}
        {isActive || downloadState === 'done' ? (
          <div className="progress-wrapper">
            <div className="progress-track">
              <div
                className={`progress-fill ${downloadState === 'done' ? 'done' : ''}`}
                style={{ width: `${progress}%` }}
              />
            </div>
            <div className="progress-meta">
              <span className="progress-pct">{progress.toFixed(0)}%</span>
              {speed && <span className="progress-speed">{speed}</span>}
              {eta   && <span className="progress-eta">ETA {eta}</span>}
            </div>
          </div>
        ) : null}

        {/* ── Controls ────────────────────────────────────────────────── */}
        <div className="controls-group">
          <select
            className="quality-select"
            value={selectedQuality}
            onChange={(e) => setSelectedQuality(e.target.value)}
            disabled={isActive}
          >
            {video.options.map(opt => (
              <option key={opt.id} value={opt.id}>{opt.label}</option>
            ))}
          </select>

          <button
            className={`action-btn download-btn ${downloadState === 'done' ? 'done' : ''} ${downloadState === 'error' ? 'error' : ''}`}
            onClick={handleDownload}
            disabled={isActive}
          >
            {isActive ? (
              <>
                <Loader2 className="spinner" size={20} />
                <span>{statusLabel()}</span>
              </>
            ) : (
              <>
                <Download size={20} />
                <span>{statusLabel()}</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default PreviewCard;
