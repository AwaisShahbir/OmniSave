import React, { useState } from 'react';
import { Download, Loader2, Clock, User } from 'lucide-react';
import toast from 'react-hot-toast';
import axios from 'axios';

const formatDuration = (seconds) => {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  if (h > 0) return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  return `${m}:${s.toString().padStart(2, '0')}`;
};

const PreviewCard = ({ video }) => {
  const [selectedQuality, setSelectedQuality] = useState(video.options?.[0]?.id || '720p');
  const [isDownloading, setIsDownloading] = useState(false);

  const handleDownload = async () => {
    try {
      setIsDownloading(true);
      toast.loading('Starting download...', { id: 'download' });

      const response = await axios.post('http://localhost:5000/api/download', {
        url: video.originalUrl,
        quality: selectedQuality
      }, {
        responseType: 'blob', // Important for receiving binary data
      });

      // Create a blob link to download
      const blob = new Blob([response.data]);
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;

      // Try to extract filename from content-disposition header if available
      let filename = 'download';
      const disposition = response.headers['content-disposition'];
      if (disposition && disposition.indexOf('attachment') !== -1) {
        const filenameRegex = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/;
        const matches = filenameRegex.exec(disposition);
        if (matches != null && matches[1]) { 
          filename = matches[1].replace(/['"]/g, '');
        }
      } else {
         // Fallback filename
         const safeTitle = video.title.replace(/[^a-z0-9]/gi, '_').toLowerCase();
         const ext = selectedQuality === 'mp3' ? '.mp3' : '.mp4';
         filename = `${safeTitle}${ext}`;
      }

      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);
      window.URL.revokeObjectURL(downloadUrl);

      toast.success('Download completed!', { id: 'download' });
    } catch (error) {
      console.error(error);
      toast.error('Failed to download. Please try again.', { id: 'download' });
    } finally {
      setIsDownloading(false);
    }
  };

  return (
    <div className="preview-card glass-panel">
      <div className="preview-image-container">
        <img src={video.thumbnail} alt={video.title} className="preview-image" />
        <div className="preview-duration">
          <Clock size={12} style={{ display: 'inline', marginRight: '4px', verticalAlign: 'middle' }} />
          {formatDuration(video.duration)}
        </div>
      </div>
      
      <div className="preview-content">
        <div>
          <h3 className="preview-title" title={video.title}>{video.title}</h3>
          <div className="preview-channel">
            <User size={16} />
            <span>{video.channel}</span>
          </div>
        </div>

        <div className="controls-group">
          <select 
            className="quality-select"
            value={selectedQuality}
            onChange={(e) => setSelectedQuality(e.target.value)}
            disabled={isDownloading}
          >
            {video.options.map(opt => (
              <option key={opt.id} value={opt.id}>
                {opt.label}
              </option>
            ))}
          </select>

          <button 
            className="action-btn download-btn" 
            onClick={handleDownload}
            disabled={isDownloading}
          >
            {isDownloading ? (
              <>
                <Loader2 className="spinner" size={20} />
                <span>Processing...</span>
              </>
            ) : (
              <>
                <Download size={20} />
                <span>Download Now</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default PreviewCard;
