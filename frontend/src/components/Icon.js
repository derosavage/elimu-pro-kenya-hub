const P = {
  home: 'M3 11l9-8 9 8v9a1 1 0 01-1 1h-5v-6H9v6H4a1 1 0 01-1-1z',
  user: 'M12 12a4 4 0 100-8 4 4 0 000 8zm-8 9a8 8 0 0116 0',
  chart: 'M4 20V10m6 10V4m6 16v-7m4 7H2',
  clock: 'M12 7v5l3 2M12 21a9 9 0 100-18 9 9 0 000 18z',
  wallet: 'M3 7h16a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2zm0 0V6a2 2 0 012-2h11M16 14h2',
  bell: 'M6 9a6 6 0 0112 0c0 6 2 7 2 7H4s2-1 2-7zm4 10a2 2 0 004 0',
  gear: 'M12 15a3 3 0 100-6 3 3 0 000 6zm7-3l2 1-2 3-2-.5-1.5 1V19h-3l-.5-2-2-.8-2 1-2-3 1.5-1.5v-2L5 8.5l2-3 2 1 1.5-1L11 3h3l.5 2 2 .8 2-1 2 3z',
  file: 'M7 3h7l5 5v13H7zM14 3v5h5M10 13h6M10 17h6',
  users: 'M9 11a3.5 3.5 0 100-7 3.5 3.5 0 000 7zm-7 9a7 7 0 0114 0m1-15a3.5 3.5 0 010 6m2 9a7 7 0 00-3-5.7',
  book: 'M4 5a2 2 0 012-2h13v16H6a2 2 0 00-2 2zM4 19V5m4 0v10',
  menu: 'M4 6h16M4 12h16M4 18h16', logout: 'M15 4h4a1 1 0 011 1v14a1 1 0 01-1 1h-4M10 16l-4-4 4-4M6 12h10',
  school: 'M3 10l9-6 9 6M5 10v9h14v-9M9 19v-5h6v5', plus: 'M12 5v14M5 12h14', print: 'M7 9V3h10v6M7 17H4v-7h16v7h-3M7 14h10v7H7z',
};
export default function Icon({ name, size = 20 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"
         strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={P[name]} /></svg>
  );
}
