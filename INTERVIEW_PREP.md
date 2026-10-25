# Interview preparation — explain the decisions, not just the interface

This project was implemented with substantial AI assistance. Before using it as evidence of your ability, personally run, inspect and modify it. Use the prompts below as checks of understanding, not a memorized script.

## 1. What question does the project investigate?

How earning an execution edge competes with inventory exposure and opportunities to trade. Compare Fixed, Inventory and Adaptive across 100 matched paths in each of five synthetic regimes. There is no single objective that makes one strategy universally best. **Do yourself:** explain the Stable and Adverse selection rows without looking at prepared text.

## 2. How can a market maker lose despite a positive spread?

Inventory can move against the dealer, fees consume execution edge, and informed customers can trade just before unfavorable price moves. Mark-to-market P&L includes these effects. **Do yourself:** calculate the buy-at-99, sell-at-102 accounting example and fees in the Chinese guide.

## 3. Why lower the quote centre when long?

It makes the bid less attractive to sellers and the ask more attractive to buyers, tending to sell inventory. This gives up price to reduce exposure. Boundary clipping can prevent crossing the reference. **Do yourself:** write both quotes for q=4 and explain why the ask is clipped.

## 4. What makes the comparison fair?

Generate reference prices, latent directions, arrival uniforms and acceptance uniforms once per seed. Reuse them for each dealer, with strategy-specific acceptance thresholds. Do not draw additional randomness conditionally on fills. These are separate counterfactual markets, so there is no claim of simultaneous competition for one order. **Do yourself:** locate `make_tape` and show deterministic replay.

## 5. How did you avoid look-ahead bias?

The policy receives a frozen observation with only S[0] through S[t], cash and inventory. Volatility uses completed returns and a fixed warm-up prior. The engine alone consumes the future tape. Tests alter a future suffix and check earlier policy behavior is unchanged. This is an interface discipline, not a malicious-code sandbox. **Do yourself:** explain every field in `Observation`.

## 6. What is adverse selection here?

D is the arriving customer's direction; the next innovation contains ρD. A customer buy predicts a rise after the dealer sells, and a sell predicts a fall after the dealer buys. Higher variance without this information link would be a different stress. **Do yourself:** derive E[Z|D]=ρD and Var(Z)=1. Note that Z is not Gaussian and that the lognormal drift correction is approximate in this scenario.

## 7. What do the results actually show?

Stable Inventory−Fixed mean P&L is −1.312 CU with a paired 95% interval [−2.279,−0.346]; mean absolute inventory falls 75.0%. In adverse selection Adaptive−Inventory is +4.533 CU [4.085,4.982], while Adaptive's own mean remains −0.305 CU. A relative improvement is not proof of profitability. **Do yourself:** rerun at new seeds and see how these estimates move.

## 8. What does the confidence interval mean?

For each seed calculate the strategy difference, then estimate its mean and standard error across independent seeds. A t interval measures Monte Carlo mean uncertainty conditional on the fixed model. Path percentiles describe individual-outcome dispersion. Neither protects against wrong fill assumptions; many intervals are reported without multiplicity adjustment. **Do yourself:** rebuild one mean difference from the raw CSV.

## 9. How realistic are the fills and historical data?

Distance-dependent acceptance is an assumed curve with at most one unit per second. No queue, latency, impact, competition or calibrated demand. A small real BTC minute sample gives descriptive volatility context only; it never establishes execution. Terminal inventory is marked, not costlessly liquidated. **Do yourself:** distinguish an execution quote, a reference mark and a candle close.

## 10. What would you change next, and what did AI do?

First isolate spread widening from volatility-scaled skew, compare informative and uninformative flow at matched volatility, and model explicit liquidation costs. Avoid adding complexity without a testable question. The delivered code, tests, UI, scripts and documents were generated/debugged with AI; the supplied requirements came from the student. Do not claim independent implementation or original strategy invention without doing the work. **Do yourself:** choose one small change, predict its effect, implement/test it and record what happened. Be able to debug `advance` on a short hand-constructed tape.

## A concise demonstration (about five minutes)

1. Play Stable seed42 for one round; explain cash versus equity and a long position.
2. Pause bid or lower the centre; advance and show inventory/trades. Replay to explain matched inputs.
3. Open Research, compare stable and adverse regimes; show distribution and paired interval.
4. Explain one disappointing result and one modeling limitation.
5. Open the deterministic accounting test. State clearly which parts you personally ran, checked or modified and which came from AI assistance.


## Follow-up discussion prompts

- How do Width only and Skew only identify the controls changed by Adaptive?
  Explain the 2×2 policy table and why an interaction need not be zero.
- Why is identical-price independent flow a better mechanism control than
  comparing Stable and Adverse selection? Identify exactly which tape changed.
- Why did a fresh-seed replication weaken the original mean-profit ranking?
  Distinguish unstable path averages from the much more consistent inventory
  reduction, and avoid selecting only the favorable seed batch.

These are discussion prompts beyond the original ten questions. The follow-up
was also AI-assisted; personally reproduce and explain it before claiming it as
an independent contribution.
