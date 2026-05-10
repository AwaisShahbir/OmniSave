import React, { useState } from 'react';
import { Toaster } from 'react-hot-toast';
import { DownloadCloud } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import Downloader from './components/Downloader';
import InstagramDownloader from './components/InstagramDownloader';

/* ── Brand icon SVGs (lucide removed these) ── */
const YtIcon = ({ size = 20 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor">
    <path d="M21.8 8s-.2-1.4-.8-2c-.8-.8-1.6-.8-2-.9C16.4 5 12 5 12 5s-4.4 0-7 .1c-.4.1-1.2.1-2 .9-.6.6-.8 2-.8 2S2 9.6 2 11.2v1.5c0 1.6.2 3.2.2 3.2s.2 1.4.8 2c.8.8 1.8.8 2.3.8C6.8 19 12 19 12 19s4.4 0 7-.1c.4-.1 1.2-.1 2-.9.6-.6.8-2 .8-2s.2-1.6.2-3.2v-1.5C22 9.6 21.8 8 21.8 8zM10 14.5v-5l5.5 2.5L10 14.5z"/>
  </svg>
);

const IgIcon = ({ size = 20 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="2" y="2" width="20" height="20" rx="5" ry="5"/>
    <circle cx="12" cy="12" r="4"/>
    <circle cx="17.5" cy="6.5" r="1" fill="currentColor" stroke="none"/>
  </svg>
);

const PLATFORMS = [
  { id: 'youtube',   label: 'YouTube',   Icon: YtIcon, color: '#ff4444' },
  { id: 'instagram', label: 'Instagram', Icon: IgIcon, color: '#e040fb' },
];

function App() {
  const [activePlatform, setActivePlatform] = useState('youtube');

  return (
    <>
      <Toaster
        position="top-center"
        toastOptions={{
          style: {
            background: '#111',
            color: '#fff',
            border: '1px solid rgba(255,255,255,0.1)',
          },
        }}
      />

      {/* ── Header ─────────────────────────────────────────── */}
      <header className="header">
        <div className="logo">
          <DownloadCloud size={28} color="#7b2cbf" />
          <span>Omni<span className="title-gradient">Save</span></span>
        </div>

        {/* Platform Tabs */}
        <nav className="platform-tabs">
          {PLATFORMS.map(({ id, label, Icon, color }) => (
            <button
              key={id}
              id={`tab-${id}`}
              className={`platform-tab ${activePlatform === id ? 'active' : ''}`}
              onClick={() => setActivePlatform(id)}
              style={{ '--tab-color': color }}
            >
              <Icon size={16} />
              <span>{label}</span>
              {activePlatform === id && (
                <motion.div
                  className="tab-indicator"
                  layoutId="tab-indicator"
                  style={{ background: color }}
                  transition={{ type: 'spring', stiffness: 400, damping: 30 }}
                />
              )}
            </button>
          ))}
        </nav>
      </header>

      {/* ── Main Content ────────────────────────────────────── */}
      <main className="container" style={{ paddingTop: '5rem' }}>
        <AnimatePresence mode="wait">
          {activePlatform === 'youtube' && (
            <motion.div
              key="youtube"
              style={{ width: '100%' }}
              initial={{ opacity: 0, x: -30 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 30 }}
              transition={{ duration: 0.3 }}
            >
              <Downloader />
            </motion.div>
          )}
          {activePlatform === 'instagram' && (
            <motion.div
              key="instagram"
              style={{ width: '100%' }}
              initial={{ opacity: 0, x: 30 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -30 }}
              transition={{ duration: 0.3 }}
            >
              <InstagramDownloader />
            </motion.div>
          )}
        </AnimatePresence>
      </main>
    </>
  );
}

export default App;
