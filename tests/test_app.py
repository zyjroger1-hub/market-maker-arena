"""Streamlit widget/state integration tests; browser inspection is separate."""
from pathlib import Path
from streamlit.testing.v1 import AppTest
APP=Path(__file__).resolve().parents[1]/"app.py"


def button(at,label):
    return next(x for x in at.button if x.label==label)


def test_play_advance_pause_replay_and_finish():
    at=AppTest.from_file(APP,default_timeout=60).run()
    assert not at.exception
    assert at.session_state["match"]["step"]==0
    button(at,"Advance round").click().run()
    assert not at.exception and at.session_state["match"]["step"]==50
    at.checkbox[0].uncheck(); at.checkbox[1].uncheck()
    button(at,"Advance round").click().run()
    game=at.session_state["match"]
    assert not any(f["step"]>50 for f in game["you"].fills)
    button(at,"Replay from start").click().run()
    assert at.session_state["match"]["step"]==0
    # Switch round length to finish; both-side pause must remain safe.
    next(x for x in at.selectbox if x.label=="Steps per round").set_value(100)
    for _ in range(6): button(at,"Advance round").click().run()
    assert at.session_state["match"]["step"]==600
    assert button(at,"Advance round").disabled
    assert at.success and not at.exception


def test_research_runs_and_stale_controls_labelled():
    at=AppTest.from_file(APP,default_timeout=90).run()
    at.radio[0].set_value("Research").run()
    assert not at.exception and len(at.dataframe)>=2
    at.multiselect[0].set_value(["Stable"])
    at.select_slider[0].set_value(20)
    button(at,"Run paired experiment").click().run(timeout=90)
    assert not at.exception
    cfg,raw=at.session_state["research"]
    assert cfg["n"]==20 and len(raw)==60 and raw.seed.nunique()==20
    next(x for x in at.slider if x.label=="Base half-spread (CU)").set_value(.06).run()
    assert at.warning and not at.exception


def test_match_settings_reset():
    at=AppTest.from_file(APP,default_timeout=60).run()
    button(at,"Advance round").click().run()
    next(x for x in at.selectbox if x.label=="Market scenario").set_value("Adverse selection").run()
    assert at.session_state["match"]["step"]==0
    assert at.session_state["match"]["tape"].scenario=="Adverse selection"
    assert not at.exception


def test_five_policy_flow_control_and_saved_restore():
    at=AppTest.from_file(APP,default_timeout=90).run()
    at.radio[0].set_value("Research").run()
    at.multiselect[0].set_value(["Adverse selection"])
    at.select_slider[0].set_value(20)
    next(x for x in at.checkbox if x.label=="Include width/skew controls").check()
    next(x for x in at.checkbox if x.label=="Informative customer flow").uncheck()
    button(at,"Run paired experiment").click().run(timeout=90)
    assert not at.exception
    cfg,raw=at.session_state['research']
    assert len(raw)==100 and len(cfg['strategy_names'])==5 and cfg['informative_flow'] is False
    # Verify that the UI forwards the information switch to the engine.
    from arena.engine import Config,make_tape,simulate
    from arena.strategies import Strategy
    expected=simulate(Config(),make_tape(Config(),'Adverse selection',cfg['seed_start'],informative_flow=False),Strategy('Fixed')).metrics()['pnl']
    assert raw[(raw.seed==cfg['seed_start'])&(raw.strategy=='Fixed')].iloc[0].pnl==expected
    next(x for x in at.selectbox if x.label=='Saved study').set_value('Mechanism study · 5 policies').run()
    button(at,'Load saved results').click().run()
    assert 'research' not in at.session_state
    assert set(at.dataframe[0].value['Strategy'])=={'Fixed','Inventory','Adaptive','Width only','Skew only'}
    assert not at.exception


def test_model_documents_include_followup_without_broken_images():
    at=AppTest.from_file(APP,default_timeout=60).run()
    at.radio[0].set_value('Model & evidence').run()
    assert any(x.label=='MECHANISM_REPORT.md' for x in at.expander)
    assert not at.exception
