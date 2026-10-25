"""Preplanned follow-up: width/skew ablation and identical-price flow control."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from dataclasses import asdict
from datetime import datetime,timezone
import hashlib,json,time
import numpy as np
import pandas as pd
from arena.engine import Config,make_tape
from arena.strategies import ALL_STRATEGIES
from arena.experiments import run_batch,summarize,paired_comparisons,paired_linear_contrasts


def main():
    out=ROOT/"RESULTS/mechanisms";out.mkdir(exist_ok=True)
    start=time.perf_counter();config=Config();seeds=list(range(30000,30100))
    cases=["Stable","High volatility","Adverse selection"]
    print("Factorial controls: 3 scenarios x 100 seeds x 5 policies",flush=True)
    ablation=run_batch(config,cases,seeds,strategy_names=ALL_STRATEGIES)
    ablation.to_csv(out/"ablation_runs.csv",index=False)
    summarize(ablation).to_csv(out/"ablation_summary.csv",index=False)
    paired_comparisons(ablation).to_csv(out/"ablation_pairs.csv",index=False)
    informed=ablation[ablation.scenario=="Adverse selection"].assign(flow="Informed")
    independent=run_batch(config,["Adverse selection"],seeds,strategy_names=ALL_STRATEGIES,
                          informative_flow=False).assign(flow="Independent")
    flow=pd.concat([informed,independent],ignore_index=True)
    flow.to_csv(out/"flow_control_runs.csv",index=False)
    sm=[];pairs=[]
    for mode,g in flow.groupby("flow",sort=False):
        sm.append(summarize(g).assign(flow=mode))
    for name,g in flow.groupby("strategy",sort=False):
        compare=g.drop(columns="strategy").rename(columns={"flow":"strategy"})
        result=paired_linear_contrasts(compare,{"Informed - Independent":{"Informed":1,"Independent":-1}})
        pairs.append(result.assign(strategy=name))
    pd.concat(sm,ignore_index=True).to_csv(out/"flow_control_summary.csv",index=False)
    pd.concat(pairs,ignore_index=True).to_csv(out/"flow_control_pairs.csv",index=False)
    diagnostics=[]
    for seed in seeds:
        a=make_tape(config,"Adverse selection",seed)
        b=make_tape(config,"Adverse selection",seed,informative_flow=False)
        shared=all(np.array_equal(getattr(a,k),getattr(b,k)) for k in ("mids","arrival_u","acceptance_u"))
        if not shared:raise AssertionError("Control changed a shared exogenous tape")
        returns=np.diff(np.log(a.mids))
        diagnostics.append(dict(seed=seed,shared_price_and_uniforms=shared,
                                price_sha256=hashlib.sha256(a.mids.tobytes()).hexdigest(),
                                informed_direction_correlation=float(np.corrcoef(a.directions,returns)[0,1]),
                                independent_direction_correlation=float(np.corrcoef(b.directions,returns)[0,1])))
    pd.DataFrame(diagnostics).to_csv(out/"tape_diagnostics.csv",index=False)
    source_paths=list((ROOT/"arena").glob("*.py"))+[Path(__file__)]
    manifest=dict(created_utc=datetime.now(timezone.utc).isoformat(),original_study_commit="5abf0eadc587fdac3ee38160fd6c4bf62b4a96e3",
                  plan="RESEARCH_ADDENDUM_PLAN.md",plan_sha256=hashlib.sha256((ROOT/"RESEARCH_ADDENDUM_PLAN.md").read_bytes()).hexdigest(),
                  seeds=seeds,config=asdict(config),strategies=list(ALL_STRATEGIES),scenarios=cases,
                  strategy_parameters=dict(half_spread=.05,skew=.015,window=30,prior_vol=.04),
                  ablation_runs=len(ablation),additional_independent_flow_runs=len(independent),new_strategy_runs=len(ablation)+len(independent),
                  flow_control_rows=len(flow),reused_informed_rows=len(informed),
                  ending="Mark to market, no closing execution",elapsed_seconds=time.perf_counter()-start,
                  source_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(source_paths)},
                  result_hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.glob('*.csv'))})
    (out/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    print(json.dumps({k:manifest[k] for k in ("new_strategy_runs","elapsed_seconds")},indent=2))

if __name__=="__main__":main()
