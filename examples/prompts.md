# Example prompts

## Complete request

Use HeatBrief's `create_briefing` tool with `examples/request.json`. Compare Phoenix Civic Plaza (33.4484, -112.074), Tempe Riverside (33.4255, -111.94), and Scottsdale Courtyard (33.4942, -111.9261) for 2025-09-20 at 14:00 America/Phoenix. Explain the lowest returned temperature and cite the evidence IDs, units, coordinates and timestamps. Keep the Mock data label. Prepare an unsent follow-up for the fictional Acme Demo Events client.

Expected calculation: Tempe Riverside, 34.1 °C; spread 2.6 °C. This is fictional demonstration data.

## Clarification needed

Compare Phoenix, Tempe and Scottsdale for an outdoor visit next Saturday afternoon. Prepare the client report.

Expected assistant behavior: ask for exact coordinates, date, time and timezone before calling the tool. Do not silently geocode or infer missing inputs. The fixed mock only supports the documented fixture.

## Unsupported data

Use the fixture coordinates and America/Phoenix timezone, but request 2030-01-01 at 14:00. Explain any limitation without inventing data.

Expected behavior: explicit unsupported-date error. No report with invented measurements.

## Incomplete evidence

If a source returns a missing reading, compare only the available readings, label the comparison incomplete, and explain what remains unknown. Never substitute zero for missing data.

## Retrieval and duplicate request

Read `demo-phoenix-001` using `read_briefing`. Repeating an identical creation request should return the saved briefing. Changed content needs a new request ID.
