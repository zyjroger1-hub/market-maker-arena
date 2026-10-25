"""Paired comparisons: exogenous tapes are generated once per scenario/seed."""
from dataclasses import asdict
import numpy as np
import pandas as pd
from scipy.stats import t as student_t
from .engine import Config, make_tape, simulate
from .strategies import STRATEGIES, Strategy


def run_batch(config: Config, scenarios, seeds, half_spread=0.05, skew=0.015,
              progress=None):
    rows = []
    total = len(scenarios)*len(seeds)
    for i,scenario in enumerate(scenarios):
        for j,seed in enumerate(seeds):
            tape = make_tape(config,scenario,int(seed))
            for name in STRATEGIES:
                result = simulate(config,tape,Strategy(name,half_spread,skew))
                rows.append(dict(scenario=scenario,seed=int(seed),strategy=name,**result.metrics()))
            if progress:
                progress((i*len(seeds)+j+1)/total)
    return pd.DataFrame(rows)


def summarize(raw):
    rows = []
    for (scenario,strategy),g in raw.groupby(["scenario","strategy"],sort=False):
        n=len(g); sd=g.pnl.std(ddof=1); margin=student_t.ppf(.975,n-1)*sd/np.sqrt(n) if n>1 else np.nan
        rows.append(dict(scenario=scenario,strategy=strategy,n=n,pnl_mean=g.pnl.mean(),
                         pnl_sd=sd,pnl_ci_low=g.pnl.mean()-margin,pnl_ci_high=g.pnl.mean()+margin,
                         pnl_p05=g.pnl.quantile(.05),pnl_median=g.pnl.median(),pnl_p95=g.pnl.quantile(.95),
                         mean_drawdown=g.max_drawdown.mean(),avg_abs_inventory=g.avg_abs_inventory.mean(),
                         max_abs_inventory=g.max_abs_inventory.max(),mean_fills=g.fills.mean(),
                         mean_fees=g.fees.mean(),mean_cap_blocked=g.cap_blocked.mean(),
                         mean_terminal_inventory=g.terminal_inventory.mean(),mean_fill_rate=g.fill_rate.mean()))
    return pd.DataFrame(rows)


def paired_comparisons(raw):
    rows=[]
    for scenario,g in raw.groupby("scenario",sort=False):
        for a,b in (("Inventory","Fixed"),("Adaptive","Inventory"),("Adaptive","Fixed")):
            for metric in ("pnl","avg_abs_inventory","max_drawdown","fills"):
                pivot=g.pivot(index="seed",columns="strategy",values=metric)
                d=(pivot[a]-pivot[b]).dropna(); n=len(d)
                margin=student_t.ppf(.975,n-1)*d.std(ddof=1)/np.sqrt(n) if n>1 else np.nan
                rows.append(dict(scenario=scenario,contrast=f"{a} - {b}",metric=metric,n=n,
                                 mean_difference=d.mean(),ci_low=d.mean()-margin,ci_high=d.mean()+margin))
    return pd.DataFrame(rows)
