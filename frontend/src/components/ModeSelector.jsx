const modes = [
  {
    key: "random",
    label: "Random DSA Topic",
    icon: (
      <svg className="mode-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="16 3 21 3 21 8" />
        <line x1="4" y1="20" x2="21" y2="3" />
        <polyline points="21 16 21 21 16 21" />
        <line x1="15" y1="15" x2="21" y2="21" />
        <line x1="4" y1="4" x2="9" y2="9" />
      </svg>
    ),
  },
  {
    key: "myproblems",
    label: "Previously Solved Problems",
    icon: (
      <svg className="mode-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
        <polyline points="14 2 14 8 20 8" />
        <line x1="16" y1="13" x2="8" y2="13" />
        <line x1="16" y1="17" x2="8" y2="17" />
        <polyline points="10 9 9 9 8 9" />
      </svg>
    ),
  },
  {
    key: "cpbites",
    label: "Random CP Topic",
    icon: (
      <svg className="mode-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
      </svg>
    ),
  },
];

export default function ModeSelector({ activeMode, onChange }) {
  return (
    <div className="mode-selector" role="tablist" aria-label="Refresher mode">
      {modes.map((mode) => (
        <button
          key={mode.key}
          className={activeMode === mode.key ? "mode-button active" : "mode-button"}
          onClick={() => onChange(mode.key)}
          type="button"
          role="tab"
          aria-selected={activeMode === mode.key}
        >
          {mode.icon}
          {mode.label}
        </button>
      ))}
    </div>
  );
}
