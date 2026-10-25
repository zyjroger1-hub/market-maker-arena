# Optional price context — Binance Vision attribution

Source: [Binance Vision BTCUSDT spot 1-minute archive, 6 January 2025 UTC](https://data.binance.vision/data/spot/daily/klines/BTCUSDT/1m/BTCUSDT-1m-2025-01-06.zip). Retrieved 25 October 2026. Archive size 72,324 bytes; 1,440 rows × 12 fields. Official [checksum](https://data.binance.vision/data/spot/daily/klines/BTCUSDT/1m/BTCUSDT-1m-2025-01-06.zip.CHECKSUM) verified SHA256 `4332f1e3f7db5d1aacaa7a21bf8b1e72ede11906eee34b2916c9933610d034a5`.

The [official schema](https://github.com/binance/binance-public-data) specifies spot timestamps from 2025 in microseconds. Fields: open time, open, high, low, close, volume, close time, quote volume, trade count, taker-buy base volume, taker-buy quote volume, ignore. One row summarizes one minute; it is not an order book.

`scripts/fetch_context_data.py` bounds downloads to 500KB per response, verifies archive SHA256 and uncompressed size, checks shape, missingness, positive OHLC consistency, expected UTC start, unique timestamps and exact 60,000,000 μs spacing. No rows removed or imputed. `btc_context_clean.csv` retains UTC candle open time and that candle's close price. A close is known at the *end* of its minute, not at its open timestamp; no trading policy consumes this file.

First 720 candles: descriptive calibration interval; last 720: held-out context interval. Within each, compute sample SD of 719 close-to-close log returns; omit the boundary return. Values: 0.0004693649 and 0.0006651686 for one-minute returns (4.694 and 6.652 bps). Normalized-price-100 difference SDs are 0.0471924 and 0.0676570 CU per one-minute observation. The diffusion notation /sqrt(minute) is only a unit convention; no empirical square-root-time scaling is established.

**These estimates do not calibrate the simulator.** Its defaults are synthetic per-second inputs. This tiny sample only illustrates how market scale and regime vary. There is no historical execution model or historical profit result. Files are optional; removing this whole directory does not affect core simulation, tests or the main experiment.

## Usage conditions checked at download

The repository's [Vision Dataset Terms](https://github.com/binance/binance-public-data/blob/master/TERMS_AND_CONDITIONS.md), version 1.0, updated 26 August 2026, permit free non-commercial educational/research access under CC BY-NC-SA 4.0 and additional terms. They restrict commercial trading/product use and require attribution and share-alike terms for redistributed dataset derivatives. See `TERMS_AT_DOWNLOAD.md` for the recorded terms and [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/) for the license. Binance does not endorse this project. This note records the checked terms, not a legal opinion.

The archive, cleaned data and dataset-derived estimates/charts/text are attributed to Binance Vision and shared under CC BY-NC-SA 4.0 subject to those terms. Synthetic results and implementation are separate from the dataset. The source, attribution and recorded terms accompany this educational project. Review current terms before a different use.

To re-fetch optionally: `python scripts/fetch_context_data.py`. Failures are recorded in `manifest.json` and do not trigger fabricated observations or block synthetic runs. Do not rerun this downloader as part of the offline reproduction workflow.
