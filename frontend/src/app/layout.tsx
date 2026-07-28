import React from 'react';
import Navbar from '@/components/Navbar';
import '@/styles/globals.css';

export const metadata = {
  title: 'Pulsecast — Kenya County Drought Phase Forecasting',
  description: 'AI-powered platform forecasting drought phase transitions in Kenya counties weeks before they happen, using NDMA published data and thresholds.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      </head>
      <body>
        <div className="min-h-screen flex flex-col bg-[#EDEEE8] text-[#232A2E]">
          <Navbar />
          <main className="flex-1 pb-16">{children}</main>
          <footer className="bg-[#F6F6F2] border-t border-[#C8CCC0] py-6 mt-12">
            <div className="container flex flex-col md:flex-row items-center justify-between text-xs text-[#5B6560] font-mono">
              <div>
                Pulsecast v1.0 · Proof-of-concept based on NDMA published drought bulletins & Barrett et al. (2020) methodology
              </div>
              <div className="mt-2 md:mt-0 flex gap-4">
                <span>Data: NDMA KnowledgeWeb</span>
                <span>Model: AR(2) + LLM Translation</span>
              </div>
            </div>
          </footer>
        </div>
      </body>
    </html>
  );
}
