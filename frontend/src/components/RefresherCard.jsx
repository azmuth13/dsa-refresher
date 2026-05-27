import { useState, useCallback } from "react";

/* ── Inline section icons ───────────────────────────────── */
const sectionIcons = {
  "Core Concept": (
    <svg className="section-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/></svg>
  ),
  "Complexity": (
    <svg className="section-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
  ),
  "Common Pitfalls": (
    <svg className="section-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
  ),
  "Template Code": (
    <svg className="section-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>
  ),
  "Example Problem": (
    <svg className="section-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
  ),
  "Practice Links": (
    <svg className="section-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>
  ),
  "Related Topics": (
    <svg className="section-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/></svg>
  ),
  "Pattern Intuition": (
    <svg className="section-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/></svg>
  ),
  "Key Steps": (
    <svg className="section-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></svg>
  ),
  "Gotchas": (
    <svg className="section-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
  ),
  "Similar Problems": (
    <svg className="section-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>
  ),
  "Why It Matters": (
    <svg className="section-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
  ),
  "When To Use": (
    <svg className="section-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="9 11 12 14 22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>
  ),
  "Key Takeaways": (
    <svg className="section-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
  ),
  "Mental Model": (
    <svg className="section-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
  ),
  "Source": (
    <svg className="section-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
  ),
};

/* ── Small helpers ──────────────────────────────────────── */
function Badge({ children, tone = "neutral" }) {
  return <span className={`badge badge-${tone}`}>{children}</span>;
}

function Section({ title, children }) {
  const icon = sectionIcons[title] || null;
  return (
    <section className="card-section">
      <div className="section-header">
        {icon}
        <h3>{title}</h3>
      </div>
      {children}
    </section>
  );
}

function CopyButton({ text }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      // Clipboard API unavailable or permission denied
    }
  }, [text]);

  return (
    <button
      type="button"
      className={copied ? "copied" : ""}
      onClick={handleCopy}
    >
      {copied ? (
        <>
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
          Copied!
        </>
      ) : (
        <>
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
          Copy
        </>
      )}
    </button>
  );
}

/* ── Card variants ──────────────────────────────────────── */
function RandomTopicCard({ data }) {
  return (
    <article className="refresher-card">
      <div className="card-header">
        <div>
          <h2>{data.topic_name}</h2>
          <div className="badge-row">
            <Badge>{data.category}</Badge>
            <Badge tone="accent">{data.difficulty}</Badge>
            {data.source_context_used && <Badge tone="success">cp-algorithms</Badge>}
          </div>
        </div>
      </div>

      <Section title="Core Concept">
        <p>{data.core_concept}</p>
      </Section>

      <Section title="Complexity">
        <div className="complexity-grid">
          <span>Best</span><strong>{data.time_complexity?.best || "N/A"}</strong>
          <span>Average</span><strong>{data.time_complexity?.average || "N/A"}</strong>
          <span>Worst</span><strong>{data.time_complexity?.worst || "N/A"}</strong>
          <span>Space</span><strong>{data.space_complexity}</strong>
        </div>
      </Section>

      <div className="callout">
        <span>💡 Key insight</span>
        <p>{data.key_insight}</p>
      </div>

      <Section title="Common Pitfalls">
        <ul>{data.common_pitfalls?.map((item) => <li key={item}>{item}</li>)}</ul>
      </Section>

      <Section title="Template Code">
        <div className="code-toolbar">
          <CopyButton text={data.template_code} />
        </div>
        <pre><code>{data.template_code}</code></pre>
      </Section>

      <Section title="Example Problem">
        <h4>{data.example_problem?.title}</h4>
        <p>{data.example_problem?.description}</p>
        <p>{data.example_problem?.approach}</p>
      </Section>

      <Section title="Practice Links">
        <div className="link-row">
          {data.practice_links?.map((link) => (
            <a href={link.url} key={link.url} target="_blank" rel="noreferrer" className="link-badge">
              {link.platform}: {link.title}
            </a>
          ))}
        </div>
      </Section>

      <Section title="Related Topics">
        <div className="chip-row">
          {data.related_topics?.map((topic) => <span className="chip" key={topic}>{topic}</span>)}
        </div>
      </Section>
    </article>
  );
}

