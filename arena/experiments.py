"""Paired simulations and explicit, complete seed-level linear contrasts."""
from numbers import Integral
import numpy as np
import pandas as pd
from scipy.stats import t as student_t
from .engine import Config, SCENARIOS, make_tape, simulate
from .strategies import STRATEGIES, ALL_STRATEGIES, Strategy

METRICS = ("pnl", "avg_abs_inventory", "max_drawdown", "fills")
BASE_CONTRASTS = {
    "Inventory - Fixed": {"Inventory":1, "Fixed":-1},
    "Adaptive - Inventory": {"Adaptive":1, "Inventory":-1},
    "Adaptive - Fixed": {"Adaptive":1, "Fixed":-1},
}
ABLATION_CONTRASTS = {
    "Width only - Inventory": {"Width only":1, "Inventory":-1},
    "Skew only - Inventory": {"Skew only":1, "Inventory":-1},
    "Adaptive - Width only": {"Adaptive":1, "Width only":-1},
    "Adaptive - Skew only": {"Adaptive":1, "Skew only":-1},
    "Interaction (width x skew)": {"Adaptive":1, "Width only":-1, "Skew only":-1, "Inventory":1},
}


def run_batch(config: Config, scenarios, seeds, half_spread=0.05, skew=0.015,
              progress=None, *, strategy_names=None, informative_flow=True):
    names=tuple(STRATEGIES if strategy_names is None else strategy_names)
    scenarios=tuple(scenarios);seeds=tuple(seeds)
    if not names or len(names)!=len(set(names)) or not set(names)<=set(ALL_STRATEGIES):
        raise ValueError("Choose unique supported strategy names")
    if not scenarios or len(scenarios)!=len(set(scenarios)) or not set(scenarios)<=set(SCENARIOS):
        raise ValueError("Choose unique supported scenarios")
    if not seeds or len(seeds)!=len(set(seeds)) or any(
        not isinstance(s,Integral) or isinstance(s,bool) or not 0<=s<2**32 for s in seeds):
        raise ValueError("Seeds must be unique integers in [0, 2**32)")
    policies=[Strategy(name,half_spread,skew) for name in names]
    rows=[];total=len(scenarios)*len(seeds)
    for i,scenario in enumerate(scenarios):
        for j,seed in enumerate(seeds):
            tape=make_tape(config,scenario,int(seed),informative_flow=informative_flow)
            for policy in policies:
                result=simulate(config,tape,policy)
                rows.append(dict(scenario=scenario,seed=int(seed),strategy=policy.name,**result.metrics()))
            if progress:progress((i*len(seeds)+j+1)/total)
    return pd.DataFrame(rows)


def summarize(raw):
    rows=[]
    for (scenario,strategy),g in raw.groupby(["scenario","strategy"],sort=False):
        n=len(g);sd=g.pnl.std(ddof=1);margin=student_t.ppf(.975,n-1)*sd/np.sqrt(n) if n>1 else np.nan
        rows.append(dict(scenario=scenario,strategy=strategy,n=n,pnl_mean=g.pnl.mean(),
                         pnl_sd=sd,pnl_ci_low=g.pnl.mean()-margin,pnl_ci_high=g.pnl.mean()+margin,
                         pnl_p05=g.pnl.quantile(.05),pnl_median=g.pnl.median(),pnl_p95=g.pnl.quantile(.95),
                         mean_drawdown=g.max_drawdown.mean(),avg_abs_inventory=g.avg_abs_inventory.mean(),
                         max_abs_inventory=g.max_abs_inventory.max(),mean_fills=g.fills.mean(),
                         mean_fees=g.fees.mean(),mean_cap_blocked=g.cap_blocked.mean(),
                         mean_terminal_inventory=g.terminal_inventory.mean(),mean_fill_rate=g.fill_rate.mean()))
    return pd.DataFrame(rows)


def paired_linear_contrasts(raw, contrasts, metrics=METRICS):
    """Reject missing pairs rather than silently changing the paired population."""
    required={"scenario","seed","strategy",*metrics}
    if raw.empty or not required<=set(raw.columns):
        raise ValueError("Nonempty scenario/seed/strategy metric rows required")
    if raw[["scenario","seed","strategy"]].isna().any().any() or raw.duplicated(["scenario","seed","strategy"]).any():
        raise ValueError("Paired keys must be complete and unique")
    if not np.isfinite(raw[list(metrics)].to_numpy(dtype=float)).all():
        raise ValueError("Paired metrics must be finite")
    rows=[]
    for scenario,g in raw.groupby("scenario",sort=False):
        for metric in metrics:
            pivot=g.pivot(index="seed",columns="strategy",values=metric)
            for label,weights in contrasts.items():
                if not set(weights)<=set(pivot.columns):
                    raise ValueError(f"Missing strategy for contrast {label}")
                values=pivot[list(weights)]
                if values.isna().any().any() or len(values)<2:
                    raise ValueError("Every contrast needs complete matched seeds and at least two pairs")
                d=sum(pivot[name]*weight for name,weight in weights.items());n=len(d)
                margin=student_t.ppf(.975,n-1)*d.std(ddof=1)/np.sqrt(n)
                rows.append(dict(scenario=scenario,contrast=label,metric=metric,n=n,
                                 mean_difference=d.mean(),ci_low=d.mean()-margin,ci_high=d.mean()+margin))
    return pd.DataFrame(rows)


def paired_comparisons(raw):
    names=set(raw.strategy)
    contrasts=dict(BASE_CONTRASTS)
    if {"Width only","Skew only"}<=names:contrasts.update(ABLATION_CONTRASTS)
    return paired_linear_contrasts(raw,contrasts)
