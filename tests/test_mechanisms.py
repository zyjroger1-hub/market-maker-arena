"""Mechanism isolation and protection against misleading paired comparisons."""
from dataclasses import replace
from pathlib import Path
import json
import numpy as np
import pytest
from arena.engine import Config,Ledger,Observation,make_tape,observe
from arena.strategies import Strategy,ALL_STRATEGIES
from arena.experiments import run_batch,paired_comparisons,paired_linear_contrasts


def test_factorial_quotes_isolate_controls():
    # Two completed returns of 0.08 -> ratio 2; q=2 -> base shift -0.03.
    obs=Observation(2,1,100.16,2,10000,(100.,100.08,100.16))
    expected={"Inventory":(100.08,100.18),"Width only":(100.03,100.23),
              "Skew only":(99.99,100.09),"Adaptive":(99.94,100.14)}
    for name,(bid,ask) in expected.items():
        q=Strategy(name).quote(obs)
        assert q.bid==pytest.approx(bid) and q.ask==pytest.approx(ask)


def test_matched_control_preserves_prices_and_acceptance_tape():
    c=Config(steps=600)
    a=make_tape(c,"Adverse selection",30000)
    b=make_tape(c,"Adverse selection",30000,informative_flow=False)
    for key in ("mids","arrival_u","acceptance_u"):
        np.testing.assert_array_equal(getattr(a,key),getattr(b,key))
    assert not np.array_equal(a.directions,b.directions)
    np.testing.assert_array_equal(b.directions,make_tape(c,"Adverse selection",30000,informative_flow=False).directions)
    assert a.flow_mode=="Informed" and b.flow_mode=="Independent"
    with pytest.raises(ValueError):b.directions[0]=1


def test_control_removes_information_without_changing_volatility():
    c=Config(steps=15000)
    a=make_tape(c,"Adverse selection",30001)
    b=make_tape(c,"Adverse selection",30001,informative_flow=False)
    returns=np.diff(np.log(a.mids))
    assert np.corrcoef(a.directions,returns)[0,1]>.8
    assert abs(np.corrcoef(b.directions,returns)[0,1])<.04
    assert np.std(returns)==np.std(np.diff(np.log(b.mids)))


@pytest.mark.parametrize("name",ALL_STRATEGIES)
def test_all_policies_use_only_prefix(name):
    c=Config(steps=10);a=make_tape(c,"High volatility",70)
    mids=a.mids.copy();mids[6:]*=2;b=replace(a,mids=mids)
    assert Strategy(name).quote(replace(observe(a,Ledger(c),5),inventory=2))==Strategy(name).quote(replace(observe(b,Ledger(c),5),inventory=2))


@pytest.mark.parametrize("bad",["missing","duplicate","nan","inf","one_pair"])
def test_invalid_paired_samples_fail_instead_of_dropping(bad):
    raw=run_batch(Config(steps=5),["Stable"],[7,8])
    if bad=="missing":raw=raw.drop(index=0)
    elif bad=="duplicate":raw=__import__('pandas').concat([raw,raw.iloc[[0]]])
    elif bad in ("nan","inf"):raw.loc[0,"pnl"]=float(bad)
    else:raw=raw[raw.seed==7]
    with pytest.raises(ValueError):paired_comparisons(raw)


def test_factorial_interaction_is_paired_linear_difference():
    raw=run_batch(Config(steps=20),["Stable"],[7,8,9],strategy_names=ALL_STRATEGIES)
    p=raw.pivot(index="seed",columns="strategy",values="pnl")
    expected=p.Adaptive-p['Width only']-p['Skew only']+p.Inventory
    row=paired_comparisons(raw).query("metric=='pnl' and contrast=='Interaction (width x skew)'").iloc[0]
    assert row.mean_difference==pytest.approx(expected.mean()) and row.n==3


@pytest.mark.parametrize("seeds",[[1,1],[1.5,2],[True,2],[-1,2]])
def test_invalid_seed_sets_rejected(seeds):
    with pytest.raises(ValueError):run_batch(Config(steps=5),["Stable"],seeds)


@pytest.mark.parametrize("window",[2.5,True])
def test_noninteger_windows_rejected(window):
    with pytest.raises(ValueError):Strategy(window=window)


def test_original_market_tapes_are_unchanged():
    fixture=json.loads((Path(__file__).parent/"fixtures/legacy_tapes.json").read_text())
    for scenario,expected in fixture.items():
        t=make_tape(Config(steps=40),scenario,42)
        np.testing.assert_allclose(t.mids,expected['mids'],rtol=1e-14,atol=0)
        for key in ('directions','arrival_u','acceptance_u'):
            np.testing.assert_array_equal(getattr(t,key),expected[key])
