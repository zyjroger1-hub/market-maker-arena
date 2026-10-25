# Changes

## v0.2.0 — 25 October 2026

- Add Width only and Skew only controls to isolate the two volatility responses
  combined by Adaptive. Keep the original three-policy defaults and results.
- Add an independent-customer-flow counterfactual with exactly identical stress
  reference prices, arrival draws and acceptance draws.
- Publish a prewritten follow-up plan, 2,000 new strategy runs on disjoint seeds,
  raw data, two additional figures and MECHANISM_REPORT.md. Preserve seed-sensitive
  and unfavorable findings; do not claim a universally profitable policy.
- Expose saved five-policy results, optional controls, the information switch,
  matched-flow contrasts and applied-config downloads in Research.
- Refresh the Play quote preview immediately when controls change, without
  advancing time or submitting a trade.
- Reject incomplete, duplicate and nonfinite paired samples rather than silently
  dropping pairs. Validate integer seed sets and estimation windows.
- Expand automated verification from 36 to 59 passing tests and independently
  recompute 116 additional contrast intervals. Record regression fingerprints
  against the initial public release; original raw run CSVs remain byte-identical.
- Update the learning guide, interview prompts and conditional AI-assisted CV
  wording. Total planned study executions are 5,480 strategy runs, not independent
  price paths. No public interactive hosting is introduced in this release.
