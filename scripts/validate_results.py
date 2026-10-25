"""Independent checks of saved results: reconstruct executions using Decimal.

Does not call the engine, metrics helper, summary helper or policy implementation.
"""
from pathlib import Path
from decimal import Decimal
import csv,hashlib,json,math,statistics
from collections import defaultdict
import pandas as pd
from scipy.stats import t
ROOT=Path(__file__).resolve().parents[1];R=ROOT/"RESULTS"


def main():
    c=json.loads((R/"config.json").read_text())
    raw=pd.read_csv(R/"main_runs.csv")
    assert len(raw)==1500 and not raw.duplicated(["scenario","strategy","seed"]).any()
    assert raw.groupby(["scenario","strategy"]).size().eq(100).all()
    assert set(raw.seed)==set(c["evaluation_seeds"])
    assert not set(c["evaluation_seeds"]) & set(c["exploration_seeds"])
    assert not set(c["evaluation_seeds"]) & set(c["sensitivity_seeds"])
    assert raw.select_dtypes("number").apply(lambda x:x.map(math.isfinite)).all().all()
    assert raw.max_abs_inventory.le(c["base_config"]["inventory_limit"]).all()
    groups=defaultdict(list)
    with (R/"representative_paths.csv").open() as f:
        for row in csv.DictReader(f):groups[(row["scenario"],row["strategy"])].append(row)
    trades=defaultdict(dict)
    with (R/"representative_fills.csv").open() as f:
        for row in csv.DictReader(f):trades[(row["scenario"],row["strategy"])][int(row["step"])]=row
    cash_error=equity_error=0.0
    for key,rows in groups.items():
        cash=Decimal("10000");q=0;fees=Decimal(0);peak=Decimal("10000");maxdd=Decimal(0)
        absq=[]
        assert len(rows)==601
        for i,row in enumerate(rows):
            assert int(row["step"])==i
            if i in trades[key]:
                fill=trades[key][i];dq=1 if fill["side"]=="buy" else -1
                price=Decimal(fill["price"]);fee=price*Decimal(str(c["base_config"]["fee_bps"]))/10000
                assert abs(fee-Decimal(fill["fee"]))<Decimal("1e-10")
                cash-=dq*price+fee;q+=dq;fees+=fee
            equity=cash+q*Decimal(row["mid"])
            cash_error=max(cash_error,abs(float(cash-Decimal(row["cash"]))))
            equity_error=max(equity_error,abs(float(equity-Decimal(row["equity"]))))
            assert q==int(row["inventory"]) and abs(q)<=10
            assert abs(fees-Decimal(row["fees"]))<Decimal("1e-8")
            peak=max(peak,equity);maxdd=max(maxdd,peak-equity)
            if i:absq.append(abs(q))
        r=raw[(raw.scenario==key[0])&(raw.strategy==key[1])&(raw.seed==10000)].iloc[0]
        assert abs(float(maxdd)-r.max_drawdown)<1e-8
        assert abs(statistics.mean(absq)-r.avg_abs_inventory)<1e-10
        assert abs(float(equity-10000)-r.pnl)<1e-8
    assert cash_error<1e-8 and equity_error<1e-8
    # Recompute means/sample SD with standard-library statistics rather than helper.
    summary=pd.read_csv(R/"summary.csv")
    for _,r in summary.iterrows():
        values=raw[(raw.scenario==r.scenario)&(raw.strategy==r.strategy)].pnl.tolist()
        assert abs(statistics.mean(values)-r.pnl_mean)<1e-10
        assert abs(statistics.stdev(values)-r.pnl_sd)<1e-10
    pc=pd.read_csv(R/"paired_comparisons.csv")
    for _,r in pc.iterrows():
        a,b=r.contrast.split(" - ")
        g=raw[raw.scenario==r.scenario]
        av=dict(zip(g[g.strategy==a].seed,g[g.strategy==a][r.metric]))
        bv=dict(zip(g[g.strategy==b].seed,g[g.strategy==b][r.metric]))
        ds=[av[k]-bv[k] for k in sorted(av)]
        mean=statistics.mean(ds);margin=t.ppf(.975,len(ds)-1)*statistics.stdev(ds)/math.sqrt(len(ds))
        assert abs(mean-r.mean_difference)<1e-10
        assert abs(mean-margin-r.ci_low)<1e-10 and abs(mean+margin-r.ci_high)<1e-10
    # All completed run families retain accounting/cap validity.
    for name,expected in (("exploration.csv",360),("sensitivity_runs.csv",1620)):
        f=pd.read_csv(R/name)
        assert len(f)==expected and f.accounting_error.lt(1e-7).all()
        assert f.select_dtypes("number").apply(lambda x:x.map(math.isfinite)).all().all()
        if name=="sensitivity_runs.csv":
            for setting,g in f.groupby("setting"):
                cap=int(setting.split("=")[1]) if setting.startswith("inventory_limit=") else 10
                assert g.max_abs_inventory.le(cap).all()
    manifest=json.loads((R/"run_manifest.json").read_text())
    for name,digest in manifest["source_hashes"].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,f"Source changed: {name}. Re-run experiments."
    assert hashlib.sha256((ROOT/"RESEARCH_PLAN.md").read_bytes()).hexdigest()==manifest["plan_sha256"]
    # Check all local Markdown links in project-authored documents (excluding data terms).
    import re
    for file in list(ROOT.glob("*.md"))+[R/"README.md",ROOT/"data/README.md"]:
        if not file.exists():continue
        document=re.sub(r"```[\s\S]*?```|`[^`]*`","",file.read_text())
        for target in re.findall(r'\]\(([^)]+)\)',document):
            if "://" not in target and not target.startswith("#"):
                destination=(file.parent/target.split("#")[0]).resolve()
                # This receipt is generated only after all substantive checks pass.
                if destination != (R/"independent_validation.json").resolve():
                    assert destination.exists(),f"Broken link {file}: {target}"
    receipt=dict(status="passed",main_runs=1500,exploration_runs=360,sensitivity_runs=1620,
                 independently_reconstructed_paths=len(groups),saved_step_end_marks_checked=sum(map(len,groups.values())),
                 max_decimal_cash_residual=cash_error,max_decimal_equity_residual=equity_error,
                 paired_intervals_checked=len(pc),checks="Counts, seed separation, finiteness, caps, independent cash/equity reconstruction, drawdown, inventory means, summary SD, paired intervals, source/plan hashes, Markdown links")
    (R/"independent_validation.json").write_text(json.dumps(receipt,indent=2)+"\n")
    print(json.dumps(receipt,indent=2))

if __name__=="__main__":main()
