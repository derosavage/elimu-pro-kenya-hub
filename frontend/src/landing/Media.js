import { useEffect, useState } from 'react';

// All landing media lives in public/landing/ (served from PUBLIC_URL). If a file is missing,
// the component hides itself and the section renders exactly as it did before.
const base = `${process.env.PUBLIC_URL || ''}/landing`;

export const MEDIA = {
  hero: {
    sources: [
      { src: `${base}/hero-classroom.webm`, type: 'video/webm' },
      { src: `${base}/hero-classroom.mp4`, type: 'video/mp4' },
    ],
    poster: `${base}/hero-poster.jpg`,
  },
  features: { src: `${base}/features-admin.jpg`, alt: 'A school administrator reviewing learner records on a laptop', width: 1280, height: 720 },
  rollout: [
    { src: `${base}/rollout-discover.jpg`, alt: 'School leaders in a planning discussion', width: 1260, height: 540 },
    { src: `${base}/rollout-prepare.jpg`, alt: 'Teachers being trained on a school system', width: 1260, height: 540 },
    { src: `${base}/rollout-golive.jpg`, alt: 'Students and a teacher using tablets in a classroom', width: 1260, height: 540 },
  ],
};

// Decorative looping hero background. Poster shows first; video fades in once it can play.
// Reduced-motion users get the still poster only.
export function HeroMedia() {
  const [still, setStill] = useState(false);
  const [ready, setReady] = useState(false);
  useEffect(() => {
    const m = window.matchMedia('(prefers-reduced-motion: reduce)');
    const on = () => setStill(m.matches);
    on();
    m.addEventListener('change', on);
    return () => m.removeEventListener('change', on);
  }, []);
  const { sources, poster } = MEDIA.hero;
  return (
    <div className="lp-hero-media" aria-hidden="true">
      <img src={poster} alt="" fetchpriority="high" onError={(e) => { e.currentTarget.style.display = 'none'; }} />
      {!still && (
        <video className={ready ? 'on' : ''} autoPlay muted loop playsInline preload="auto" poster={poster} onLoadedData={() => setReady(true)}>
          {sources.map((s) => <source key={s.src} src={s.src} type={s.type} />)}
        </video>
      )}
    </div>
  );
}

export function Photo({ item, className = '' }) {
  const [bad, setBad] = useState(false);
  if (bad) return null;
  return (
    <figure className={`lp-photo ${className}`}>
      <img src={item.src} alt={item.alt} width={item.width} height={item.height} loading="lazy" decoding="async" onError={() => setBad(true)} />
    </figure>
  );
}