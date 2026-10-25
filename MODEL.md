# Model specification

All amounts are fictional currency units (CU), not GBP or BTC. One inventory unit is an abstract share of the simulated asset. The reference is a synthetic frictionless valuation mark, not an executable exchange price. Default horizon: 600 steps × 1 second. Initial reference S₀=100, cash X₀=10,000, inventory q₀=0.

## Exogenous market tape

The engine draws a complete tape once using NumPy `default_rng(seed)` (PCG64 with the pinned environment). It draws standard normals ε, independent equiprobable customer directions D∈{−1,+1}, arrival uniforms U, acceptance uniforms V, then an independent jump sign. Every strategy reuses that immutable tape in its own counterfactual market. Dealers do not compete for one shared fill. Quotes never influence reference prices, customer directions or the random-number stream.

At step t (before the next reference move), D=+1 means a customer buys from the dealer's ask; D=−1 means a customer sells to the dealer's bid. The tape contains latent customer directions even when no customer arrives.

`log(S[t+1]/S[t]) = (μ − σ[t]²/2)Δt + σ[t]√Δt Z[t] + J[t]`.

μ has units /second, σ has units /sqrt(second). Near S=100, σ=0.0004 corresponds approximately to 0.04 CU per sqrt(second). These are synthetic design inputs, not estimates of BTC volatility.

| Scenario | μ | σ (/sqrt(second)) | Z and jump |
|---|---:|---:|---|
| Stable | 0 | 0.0004 | independent standard normal ε |
| Trend | 0.00006 | 0.0004 | ε; positive expected drift |
| High volatility | 0 | 0.0004 or 0.0014 | ε; low/high/low/high blocks |
| Jump | 0 | 0.0004 | ε plus one ±0.016 log jump |
| Adverse selection | 0 | 0.0008 | Z=√(1−ρ²)ε+ρD, ρ=0.85 |

At defaults each volatility block lasts 150 seconds; the jump is in the transition from step 300 to 301. For other horizons blocks and jump time scale with the number of steps. `vol_multiplier` multiplies σ, not jump size or μ. High volatility is independent of direction. The adverse shock has mean zero and variance one, but is a mixture, not Gaussian; the −σ²/2 correction is therefore only an approximate martingale correction in that scenario. No strategy exploits an assumed exact martingale property.

In adverse selection, conditional on an arriving customer buy, the expected next *log* return is `(μ−σ²/2)Δt+ρσ√Δt`. For a sell it is `(μ−σ²/2)Δt−ρσ√Δt`. A dealer sells just before an expected rise, or buys just before an expected fall. Near S=100, the directional component is approximately 0.068 CU in one second. This mechanism applies whether or not the dealer accepts the trade; the dealer does not move the reference. The strategy sees neither D nor the pending shock before quoting. Increasing volatility alone does not implement this mechanism.

## Within-step sequence

1. Observe S[t], current cash/inventory, and an immutable tuple S[0]…S[t]. The policy receives no tape, future price, pending direction or random seed.
2. Submit bid/ask; cancel and replace the previous quotes. Relative quoting rules in Play are recalculated at every step in the round.
3. Clip prices to the allowed range and disable any side that would breach the inventory cap.
4. A potential customer arrives if `U[t] < 1−exp(−AΔt)`, with A=0.8 /second. It has the exogenous direction D[t]. This is a Bernoulli approximation/cap: at most one customer per step. It is **not** a full Poisson count simulation. At Δt=1 the arrival probability is about 0.551, not 0.8.
5. If the relevant quote is enabled, a single unit fills when `V[t] < exp(−kδ)`, with k=15 /CU and δ the quote's nonnegative distance from S[t]. Arrival and acceptance draws are independent of ε and D. At δ=0.05, acceptance is about 0.472; unconditional fill chance with both sides on is about 0.260 before cap blocking.
6. Execute at the submitted quote; charge the fee; update cash and inventory immediately.
7. Move reference to S[t+1]; mark equity using the **post-fill** inventory. Record step-end metrics.

Distance-based acceptance is an assumed reduced-form demand curve. It is not inferred from candle touches or a queue. No partial fills. Paused quotes do not execute. The cap is checked before accepting a fill; opposing trades can unwind an existing position. Cap-blocked and paused-arrival counters have mutually exclusive attribution, with cap first. One filled unit counts as one trade and one unit of volume. There are no round-trip counts.

## Bounds and capital

Base quote distance is constrained between 0.01 CU and 5 CU. At low prices the minimum becomes min(0.01, 1% of S), the maximum min(5, 20% of S), preserving positive bid, bid < S < ask, and bid < ask. Prices are continuous: there is no tick rounding. An aggressive centre shift can clip one side; the executed spread can differ from the requested spread. Missing sides are represented by `None`, never artificial infinite prices.

