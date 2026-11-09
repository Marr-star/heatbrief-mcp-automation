import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import {
  comparisonSummary,
  highestReading,
  questionFocus,
} from "../src/analysis.ts";

const legacy = JSON.parse(
  readFileSync(
    new URL(
      "../../examples/generated/demo-phoenix-001/briefing.json",
      import.meta.url,
    ),
    "utf8",
  ),
);

test("old saved briefings derive the maximum from their stored ranking", () => {
  assert.equal(legacy.comparison.highest_c, undefined);
  assert.deepEqual(highestReading(legacy), {
    value: 36.7,
    names: ["Scottsdale Courtyard"],
  });
  assert.match(
    comparisonSummary(legacy),
    /Highest: Scottsdale Courtyard at 36.7/,
  );
  assert.match(comparisonSummary(legacy), /Lowest: Tempe Riverside at 34.1/);
});
test("highest requests lead with the requested statistic while retaining both extremes", () => {
  const request = {
    ...legacy,
    request: { ...legacy.request, question: "Which location is hottest?" },
  };
  assert.equal(questionFocus(request.request.question), "highest");
  assert.match(comparisonSummary(request), /^Highest:/);
  assert.match(comparisonSummary(request), /Lowest:/);
});
test("tied maxima remain visible as multiple sites", () => {
  const result = {
    ...legacy,
    comparison: {
      ...legacy.comparison,
      highest_c: 36.7,
      highest_locations: ["Phoenix Civic Plaza", "Scottsdale Courtyard"],
    },
  };
  assert.deepEqual(highestReading(result).names, [
    "Phoenix Civic Plaza",
    "Scottsdale Courtyard",
  ]);
});

test("ordinary comparative wording keeps the requested focus", () => {
  assert.equal(questionFocus("Which one is hotter?"), "highest");
  assert.equal(questionFocus("Which is warmer?"), "highest");
  assert.equal(questionFocus("Which is cooler?"), "lowest");
  assert.equal(questionFocus("Which is colder?"), "lowest");
});
