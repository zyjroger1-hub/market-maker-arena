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
