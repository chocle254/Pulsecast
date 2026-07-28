/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  
  // Environment variables exposed to the browser
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || '',
  },
  
  // Proxy API calls to the backend — runs server-side, uses server env vars
  async rewrites() {
    // BACKEND_URL is the Railway backend URL set in Vercel's project env vars
    // Falls back to NEXT_PUBLIC_API_URL, then localhost for dev
    const apiUrl = process.env.BACKEND_URL 
      || process.env.NEXT_PUBLIC_API_URL 
      || 'http://127.0.0.1:8000';
    
    return [
      {
        source: '/api/:path*',
        destination: `${apiUrl}/api/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
