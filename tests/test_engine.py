from dataclasses import replace
import math
import numpy as np
import pytest
from arena.engine import Config, Tape, Quote, Ledger, make_tape, observe, advance, simulate, bound_quote, SCENARIOS
from arena.strategies import Strategy, Manual, STRATEGIES, ALL_STRATEGIES


def tape(mids, directions, accept=0.0, arrival=0.0):
    n=len(directions)
    return Tape(np.array(mids,dtype=float),np.array(directions),np.full(n,arrival),np.full(n,accept),"test",0)


def test_buy_sell_accounting_and_fee():
    c=Config(steps=2,fee_bps=10)
    t=tape([100,101,102],[-1,1])
    l=Ledger(c)
    advance(t,l,Quote(99,101),0)
    assert l.inventory==1 and l.cash==pytest.approx(10000-99-.099)
    assert l.history[-1]["pnl"]==pytest.approx(1.901)
    advance(t,l,Quote(100,102),1)
    assert l.inventory==0 and l.cash==pytest.approx(10002.799)
    m=l.metrics()
    assert m["pnl"]==pytest.approx(2.799)
    assert m["fees"]==pytest.approx(.201)
    assert m["spread_capture"]==pytest.approx(2)
    assert m["holding_pnl"]==pytest.approx(1)


def test_terminal_inventory_marked_no_liquidation():
    c=Config(steps=1,fee_bps=0)
    l=simulate(c,tape([100,98],[-1]),Manual(1,0))
    assert l.inventory==1 and len(l.fills)==1
    assert l.metrics()["pnl"]==pytest.approx(-1)
    assert l.metrics()["max_drawdown"]==pytest.approx(1)


@pytest.mark.parametrize("direction",[-1,1])
def test_cap_blocks_fills_and_permits_unwind(direction):
    c=Config(steps=4,inventory_limit=1,fee_bps=0)
    l=simulate(c,tape([100]*5,[direction,direction,-direction,-direction]),Manual(.05,0))
    assert len(l.fills)==3 and l.metrics()["max_abs_inventory"]==1
    assert l.cap_blocked==1
    for row in l.history: assert abs(row["inventory"])<=1


def test_quote_bounds_and_pause():
    c=Config(steps=2)
    q=bound_quote(Quote(1000,-100),100,c)
    assert q.bid==99.99 and q.ask==100.01
    q=bound_quote(Quote(-1,1000),100,c)
    assert q.bid==95 and q.ask==105
    with pytest.raises(ValueError): bound_quote(Quote(float("nan"),None),100,c)
    l=simulate(c,tape([100]*3,[-1,1]),Manual(.05,0,False,False))
    assert l.metrics()["fills"]==0 and l.paused_arrivals==2


def test_same_seed_and_common_inputs():
    c=Config(steps=80)
    a,b=make_tape(c,"Stable",42),make_tape(c,"Stable",42)
    for name in ("mids","directions","arrival_u","acceptance_u"):
        np.testing.assert_array_equal(getattr(a,name),getattr(b,name))
    for s in ALL_STRATEGIES:
        assert simulate(c,a,Strategy(s)).history==simulate(c,b,Strategy(s)).history
    with pytest.raises(ValueError): a.mids[0]=0


def test_future_is_not_in_observation_or_policy():
    c=Config(steps=12)
    a=make_tape(c,"Stable",73)
    altered=a.mids.copy(); altered[6:]*=1.2
    b=replace(a,mids=altered)
    la,lb=Ledger(c),Ledger(c)
    for t in range(5):
        oa,ob=observe(a,la,t),observe(b,lb,t)
        assert oa==ob and len(oa.past_mids)==t+1 and oa.past_mids[-1]==oa.mid
        assert not hasattr(oa,"tape")
        for s in ALL_STRATEGIES: assert Strategy(s).quote(oa)==Strategy(s).quote(ob)
        advance(a,la,Strategy().quote(oa),t)
        advance(b,lb,Strategy().quote(ob),t)
    assert la.history==lb.history


def test_volatility_uses_history_only():
    c=Config(steps=3)
    t=tape([100,100.1,100.2,999],[-1,-1,-1])
    l=Ledger(c); p=Strategy("Adaptive")
    assert p.vol_ratio(observe(t,l,0))==1
    advance(t,l,Quote(None,None),0)
    assert p.vol_ratio(observe(t,l,1))==1
    advance(t,l,Quote(None,None),1)
    assert p.vol_ratio(observe(t,l,2))==pytest.approx(2.5)


def test_adverse_selection_has_directional_information():
    c=Config(steps=15000)
    toxic=make_tape(c,"Adverse selection",55)
    clean=make_tape(c,"Stable",55)
    toxic_corr=np.corrcoef(toxic.directions,np.diff(np.log(toxic.mids)))[0,1]
    clean_corr=np.corrcoef(clean.directions,np.diff(np.log(clean.mids)))[0,1]
    assert toxic_corr>.8 and abs(clean_corr)<.04


def test_acceptance_declines_with_distance():
    c=Config(steps=1,fee_bps=0)
    t=tape([100,100],[-1],accept=.4)
    assert simulate(c,t,Manual(.01,0)).metrics()["fills"]==1
    assert simulate(c,t,Manual(1,0)).metrics()["fills"]==0


@pytest.mark.parametrize("scenario",SCENARIOS)
@pytest.mark.parametrize("variant",[dict(arrival_rate=0,vol_multiplier=0),dict(fee_bps=100,arrival_rate=100,inventory_limit=1,vol_multiplier=10),dict(distance_decay=1000)])
def test_extremes_finite_and_bounded(scenario,variant):
    c=Config(steps=120,**variant)
    for name in ALL_STRATEGIES:
        l=simulate(c,make_tape(c,scenario,19),Strategy(name))
        assert all(math.isfinite(v) for v in l.metrics().values())
        assert l.metrics()["max_abs_inventory"]<=c.inventory_limit
        assert l.metrics()["accounting_error"]<1e-7


@pytest.mark.parametrize("kwargs",[dict(fee_bps=-1),dict(inventory_limit=0),dict(steps=1.5),dict(arrival_rate=float("nan")),dict(vol_multiplier=-1),dict(dt=0)])
def test_invalid_config_rejected(kwargs):
    with pytest.raises(ValueError): Config(**kwargs)


def test_hand_drawdown_and_inventory_average():
    c=Config(steps=3,fee_bps=0)
    l=simulate(c,tape([100,101,99,100],[-1,-1,-1]),Manual(.05,0))
    # q after each fill: 1,2,3. Equity: 10000,10001.05,9997.10,10000.15.
    assert l.metrics()["max_drawdown"]==pytest.approx(3.95)
    assert l.metrics()["avg_abs_inventory"]==2


def test_batch_pairs_complete():
    from arena.experiments import run_batch,paired_comparisons
    raw=run_batch(Config(steps=15),["Stable"],[11,12,13])
    assert len(raw)==9 and not raw.duplicated(["scenario","seed","strategy"]).any()
    pairs=paired_comparisons(raw)
    p=raw.pivot(index="seed",columns="strategy",values="pnl")
    row=pairs[(pairs.contrast=="Inventory - Fixed") & (pairs.metric=="pnl")].iloc[0]
    assert row.mean_difference==pytest.approx((p.Inventory-p.Fixed).mean())
