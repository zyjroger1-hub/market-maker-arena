# Validation record

25 October 2026. **Share with caveats:** the project is ready within the educational simulation scope checked below. It is not validated for real execution or calibrated market forecasting.

## Automated and numerical checks

- **36 tests**: deterministic buy/sell cash, inventory, notional fees and P&L; terminal inventory marking; exact drawdown example; both inventory cap directions and permitted unwind; pause semantics; quote clipping/nonfinite rejection; seed reproducibility and immutable random tapes; prefix-only observations; historical-only volatility; adverse-selection direction/next-return correlation; distance-dependent acceptance; invalid input rejection; extreme intensity/fee/volatility/cap settings; matched batch completeness.
- Three Streamlit integration tests cover advance, pause both sides, replay, completing a full match, disabled completion button, changing scenario/reset, a fresh20-seed research run, and changed-but-unapplied controls. They use Streamlit's AppTest, not screenshot mocks.
- All3,480 study runs check the internal cash/inventory/fee and telescoping P&L identities. See [run manifest](RESULTS/run_manifest.json) and [complete test output](RESULTS/tests-all.txt).
- An independent script does not call engine accounting helpers: Decimal execution reconstruction checks all 15 saved representative paths and 9,015 step-end marks, along with drawdown and inventory means. It recomputes summary SD/means and 60 paired intervals from saved seed rows, checks seeds, caps, finiteness, source hashes and document links. [Receipt](RESULTS/independent_validation.json).

The first UI test invocation used a relative AppTest path that resolved inside the tests folder; it was corrected to an absolute project path. Empty-startup inventory averaging and an empty-column concatenation warning were also fixed. The final test log covers the delivered code. No failed strategy outcomes were removed.

## Live browser inspection

The local server returned HTTP 200 at 127.0.0.1:8501. Actual in-app browser inspection covered the Play overview and a 50-step advance, showing updated reference, cash, inventory, equity and explanatory copy. A full 1,500-run experiment was triggered through the Research button and completed; the rendered P&L distribution, inventory/outcome scatter, paired comparisons and example trajectory were inspected. Captures: [Research](RESULTS/figures/research_browser.png), [Play](RESULTS/figures/play_browser.png).

A narrow 805px browser initially truncated five metric columns. Metrics were split into two rows, controls shortened and chart views placed in tabs. A chart legend overlapping its title was moved below the plot, and the 0.015 skew display was given three decimal places. The final browser inspection checked these fixes. English interface text and chart units remain explicit.

Five generated research PNGs were visually inspected for marks, labels, scales and clipping. Their source rows are listed in [figures/sources.json](RESULTS/figures/sources.json). Report numbers are generated from the saved summary; no chart values are fabricated.

## Optional data verification

A 72,324-byte official daily archive was downloaded with a response-size cap and verified against its official SHA256. The 1,440×12 format, microsecond epoch unit, expected UTC date, exact minute spacing, no gaps/duplicates/missing values, and positive consistent OHLC were checked. A separate first/last 12-hour comparison was saved. None of these real-data observations is used to infer fills or to set synthetic default parameters. [Provenance](data/manifest.json).

## Verification limits

Browser checks are representative, not exhaustive testing of all seeds, browser sizes, OS versions or widget permutations. Only the tested Mac/Python environment is claimed. Test isolation prevents ordinary strategies from receiving future fields but is not a security sandbox for malicious Python code. End-of-step marking cannot measure intrastep drawdowns. Statistical intervals condition on the assumed market/fill model; they cannot validate it. No real-trading, order-book replay, latency, queue or market-impact verification was performed.
