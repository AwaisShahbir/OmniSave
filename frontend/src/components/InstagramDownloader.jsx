import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Search, Loader2, User, Download, ExternalLink,
  AlertCircle, Camera,
} from 'lucide-react';
import toast from 'react-hot-toast';
import axios from 'axios';
import InstagramPreviewCard from './InstagramPreviewCard';

const API = 'http://localhost:5000';

/* ══════════════════════════════════════════════════════════════════
   Profile Picture Card
══════════════════════════════════════════════════════════════════ */
const ProfilePicCard = ({ profile }) => {
  const [dlState, setDlState] = useState('idle');

  const handleDownload = async () => {
    if (!profile.job_id) return;
    setDlState('downloading');
    try {
      const link = document.createElement('a');
      link.href = `${API}/api/get-file/${profile.job_id}`;
      link.setAttribute('download', '');
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      toast.success('Profile picture downloaded! 🎉');
      setDlState('done');
      setTimeout(() => setDlState('idle'), 3000);
    } catch {
      toast.error('Download failed.');
      setDlState('idle');
    }
  };

  return (
    <motion.div
      className="ig-profile-card glass-panel"
      initial={{ opacity: 0, y: 30 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, type: 'spring', bounce: 0.3 }}
    >
      <div className="ig-profile-avatar-wrap">
        {profile.avatar ? (
          <img src={profile.avatar} alt={profile.username} className="ig-profile-avatar" referrerPolicy="no-referrer" />
        ) : (
          <div className="ig-profile-avatar-placeholder">
            <User size={40} color="#888" />
          </div>
        )}
        <div className="ig-profile-ring" />
      </div>

      <div className="ig-profile-info">
        <h3 className="ig-profile-name">@{profile.username}</h3>
        {profile.followers > 0 && (
          <p className="ig-profile-followers">
            {Number(profile.followers).toLocaleString()} followers
          </p>
        )}
        {profile.bio && <p className="ig-profile-bio">{profile.bio}</p>}
      </div>

      <button
        className={`ig-profile-dl-btn action-btn ${dlState === 'done' ? 'done' : ''}`}
        onClick={handleDownload}
        disabled={dlState === 'downloading'}
      >
        <Download size={18} />
        <span>{dlState === 'done' ? 'Downloaded ✓' : 'Download Profile Pic'}</span>
      </button>
    </motion.div>
  );
};


/* ══════════════════════════════════════════════════════════════════
   Main Instagram Downloader
══════════════════════════════════════════════════════════════════ */
const InstagramDownloader = () => {
  const [url, setUrl]           = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult]     = useState(null);  // { type, ... }
  const [profileData, setProfileData] = useState(null);
  const [mode, setMode]         = useState('media'); // 'media' | 'profile'

  const handleFetch = async (e) => {
    e.preventDefault();
    const input = url.trim();
    if (!input) { toast.error('Please paste an Instagram URL or username'); return; }

    setIsLoading(true);
    setResult(null);
    setProfileData(null);

    try {
      if (mode === 'profile') {
        // Profile picture mode
        const { data } = await axios.post(`${API}/api/instagram/profile-pic`, {
          username: input,
        });
        setProfileData(data);
        toast.success('Profile info loaded!');
      } else {
        // Post / reel / story / igtv
        const { data } = await axios.post(`${API}/api/instagram/get-info`, { url: input });
        if (data.type === 'profile') {
          // Redirect to profile pic flow
          const pd = await axios.post(`${API}/api/instagram/profile-pic`, { username: input });
          setProfileData(pd.data);
          toast.success('Profile info loaded!');
        } else {
          setResult(data);
          toast.success(`${data.items?.length || 1} item(s) ready to download!`);
        }
      }
    } catch (err) {
      toast.error(err.response?.data?.error || 'Failed to fetch. Check the URL and try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const exampleUrls = [
    { label: 'Reel',    icon: '🎬', hint: 'instagram.com/reel/…' },
    { label: 'Post',    icon: '🖼️', hint: 'instagram.com/p/…' },
    { label: 'Story',   icon: '⭕', hint: 'instagram.com/stories/…' },
    { label: 'Profile', icon: '👤', hint: 'instagram.com/username' },
  ];

  return (
    <div className="ig-downloader hero-section">
      {/* Hero text */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
      >
        <h1>
          Download{' '}
          <span className="ig-gradient">Instagram</span>{' '}
          Content
        </h1>
        <p>Reels, Posts, Stories, Profile Pictures — all in one place.</p>
      </motion.div>

      {/* Mode toggle */}
      <motion.div
        className="ig-mode-toggle"
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.4, delay: 0.15 }}
      >
        <button
          className={`ig-mode-btn ${mode === 'media' ? 'active' : ''}`}
          onClick={() => setMode('media')}
        >
          <Search size={15} /> Media (Reels / Posts / Stories)
        </button>
        <button
          className={`ig-mode-btn ${mode === 'profile' ? 'active' : ''}`}
          onClick={() => setMode('profile')}
        >
          <Camera size={15} /> Profile Picture
        </button>
      </motion.div>

      {/* URL / username input */}
      <motion.form
        className="search-container glass-panel"
        style={{ marginTop: '1.5rem', padding: '0.5rem', borderRadius: '16px' }}
        onSubmit={handleFetch}
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5, delay: 0.25 }}
      >
        <input
          type="text"
          className="search-input"
          placeholder={
            mode === 'profile'
              ? 'Enter username or profile URL  (e.g. @nasa)'
              : 'Paste Instagram URL — reel, post, or story…'
          }
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          disabled={isLoading}
        />
        <button type="submit" className="action-btn ig-fetch-btn" disabled={isLoading || !url.trim()}>
          {isLoading ? (
            <Loader2 className="spinner" size={20} />
          ) : (
            <>
              <Search size={20} />
              <span>{mode === 'profile' ? 'Fetch Pic' : 'Fetch Media'}</span>
            </>
          )}
        </button>
      </motion.form>

      {/* Example chips */}
      <motion.div
        className="ig-chips"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.4 }}
      >
        {exampleUrls.map((ex) => (
          <span key={ex.label} className="ig-chip">
            {ex.icon} {ex.label} <code>{ex.hint}</code>
          </span>
        ))}
      </motion.div>

      {/* Tip banner */}
      <motion.div
        className="ig-tip-banner glass-panel"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.5 }}
      >
        <AlertCircle size={15} style={{ flexShrink: 0, color: '#f59e0b' }} />
        <span>
          <strong>Instagram tips:</strong> Keep <strong>Chrome open and logged into Instagram</strong> — 
          the backend uses your browser cookies automatically. Private accounts &amp; stories always 
          require login. If you get a rate-limit error, wait a few minutes and try again.
        </span>
      </motion.div>


      {/* Results */}
      <AnimatePresence mode="wait">
        {profileData && (
          <ProfilePicCard key="profile" profile={profileData} />
        )}
        {result && !profileData && (
          <motion.div
            key="result"
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.5, type: 'spring', bounce: 0.3 }}
            style={{ width: '100%', display: 'flex', justifyContent: 'center' }}
          >
            <InstagramPreviewCard info={result} />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default InstagramDownloader;
