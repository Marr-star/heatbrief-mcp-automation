import {
  ArrowDown,
  ArrowUp,
  ArrowUpRight,
  Check,
  ChevronRight,
  Download,
  FileText,
  Info,
  Loader2,
  Pencil,
  ShieldCheck,
} from "lucide-react";
import type { Briefing, Measurement, Run } from "../types";
import { highestReading, questionFocus, siteLetter } from "../analysis";

export function displayDate(date: string) {
  return new Intl.DateTimeFormat("en", {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  }).format(new Date(date + "T00:00:00Z"));
}
export function statusLabel(status: string) {
  return (
    (
      {
        draft_pending_review: "Awaiting review",
        approved_for_manual_send: "Approved for manual send",
        rejected: "Rejected",
      } as Record<string, string>
    )[status] || status
  );
}
export function ComparisonCards({
  briefing,
  onSelect,
  selected,
}: {
  briefing: Briefing;
  onSelect: (name: string) => void;
  selected: string | null;
}) {
  return (
    <div className="comparison-grid">
      {briefing.measurements.map((item, index) => {
        const lowest = briefing.comparison.lowest_locations.includes(item.name);
        const highest = highestReading(briefing).names.includes(item.name);
        return (
          <button
            type="button"
            key={item.name}
            className={`temperature-card ${lowest ? "is-lowest" : ""} ${highest ? "is-highest" : ""} ${selected === item.name ? "is-selected" : ""}`}
            onClick={() => onSelect(item.name)}
          >
            <div className="temperature-card-top">
              <span className="site-letter">
                {siteLetter(item.name, index)}
              </span>
              {lowest ? (
                <span className="lowest-label">
                  <ArrowDown size={11} /> Lowest
                </span>
              ) : null}
              {highest ? (
                <span className="highest-label">
                  <ArrowUp size={11} /> Highest
                </span>
              ) : null}
            </div>
            <div className="temperature-value">
              {item.temperature_c != null ? item.temperature_c.toFixed(1) : "—"}
              <span>°C</span>
            </div>
            <strong>{item.name}</strong>
            <span className="temperature-card-footer">
              {item.temperature_c != null
                ? "Fictional demo reading"
                : "Measurement unavailable"}
              <ArrowUpRight size={13} />
            </span>
          </button>
        );
      })}
    </div>
  );
}
export function Finding({ briefing }: { briefing: Briefing }) {
  const { comparison: c } = briefing;
  const high = highestReading(briefing);
  const focus = questionFocus(briefing.request.question);
  const names = focus === "highest" ? high.names : c.lowest_locations;
  const label = focus === "highest" ? "highest" : "lowest";
  return (
    <section className="finding-card">
      <span className="finding-icon">
        <ShieldCheck size={21} />
      </span>
      <div>
        <p className="eyebrow">THE COMPARISON</p>
        <h3>
          {focus === "both" ? (
            "Lowest and highest temperatures."
          ) : (
            <>
              {names.join(" and ")}{" "}
              {names.length > 1
                ? `tie for the ${label} temperature`
                : `has the ${label} temperature`}
              .
            </>
          )}
        </h3>
        <dl className="finding-extremes">
          <div>
            <dt>Lowest</dt>
            <dd>
              {c.lowest_c.toFixed(1)} °C · {c.lowest_locations.join(", ")}
            </dd>
          </div>
          <div>
            <dt>Highest</dt>
            <dd>
              {high.value.toFixed(1)} °C · {high.names.join(", ")}
            </dd>
          </div>
        </dl>
        <p>
          {c.spread_c.toFixed(1)} °C separates the highest and lowest available
          readings. {c.ranking.length}/{briefing.request.locations.length} sites
          returned data.{c.incomplete ? " This comparison is incomplete." : ""}
        </p>
        <span className="finding-limitation">
          <Info size={12} /> Temperature alone does not establish outdoor
          safety.
        </span>
      </div>
    </section>
  );
}
export function Evidence({ briefing }: { briefing: Briefing }) {
  return (
    <section className="evidence-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">FOLLOW THE EVIDENCE</p>
          <h2>Every number has a source.</h2>
        </div>
        <span className="tag">
          {briefing.measurements.length} source records
        </span>
      </div>
      <div className="evidence-table-scroll">
        <table className="evidence-table">
          <thead>
            <tr>
              <th>Location</th>
              <th>Temperature</th>
              <th>Coordinates</th>
              <th>Observed at</th>
            </tr>
          </thead>
          <tbody>
            {briefing.measurements.map((item) => (
              <tr key={item.name}>
                <td>
                  <strong>{item.name}</strong>
                  <span>
                    {item.unit ? `Original unit: °${item.unit}` : "Unavailable"}
                  </span>
                </td>
                <td>
                  {item.temperature_c != null
                    ? `${item.temperature_c.toFixed(1)} °C`
                    : "Unavailable"}
                </td>
                <td>
                  {item.latitude}
                  <br />
                  {item.longitude}
                </td>
                <td>{item.observed_at || "Unavailable"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="source-list">
        {briefing.measurements.map((item) => (
          <SourceRecord key={item.name} item={item} />
        ))}
      </div>
      <div className="limitations">
        <h3>
          <Info size={16} /> What this comparison can tell you
        </h3>
        <ul>
          {briefing.limitations.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </div>
    </section>
  );
}
function SourceRecord({ item }: { item: Measurement }) {
  return (
    <details className="source-record" open>
      <summary>
        <span>
          <FileText size={15} />
          {item.name}
        </span>
        <ChevronRight size={15} />
      </summary>
      <div>
        <p>{item.source || item.issue || "No source returned"}</p>
        <span>Evidence ID</span>
        <code>{item.source_id || "Unavailable"}</code>
      </div>
    </details>
  );
}
export function ClientBriefing({
  briefing,
  draft,
  setDraft,
  onSave,
  saving,
  onReview,
  onDownload,
  downloading,
}: {
  briefing: Briefing;
  draft: string;
  setDraft: (text: string) => void;
  onSave: () => void;
  saving: boolean;
  onReview: (decision: "approve" | "reject") => void;
  onDownload: () => void;
  downloading: boolean;
}) {
  const edited = draft !== briefing.follow_up_draft;
  const reviewed = Boolean(briefing.review);
  return (
    <div className="client-panel">
      <section className="report-preview">
        <div className="section-heading">
          <div>
            <p className="eyebrow">
              PREPARED FOR {briefing.request.client_name.toUpperCase()}
            </p>
            <h2>One briefing. All the context.</h2>
          </div>
          <button
            className="button button-secondary"
            onClick={onDownload}
            disabled={downloading}
          >
            {downloading ? (
              <Loader2 size={15} className="spin" />
            ) : (
              <Download size={15} />
            )}{" "}
            PDF
          </button>
        </div>
        <div className="report-paper">
          <div className="report-paper-top">
            <span>HEATBRIEF</span>
            <span className="tag tag-amber">Mock data</span>
          </div>
          <h3>Location temperature briefing</h3>
          <p className="report-question">{briefing.request.question}</p>
          <div className="report-time">
            {displayDate(briefing.request.date)} ·{" "}
            {briefing.request.time.slice(0, 5)} · {briefing.request.timezone}
          </div>
          <div className="report-stat">
            <span>Lowest temperature</span>
            <strong>{briefing.comparison.lowest_c.toFixed(1)} °C</strong>
            <span>{briefing.comparison.lowest_locations.join(", ")}</span>
          </div>
          <div className="report-stat report-stat-highest">
            <span>Highest temperature</span>
            <strong>{highestReading(briefing).value.toFixed(1)} °C</strong>
            <span>{highestReading(briefing).names.join(", ")}</span>
          </div>
          {briefing.measurements.map((item) => (
            <div key={item.name} className="report-line">
              <span>{item.name}</span>
              <strong>
                {item.temperature_c != null
                  ? `${item.temperature_c.toFixed(1)} °C`
                  : "Unavailable"}
              </strong>
            </div>
          ))}
          <p className="report-footnote">
            Fictional demonstration readings. Review the Evidence tab for source
            records and limitations. Temperature alone does not establish
            outdoor safety.
          </p>
        </div>
      </section>
      <section className="draft-editor">
        <div className="section-heading">
          <div>
            <p className="eyebrow">THE NEXT CONVERSATION</p>
            <h2>Client follow-up</h2>
          </div>
          <span className="tag">
            <Pencil size={12} />
            {reviewed ? "Review recorded" : "Editable draft"}
          </span>
        </div>
        <label className="sr-only" htmlFor="follow-up-draft">
          Client follow-up draft
        </label>
        <textarea
          id="follow-up-draft"
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          disabled={reviewed}
          maxLength={20000}
        />
        <div className="draft-actions">
          <span>
            {edited
              ? "Unsaved changes"
              : reviewed
                ? `Reviewed by ${briefing.review?.reviewer}`
                : "Saved draft · ready for review"}
          </span>
          {!reviewed ? (
            <button
              className="button button-secondary"
              disabled={!edited || saving}
              onClick={onSave}
            >
              {saving ? (
                <Loader2 size={14} className="spin" />
              ) : (
                <Check size={14} />
              )}{" "}
              Save changes
            </button>
          ) : null}
        </div>
        <div
          className={`review-banner ${briefing.status === "approved_for_manual_send" ? "approved" : ""}`}
        >
          <ShieldCheck size={20} />
          <div>
            <strong>{statusLabel(briefing.status)}</strong>
            <p>
              {reviewed
                ? "The decision is recorded. Sending remains a manual action."
                : "Review the evidence and draft before recording your decision."}
            </p>
          </div>
        </div>
        {!reviewed ? (
          <div className="review-actions">
            <button
              className="button button-secondary"
              onClick={() => onReview("reject")}
              disabled={edited}
            >
              Reject draft
            </button>
            <button
              className="button button-primary"
              onClick={() => onReview("approve")}
              disabled={edited}
            >
              <ShieldCheck size={15} /> Review & approve
            </button>
          </div>
        ) : null}
      </section>
    </div>
  );
}
export function RunTimeline({
  run,
  workflowUrl,
}: {
  run: Run | null;
  workflowUrl: string;
}) {
  if (!run) return null;
  return (
    <section className="run-timeline" aria-live="polite">
      <div className="run-timeline-heading">
        <span
          className={`status-dot ${run.state === "running" || run.state === "queued" ? "pulse" : ""}`}
        />
        <strong>
          {run.state === "completed"
            ? "Workflow complete"
            : run.state === "failed"
              ? "Request needs attention"
              : "Running your briefing"}
        </strong>
        {run.elapsed_ms != null ? (
          <span>{(run.elapsed_ms / 1000).toFixed(1)}s</span>
        ) : null}
      </div>
      <div className="timeline-events">
        {run.events.map((event, index) => (
          <div className="timeline-event" key={event.at + index}>
            <span>
              {index === run.events.length - 1 &&
              (run.state === "running" || run.state === "queued") ? (
                <Loader2 size={13} className="spin" />
              ) : (
                <Check size={12} />
              )}
            </span>
            <p>{event.title}</p>
          </div>
        ))}
      </div>
      {run.execution_id ? (
        <a
          href={workflowUrl + "/executions/" + run.execution_id}
          target="_blank"
          rel="noreferrer"
        >
          n8n execution #{run.execution_id}
          <ArrowUpRight size={13} />
        </a>
      ) : null}
    </section>
  );
}
