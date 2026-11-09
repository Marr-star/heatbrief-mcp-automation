# Example prompts

## Complete request

Use HeatBrief's `create_briefing` tool with `examples/request.json`. Compare Phoenix Civic Plaza (33.4484, -112.074), Tempe Riverside (33.4255, -111.94), and Scottsdale Courtyard (33.4942, -111.9261) for 2025-09-20 at 14:00 America/Phoenix. Explain the lowest returned temperature and cite the evidence IDs, units, coordinates and timestamps. Keep the Mock data label. Prepare an unsent follow-up for the fictional Acme Demo Events client.

Expected calculation: Tempe Riverside, 34.1 °C; spread 2.6 °C. This is fictional demonstration data.

## Clarification needed

Compare Phoenix, Tempe and Scottsdale for an outdoor visit next Saturday afternoon. Prepare the client report.

Expected assistant behavior: ask for exact coordinates, date, time and timezone before calling the tool. Do not silently geocode or infer missing inputs. The mock supports every minute from 2025-01-01 00:00 through 2027-12-31 23:59 America/Phoenix inclusive at the three demo sites.

## Unsupported data

Use the fixture coordinates and America/Phoenix timezone, but request 2030-01-01 at 14:00. Explain any limitation without inventing data.

Expected behavior: explicit unsupported-date error. No report with invented measurements.

## Incomplete evidence

If a source returns a missing reading, compare only the available readings, label the comparison incomplete, and explain what remains unknown. Never substitute zero for missing data.

## Retrieval and duplicate request

Read `demo-phoenix-001` using `read_briefing`. Repeating an identical creation request should return the saved briefing. Changed content needs a new request ID.


## More dates and times

Compare the three demo sites on 2025-09-09 at 14:00 America/Phoenix.

Compare the three demo sites on 2026-07-15 at 15:37 America/Phoenix.

Compare the three demo sites on 2026-11-09 at 18:45 Africa/Cairo.

Each request produces generated mock readings for that instant. Keep the synthetic label and cite its timestamp-specific evidence IDs. Use a new request ID when changing the date/time.


## Chat commands that run directly

Which is hottest among all demo sites on July 17, 2026 at noon Cairo time?

Compare all demo sites and show both the highest and lowest temperatures.

If the second request is missing a date/time/timezone, reply: July 16, 2026 at 4:12pm Phoenix time. The pending comparison runs directly, without selecting locations or pressing Run comparison.

Follow-ups: Which is highest? Which is lowest? What is the average? Show the ranking. What does spread mean? What is n8n?

To prepare without executing: Just prepare, don't run. Compare all demo sites on 2026-07-15 at 15:37 America/Phoenix. Then say: Run it.
