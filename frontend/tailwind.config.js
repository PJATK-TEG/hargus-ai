/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      colors: {
        void: {
          950: '#05060D',
          900: '#080A14',
          800: '#0D0F1C',
          700: '#111426',
          600: '#161A30',
          500: '#1C2138',
        },
        ink: {
          700: '#1E2340',
          600: '#252C4A',
          500: '#2E3658',
          400: '#3D4870',
        },
        aurora: {
          purple: '#7C3AED',
          violet: '#8B5CF6',
          indigo: '#6366F1',
          cyan: '#06B6D4',
          teal: '#14B8A6',
          pink: '#EC4899',
          amber: '#F59E0B',
          emerald: '#10B981',
          red: '#EF4444',
        },
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'glass': 'linear-gradient(135deg, rgba(255,255,255,0.06) 0%, rgba(255,255,255,0.02) 100%)',
      },
      boxShadow: {
        'glow-purple': '0 0 20px rgba(124, 58, 237, 0.3)',
        'glow-cyan': '0 0 20px rgba(6, 182, 212, 0.3)',
        'glow-sm': '0 0 10px rgba(124, 58, 237, 0.2)',
        'card': '0 4px 24px rgba(0, 0, 0, 0.4)',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'shimmer': 'shimmer 2s linear infinite',
        'float': 'float 6s ease-in-out infinite',
      },
      keyframes: {
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-6px)' },
        },
      },
    },
  },
  plugins: [],
}
