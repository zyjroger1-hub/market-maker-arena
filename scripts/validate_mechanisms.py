"""Independent CSV arithmetic for the follow-up; no engine/experiment imports."""
from pathlib import Path
import hashlib,json,math,statistics
import pandas as pd
import numpy as np
from scipy.stats import t
ROOT=Path(__file__).resolve().parents[1];R=ROOT/'RESULTS/mechanisms'
WEIGHTS={
    'Inventory - Fixed':{'Inventory':1,'Fixed':-1},
    'Adaptive - Inventory':{'Adaptive':1,'Inventory':-1},
    'Adaptive - Fixed':{'Adaptive':1,'Fixed':-1},
    'Width only - Inventory':{'Width only':1,'Inventory':-1},
    'Skew only - Inventory':{'Skew only':1,'Inventory':-1},
    'Adaptive - Width only':{'Adaptive':1,'Width only':-1},
    'Adaptive - Skew only':{'Adaptive':1,'Skew only':-1},
    'Interaction (width x skew)':{'Adaptive':1,'Width only':-1,'Skew only':-1,'Inventory':1},
}


def verify_interval(values,r):
    assert len(values)==int(r.n)==100
    mean=statistics.mean(values)
    half=t.ppf(.975,len(values)-1)*statistics.stdev(values)/math.sqrt(len(values))
    assert abs(mean-r.mean_difference)<1e-9
    assert abs(mean-half-r.ci_low)<1e-9 and abs(mean+half-r.ci_high)<1e-9


def main():
    m=json.loads((R/'manifest.json').read_text())
    original=json.loads((ROOT/'RESULTS/config.json').read_text())
    assert not set(m['seeds']) & set(original['evaluation_seeds']+original['exploration_seeds']+original['sensitivity_seeds'])
    assert hashlib.sha256((ROOT/m['plan']).read_bytes()).hexdigest()==m['plan_sha256']
    for name,digest in m['source_hashes'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,name
    for name,digest in m['result_hashes'].items():assert hashlib.sha256((R/name).read_bytes()).hexdigest()==digest,name
    a=pd.read_csv(R/'ablation_runs.csv');flow=pd.read_csv(R/'flow_control_runs.csv')
    assert len(a)==1500 and len(flow)==1000 and m['new_strategy_runs']==2000
    assert not a.duplicated(['scenario','seed','strategy']).any()
    assert not flow.duplicated(['scenario','seed','strategy','flow']).any()
    for rows in (a,flow):
        assert rows.select_dtypes('number').apply(lambda col:np.isfinite(col)).all().all()
        assert rows.max_abs_inventory.le(10).all() and rows.accounting_error.lt(1e-7).all()
        assert rows.groupby(['scenario','strategy']).seed.nunique().eq(100).all()
        assert set(rows.seed)==set(m['seeds'])
    assert set(a.strategy)==set(m['strategies']) and set(a.scenario)==set(m['scenarios'])
    a_informed=a[a.scenario=='Adverse selection'].sort_values(['seed','strategy']).reset_index(drop=True)
    f_informed=flow[flow.flow=='Informed'].drop(columns='flow').sort_values(['seed','strategy']).reset_index(drop=True)
    pd.testing.assert_frame_equal(a_informed,f_informed)
    for filename,data,group in [('ablation_summary.csv',a,['scenario','strategy']),
                                ('flow_control_summary.csv',flow,['scenario','strategy','flow'])]:
        for _,r in pd.read_csv(R/filename).iterrows():
            chosen=data
            for k in group:chosen=chosen[chosen[k]==r[k]]
            assert len(chosen)==r.n==100
            assert abs(statistics.mean(chosen.pnl.tolist())-r.pnl_mean)<1e-9
            assert abs(statistics.stdev(chosen.pnl.tolist())-r.pnl_sd)<1e-9
    ap=pd.read_csv(R/'ablation_pairs.csv')
    for _,r in ap.iterrows():
        g=a[a.scenario==r.scenario];weights=WEIGHTS[r.contrast]
        by_name={name:dict(zip(g[g.strategy==name].seed,g[g.strategy==name][r.metric])) for name in weights}
        values=[math.fsum(weight*by_name[name][seed] for name,weight in weights.items()) for seed in m['seeds']]
        verify_interval(values,r)
    fp=pd.read_csv(R/'flow_control_pairs.csv')
    for _,r in fp.iterrows():
        g=flow[flow.strategy==r.strategy]
        informed=dict(zip(g[g.flow=='Informed'].seed,g[g.flow=='Informed'][r.metric]))
        independent=dict(zip(g[g.flow=='Independent'].seed,g[g.flow=='Independent'][r.metric]))
        verify_interval([informed[seed]-independent[seed] for seed in m['seeds']],r)
    d=pd.read_csv(R/'tape_diagnostics.csv')
    assert len(d)==100 and d.shared_price_and_uniforms.all()
    assert d.informed_direction_correlation.mean()>.8 and abs(d.independent_direction_correlation.mean())<.03
    receipt=dict(status='passed',new_strategy_runs=2000,ablation_rows=1500,flow_control_rows=1000,
                 reused_informed_rows=500,paired_intervals_recomputed=len(ap)+len(fp),
                 seed_pairs_with_identical_prices_and_uniforms=100,
                 checks='Disjoint seeds, complete counts, finiteness, inventory caps, per-run accounting residuals, reused row identity, independent means/SD/linear contrast intervals, source/plan/result hashes')
    (R/'validation.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt,indent=2))

if __name__=='__main__':main()
