/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50:  '#eff6ff', 100: '#dbeafe', 200: '#bfdbfe', 300: '#93c5fd',
          400: '#60a5fa', 500: '#3b82f6', 600: '#2563eb', 700: '#1d4ed8',
          800: '#1e40af', 900: '#1e3a8a',
        },
        success: { 50: '#f0fdf4', 500: '#22c55e', 600: '#16a34a', 700: '#15803d' },
        warning: { 50: '#fffbeb', 500: '#f59e0b', 600: '#d97706', 700: '#b45309' },
        danger:  { 50: '#fef2f2', 500: '#ef4444', 600: '#dc2626', 700: '#b91c1c' },
        ink: {
          50: '#f8fafc', 100: '#f1f5f9', 200: '#e2e8f0', 300: '#cbd5e1',
          400: '#94a3b8', 500: '#64748b', 600: '#475569', 700: '#334155',
          800: '#1e293b', 900: '#0f172a',
        },
      },
      fontSize: {
        'display-lg': ['3.5rem', { lineHeight: '1', fontWeight: '700', letterSpacing: '-0.02em' }],
        'display':    ['2.5rem', { lineHeight: '1.1', fontWeight: '700', letterSpacing: '-0.01em' }],
        'h1':         ['1.875rem', { lineHeight: '1.3', fontWeight: '700' }],
        'h2':         ['1.5rem',   { lineHeight: '1.3', fontWeight: '600' }],
        'h3':         ['1.25rem',  { lineHeight: '1.4', fontWeight: '600' }],
        'body-lg':    ['1.125rem', { lineHeight: '1.6' }],
        'body':       ['0.9375rem', { lineHeight: '1.6' }],
        'body-sm':    ['0.875rem', { lineHeight: '1.5' }],
        'caption':    ['0.75rem',  { lineHeight: '1.4' }],
      },
      fontFamily: {
        sans: [
          '"Noto Sans TC"', '"PingFang TC"', '"Microsoft JhengHei"',
          '"Microsoft YaHei"', 'system-ui', '-apple-system', 'Segoe UI',
          'Helvetica', 'Arial', 'sans-serif',
        ],
        mono: ['"JetBrains Mono"', '"Fira Code"', 'Consolas', 'monospace'],
      },
      borderRadius: { 'card': '1rem', 'input': '0.625rem' },
      boxShadow: {
        'card':       '0 1px 3px 0 rgb(0 0 0 / 0.06), 0 1px 2px -1px rgb(0 0 0 / 0.04)',
        'card-hover': '0 4px 12px -2px rgb(0 0 0 / 0.08), 0 2px 6px -2px rgb(0 0 0 / 0.04)',
        'pop':        '0 12px 32px -8px rgb(0 0 0 / 0.16)',
      },
      animation: {
        'fade-in':  'fade-in 0.3s ease-out',
        'slide-up': 'slide-up 0.3s ease-out',
        'shimmer':  'shimmer 1.8s linear infinite',
      },
      keyframes: {
        'fade-in':  { '0%': { opacity: '0' }, '100%': { opacity: '1' } },
        'slide-up': { '0%': { opacity: '0', transform: 'translateY(8px)' }, '100%': { opacity: '1', transform: 'translateY(0)' } },
        'shimmer':  { '0%': { backgroundPosition: '-200% 0' }, '100%': { backgroundPosition: '200% 0' } },
      },
    },
  },
  plugins: [],
}
