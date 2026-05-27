export default function LoadingState() {
  return (
    <div className="state-panel" style={{ animation: "fade-up 0.3s ease-out both" }}>
      <div className="spinner-ring" aria-hidden="true" />
      <p>Preparing your refresher bite…</p>
      <div className="loading-shimmer" aria-hidden="true" />
    </div>
  );
}
