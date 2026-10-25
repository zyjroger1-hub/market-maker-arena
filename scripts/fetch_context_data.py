"""Optional bounded public-data download; never called by the app/experiments."""
from pathlib import Path
from urllib.request import urlopen, Request
import hashlib, io, json, zipfile
from datetime import datetime, timezone
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
BASE="https://data.binance.vision/data/spot/daily/klines/BTCUSDT/1m/"
NAME="BTCUSDT-1m-2025-01-06.zip"
TERMS="https://raw.githubusercontent.com/binance/binance-public-data/master/TERMS_AND_CONDITIONS.md"


def bounded_get(url,limit=500000):
    with urlopen(Request(url,headers={"User-Agent":"MarketMakerArena-Educational/1.0"}),timeout=30) as r:
        body=r.read(limit+1)
        if len(body)>limit:
            raise ValueError("Download exceeds size budget")
        return body


def main():
    out=ROOT/"data"; out.mkdir(exist_ok=True)
    try:
        terms=bounded_get(TERMS)
        body=bounded_get(BASE+NAME)
        checksum=bounded_get(BASE+NAME+".CHECKSUM").decode().split()[0]
        actual=hashlib.sha256(body).hexdigest()
        if checksum!=actual:
            raise ValueError("SHA256 mismatch")
        z=zipfile.ZipFile(io.BytesIO(body))
        if len(z.namelist())!=1 or z.infolist()[0].file_size>1000000:
            raise ValueError("Unexpected archive")
        df=pd.read_csv(z.open(z.namelist()[0]),header=None)
        if df.shape!=(1440,12):
            raise ValueError(f"Unexpected format {df.shape}")
        times=pd.to_datetime(df[0],unit="us",utc=True)
        close=pd.to_numeric(df[4])
        if times.iloc[0]!=pd.Timestamp("2025-01-06",tz="UTC") or not np.all(np.diff(df[0].to_numpy()) == 60_000_000):
            raise ValueError("Bad timestamps or gaps")
        if times.duplicated().any() or df.isna().any().any() or (close<=0).any():
            raise ValueError("Invalid rows")
        for col in (1,2,3,4):
            if not pd.to_numeric(df[col]).gt(0).all(): raise ValueError("Nonpositive OHLC")
        if not ((df[2]>=df[[1,4]].max(axis=1)) & (df[3]<=df[[1,4]].min(axis=1)) & (df[2]>=df[3])).all():
            raise ValueError("OHLC inconsistency")
        clean=pd.DataFrame({"open_time_utc":times,"close":close})
        clean.to_csv(out/"btc_context_clean.csv",index=False)
        # Do not include the transition return between the two intervals.
        estimates={}
        for label,part in (("calibration_first_12h",close.iloc[:720]),("heldout_last_12h",close.iloc[720:])):
            returns=np.diff(np.log(part.to_numpy()))
            estimates[label]={"n_returns":len(returns),"log_return_sd_per_sqrt_minute":float(returns.std(ddof=1)),
                              "normalized_price100_sd_per_minute":float(np.diff(100*part/part.iloc[0]).std(ddof=1))}
        (out/NAME).write_bytes(body)
        (out/"TERMS_AT_DOWNLOAD.md").write_bytes(terms)
        manifest=dict(status="success",retrieved_utc=datetime.now(timezone.utc).isoformat(),source=BASE+NAME,
                      checksum_source=BASE+NAME+".CHECKSUM",sha256=actual,archive_bytes=len(body),rows=len(df),
                      timestamp_unit="microseconds since Unix epoch",interval="1 minute",estimates=estimates,
                      use="Descriptive context only; no simulator parameter fitted to this sample",
                      license="Binance Vision dataset terms, CC BY-NC-SA 4.0; educational non-commercial use",
                      terms_url=TERMS,cleaning="Validated 12 columns, 1440 unique gap-free timestamps, positive consistent OHLC; retained UTC open time and close. No rows removed or imputed.")
    except Exception as e:
        manifest=dict(status="unavailable",error=str(e),source=BASE+NAME,
                      use="Core synthetic simulator remains available; no historical observations invented")
    (out/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    print(json.dumps(manifest,indent=2))

if __name__=="__main__": main()
