/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Figtree', 'sans-serif'],
      },
      colors: {
        page: 'var(--color-bg-page)',
        sidebar: 'var(--color-bg-sidebar)',
        card: 'var(--color-bg-card)',
        'card-hover': 'var(--color-bg-card-hover)',
        input: 'var(--color-bg-input)',
        header: 'var(--color-bg-header)',
        border: 'var(--color-border)',
        'border-focus': 'var(--color-border-focus)',
        primary: {
          DEFAULT: 'var(--color-primary)',
          hover: 'var(--color-primary-hover)',
        },
        teal: {
          DEFAULT: 'var(--color-secondary-teal)',
          container: 'var(--color-secondary-teal-container)',
        },
        error: {
          DEFAULT: 'var(--color-error)',
          container: 'var(--color-error-container)',
        },
        warning: {
          DEFAULT: 'var(--color-warning)',
          container: 'var(--color-warning-container)',
        },
        'text-primary': 'var(--color-text-primary)',
        'text-secondary': 'var(--color-text-secondary)',
        'text-muted': 'var(--color-text-muted)',
      },
      boxShadow: {
        card: '0 1px 3px rgba(0,0,0,0.02), 0 1px 2px rgba(0,0,0,0.04)',
      },
      keyframes: {
        shimmer: {
          '0%': { backgroundPosition: '200% 0' },
          '100%': { backgroundPosition: '-200% 0' },
        },
      },
      animation: {
        shimmer: 'shimmer 1.5s infinite',
      },
    },
  },
  plugins: [],
};
