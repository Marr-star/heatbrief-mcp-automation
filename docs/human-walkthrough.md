# HeatBrief customer walkthrough

Tested on November 9, 2026 in the actual local browser at http://127.0.0.1:8001/.

The story tested was: type a comparison, revise the time and sites conversationally, ask about the result, inspect evidence, prepare a client draft, retrieve it from history, download it, and recover from an invalid date. No form selections or Run-comparison clicks were used to start the conversational comparisons.

## Problems found and fixed

1. **“Just Tempe and Scottsdale” was ignored.** Contextual short names now resolve to the existing named demo points, and narrowing the selection preserves its date/time/timezone. Fresh ambiguous cities still require an exact site choice; this does not geocode arbitrary cities.
2. **“Which one is hotter?” returned generic instructions.** Hotter/warmer and cooler/colder now answer from the saved ranking without another workflow run.
3. **The report retained stale request wording.** After changing 2pm to 5pm and three sites to two, its description still mentioned the original parameters. New refined requests now describe their actual selected sites, time and timezone, preserving the requested statistical focus. Previously saved reports are retained as historical records.
4. **One PDF limitation bullet was orphaned across a page break.** The limitations heading and list now stay together. The regenerated two-page PDF was visually inspected.

## Browser results

| Customer action | Observed result |
|---|---|
| “Compare all three demo locations on November 10, 2026 at 2 pm Phoenix time.” | Started automatically; n8n execution 29 completed, three sites, lowest 23.1 °C and highest 27.0 °C. |
| “Actually, make it 5pm.” | Execution 30 completed at 17:00; date/timezone/sites were retained. Lowest 22.4 °C and highest 26.6 °C. |
| “Just Tempe and Scottsdale.” | Failed initially; after the fix, execution 31 compared only Tempe Riverside and Scottsdale Courtyard at 17:00. |
| “Which one is hotter?” | Failed initially; after the fix, answered Scottsdale Courtyard at 26.6 °C with a 4.2 °C spread, using the saved result. |
| “Show me the proof.” | Opened Evidence with exactly two matching source records, their coordinates, timestamps, units and expanded source IDs. |
| Open the client briefing | Revealed stale wording initially. Execution 32 produced the corrected two-site/17:00 request description and matching report/draft. |
| Edit draft, save, search history, reopen | The test note “Human walkthrough: verified the two-site request at 17:00” persisted and was restored from the saved briefing. |
| Download PDF | Browser download succeeded. Both temperatures, correct request details, mock labels, evidence IDs and the saved edit were present. The two-page layout was rendered and checked. |
| “Make it January 1, 2030 at 5pm.” | Clear inclusive-window explanation; Run comparison disabled; no comparison was started. |
| “Sorry, use November 10, 2026 instead.” | Recovered in chat and completed execution 33 with the two selected sites at 17:00, without re-entering the other details. |

Run IDs, completed states, dates, times, site counts and extrema were also checked in the persisted workspace data. The browser's error-console capture was empty at the end of the walkthrough. One browser session expired during a development-server code reload; refreshing restored it before continuing.

## Regression checks

- 118 Python tests passed.
- 9 frontend tests passed.
- Ruff lint and formatting passed; React/TypeScript production build passed.
- Added regressions for contextual selection, adding/removing sites, timezone mentions, read-only site questions, comparative words, and consistency of refined/prepared request descriptions.

## Scope

This verifies the local guided assistant and synthetic temperature workflow. It does not establish live weather accuracy, general-purpose conversation coverage, an external model connection, email delivery or a real reviewer approval. A test edit was saved on the newly generated execution-32 briefing; no approval or sending action was performed.
