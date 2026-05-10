import React, { useState, useRef } from 'react';
import {
  Download, Loader2, User, Film, Image as ImageIcon,
  Pencil, Check, X, Play,
} from 'lucide-react';

import toast from 'react-hot-toast';
import axios from 'axios';

const API = 'http://localhost:5000';

const formatDuration = (seconds) => {
  if (!seconds) return '';
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, '0')}`;
};

/* ── Single media item row inside a carousel/multi post ── */
const MediaItem = ({ item, postUrl }) => {
  const [dlState, setDlState] = useState('idle');
  const [progress, setProgress] = useState(0);
  const [speed, setSpeed]       = useState('');
  const [eta, setEta]           = useState('');
  const [isEditingName, setIsEditingName]   = useState(false);
  const [customFilename, setCustomFilename] = useState(
    `instagram_${item.is_video ? 'video' : 'photo'}_${item.index + 1}`
  );
  const [editDraft, setEditDraft] = useState(customFilename);
  const nameInputRef = useRef(null);
  const pollRef      = useRef(null);

  const stopPolling = () => {
    if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
  };

  const confirmRename = () => {
    const t = editDraft.trim();
    if (t) setCustomFilename(t);
    else setEditDraft(customFilename);
    setIsEditingName(false);
  };
  const cancelRename = () => { setEditDraft(customFilename); setIsEditingName(false); };

  const handleDownload = async () => {
    if (dlState === 'downloading' || dlState === 'processing') return;
    setDlState('downloading');
    setProgress(0); setSpeed(''); setEta('');

    try {
      const { data } = await axios.post(`${API}/api/instagram/download`, {
        url:        item.webpage_url || postUrl,
        media_type: item.is_video ? 'video' : 'image',
        filename:   customFilename,
        direct_url: item.direct_url || '',   // CDN URL for photo-only posts
      });

      const { job_id } = data;
      pollRef.current = setInterval(async () => {
        try {
          const { data: prog } = await axios.get(`${API}/api/progress/${job_id}`);
          setProgress(prog.percent ?? 0);
          setSpeed(prog.speed ?? '');
          setEta(prog.eta ?? '');

          if (prog.status === 'processing') setDlState('processing');

          if (prog.status === 'done') {
            stopPolling();
            setProgress(100);
            setDlState('done');
            const link = document.createElement('a');
            link.href = `${API}/api/get-file/${job_id}`;
            link.setAttribute('download', '');
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            toast.success('Downloaded! 🎉');
            setTimeout(() => setDlState('idle'), 3000);
          }

          if (prog.status === 'error') {
            stopPolling();
            setDlState('error');
            toast.error(prog.error || 'Download failed.');
            setTimeout(() => setDlState('idle'), 3000);
          }
        } catch {
          stopPolling(); setDlState('error');
          toast.error('Lost connection to server.');
          setTimeout(() => setDlState('idle'), 3000);
        }
      }, 600);
    } catch (err) {
      setDlState('error');
      toast.error(err.response?.data?.error || 'Failed to start download.');
      setTimeout(() => setDlState('idle'), 3000);
    }
  };

  const isActive = dlState === 'downloading' || dlState === 'processing';

  const btnLabel = () => {
    if (dlState === 'downloading') return `${progress.toFixed(0)}%`;
    if (dlState === 'processing')  return 'Processing…';
    if (dlState === 'done')        return 'Done ✓';
    if (dlState === 'error')       return 'Retry';
    return item.is_video ? 'Download Video' : 'Download Image';
  };

  return (
    <div className="ig-media-item">
      {/* Thumbnail */}
      <div className="ig-item-thumb">
        {item.thumbnail
          ? <img src={item.thumbnail} alt={item.title} referrerPolicy="no-referrer" />
          : <div className="ig-thumb-placeholder">
              {item.is_video ? <Film size={28} color="#a0a0a0" /> : <ImageIcon size={28} color="#a0a0a0" />}
            </div>
        }
        {item.is_video && (
          <div className="ig-play-badge"><Play size={12} fill="white" /></div>
        )}
        {item.duration > 0 && (
          <span className="ig-item-duration">{formatDuration(item.duration)}</span>
        )}
      </div>

      {/* Info + controls */}
      <div className="ig-item-body">
        <p className="ig-item-title">{item.title || `Media ${item.index + 1}`}</p>

        {/* Filename editor */}
        <div className="ig-filename-editor">
          {isEditingName ? (
            <div className="filename-input-row">
              <input
                ref={nameInputRef}
                className="filename-input"
                value={editDraft}
                autoFocus
                onChange={(e) => setEditDraft(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') confirmRename();
                  if (e.key === 'Escape') cancelRename();
                }}
                maxLength={100}
              />
              <button className="icon-btn confirm" onClick={confirmRename}><Check size={13} /></button>
              <button className="icon-btn cancel"  onClick={cancelRename}><X size={13} /></button>
            </div>
          ) : (
            <div className="filename-display" onClick={() => { setEditDraft(customFilename); setIsEditingName(true); }}>
              <span className="filename-text">{customFilename}</span>
              <Pencil size={11} className="pencil-icon" />
            </div>
          )}
        </div>

        {/* Progress */}
        {(isActive || dlState === 'done') && (
          <div className="ig-progress">
            <div className="progress-track" style={{ height: '5px' }}>
              <div
                className={`progress-fill ${dlState === 'done' ? 'done' : ''}`}
                style={{ width: `${progress}%` }}
              />
            </div>
            <div className="progress-meta" style={{ fontSize: '0.7rem' }}>
              <span className="progress-pct" style={{ fontSize: '0.7rem' }}>{progress.toFixed(0)}%</span>
              {speed && <span className="progress-speed">{speed}</span>}
              {eta   && <span className="progress-eta">ETA {eta}</span>}
            </div>
          </div>
        )}

        {/* Download btn */}
        <button
          className={`ig-item-dl-btn ${dlState === 'done' ? 'done' : ''} ${dlState === 'error' ? 'error' : ''}`}
          onClick={handleDownload}
          disabled={isActive}
        >
          {isActive
            ? <><Loader2 className="spinner" size={14} /><span>{btnLabel()}</span></>
            : <><Download size={14} /><span>{btnLabel()}</span></>
          }
        </button>
      </div>
    </div>
  );
};


/* ══════════════════════════════════════════════════════════════════
   Main Instagram Preview Card
══════════════════════════════════════════════════════════════════ */
const InstagramPreviewCard = ({ info }) => {
  const typeLabels = {
    reel:    { label: 'Reel',    color: '#e040fb' },
    story:   { label: 'Story',   color: '#ff6b35' },
    post:    { label: 'Post',    color: '#00b4d8' },
    igtv:    { label: 'IGTV',   color: '#7b2cbf' },
    profile: { label: 'Profile', color: '#43aa8b' },
    unknown: { label: 'Media',   color: '#888' },
  };

  const badge = typeLabels[info.type] || typeLabels.unknown;

  return (
    <div className="ig-preview-card glass-panel">
      {/* Card Header */}
      <div className="ig-card-header">
        <div className="ig-card-meta">
          <span className="ig-type-badge" style={{ background: badge.color + '22', color: badge.color, border: `1px solid ${badge.color}44` }}>
            {badge.label}
          </span>
          <div className="ig-uploader">
            <User size={14} />
            <span>{info.uploader || 'Instagram'}</span>
          </div>
        </div>
        <p className="ig-card-title">{info.title}</p>
      </div>

      {/* Media Items */}
      {info.items && info.items.length > 0 ? (
        <div className="ig-items-list">
          {info.items.map((item) => (
            <MediaItem key={item.index} item={item} postUrl={info.url} />
          ))}
        </div>
      ) : (
        <p className="ig-no-items">No downloadable items found. The content may be private or require login cookies.</p>
      )}
    </div>
  );
};

export default InstagramPreviewCard;
