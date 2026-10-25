"""Follow-up report: every numerical finding is read from the current CSVs."""
from pathlib import Path
import json
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];R=ROOT/'RESULTS/mechanisms'
s=pd.read_csv(R/'ablation_summary.csv');p=pd.read_csv(R/'ablation_pairs.csv')
f=pd.read_csv(R/'flow_control_summary.csv');fp=pd.read_csv(R/'flow_control_pairs.csv')
d=pd.read_csv(R/'tape_diagnostics.csv');m=json.loads((R/'manifest.json').read_text())


def cell(scenario,name):return s[(s.scenario==scenario)&(s.strategy==name)].iloc[0]
def diff(scenario,contrast):
    r=p[(p.scenario==scenario)&(p.contrast==contrast)&(p.metric=='pnl')].iloc[0]
    return f'{r.mean_difference:+.3f} CU [{r.ci_low:+.3f}, {r.ci_high:+.3f}]'
def table(df,columns):
    lines=['| '+' | '.join(v for _,v in columns)+' |','|'+'---|'*len(columns)]
    for _,r in df.iterrows():
        lines.append('| '+' | '.join(str(r[k]) if isinstance(r[k],str) else f'{r[k]:.3f}' for k,_ in columns)+' |')
    return '\n'.join(lines)

w=cell('Adverse selection','Width only');a=cell('Adverse selection','Adaptive')
report=f'''# Mechanism study — width, skew and informative fills

Follow-up recorded 25 October 2026 · all amounts fictional CU · no real trading results.

## What this adds

The original Adaptive policy changed two controls at once. This follow-up uses
a 2×2 inventory-policy design to separate them, then holds stress prices exactly
fixed while replacing informative customer directions with independent ones.
It also re-evaluates the original policies on a fresh seed set. This is an
exploratory follow-up motivated by the original results, not a claim that those
mechanisms were isolated in the original study.

The [addendum plan](RESEARCH_ADDENDUM_PLAN.md) was saved before these experiments.
No coefficients were tuned. Each case uses 100 new matched seeds (30000–30099),
disjoint from all original seed sets. Three scenarios × five policies = 1,500
ablation runs; an additional 500 independent-flow runs give **{m['new_strategy_runs']:,}
new strategy runs**. The 500 informed stress rows are reused in the flow-control
CSV, not counted a second time. Along with the original 3,480 strategy runs,
there are **5,480 research runs**. This count is not the number of independent
market paths. The extension took {m['elapsed_seconds']:.1f} seconds on this Mac.

## Policies and fixed conditions

Inventory uses centre S−κq and width h. Width only changes width to hr; Skew only
changes centre to S−κqr². Adaptive changes both. Both added controls still manage
inventory: "only" refers to the volatility-dependent adjustment. Fixed provides
context. Defaults remain h=0.05 CU, κ=0.015 CU/unit, 30-return RMS and a fixed
0.04 CU/√second warm-up prior. Every policy receives current/past prices only.
Same fees, caps, quote clipping, 600-second horizon and terminal mark-to-market
convention as the [original model](MODEL.md). No terminal closing trade is added.

## Factorial outcomes

{table(s,[('scenario','Scenario'),('strategy','Policy'),('pnl_mean','Mean net P&L'),('mean_drawdown','Mean max DD'),('avg_abs_inventory','Mean abs inventory'),('mean_fills','Mean fills')])}

[All 1,500 rows](RESULTS/mechanisms/ablation_runs.csv) ·
[Means, SD, percentiles and intervals](RESULTS/mechanisms/ablation_summary.csv) ·
[All paired contrasts](RESULTS/mechanisms/ablation_pairs.csv)

![Ablation contrasts](RESULTS/figures/ablation_effects.png)

Intervals are two-sided 95% Student t intervals on seed-level differences;
shared horizontal scales permit comparison. They are unadjusted for multiple
comparisons. The interaction is Adaptive−Width only−Skew only+Inventory. It
measures departure from adding the two isolated effects, not a regression fitted
to real market data. Secondary risk/fill contrasts are saved alongside P&L.

In adverse selection, Width only−Inventory is
**{diff('Adverse selection','Width only - Inventory')}**. Strengthening skew
alone gives **{diff('Adverse selection','Skew only - Inventory')}**. Adaptive−Width
only is **{diff('Adverse selection','Adaptive - Width only')}**. Thus the combined
policy's improvement in this stress comes primarily from its width adjustment;
stronger skew is costly here. Width only's own mean is {w.pnl_mean:+.3f} CU
(marginal 95% interval [{w.pnl_ci_low:+.3f}, {w.pnl_ci_high:+.3f}]); Adaptive's is
{a.pnl_mean:+.3f} CU. This positive toy-market mean for Width only does not establish
an executable edge or robustness outside these fixed assumptions. The original
fee/volatility sensitivities covered three policies, not these new controls.

A plausible model mechanism is that stronger skew repeatedly offers a closer
inventory-reducing quote to informative customers, sacrificing execution edge.
The ablation establishes the policy effect within the simulator; it does not
identify every individual fill-level causal pathway.

In High volatility, Width only−Inventory is
**{diff('High volatility','Width only - Inventory')}**, and the combined policy's
interaction is **{diff('High volatility','Interaction (width x skew)')}**. The
controls do not simply add: inventory feedback, distance-dependent acceptance
and clipping make the response nonlinear. Lower inventory exposure, lower
drawdown, fewer fills and higher profit remain distinct objectives.

## Replication changes how strongly the original ranking should be stated

On these fresh Stable seeds, Inventory−Fixed is
**{diff('Stable','Inventory - Fixed')}**. Compare the original −1.312 CU
[−2.279, −0.346]. The new interval crosses zero. Inventory exposure and drawdown
remain much lower, but the original stable-market mean-profit penalty is not a
reliable universal ranking across these two finite seed batches. Fixed has
substantial path dispersion; preserve both batches rather than choosing one.
Similarly, differences involving Fixed in High volatility are sensitive to
which paths were sampled. Do not pool or cherry-pick scenarios to manufacture
confidence. No claim of a uniformly best policy is supported.

## Same prices, independent customer directions

The control leaves every reference value, arrival uniform and acceptance uniform
unchanged for each seed. The original latent sign continues to generate the
stress prices. Only the direction of the arriving customer is replaced using a
separate deterministic random stream. Thus volatility, jumps (none in this
case), price distribution and the realized price path cannot explain a
stress/control difference. This is stronger than comparing the original Stable
and Adverse selection scenarios, which also changed volatility.

All {len(d)} seed pairs passed exact array equality checks for prices and both
uniform tapes. Mean within-path direction/next-log-return correlation is
**{d.informed_direction_correlation.mean():.4f}** for informed flow and
**{d.independent_direction_correlation.mean():.4f}** for independent flow. The
latter fluctuates around zero in finite samples. Strategy-specific fills can
differ because arriving directions and subsequent inventories differ.

![Same-price information control](RESULTS/figures/flow_control.png)

{table(fp[fp.metric=='pnl'],[('strategy','Policy'),('mean_difference','Informed minus independent'),('ci_low','95% low'),('ci_high','95% high')])}

The right panel and table use paired mean intervals; the left panel uses marginal
mean intervals. Do not compare marginal-interval overlap as a significance test.
Every saved P&L interval here is below zero: the information link harms all five
policies on this seed batch, even though wider quotes reduce the damage. This is
a counterfactual result inside an explicitly imposed model, not measured causal
evidence about a real exchange.

[Raw control rows](RESULTS/mechanisms/flow_control_runs.csv) ·
[Control summaries](RESULTS/mechanisms/flow_control_summary.csv) ·
[All control contrasts](RESULTS/mechanisms/flow_control_pairs.csv) ·
[Direction diagnostics and price hashes](RESULTS/mechanisms/tape_diagnostics.csv)

## Verification, limitations and reproduction

The added tests check isolated policy formulas, historical-only observations,
exact preservation of the original market tapes, equal stress/control price
and uniform arrays, loss of directional information, deterministic control
replay, and rejection of incomplete/nonfinite paired samples. An independent
saved-row audit recomputes all factorial and flow intervals. Main-study CSV
metrics were checked against the original release and remained unchanged.
See [VALIDATION.md](VALIDATION.md) for test counts and browser evidence.

These checks strengthen internal validity. They do not validate the assumed
fill curve, calibrate real customer behavior, model queues/latency/impact,
account for financing or price a real terminal liquidation. The original
adverse shock is a non-Gaussian mixture; its −σ²/2 log drift correction remains
approximate. That approximation is identical in both matched flow conditions.
Only three selected regimes and one skew/width configuration are included in
the ablation. Further parameter stress tests, transaction-level decomposition
and out-of-model evaluation would be needed before generalizing its ranking.

Run `bash reproduce.sh` for both studies, charts, reports and audits. No data
network is needed after installing dependencies. In Research, load Mechanism
study, or enable width/skew controls for new runs. The Informative customer flow
checkbox creates the same-price counterfactual in Adverse selection only.
'''
(ROOT/'MECHANISM_REPORT.md').write_text(report)
print('Follow-up report generated from saved rows')
