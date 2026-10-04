// Placeholder mark: blue square + wordmark. Swap for the real ElimuPro logo file later.
export default function Logo({ light }) {
  return (
    <span className={`lp-brand${light ? ' light' : ''}`}>
      <span className="lp-logo-sq"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 4 2 9l10 5 8-4v6h2V9L12 4zM6 13v4c0 1.5 3 3 6 3s6-1.5 6-3v-4l-6 3-6-3z" fill="#fff" /></svg></span>
      <span>Elimu Pro</span>
    </span>
  );
}
