"""Generate a compact English report from the actual experiment CSV files."""
from pathlib import Path
import json
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
R=ROOT/"RESULTS"
s=pd.read_csv(R/"summary.csv"); p=pd.read_csv(R/"paired_comparisons.csv")
sens=pd.read_csv(R/"sensitivity_summary.csv"); manifest=json.loads((R/"run_manifest.json").read_text())


def row(scenario,strategy):
    return s[(s.scenario==scenario)&(s.strategy==strategy)].iloc[0]


def contrast(scenario,a,b):
    x=p[(p.scenario==scenario)&(p.contrast==f"{a} - {b}")&(p.metric=="pnl")].iloc[0]
    return f"{x.mean_difference:+.3f} CU (95% paired CI {x.ci_low:+.3f} to {x.ci_high:+.3f})"


def markdown_table(frame,columns):
    lines=["| "+" | ".join(label for _,label in columns)+" |","|"+"---|"*len(columns)]
    for _,r in frame.iterrows():
        vals=[r[k] if isinstance(r[k],str) else f"{r[k]:.2f}" for k,_ in columns]
        lines.append("| "+" | ".join(vals)+" |")
    return "\n".join(lines)

stable_f=row("Stable","Fixed"); stable_i=row("Stable","Inventory")
h_i=row("High volatility","Inventory");h_a=row("High volatility","Adaptive")
a_i=row("Adverse selection","Inventory");a_a=row("Adverse selection","Adaptive")
report=f"""# Market Maker Arena — research report

25 October 2026 · Synthetic simulation study · Currency units (CU), no real trading results

## Question and answer

How does a market maker balance execution edge, inventory exposure and opportunities to trade? Inventory skew reduced exposure and drawdown, with a profit cost in the stable toy market. Adding trailing-volatility adaptation traded less during noisy periods. It reduced loss under explicitly informative customer flow, yet did not establish a positive expected profit there. There is no universal winner across the chosen objectives.

## Method fixed before the main experiment

The [research plan](RESEARCH_PLAN.md) fixes the three policies, primary net terminal P&L endpoint, secondary risk/execution measures, seeds and sensitivities. Each of five scenarios has **100 independent price/customer tapes** (seeds 10000–10099), reused by all three strategies: **{manifest['main_runs']:,} main strategy runs**. Each run is 600 one-second steps, starting at S=100, cash=10,000 and inventory zero; cap ±10 units and a 0.5 bp fee per filled notional. Quotes precede customer arrivals/fills; prices change afterward. All terminal positions are marked to reference, without a closing trade.

Fixed quotes symmetrically. Inventory shifts the centre by −0.015q CU. Adaptive uses only the last 30 completed price changes to scale both width and inventory skew. It has a fixed volatility prior during warm-up. The engine gives policies only an immutable current/past observation. [MODEL.md](MODEL.md) specifies equations, units, event order and limits.

The price is a positive log process. A synthetic arriving customer accepts a quote with exponentially decreasing probability in its distance from reference. At most one unit fills per second; it is a Bernoulli arrival cap, not a full Poisson count model or an order-book simulation. The adverse-selection scenario makes customer direction predict the next price innovation (ρ=0.85). High volatility alone leaves direction uninformative.

Exploration used seeds 1000–1019 and three skew settings, **{manifest['exploration_runs']:,} runs**; it did not select the already-fixed primary parameters. Separate sensitivity seeds 20000–20029 generated **{manifest['sensitivity_runs']:,} runs**. All default-design runs completed in {manifest['elapsed_seconds']:.1f} seconds on this Mac (environment in the manifest; timing is machine-specific). There were no changes to the initial experiment design. UI fixes and independent verification followed the first run; the final saved experiment was rerun against the delivered engine.

## Main results

All numbers below are means across 100 paths. P&L is after fees; drawdown is the maximum step-end equity drop from its running peak. Inventory is the time-average of absolute units.

{markdown_table(s,[("scenario","Scenario"),("strategy","Policy"),("pnl_mean","Net P&L"),("pnl_sd","P&L SD"),("mean_drawdown","Max DD"),("avg_abs_inventory","Mean abs inventory"),("mean_fills","Fills")])}

[Exact summary including percentiles and marginal mean intervals](RESULTS/summary.csv) · [Seed-level results](RESULTS/main_runs.csv)

![P&L distributions](RESULTS/figures/pnl_distributions.png)

The boxes describe the spread of path outcomes. They are not confidence intervals. Separate panel scales are explicit. A high mean in one small sample can coexist with substantial downside risk.

### 1. Inventory control buys stability at a cost

In Stable, mean absolute inventory falls from {stable_f.avg_abs_inventory:.3f} to {stable_i.avg_abs_inventory:.3f} units, a {100*(1-stable_i.avg_abs_inventory/stable_f.avg_abs_inventory):.1f}% reduction. Mean maximum drawdown falls from {stable_f.mean_drawdown:.3f} to {stable_i.mean_drawdown:.3f} CU. The paired P&L change Inventory−Fixed is {contrast('Stable','Inventory','Fixed')}. Stronger control executes more inventory-reducing quotes near reference, giving up execution edge. It also avoids spending as much time stuck at a cap, so lower inventory need not mean fewer fills.

In Trend the same P&L contrast is {contrast('Trend','Inventory','Fixed')}; that interval crosses zero. A positive sample mean difference is insufficient to establish a mean-profit improvement even within this model. Across scenarios Fixed and Inventory have identical fill counts for a given seed because their absolute quote distances and direction rules do not use price moves, and clipping bounds are unchanged at these prices. The P&L differs through mark-to-market holding risk.

### 2. Volatility adaptation sacrifices opportunities

In High volatility, Adaptive versus Inventory reduces mean fills from {h_i.mean_fills:.2f} to {h_a.mean_fills:.2f}, mean absolute inventory from {h_i.avg_abs_inventory:.3f} to {h_a.avg_abs_inventory:.3f}, and mean maximum drawdown from {h_i.mean_drawdown:.3f} to {h_a.mean_drawdown:.3f} CU. The paired P&L change is {contrast('High volatility','Adaptive','Inventory')}. Here protection costs average profit. The strategy cannot anticipate regime changes or jumps; its estimates lag.

Adaptive changes both spread and skew strength, so this is a combined policy effect. The original study does not isolate widening alone. The [follow-up mechanism study](MECHANISM_REPORT.md) now adds width/skew controls on fresh seeds.

### 3. Informative fills change the economics

In Adverse selection, Inventory averages {a_i.pnl_mean:+.3f} CU and Adaptive {a_a.pnl_mean:+.3f} CU. Their paired difference is {contrast('Adverse selection','Adaptive','Inventory')}. Mean fills fall from {a_i.mean_fills:.2f} to {a_a.mean_fills:.2f}. Near S=100 the imposed information link creates approximately 0.068 CU of unfavorable immediate directional movement for a dealer fill, before the quoted edge and fees. Wider, less frequent quotes can reduce exposure to this mechanism.

Adaptive's marginal 95% interval for mean P&L is [{a_a.pnl_ci_low:+.3f}, {a_a.pnl_ci_high:+.3f}] CU. Improvement over another policy does not mean profitability. The adverse scenario differs from Stable in both volatility and directional information; their whole P&L difference is not an isolated causal estimate of adverse selection. The follow-up holds the realized stress price paths fixed and replaces only customer directions.

![Paired P&L effects](RESULTS/figures/paired_pnl.png)

Intervals use mean paired seed differences ± t(0.975,n−1) × SD(difference)/√n. They are approximate Monte Carlo intervals conditional on this model. The comparison family is unadjusted for multiplicity; avoid broad significance claims. SD/quantiles describe path dispersion; these intervals describe uncertainty in a mean difference. Neither measures model error.

## Risk and execution opportunity

![Risk and opportunity](RESULTS/figures/risk_opportunity.png)

Each mark is a scenario-policy mean across 100 paths. These descriptive plots encode no uncertainty. Inventory controls compress the range of inventory and drawdown. Informed customers can make extra fills harmful. There is no annualized Sharpe ratio for a ten-minute synthetic path.

![Predetermined example path](RESULTS/figures/example_path.png)

This is the preselected seed 10000, not a favorable example chosen after observing outcomes. Shaded high-volatility periods show estimation lag. The hard cap is visible. [All 15 example paths](RESULTS/representative_paths.csv) and [their fills](RESULTS/representative_fills.csv) are retained for accounting inspection.

## Robustness and sensitivity

Each factor is changed alone in Stable and Adverse selection, with 30 matched seeds per setting. Controls include the base setting on the same sensitivity seeds. These smaller exploratory estimates are less precise than the main experiment. [Full settings and means](RESULTS/sensitivity_summary.csv), [paired intervals](RESULTS/sensitivity_pairs.csv), and [raw runs](RESULTS/sensitivity_runs.csv) retain poor outcomes.

![Sensitivity results](RESULTS/figures/sensitivity.png)

Higher fees reduce net P&L without changing quotes/fills because these policies do not optimize for fees. For Adaptive in Adverse selection on sensitivity seeds, mean P&L is +0.388 CU at zero fees, −0.069 at 0.5 bp and −1.439 at 2 bps. The slight zero-fee positive mean is not robust evidence of an edge. Higher arrival intensity increases both benign opportunities and exposure to informative flow. Loosening the cap mainly changes Fixed, whose inventory is less constrained by skew. Doubling volatility leaves all policies with negative mean P&L in the adverse scenario; the Adaptive mean is −2.735 CU. No parameter configuration is marketed as optimal.

## Optional public data context

One [Binance Vision BTCUSDT 1-minute daily archive](https://data.binance.vision/data/spot/daily/klines/BTCUSDT/1m/BTCUSDT-1m-2025-01-06.zip), 6 January 2025 UTC, was downloaded on 25 October 2026. Its official SHA256 matches. All 1,440 rows have 12 columns, unique gap-free microsecond timestamps and positive consistent OHLC. No rows were dropped or imputed. The first 12 hours give a one-minute log-return SD of 0.000469; the held-out last 12 hours give 0.000665 (719 returns each, boundary return excluded). See [provenance, units and usage terms](data/README.md).

These are descriptive real-price estimates. They do **not** set simulator defaults: the synthetic base 0.0004 /√second is deliberately different from a minute estimate. No conversion or calibration is silently applied, no historical fills are constructed, and no historical P&L is reported. Minute closes are not a complete order book. The core simulation and saved results are offline. Dataset-derived material carries Binance Vision attribution and the dataset's CC BY-NC-SA 4.0 terms.

## Verification and limitations

Every run verifies cash, inventory and fees plus the exact P&L decomposition into execution edge, inventory holding P&L and fees. Maximum main-run accounting residual is {manifest['max_accounting_error']:.3g} CU. Tests also cover deterministic buy/sell examples, quote bounds, hard caps, terminal marking, no-arrival cases, extreme parameters, random reproducibility, causal prefixes and directional information. Independent saved-fill reconstruction and UI validation are recorded in [VALIDATION.md](VALIDATION.md).

The largest limitation is the assumed fill curve. There is no queue, competitor, latency, partial fill, impact, financing or calibrated order flow. The dealer is a price taker in independent counterfactual worlds. Terminal marks omit executable liquidation costs; unclosed inventory must not be described as realized cash profit. Synthetic stress severities, 600-step horizon and single-window RMS estimator are modeling choices. Repeated random seeds reduce Monte Carlo noise, not model risk. A one-day BTC context sample is not a representative calibration dataset.

The [follow-up report](MECHANISM_REPORT.md) adds width/skew ablations and an identical-price information control using 2,000 additional strategy runs. It also shows that some mean-profit rankings change on fresh seeds, so treat the original rankings as conditional on their sampled paths. Remaining work includes testing more information-link strengths and policy coefficients, explicit executable liquidation costs, and richer historical order-book/queue modeling.

## Primary reading and reproducibility

- [Citadel Securities: market maker introduction](https://www.citadelsecurities.com/what-we-do/what-is-a-market-maker/)
- [Avellaneda & Stoikov (2008): original paper](https://math.nyu.edu/inmemoriam/avellaneda/HighFrequencyTrading.pdf)
- [HftBacktest: fill assumptions and queue limitations](https://hftbacktest.readthedocs.io/en/latest/order_fill.html)
- [Binance: public-data schema and checksums](https://github.com/binance/binance-public-data)

These sources informed concepts and limitations; they do not validate our chosen numerical inputs. Exact environment, source hashes and seed lists are in [RESULTS](RESULTS/README.md). Run `bash reproduce.sh` from the project directory. The [CV draft](CV_DRAFT.md) distinguishes AI assistance from skills the student must personally demonstrate.
"""
(ROOT/"RESEARCH_REPORT.md").write_text(report)
print("Report regenerated from saved CSVs")
