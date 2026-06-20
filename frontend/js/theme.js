/* Shared Tailwind theme (brand palette). Load right after the Tailwind CDN:
     <script src="https://cdn.tailwindcss.com"></script>
     <script src="/js/theme.js"></script> */
tailwind.config = {
  theme: {
    extend: {
      colors: {
        green: { DEFAULT: '#005F02', dark: '#004a01', light: '#e6f0e6' },
        gold:  { DEFAULT: '#C0B87A', light: '#f7f4e8' },
        cream: '#F2E3BB',
      },
    },
  },
};
