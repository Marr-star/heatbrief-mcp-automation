import assert from "node:assert/strict";
import test from "node:test";
import { demoTimeIssue } from "../src/demo.ts";

const coverage = {
  start: "2025-01-01T00:00:00-07:00",
  end: "2027-12-31T23:59:00-07:00",
  start_date: "2025-01-01",
  start_time: "00:00",
  end_date: "2027-12-31",
  end_time: "23:59",
  timezone: "America/Phoenix",
  step_minutes: 1,
  presets: [],
};
const issue = (date, time, timezone = "America/Phoenix") =>
  demoTimeIssue({ date, time, timezone }, coverage);

test("admits many dates and arbitrary minutes, including both endpoints", () => {
  for (const [date, time] of [
    ["2025-01-01", "00:00"],
    ["2025-09-09", "14:00"],
    ["2026-07-15", "15:37"],
    ["2027-12-31", "23:59"],
  ]) {
    assert.equal(issue(date, time), null);
  }
});
test("rejects one minute before and after the inclusive window", () => {
  assert.match(issue("2024-12-31", "23:59"), /Outside the demo window/);
  assert.match(issue("2028-01-01", "00:00"), /Outside the demo window/);
});
test("converts the entered IANA timezone before comparing bounds", () => {
  assert.equal(issue("2025-01-01", "07:00", "UTC"), null);
  assert.equal(issue("2028-01-01", "06:59", "UTC"), null);
  assert.match(issue("2025-01-01", "06:59", "UTC"), /Outside/);
  assert.match(issue("2028-01-01", "07:00", "UTC"), /Outside/);
  assert.equal(issue("2026-11-09", "18:45", "Africa/Cairo"), null);
});
test("does not guess a DST gap or repeated local hour", () => {
  assert.match(issue("2025-03-09", "02:30", "America/New_York"), /unambiguous/);
  assert.match(issue("2025-11-02", "01:30", "America/New_York"), /unambiguous/);
  assert.equal(issue("2025-11-02", "03:30", "America/New_York"), null);
});
test("rejects invalid local fields and unknown zones", () => {
  assert.match(issue("2025-02-30", "12:00"), /valid/);
  assert.match(issue("2026-07-15", "24:00"), /valid/);
  assert.match(issue("2026-07-15", "12:00:30"), /valid/);
  assert.match(issue("2026-07-15", "12:00", "Unknown/Zone"), /timezone/);
  assert.equal(issue("", ""), null);
});
