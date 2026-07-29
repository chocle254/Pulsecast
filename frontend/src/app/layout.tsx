import React from 'react';
import Sidebar from '@/components/Sidebar';
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
        <div className="flex min-h-screen bg-[var(--bg-app)] text-[var(--ink)]">
          <Sidebar />
          <div className="flex-1 flex flex-col min-w-0">
            <main className="flex-1 pb-16">{children}</main>
            <footer className="bg-[var(--bg-surface)] border-t border-[var(--border-medium)] py-6 mt-12">
              <div className="container flex flex-col md:flex-row items-center justify-between text-xs text-[var(--ink-muted)] font-mono">
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
        </div>
      </body>
    </html>
  );
}
