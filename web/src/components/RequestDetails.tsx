import {
  CalendarDays,
  ChevronDown,
  Clock3,
  MapPin,
  Settings2,
} from "lucide-react";
import type { Draft, Site } from "../types";

type Props = {
  draft: Draft;
  catalog: Site[];
  onChange: (draft: Draft) => void;
  disabled: boolean;
};
export function RequestDetails({ draft, catalog, onChange, disabled }: Props) {
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
        <div className="field-row">
          <label>
            <span className="field-label">
              <CalendarDays size={12} /> Date
            </span>
            <input
              aria-label="Comparison date"
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
              type="time"
              value={draft.time}
              onChange={(e) => update("time", e.target.value)}
            />
          </label>
        </div>
        <label>
          <span className="field-label">Timezone</span>
          <select
            aria-label="Comparison timezone"
            value={draft.timezone}
            onChange={(e) => update("timezone", e.target.value)}
          >
            <option value="">Choose a timezone</option>
            <option value="America/Phoenix">America/Phoenix</option>
            <option value="America/New_York">America/New_York</option>
            <option value="Africa/Cairo">Africa/Cairo</option>
            <option value="UTC">UTC</option>
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
        <p className="fixture-note">
          Demo coverage: 20 Sep 2025, 14:00 America/Phoenix.
        </p>
      </fieldset>
    </details>
  );
}
