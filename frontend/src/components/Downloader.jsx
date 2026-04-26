import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, Loader2 } from 'lucide-react';
import toast from 'react-hot-toast';
import axios from 'axios';
import PreviewCard from './PreviewCard';

const Downloader = () => {
  const [url, setUrl] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [videoInfo, setVideoInfo] = useState(null);

  const handleGetInfo = async (e) => {
    e.preventDefault();
    if (!url) {
      toast.error('Please enter a valid URL');
      return;
    }

    try {
      setIsLoading(true);
      setVideoInfo(null);
      
      const response = await axios.post('http://localhost:5000/api/get-info', { url });
      setVideoInfo({ ...response.data, originalUrl: url });
      toast.success('Video info retrieved successfully!');
      
    } catch (error) {
      console.error(error);
      toast.error(error.response?.data?.error || 'Failed to fetch video info. Make sure the URL is valid.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="hero-section">
      <motion.div 
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
      >
        <h1>Download The <span className="title-gradient">Future</span></h1>
        <p>Premium downloads for YouTube videos and audio. Crisp quality, seamless experience.</p>
      </motion.div>

      <motion.form 
        className="search-container glass-panel"
        style={{ marginTop: '2.5rem', padding: '0.5rem', borderRadius: '16px' }}
        onSubmit={handleGetInfo}
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5, delay: 0.2 }}
      >
        <input 
          type="text" 
          className="search-input" 
          placeholder="Paste video URL here..." 
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          disabled={isLoading}
        />
        <button type="submit" className="action-btn" disabled={isLoading || !url}>
          {isLoading ? (
            <Loader2 className="spinner" size={20} />
          ) : (
            <>
              <Search size={20} />
              <span>Get Info</span>
            </>
          )}
        </button>
      </motion.form>

      <AnimatePresence>
        {videoInfo && (
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -30 }}
            transition={{ duration: 0.5, type: 'spring', bounce: 0.4 }}
            style={{ display: 'flex', justifyContent: 'center' }}
          >
            <PreviewCard video={videoInfo} />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default Downloader;
