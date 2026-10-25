# Research plan — fixed before the main experiment

Recorded 25 October 2026. Question: how do spread capture, inventory exposure and execution opportunities trade off in a transparent simulated market?

## Confirmatory design

- Strategies: Fixed, Inventory, Adaptive (inventory + trailing volatility). These are educational heuristics, not exact Avellaneda–Stoikov solutions.
- Five scenarios: Stable, Trend, High volatility, Jump, Adverse selection.
- 600 steps of one second, initial reference 100 currency units (CU), cash 10,000 CU, inventory zero; one unit per fill, hard inventory cap 10; fee 0.5 basis points per filled notional. Terminal inventory is marked to the terminal reference, never silently liquidated.
- Fixed half-spread 0.05 CU; inventory skew 0.015 CU per inventory unit. Adaptive half-spread = 0.05 × clipped(trailing RMS price change / 0.04, 0.5, 3); adaptive skew multiplies by the square of that ratio. Window 30 observations, fixed warm-up volatility 0.04 CU per sqrt(second), no oracle volatility.
- Arrival intensity 0.8 /second, distance decay 15 /CU. One potential customer per step, arrival probability 1-exp(-0.8); equally likely customer buy/sell, then acceptance probability exp(-15 × quote distance). No fill if that side is paused or its inventory cap is reached.
- Primary endpoint: final net mark-to-market P&L in CU. Paired contrasts: Inventory − Fixed, Adaptive − Inventory, Adaptive − Fixed, within each scenario. Two-sided 95% Student t intervals on paired seed differences; exploratory family, no multiplicity adjustment or real-market inference.
- Secondary: sample P&L SD and 5th/50th/95th percentiles, maximum drawdown in CU from the step-end equity curve including time zero, time-average absolute inventory, maximum absolute inventory, fills, fees, terminal inventory, potential arrivals, and cap-blocked arrivals. No annualized Sharpe ratio for ten-minute toy paths.
- Main evaluation seeds 10000…10099, reused across scenarios and strategies. Each scenario has 100 independent market paths. Comparisons across scenarios are descriptive, not pooled independent evidence.
- Exploration only: seeds 1000…1019, Stable and Adverse selection, skew {0.005,0.015,0.03}. Primary parameters are fixed above and will not be selected from this search.
- Sensitivity: seeds 20000…20029; Stable and Adverse selection, each factor changed alone: fee {0,2 bps}, intensity {0.4,1.6}, cap {5,20}, volatility multiplier {0.5,2}. Retain the primary configuration as a reference. Do not retune other parameters.
- Save raw seed-level metrics, paired intervals, configs, seed lists, environment, timings, hashes, and unselected representative path seed 10000. Retain poor outcomes.

## Market regimes (synthetic inputs)

Log price increments = (mu − sigma²/2)dt + sigma sqrt(dt)Z + J. Stable sigma=0.0004 /sqrt(second), mu=0; Trend mu=0.00006 /second; High volatility alternates sigma 0.0004 and 0.0014 every 150 seconds; Jump adds a signed 0.016 log jump halfway through; Adverse selection sigma=0.0008 and Z=sqrt(1−0.85²)epsilon+0.85D, where D=+1 is a customer buy and D=−1 a customer sell. D and epsilon are independent; all other scenarios use epsilon. Thus buy orders predict positive next returns, rather than merely coinciding with high variance. Correlation is an imposed stress parameter, not calibrated.

## Data and model checks

Read the four requested primary references before implementation. Optional: one daily BTCUSDT 1-minute archive, SHA256 checked; first 12h descriptive calibration, second 12h held-out volatility comparison. These estimates do not set simulator defaults or establish fills. Minute bars are not an order book. Core experiments require no network.

Before reporting: deterministic accounting tests; fee, cap and boundary tests; common random numbers; reproducibility; prefix-only strategy observation; adverse-selection sign check; extreme configurations; Streamlit state and browser interaction checks. Report missing checks explicitly. Changes to this plan must be disclosed in the report.