Inventory is an integer in [−Q,Q], default Q=10. A buy at +Q and a sell at −Q are disabled. Short inventory and cash debits are permitted; there is no margin, borrow fee or capital-based cap. Initial cash is a reporting baseline, not a calibrated leverage constraint. Numerical input ranges and a supported price range reject pathological paths explicitly; no price-floor rescue creates free P&L. These capital/financing simplifications matter for longer horizons.

## Policies

Let h=0.05 CU, κ=0.015 CU per inventory unit. The strategies return centre c and half-width w before engine clipping.

| Policy | Centre | Half-width |
|---|---|---|
| Fixed | S[t] | h |
| Inventory | S[t] − κq[t] | h |
| Adaptive | S[t] − κq[t]r[t]² | h r[t] |

Bid=c−w and ask=c+w. Estimate `v̂[t] = sqrt(mean((S[i]−S[i−1])²)/Δt)` over at most 30 completed returns; use a fixed 0.04 CU/sqrt(second) prior until two returns exist. Set r=clip(v̂/0.04,0.5,3). It is RMS, not a demeaned sample standard deviation; jumps and drift affect it. There is no use of the scenario's true σ. Warm-up and adaptation lag are intentional limitations. Adaptive changes both spread and inventory sensitivity, so Adaptive−Inventory is a combined effect, not an isolated estimate of widening alone.

The negative inventory skew follows reservation-price intuition. We do not optimize exponential utility, solve an HJB equation or implement the exact Avellaneda–Stoikov policy. There is no global optimality claim.

## Accounting and metrics

For a fill with Δq=+1 (buy) or −1 (sell), execution price P and fee rate f=fee_bps/10,000:

`X ← X − Δq P − fP`, `q ← q+Δq`, `fees ← fees+fP`.

`E[t]=X[t]+q[t]S[t]`, `net P&L=E[T]−X₀`.

For every run verify the telescoping identity:

`net P&L = Σfills Δq(S[t]−P) + Σsteps q[t+1](S[t+1]−S[t]) − Σfills fP`.

The first sum is execution edge to the current reference; it is not added to equity a second time. The second is inventory holding P&L, including the move immediately after a trade. Reconstruct terminal cash and inventory independently from all fills.

- Maximum drawdown: max over recorded times of running peak equity minus current equity, in CU, including time zero. Intrastep excursions are unobserved.
- Average absolute inventory: mean |q[t]| over step-end times 1…T; maximum absolute inventory includes time zero.
- Final P&L is net of all charged fees and includes terminal inventory at the last reference. We do **not** execute a free terminal liquidation. Cash alone is not profit. Remaining inventory has liquidation costs and risks absent from this mark.
- Report cross-seed sample SD and empirical 5th/50th/95th percentiles. Paired mean differences use a Student t 95% interval over seed differences. These approximate Monte Carlo intervals condition on this model and fixed parameters; they do not measure model risk. No annualized Sharpe or implausible accuracy claim.

## What is absent

A limit order book, queue priority, competitors, latency, exchange cancellations, partial fills, size-dependent execution, market impact, hidden liquidity, tick sizes, financing, exchange fee tiers/rebates, bid/ask marking, estimation of real customer demand, and calibrated volatility dynamics. The absence of informative flow outside the dedicated stress scenario favors spread capture. Changing A, k, fees or the information link can change conclusions. A positive modeled P&L is not a real trading opportunity.

## Sources and design decisions

Verified on 25 October 2026:

- [Citadel Securities: What is a market maker?](https://www.citadelsecurities.com/what-we-do/what-is-a-market-maker/) — two-way liquidity provision, spread and risk. Institutional description, not a fill calibration.
- [Avellaneda & Stoikov, Quantitative Finance 8(3), 217–224 (2008)](https://math.nyu.edu/inmemoriam/avellaneda/HighFrequencyTrading.pdf) — reservation-price intuition and distance-dependent execution rates. Our discrete-time heuristics and stress model are our own specification.
- [HftBacktest: Order Fill](https://hftbacktest.readthedocs.io/en/latest/order_fill.html) — queue/fill assumptions and limitations of replay without impact. Our simulator is not HftBacktest and uses no claimed queue reconstruction.
- [Binance public data](https://github.com/binance/binance-public-data) — optional archive schema, microsecond timestamps for spot data from 2025, and checksum mechanism. See [data/README.md](data/README.md) for sample provenance and terms.
