import { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  getHealth,
  sendExistingBiteToTelegram,
  syncLeetCodeProblems,
} from "./api/client";
import ErrorBoundary from "./components/ErrorBoundary";
import ErrorState from "./components/ErrorState";
import LoadingState from "./components/LoadingState";
import ModeSelector from "./components/ModeSelector";
import RefresherCard from "./components/RefresherCard";
import { useRefresher } from "./hooks/useRefresher";
import "./index.css";

function App() {
  const [activeMode, setActiveMode] = useState("random");
  const [health, setHealth] = useState({ ok: false, provider: "unknown", problems: 0 });
  const [telegramStatus, setTelegramStatus] = useState("");
  const [telegramLoading, setTelegramLoading] = useState(false);
  const [syncStatus, setSyncStatus] = useState("");
  const [syncLoading, setSyncLoading] = useState(false);
  const { refresherDataByMode, loadingByMode, errorByMode, fetchRefresher, fetchCount } = useRefresher();
  const refresherData = refresherDataByMode[activeMode];
  const loading = loadingByMode[activeMode];
  const error = errorByMode[activeMode];

  useEffect(() => {
    let mounted = true;
    getHealth()
      .then((data) => {
        if (mounted) setHealth({ ok: data.status === "ok", provider: data.provider, problems: data.problems_count });
      })
      .catch(() => {
        if (mounted) setHealth({ ok: false, provider: "offline", problems: 0 });
      });
    return () => {
      mounted = false;
    };
  }, []);

  function handleModeChange(mode) {
    setActiveMode(mode);
    setTelegramStatus("");
    setSyncStatus("");
  }

  async function handleSendTelegram() {
    if (!refresherData) return;

    setTelegramLoading(true);
    setTelegramStatus("");
    try {
      const result = await sendExistingBiteToTelegram(activeMode, refresherData);
      setTelegramStatus(result.message || "Sent to Telegram");
    } catch (err) {
      setTelegramStatus(err.message || "Could not send Telegram notification");
    } finally {
      setTelegramLoading(false);
    }
  }

  async function handleSyncLeetCode() {
    setSyncLoading(true);
    setSyncStatus("");
    try {
      const result = await syncLeetCodeProblems();
      setSyncStatus(`Added ${result.added} new accepted problems. Total saved: ${result.total}.`);
      const latestHealth = await getHealth();
      setHealth({
        ok: latestHealth.status === "ok",
        provider: latestHealth.provider,
        problems: latestHealth.problems_count,
      });
    } catch (err) {
      setSyncStatus(err.message || "Could not sync LeetCode submissions");
    } finally {
      setSyncLoading(false);
    }
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Daily practice</p>
          <h1>DSA Refresher</h1>
        </div>
        <div className="health-pill" title={`Provider: ${health.provider}`}>
          <span className={health.ok ? "health-dot online" : "health-dot offline"} />
          <span>{health.ok ? `${health.provider} ready` : "backend offline"}</span>
        </div>
      </header>

      <section className="control-band">
        <ModeSelector activeMode={activeMode} onChange={handleModeChange} />
        <div className="action-row">
          {activeMode === "myproblems" && (
            <button
              className="secondary-action"
              type="button"
              disabled={syncLoading}
              onClick={handleSyncLeetCode}
              title="Fetch latest accepted LeetCode submissions and append new problems"
            >
              {syncLoading ? "Syncing…" : "Sync LeetCode"}
            </button>
          )}
          <button
            className="primary-action"
            type="button"
            disabled={loading}
            onClick={() => fetchRefresher(activeMode)}
          >
            {loading ? "Generating…" : "Get Today's Bite"}
          </button>
        </div>
      </section>

      {telegramStatus && <div className="telegram-status">{telegramStatus}</div>}
      {syncStatus && <div className="telegram-status">{syncStatus}</div>}
      {loading && <LoadingState />}
      {error && !loading && <ErrorState message={error} />}
      {!loading && !error && (
        <ErrorBoundary resetKey={`${activeMode}-${fetchCount}`}>
          <RefresherCard mode={activeMode} data={refresherData} />
        </ErrorBoundary>
      )}
      {!loading && !error && refresherData && (
        <div className="post-card-actions">
          <button
            className="secondary-action"
            type="button"
            disabled={telegramLoading}
            onClick={handleSendTelegram}
            title="Send the currently displayed bite to Telegram"
          >
            {telegramLoading ? "Sending…" : "Send this bite to Telegram"}
          </button>
        </div>
      )}
      {!loading && !error && !refresherData && (
        <section className="empty-state">
          <span className="empty-icon">⚡</span>
          <h2>Ready when you are.</h2>
          <p>Choose a mode and pull a compact refresher for today's revision session.</p>
        </section>
      )}

      <footer className="app-footer">
        Built for daily reps · {health.problems > 0 ? `${health.problems} problems tracked` : ""}
      </footer>
    </main>
  );
}

createRoot(document.getElementById("root")).render(<App />);
