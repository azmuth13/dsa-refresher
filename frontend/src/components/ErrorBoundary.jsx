import { Component } from "react";

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidUpdate(prevProps) {
    // Auto-reset when parent signals new data (e.g., new fetch or mode change)
    if (prevProps.resetKey !== this.props.resetKey && this.state.hasError) {
      this.setState({ hasError: false, error: null });
    }
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="state-panel error-panel" style={{ animation: "fade-up 0.3s ease-out both" }}>
          <svg className="error-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          <strong>Something went wrong rendering this content</strong>
          <p style={{ marginBottom: 16 }}>
            {this.state.error?.message || "An unexpected error occurred while displaying the refresher card."}
          </p>
          <button
            className="secondary-action"
            type="button"
            onClick={this.handleReset}
          >
            Dismiss
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
