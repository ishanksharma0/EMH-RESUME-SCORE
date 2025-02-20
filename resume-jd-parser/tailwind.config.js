module.exports = {
  content: [
    './src/**/*.{html,js,jsx,ts,tsx}', 
  ],
  darkMode: 'class', // Enable dark mode via a class
  theme: {
    extend: {
      colors: {
        'dark-background': '#2c2c2c',
        'neon-blue': '#00c8ff',
        'neon-green': '#00ff00',
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
