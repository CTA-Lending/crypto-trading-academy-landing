/** Tailwind config for pre-compiled per-page CSS (course.html).
 *  Migrated from the former inline `tailwind.config` script in course.html.
 *  Build: npx -y tailwindcss@3 -c tailwind.config.js -o assets/tw-course.css --minify
 */
module.exports = {
  content: ['./course.html'],
  // Classes added dynamically by JS (classList.add/toggle) — content scan
  // already sees them in course.html, but safelist to be bulletproof.
  safelist: ['hidden', 'visible'],
  theme: {
    extend: {
      colors: {
        void:  '#05080F',
        deep:  '#0A111E',
        panel: '#0D1626',
        line:  '#1B2A44',
        gold:  '#E5B84B',
        'gold-soft': '#F2D38B',
        ice:   '#8FC7E8',
      },
      fontFamily: {
        serif: ['"Noto Serif TC"', 'serif'],
        sans:  ['"Noto Sans TC"', 'sans-serif'],
        mono:  ['"JetBrains Mono"', 'monospace'],
      },
      animation: {
        'fade-in-up': 'fade-in-up 0.7s ease-out forwards',
        'orbit-spin': 'orbit-spin 40s linear infinite',
        'pulse-soft': 'pulse-soft 4s ease-in-out infinite',
      },
      keyframes: {
        'fade-in-up': {
          '0%': { opacity: '0', transform: 'translateY(24px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'orbit-spin': {
          '0%': { transform: 'rotate(0deg)' },
          '100%': { transform: 'rotate(360deg)' },
        },
        'pulse-soft': {
          '0%, 100%': { opacity: '0.5' },
          '50%': { opacity: '1' },
        },
      },
    },
  },
};
