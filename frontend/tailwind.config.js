/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // Field Paper Palette
        'field-bg': '#EDEEE8',
        'field-surface': '#F6F6F2',
        'field-card': '#FFFFFF',
        'field-elevated': '#F8F9F5',
        'ink': '#232A2E',
        'ink-muted': '#5B6560',
        'ink-light': '#8A948E',
        'border-subtle': '#DDE0D8',
        'border-medium': '#C8CCC0',
        'border-strong': '#A3A89A',
        // NDMA 5-Phase Ramp
        'phase-normal': '#7A9B76',
        'phase-normal-bg': '#EAF2E8',
        'phase-alert': '#C9A24B',
        'phase-alert-bg': '#FDF7E7',
        'phase-alarm': '#B9713A',
        'phase-alarm-bg': '#FBF0E6',
        'phase-emergency': '#9B3B34',
        'phase-emergency-bg': '#FAECEB',
        'phase-recovery': '#4A8B8C',
        'phase-recovery-bg': '#E8F4F4',
      },
      fontFamily: {
        display: ['Space Grotesk', 'system-ui', 'sans-serif'],
        body: ['IBM Plex Sans', 'system-ui', 'sans-serif'],
        mono: ['IBM Plex Mono', 'monospace'],
      },
    },
  },
  plugins: [],
};
