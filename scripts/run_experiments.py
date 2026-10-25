"""Reproduce the preregistered synthetic experiments, offline."""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from dataclasses import asdict, replace
from datetime import datetime,timezone
import hashlib,json,platform,subprocess,time
import pandas as pd
from arena.engine import Config,SCENARIOS,make_tape,simulate
from arena.strategies import Strategy,STRATEGIES
from arena.experiments import run_batch,summarize,paired_comparisons


def main():
    out=ROOT/"RESULTS"; out.mkdir(exist_ok=True)
    start=time.perf_counter(); c=Config()
    config=dict(plan="RESEARCH_PLAN.md",base_config=asdict(c),strategy=dict(half_spread=.05,skew=.015,window=30,prior_vol=.04),
                scenarios=list(SCENARIOS),evaluation_seeds=list(range(10000,10100)),
                exploration_seeds=list(range(1000,1020)),sensitivity_seeds=list(range(20000,20030)),
                representative_seed=10000,ending="Mark to market, inventory retained; no terminal fill")
    (out/"config.json").write_text(json.dumps(config,indent=2)+"\n")
    print("Exploration (parameters already fixed)",flush=True)
    explore=[]
    for skew in (.005,.015,.03):
        frame=run_batch(c,["Stable","Adverse selection"],config["exploration_seeds"],skew=skew)
        frame["skew"]=skew; explore.append(frame)
    pd.concat(explore,ignore_index=True).to_csv(out/"exploration.csv",index=False)
    print("Main: 5 scenarios x 100 seeds x 3 strategies",flush=True)
    raw=run_batch(c,SCENARIOS,config["evaluation_seeds"])
    raw.to_csv(out/"main_runs.csv",index=False)
    summarize(raw).to_csv(out/"summary.csv",index=False)
    paired_comparisons(raw).to_csv(out/"paired_comparisons.csv",index=False)
    paths=[]; trades=[]
    for scenario in SCENARIOS:
        tape=make_tape(c,scenario,10000)
        for name in STRATEGIES:
            l=simulate(c,tape,Strategy(name))
            trace=pd.DataFrame(l.history); trace["scenario"]=scenario; trace["strategy"]=name; trace["seed"]=10000
            paths.append(trace)
            fills=pd.DataFrame(l.fills); fills["scenario"]=scenario; fills["strategy"]=name; fills["seed"]=10000
            trades.append(fills)
    pd.concat(paths,ignore_index=True).to_csv(out/"representative_paths.csv",index=False)
    pd.concat(trades,ignore_index=True).to_csv(out/"representative_fills.csv",index=False)
    print("One-factor sensitivities",flush=True)
    sensitivities=[("reference",c)]
    for factor,values in dict(fee_bps=(0,2),arrival_rate=(.4,1.6),inventory_limit=(5,20),vol_multiplier=(.5,2)).items():
        for value in values: sensitivities.append((f"{factor}={value}",replace(c,**{factor:value})))
    frames=[]; summaries=[]; contrasts=[]
    for label,sc in sensitivities:
        print(label,flush=True)
        frame=run_batch(sc,["Stable","Adverse selection"],config["sensitivity_seeds"])
        frame["setting"]=label; frames.append(frame)
        sm=summarize(frame); sm["setting"]=label; summaries.append(sm)
        pc=paired_comparisons(frame); pc["setting"]=label; contrasts.append(pc)
    pd.concat(frames,ignore_index=True).to_csv(out/"sensitivity_runs.csv",index=False)
    pd.concat(summaries,ignore_index=True).to_csv(out/"sensitivity_summary.csv",index=False)
    pd.concat(contrasts,ignore_index=True).to_csv(out/"sensitivity_pairs.csv",index=False)
    manifest=dict(created_utc=datetime.now(timezone.utc).isoformat(),python=sys.version,platform=platform.platform(),
                  elapsed_seconds=time.perf_counter()-start,main_runs=len(raw),exploration_runs=sum(map(len,explore)),
                  sensitivity_runs=sum(map(len,frames)),
                  max_accounting_error=float(raw.accounting_error.max()),
                  source_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
                                 for p in sorted((ROOT/"arena").glob("*.py"))},
                  plan_sha256=hashlib.sha256((ROOT/"RESEARCH_PLAN.md").read_bytes()).hexdigest())
    (out/"run_manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    freeze=subprocess.check_output([sys.executable,"-m","pip","freeze"],text=True)
    (ROOT/"requirements-lock.txt").write_text(freeze)
    print(json.dumps(manifest,indent=2))

if __name__=="__main__": main()
