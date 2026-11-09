import {
  CalendarDays,
  ChevronDown,
  Clock3,
  MapPin,
  Settings2,
} from "lucide-react";
import type { DemoCoverage, Draft, Site } from "../types";

type Props = {
  draft: Draft;
  catalog: Site[];
  coverage: DemoCoverage;
  timeIssue: string | null;
  onUseDemoTime: () => void;
  onPreset: (value: Pick<Draft, "date" | "time" | "timezone">) => void;
  onChange: (draft: Draft) => void;
  disabled: boolean;
};
export function RequestDetails({
  draft,
  catalog,
  coverage,
  timeIssue,
  onUseDemoTime,
  onPreset,
  onChange,
  disabled,
}: Props) {
  const update = (key: keyof Draft, value: unknown) =>
    onChange({ ...draft, [key]: value });
  function toggle(site: Site) {
    const selected = draft.locations.some((value) => value.name === site.name);
    update(
      "locations",
      selected
        ? draft.locations.filter((value) => value.name !== site.name)
        : [...draft.locations, site],
    );
  }
  return (
    <details className="request-details" open>
      <summary>
        <span>
          <Settings2 size={15} /> Request details
        </span>
        <ChevronDown size={15} />
      </summary>
      <fieldset disabled={disabled}>
        <legend className="sr-only">Comparison request details</legend>
        <label className="field-label">
          Locations <span>{draft.locations.length}/3 selected</span>
        </label>
        <div className="site-choices">
          {catalog.map((site, index) => (
            <label
              key={site.name}
              className={`site-choice ${draft.locations.some((value) => value.name === site.name) ? "checked" : ""}`}
            >
              <input
                type="checkbox"
                checked={draft.locations.some(
                  (value) => value.name === site.name,
                )}
                onChange={() => toggle(site)}
              />
              <span className="site-letter">
                {String.fromCharCode(65 + index)}
              </span>
              <span>{site.name}</span>
              <MapPin size={12} />
            </label>
          ))}
        </div>
        <label>
          <span className="field-label">Date and time examples</span>
          <select
            aria-label="Demo date and time example"
            value=""
            onChange={(event) => {
              const preset = coverage.presets.find(
                (value) => value.label === event.target.value,
              );
              if (preset) onPreset(preset);
            }}
          >
            <option value="">Choose an example, or enter your own</option>
            {coverage.presets.map((preset) => (
              <option key={preset.label} value={preset.label}>
                {preset.label} · {preset.date} {preset.time}
              </option>
            ))}
          </select>
        </label>
        <div className="field-row">
          <label>
            <span className="field-label">
              <CalendarDays size={12} /> Date
            </span>
            <input
              aria-label="Comparison date"
              aria-invalid={Boolean(timeIssue)}
              aria-describedby="demo-time-coverage"
              type="date"
              value={draft.date}
              onChange={(e) => update("date", e.target.value)}
            />
          </label>
          <label>
            <span className="field-label">
              <Clock3 size={12} /> Local time
            </span>
            <input
              aria-label="Comparison time"
              aria-invalid={Boolean(timeIssue)}
              aria-describedby="demo-time-coverage"
              type="time"
              step={60}
              value={draft.time}
              onChange={(e) => update("time", e.target.value)}
            />
          </label>
        </div>
        <label>
          <span className="field-label">Timezone</span>
          <select
            aria-label="Comparison timezone"
            aria-invalid={Boolean(timeIssue)}
            aria-describedby="demo-time-coverage"
            value={draft.timezone}
            onChange={(e) => update("timezone", e.target.value)}
          >
            <option value="">Choose a timezone</option>
            <option value="America/Phoenix">America/Phoenix</option>
            <option value="America/New_York">America/New_York</option>
            <option value="Africa/Cairo">Africa/Cairo</option>
            <option value="UTC">UTC</option>
            {draft.timezone &&
            ![
              "America/Phoenix",
              "America/New_York",
              "Africa/Cairo",
              "UTC",
            ].includes(draft.timezone) ? (
              <option value={draft.timezone}>{draft.timezone}</option>
            ) : null}
          </select>
        </label>
        <label>
          <span className="field-label">Prepared for</span>
          <input
            aria-label="Client name"
            value={draft.client_name}
            maxLength={120}
            onChange={(e) => update("client_name", e.target.value)}
          />
        </label>
        <div className={timeIssue ? "demo-time-warning" : "demo-window"}>
          <p id="demo-time-coverage" role={timeIssue ? "alert" : undefined}>
            {timeIssue || (
              <>
                <strong>Synthetic demo window</strong>
                <br />
                From {coverage.start_date} at {coverage.start_time}
                <br />
                Through {coverage.end_date} at {coverage.end_time}
                <br />
                {coverage.timezone} · inclusive · every minute
              </>
            )}
          </p>
          {timeIssue ? (
            <button
              type="button"
              className="button button-secondary"
              onClick={onUseDemoTime}
            >
              Use default demo time
            </button>
          ) : (
            <p className="muted">
              Choose any instant inside the window. Values are generated, not
              weather observations.
            </p>
          )}
        </div>
      </fieldset>
    </details>
  );
}
