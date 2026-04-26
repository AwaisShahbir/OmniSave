import React from 'react';
import { Toaster } from 'react-hot-toast';
import Downloader from './components/Downloader';
import { DownloadCloud } from 'lucide-react';

function App() {
  return (
    <>
      <Toaster position="top-center" toastOptions={{
        style: {
          background: '#111',
          color: '#fff',
          border: '1px solid rgba(255,255,255,0.1)'
        }
      }} />
      
      <header className="header">
        <div className="logo">
          <DownloadCloud size={28} color="#7b2cbf" />
          <span>Omni<span className="title-gradient">Save</span></span>
        </div>
      </header>

      <main className="container">
        <Downloader />
      </main>
    </>
  );
}

export default App;
