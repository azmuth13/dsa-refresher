export default function ErrorState({ message }) {
  return (
    <div className="state-panel error-panel" style={{ animation: "fade-up 0.3s ease-out both" }}>
      <svg className="error-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="10" />
        <line x1="12" y1="8" x2="12" y2="12" />
        <line x1="12" y1="16" x2="12.01" y2="16" />
      </svg>
      <strong>Could not load refresher</strong>
      <p>{message}</p>
    </div>
  );
}
