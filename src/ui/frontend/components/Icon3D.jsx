import { useId } from "react";

// Colourful "clay" tiles: gradient body, extruded base, top highlight and a soft shadow.
// The Figma tile carries the official Figma mark unaltered, as Figma's brand guidelines require.
const TILES = {
  website: ["#6f9bff", "#2f5bea", "#1f43b8"],
  screenshot: ["#ffc35c", "#f08a24", "#c4660f"],
  mobile: ["#4fe0a8", "#0e9f6e", "#08734f"],
  figma: ["#ffffff", "#eef1f6", "#cfd6e2"],
  evidence: ["#ffe36b", "#d9a92c", "#9c7612"],
  coverage: ["#7aa6ff", "#3858e9", "#24399f"],
  review: ["#5ee6b0", "#10a473", "#0a7553"],
};

function Glyph({ name }) {
  switch (name) {
    case "website": return <g><rect x="11" y="13" width="26" height="21" rx="3.5" fill="#fff"/><path d="M11 16.5a3.5 3.5 0 0 1 3.5-3.5h19a3.5 3.5 0 0 1 3.5 3.5V19H11Z" fill="#dbe5ff"/><circle cx="15" cy="16" r="1.2" fill="#ff6b6b"/><circle cx="18.5" cy="16" r="1.2" fill="#ffc94d"/><circle cx="22" cy="16" r="1.2" fill="#3ddc97"/><rect x="15" y="23" width="12" height="2.4" rx="1.2" fill="#2f5bea"/><rect x="15" y="28" width="18" height="2" rx="1" fill="#c7d4f5"/></g>;
    case "screenshot": return <g><rect x="13" y="11" width="22" height="24" rx="3" fill="#ffe6c2" transform="rotate(-8 24 23)"/><rect x="12" y="13" width="24" height="22" rx="3.5" fill="#fff"/><circle cx="29.5" cy="19" r="2.6" fill="#ffc35c"/><path d="M14.5 32 21 24.5l4.5 5 3-3 5.5 5.5Z" fill="#2fbf71"/></g>;
    case "mobile": return <g><rect x="16" y="9" width="16" height="30" rx="4" fill="#fff"/><rect x="18" y="13" width="12" height="20" rx="1.8" fill="#c9f5e2"/><rect x="20" y="16" width="8" height="2.4" rx="1.2" fill="#0e9f6e"/><rect x="20" y="21" width="8" height="5" rx="1.2" fill="#7fe3bb"/><rect x="21.5" y="35" width="5" height="1.6" rx=".8" fill="#9ad9bf"/></g>;
    case "figma": return <g transform="translate(17.7 10.5) scale(.44)"><path fill="#0acf83" d="M9.5 57A9.5 9.5 0 0 0 19 47.5V38H9.5a9.5 9.5 0 0 0 0 19Z"/><path fill="#a259ff" d="M0 28.5A9.5 9.5 0 0 1 9.5 19H19v19H9.5A9.5 9.5 0 0 1 0 28.5Z"/><path fill="#f24e1e" d="M0 9.5A9.5 9.5 0 0 1 9.5 0H19v19H9.5A9.5 9.5 0 0 1 0 9.5Z"/><path fill="#ff7262" d="M19 0h9.5a9.5 9.5 0 0 1 0 19H19Z"/><path fill="#1abcfe" d="M38 28.5a9.5 9.5 0 1 1-19 0 9.5 9.5 0 0 1 19 0Z"/></g>;
    case "evidence": return <g><circle cx="21.5" cy="21.5" r="8.5" fill="#fff"/><circle cx="21.5" cy="21.5" r="5.2" fill="#fff4c2"/><path d="m27.5 27.5 7 7" stroke="#fff" strokeWidth="4.2" strokeLinecap="round"/><path d="m18.8 21.6 2 2 3.6-4" fill="none" stroke="#9c7612" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/></g>;
    case "coverage": return <g><circle cx="24" cy="25" r="10" fill="none" stroke="#dbe5ff" strokeWidth="4.5"/><path d="M24 15a10 10 0 1 1-9.5 13.1" fill="none" stroke="#fff" strokeWidth="4.5" strokeLinecap="round"/><circle cx="24" cy="25" r="3" fill="#fff"/></g>;
    case "review": return <g><path d="M24 10.5 34 14v8.2c0 6.4-4.2 11.4-10 13.8-5.8-2.4-10-7.4-10-13.8V14Z" fill="#fff"/><path d="m19.5 23.4 3.2 3.2 6-6.4" fill="none" stroke="#10a473" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round"/></g>;
    default: return null;
  }
}

export default function Icon3D({ name, size = 44, className = "" }) {
  const id = useId().replace(/:/g, "");
  const [light, mid, base] = TILES[name] || TILES.website;
  return <svg className={`icon-3d ${className}`} width={size} height={size} viewBox="0 0 48 48" aria-hidden="true" focusable="false">
    <defs>
      <linearGradient id={`${id}b`} x1="0" y1="0" x2=".35" y2="1"><stop offset="0" stopColor={light}/><stop offset="1" stopColor={mid}/></linearGradient>
      <linearGradient id={`${id}h`} x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#fff" stopOpacity=".55"/><stop offset="1" stopColor="#fff" stopOpacity="0"/></linearGradient>
      <filter id={`${id}s`} x="-30%" y="-30%" width="160%" height="170%"><feDropShadow dx="0" dy="3" stdDeviation="2.4" floodColor={base} floodOpacity=".35"/></filter>
      <filter id={`${id}g`} x="-20%" y="-20%" width="140%" height="150%"><feDropShadow dx="0" dy="1.2" stdDeviation=".9" floodColor="#0f172a" floodOpacity=".22"/></filter>
    </defs>
    <g filter={`url(#${id}s)`}>
      <rect x="3" y="5" width="42" height="40" rx="12" fill={base}/>
      <rect x="3" y="3" width="42" height="40" rx="12" fill={`url(#${id}b)`}/>
      <rect x="6" y="4.5" width="36" height="17" rx="9" fill={`url(#${id}h)`}/>
    </g>
    <g filter={`url(#${id}g)`}><Glyph name={name}/></g>
  </svg>;
}
