import type { Briefing } from "./types";

export function highestReading(briefing: Briefing) {
  const c = briefing.comparison;
  const value =
    c.highest_c ?? Math.max(...c.ranking.map((row) => row.temperature_c));
  return {
    value,
    names:
      c.highest_locations ??
      c.ranking
        .filter((row) => row.temperature_c === value)
        .map((row) => row.name),
  };
}
export function questionFocus(question: string) {
  const high = /\b(highest|hottest|hotter|warmest|warmer|maximum|max)\b/i.test(
    question,
  );
  const low = /\b(lowest|coldest|colder|coolest|cooler|minimum|min)\b/i.test(
    question,
  );
  return high && !low ? "highest" : low && !high ? "lowest" : "both";
}
export function comparisonSummary(briefing: Briefing) {
  const high = highestReading(briefing);
  const low = {
    value: briefing.comparison.lowest_c,
    names: briefing.comparison.lowest_locations,
  };
  const text = (label: string, value: typeof high) =>
    `${label}: ${value.names.join(" and ")} at ${value.value.toFixed(1)} °C.`;
  return (
    (questionFocus(briefing.request.question) === "highest"
      ? text("Highest", high) + " " + text("Lowest", low)
      : text("Lowest", low) + " " + text("Highest", high)) +
    ` Spread: ${briefing.comparison.spread_c.toFixed(1)} °C.`
  );
}

// One letter per site everywhere (form, map, cards), following the catalog order.
let siteOrder: string[] = [];
export function setSiteOrder(names: string[]) {
  siteOrder = names;
}
export function siteLetter(name: string, index: number) {
  const position = siteOrder.indexOf(name);
  return String.fromCharCode(65 + (position >= 0 ? position : index));
}
