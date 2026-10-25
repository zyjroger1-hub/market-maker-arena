# Follow-up research plan — fixed before the added experiments

25 October 2026. Follow-up to the published original study, commit
`5abf0eadc587fdac3ee38160fd6c4bf62b4a96e3`. The original plan, default policies,
seed sets and findings remain identifiable. This extension was motivated by
limitations observed in the original results; it is a follow-up, not a new
claim that the original analysis isolated these mechanisms.

## Questions and fixed design

1. Does volatility-driven spread adjustment or volatility-driven inventory skew
   account for the combined Adaptive policy's behavior?
2. What changes when the same stress price tape is paired with customer directions
   that contain no information about its pending price move?

Use original Config defaults, h=0.05, skew=0.015, 30-return RMS window and
0.04 CU/sqrt(second) warm-up prior. No tuning or policy selection. New evaluation
seeds **30000–30099**, disjoint from all original study seed sets.

The inventory-policy factorial design is:

| Policy | Centre | Half-spread |
|---|---|---|
| Inventory | S − κq | h |
| Width only | S − κq | h r |
| Skew only | S − κq r² | h |
| Adaptive | S − κq r² | h r |

Here "only" refers to the volatility-dependent control; both added policies still
include inventory management. Include Fixed as context. Run all five policies
on Stable, High volatility and Adverse selection: 3 × 100 × 5 = **1,500 runs**.

For each original Adverse selection tape, construct an independent-flow control:
keep **exactly** the same reference path, arrival uniforms and acceptance
uniforms; replace only the quoted-to customer directions with independent
Rademacher draws from a deterministic separate NumPy SeedSequence([seed, 20261025])
stream. Prices continue to use the original latent directions internally. Do
not set rho to zero in the price equation, which would change the realized path
and its distribution. Policies receive neither latent nor arriving directions
before quoting. Add 100 × 5 = **500 independent-flow policy runs**. The informed
500 rows are reused from the ablation, not counted twice. Total extension:
**2,000 new strategy runs**, not 2,000 independent market paths.

## Endpoints and inference

Retain net terminal mark-to-market P&L as primary, and mean absolute inventory,
maximum drawdown and fills as secondary. No free terminal liquidation or new
cost model. Paired contrasts per scenario:

- Width only − Inventory; Skew only − Inventory.
- Adaptive − Width only; Adaptive − Skew only.
- Factorial interaction: Adaptive − Width only − Skew only + Inventory.

For each policy compare informed − independent flow on matched seeds. Negative
P&L differences quantify damage from the information link within this
counterfactual model. Report two-sided 95% Student t intervals on seed-level
linear contrasts, with no multiplicity correction. These are exploratory,
model-conditional intervals. Do not infer real-market causality or profits.

Save raw runs, seed lists, exact config, paired contrasts, source/plan hashes,
timing, direction/next-log-return correlations, and equality checks for shared
tapes. Preserve unfavorable results. No learning or tuning seeds are used in
this extension. Verify original seed-level metrics remain numerically unchanged.

## Engineering checks

Test isolated strategy formulas, causal prefixes for all five policies,
unchanged original tapes, equal stress/control price and uniform arrays,
independent-flow sign correlation, and strict rejection of incomplete/nonfinite
paired samples. Make both controls available in Research with applied-config
exports. Inspect the page and figures. Re-run the original study, extension and
independent audits before updating GitHub. No website hosting is included.
