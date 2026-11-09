import type { DemoCoverage, Draft } from "./types";

type LocalTime = Pick<Draft, "date" | "time" | "timezone">;

// Resolve wall-clock input with the selected IANA zone, independent of the
// browser's zone. Reject DST gaps and repeated hours rather than guessing.
function localInstant(value: LocalTime): number | null {
  if (
    !/^\d{4}-\d{2}-\d{2}$/.test(value.date) ||
    !/^\d{2}:\d{2}(?::00)?$/.test(value.time)
  )
    return null;
  const [year, month, day] = value.date.split("-").map(Number);
  const [hour, minute] = value.time.split(":").map(Number);
  const wall = Date.UTC(year, month - 1, day, hour, minute);
  if (!Number.isFinite(wall)) return null;
  const format = new Intl.DateTimeFormat("en-CA", {
    timeZone: value.timezone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  });
  const represented = (instant: number) => {
    const parts = Object.fromEntries(
      format.formatToParts(new Date(instant)).map((p) => [p.type, p.value]),
    );
    return Date.UTC(
      Number(parts.year),
      Number(parts.month) - 1,
      Number(parts.day),
      Number(parts.hour),
      Number(parts.minute),
    );
  };
  const offsets = new Set(
    [-86400000, 0, 86400000].map(
      (delta) => wall + delta - represented(wall + delta),
    ),
  );
  const matches = [...offsets]
    .map((offset) => wall + offset)
    .filter((instant) => represented(instant) === wall);
  // Date.UTC normalizes impossible dates, so compare to the original fields too.
  const normalized = new Date(wall);
  if (
    normalized.getUTCFullYear() !== year ||
    normalized.getUTCMonth() + 1 !== month ||
    normalized.getUTCDate() !== day ||
    hour > 23 ||
    minute > 59
  )
    return null;
  return matches.length === 1 ? matches[0] : null;
}

export function demoTimeIssue(
  value: LocalTime,
  coverage: DemoCoverage,
): string | null {
  if (!value.date || !value.time || !value.timezone) return null;
  try {
    const instant = localInstant(value);
    if (instant === null)
      return "Choose a valid, unambiguous local date and time for this timezone.";
    if (
      instant < Date.parse(coverage.start) ||
      instant > Date.parse(coverage.end)
    ) {
      return `Outside the demo window. Choose an instant from ${coverage.start_date} ${coverage.start_time} through ${coverage.end_date} ${coverage.end_time} ${coverage.timezone}, inclusive.`;
    }
    return null;
  } catch {
    return "Choose a valid IANA timezone.";
  }
}