function ProblemCard({ problem }) {
  return (
    <article className="refresher-card">
      <div className="card-header">
        <div>
          <h2>{problem.problem_title}</h2>
          <div className="badge-row">
            <Badge>{problem.platform}</Badge>
            <a href={problem.url} target="_blank" rel="noreferrer" className="inline-link">Open problem</a>
            {problem.submissions_url && (
              <a href={problem.submissions_url} target="_blank" rel="noreferrer" className="inline-link">
                Submissions
              </a>
            )}
          </div>
        </div>
      </div>

      <div className="pattern-name">{problem.pattern_name}</div>

      <Section title="Pattern Intuition">
        <p>{problem.pattern_intuition}</p>
      </Section>

      <Section title="Key Steps">
        <ol>{problem.key_steps?.map((step) => <li key={step}>{step}</li>)}</ol>
      </Section>

      <Section title="Gotchas">
        <ul>{problem.gotchas?.map((item) => <li key={item}>{item}</li>)}</ul>
      </Section>

      <div className="callout challenge">
        <span>🧠 Revision prompt</span>
        <p>{problem.revision_prompt}</p>
      </div>

      <Section title="Similar Problems">
        <div className="link-row">
          {problem.similar_problems?.map((link) => (
            <a href={link.url} key={link.url} target="_blank" rel="noreferrer" className="link-badge">
              {link.platform}: {link.title}
            </a>
          ))}
        </div>
      </Section>
    </article>
  );
}

function CPBiteCard({ data }) {
  return (
    <article className="refresher-card">
      <div className="card-header">
        <div>
          <h2>{data.article_title}</h2>
          <div className="badge-row">
            <Badge>{data.category}</Badge>
            <Badge tone="accent">CPBites</Badge>
            {data.source_excerpt_used && <Badge tone="success">source excerpt</Badge>}
          </div>
        </div>
      </div>

      <div className="callout">
        <span>💡 Core idea</span>
        <p>{data.core_idea}</p>
      </div>

      <Section title="Why It Matters">
        <p>{data.why_it_matters}</p>
      </Section>

      <Section title="When To Use">
        <ul>{data.when_to_use?.map((item) => <li key={item}>{item}</li>)}</ul>
      </Section>

      <Section title="Key Takeaways">
        <ul>{data.key_takeaways?.map((item) => <li key={item}>{item}</li>)}</ul>
      </Section>

      <Section title="Mental Model">
        <p>{data.mental_model}</p>
      </Section>

      <div className="callout challenge">
        <span>🎯 Practice angle</span>
        <p>{data.practice_angle}</p>
      </div>

      <Section title="Source">
        <div className="link-row">
          <a href={data.source_url} target="_blank" rel="noreferrer" className="link-badge">
            Codeforces article
          </a>
          <a href={data.source_index_url} target="_blank" rel="noreferrer" className="link-badge">
            CPBites index
          </a>
        </div>
        {data.model_used && <p className="model-note">Generated with {data.model_used}</p>}
      </Section>
    </article>
  );
}

export default function RefresherCard({ mode, data }) {
  if (!data) return null;
  if (mode === "random") return <RandomTopicCard data={data} />;
  if (mode === "cpbites") return <CPBiteCard data={data} />;
  if (!Array.isArray(data)) {
    return (
      <div className="state-panel error-panel" style={{ animation: "fade-up 0.3s ease-out both" }}>
        <strong>Unexpected data format</strong>
        <p>The server returned data in an unexpected format. Try fetching again.</p>
      </div>
    );
  }
  return (
    <div className="problem-list">
      {data.map((problem) => <ProblemCard key={problem.url} problem={problem} />)}
    </div>
  );
}
