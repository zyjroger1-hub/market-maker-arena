"""Run with: python -m streamlit run app.py --server.address 127.0.0.1"""
from pathlib import Path
from dataclasses import asdict
import json
import re
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import streamlit as st
from arena.engine import Config,SCENARIOS,make_tape,Ledger,observe,advance,bound_quote
from arena.strategies import Strategy,Manual,STRATEGIES
from arena.experiments import run_batch,summarize,paired_comparisons

ROOT=Path(__file__).resolve().parent
COLORS={"You":"#A85F13","Fixed":"#728399","Inventory":"#245E87","Adaptive":"#724B88"}
st.set_page_config(page_title="Market Maker Arena",page_icon="↔",layout="wide")
st.markdown("""<style>
.block-container {max-width:1250px;padding-top:3.8rem;padding-bottom:2rem;}
h1 {letter-spacing:-1.2px;} [data-testid="stMetricValue"] {font-size:1.65rem;}
[data-testid="stCaptionContainer"] {font-size:.88rem;}
div.stButton > button[kind="primary"] {font-weight:650;}
</style>""",unsafe_allow_html=True)
st.caption("OXFORD MATHS · EDUCATIONAL RESEARCH PROJECT")
st.title("Market Maker Arena")
st.markdown("**Earn the spread. Carry the risk.** Explore how quotes change fills, inventory and net P&L.")
st.caption("SIMULATION ONLY · No live trading · Synthetic customer fills · Terminal inventory marked to the reference price")
mode=st.radio("Workspace",["Play","Research","Model & evidence"],horizontal=True,label_visibility="collapsed")


def chart_style(fig,height=360):
    fig.update_layout(template="plotly_white",height=height,margin=dict(l=20,r=20,t=55,b=75),
                      font=dict(family="Arial",size=13,color="#172B40"),paper_bgcolor="rgba(0,0,0,0)",
                      legend=dict(orientation="h",y=-.18,x=0,title_text=""),
                      hovermode=fig.layout.hovermode or "x unified")
    return fig


def scoreboard(players):
    rows=[]
    for label,l in players.items():
        m=l.metrics()
        rows.append({"Dealer":label,"Net P&L (CU)":m["pnl"],"Max drawdown (CU)":m["max_drawdown"],
                     "Mean |inventory|":m["avg_abs_inventory"],"Max |inventory|":m["max_abs_inventory"],
                     "Fills":m["fills"],"Fees (CU)":m["fees"],"End inventory":m["terminal_inventory"]})
    return pd.DataFrame(rows).set_index("Dealer")


if mode=="Play":
    with st.sidebar:
        st.header("Match settings")
        scenario=st.selectbox("Market scenario",SCENARIOS,key="play_scenario")
        seed=int(st.number_input("Random seed",min_value=0,max_value=2**31-1,value=42,step=1,key="play_seed"))
        opponent=st.selectbox("Algorithm",["Adaptive","Inventory","Fixed"])
        st.caption("Each match: 600 one-second steps. Changing match settings restarts the match. Replay uses the same hidden tape.")
        restart=st.button("Replay from start",width="stretch")
        with st.expander("Scenario guide"):
            st.write("Stable: no drift. Trend: positive expected drift. High volatility: alternating quiet/noisy blocks. Jump: one surprise signed jump. Adverse selection: customer buys tend to precede rises, and sells precede falls.")
        st.markdown("**A round is a quoting rule**")
        st.caption("Within a round, quotes follow the current reference with your chosen width and offset. No clicking-speed advantage. At most one unit fills per step.")
    c=Config(); signature=(scenario,seed,opponent)
    if restart or st.session_state.get("match_signature")!=signature:
        st.session_state.match_signature=signature
        st.session_state.match=dict(tape=make_tape(c,scenario,seed),you=Ledger(c),algo=Ledger(c),step=0)
    game=st.session_state.match; step=game["step"]
    you,algo=game["you"],game["algo"]
    mid=float(game["tape"].mids[step])
    st.subheader(f"{scenario} · You vs {opponent}")
    st.progress(step/c.steps,text=f"Step {step} / {c.steps} · {step} simulated seconds elapsed")
    cols=st.columns(3)+st.columns(2)
    vals=[("Reference (CU)",f"{mid:.3f}"),("Your cash (CU)",f"{you.cash:,.2f}"),
          ("Inventory (units)",f"{you.inventory:+d}"),("Your total assets (CU)",f"{you.cash+you.inventory*mid:,.2f}"),
          ("Your net P&L (CU)",f"{you.cash+you.inventory*mid-c.initial_cash:+.2f}")]
    for col,(label,value) in zip(cols,vals): col.metric(label,value)
    if you.inventory>0:
        st.info("You are long inventory. A lower quote centre makes selling more likely and buying less likely. It also gives up some price on sales.")
    elif you.inventory<0:
        st.info("You are short inventory. A higher quote centre makes buying more likely and selling less likely. It also gives up some price on purchases.")
    else:
        st.info("You are flat. A narrower spread attracts more fills; a wider spread earns more per accepted quote but misses more customers.")
    with st.form("quote_form"):
        a,b=st.columns(2)
        with a:
            full_spread=st.slider("Full spread (CU)",.02,.60,.10,.02,help="Bid/ask separation before boundary clipping. 0.10 means 0.05 on each side.")
        with b:
            offset=st.slider("Quote centre offset (CU)",-.30,.30,.0,.01,help="Negative shifts both quotes down; positive shifts both up. Quotes cannot cross the reference.")
        d,e,f=st.columns(3)
        bid_on=d.checkbox("Bid (buy)",value=True)
        ask_on=e.checkbox("Ask (sell)",value=True)
        steps_round=f.selectbox("Steps per round",[10,25,50,100],index=2)
        submitted=st.form_submit_button("Advance round",type="primary",disabled=step>=c.steps,width="stretch")
    manual=Manual(full_spread/2,offset,bid_on,ask_on)
    preview=bound_quote(manual.quote(observe(game["tape"],you,step)),mid,c)
    bp=preview.bid if you.inventory<c.inventory_limit else None
    ap=preview.ask if you.inventory>-c.inventory_limit else None
    st.caption(f"Next quote preview · bid {f'{bp:.3f}' if bp is not None else 'OFF'} · ask {f'{ap:.3f}' if ap is not None else 'OFF'} · Quotes clipped to [0.01, 5] CU from reference (relative safety bounds at very low prices). Hard inventory cap ±10.")
    if submitted:
        for i in range(step,min(c.steps,step+steps_round)):
            advance(game["tape"],you,manual.quote(observe(game["tape"],you,i)),i)
            advance(game["tape"],algo,Strategy(opponent).quote(observe(game["tape"],algo,i)),i)
        game["step"]=len(you.history)-1
        st.rerun()
    if step==c.steps:
        diff=you.metrics()["pnl"]-algo.metrics()["pnl"]
        st.success(f"Match complete · your P&L minus {opponent}: {diff:+.2f} CU. Compare inventory and drawdown alongside profit. No terminal liquidation occurred.")
    players={"You":you,opponent:algo}
    chart=make_subplots(rows=2,cols=1,shared_xaxes=True,vertical_spacing=.12,
                        subplot_titles=("Reference and your submitted quotes","Net mark-to-market P&L · after fees"))
    h=pd.DataFrame(you.history)
    chart.add_trace(go.Scatter(x=h.time_s,y=h.mid,name="Reference",line=dict(color="#172B40")),row=1,col=1)
    # Quote recorded in row t+1 was submitted at time t.
    if step:
        for side,color in (("bid","#245E87"),("ask","#A85F13")):
            chart.add_trace(go.Scatter(x=h.time_s.iloc[:-1],y=h[side].iloc[1:],name=f"Your {side}",
                                      connectgaps=False,line=dict(color=color,width=1,dash="dot")),row=1,col=1)
    for name,l in players.items():
        trace=pd.DataFrame(l.history)
        chart.add_trace(go.Scatter(x=trace.time_s,y=trace.pnl,name=name,line=dict(color=COLORS[name])),row=2,col=1)
    chart.update_yaxes(title_text="Price (CU)",row=1,col=1)
    chart.update_yaxes(title_text="Net P&L (CU)",row=2,col=1)
    chart.update_xaxes(title_text="Elapsed seconds",row=2,col=1)
    st.plotly_chart(chart_style(chart,530),width="stretch")
    st.dataframe(scoreboard(players).style.format(precision=2),width="stretch")
    with st.expander("Inventory trajectories and trade history",expanded=step==c.steps):
        fig=go.Figure()
        for name,l in players.items():
            tr=pd.DataFrame(l.history)
            fig.add_trace(go.Scatter(x=tr.time_s,y=tr.inventory,name=name,line=dict(color=COLORS[name],shape="hv")))
        fig.add_hline(y=10,line_dash="dot"); fig.add_hline(y=-10,line_dash="dot")
        fig.update_yaxes(title="Inventory (units)",range=[-11,11]); fig.update_xaxes(title="Elapsed seconds")
        st.plotly_chart(chart_style(fig,280),width="stretch")
        view=st.selectbox("Trade history",list(players))
        st.dataframe(pd.DataFrame(players[view].fills).tail(30),width="stretch")
        st.download_button("Download all match paths",pd.DataFrame.from_records([dict(row,dealer=n) for n,l in players.items() for row in l.history]).to_csv(index=False),"match_paths.csv","text/csv")

elif mode=="Research":
    st.subheader("Strategy research lab")
    st.write("Compare the same market paths across three policies. Repeated seeds measure uncertainty within this model; they do not establish real-world returns.")
    with st.sidebar:
        st.header("Experiment controls")
        scenarios=st.multiselect("Scenarios",SCENARIOS,default=list(SCENARIOS))
        n=st.select_slider("Replicates per scenario",[20,50,100,200],value=100)
        seed_start=int(st.number_input("First evaluation seed",0,2**31-1000,10000))
        width=st.slider("Base half-spread (CU)",.02,.20,.05,.01,help="Fixed and Inventory use this width; Adaptive scales it by trailing volatility.")
        skew=st.slider("Inventory skew (CU per unit)",.0,.04,.015,.005,format="%.3f",help="Each long unit lowers the quote centre by this amount. Adaptive additionally scales by squared trailing volatility.")
        with st.expander("Costs and market assumptions"):
            fee=st.slider("Fee (basis points per fill)",.0,2.0,.5,.1)
            rate=st.slider("Customer intensity (/second)",.1,2.0,.8,.1)
            cap=st.slider("Inventory cap (units)",1,20,10)
            vm=st.slider("Volatility multiplier",.5,2.0,1.0,.1)
        run=st.button("Run paired experiment",type="primary",width="stretch",disabled=not scenarios)
        st.caption("The published report uses fixed defaults. These controls create exploratory results; keep fresh seeds for later evaluation.")
    c=Config(fee_bps=fee,arrival_rate=rate,inventory_limit=cap,vol_multiplier=vm)
    requested=dict(config=asdict(c),scenarios=scenarios,n=n,seed_start=seed_start,half_spread=width,skew=skew)
    if run:
        bar=st.progress(0,text="Running matched price and customer tapes…")
        raw=run_batch(c,scenarios,list(range(seed_start,seed_start+n)),width,skew,progress=bar.progress)
        st.session_state.research=(requested,raw)
        bar.empty()
    if "research" in st.session_state:
        used,raw=st.session_state.research
        if used!=requested: st.warning("Controls changed. The results below retain the last run configuration; run again to apply the new settings.")
        st.caption(f"Last run · {len(raw):,} strategy runs · {used['n']} seeds/scenario · seeds {used['seed_start']}–{used['seed_start']+used['n']-1} · 600 seconds each")
        with st.expander("Exact last-run configuration"): st.json(used)
        source_label="Your exploratory run"
    else:
        raw=pd.read_csv(ROOT/"RESULTS/main_runs.csv")
        source_label="Saved main evaluation · fixed defaults · 100 seeds per scenario"
        st.info("Showing the completed main experiment. Use Run paired experiment to generate your own offline results.")
    st.caption(source_label)
    selected=st.selectbox("Inspect scenario",raw.scenario.unique())
    selected_raw=raw[raw.scenario==selected]
    summary=summarize(selected_raw)
    table=summary[["strategy","n","pnl_mean","pnl_sd","pnl_p05","pnl_p95","mean_drawdown","avg_abs_inventory","mean_fills"]].rename(columns={
        "strategy":"Strategy","pnl_mean":"Mean net P&L (CU)","pnl_sd":"P&L SD (CU)","pnl_p05":"P&L 5%","pnl_p95":"P&L 95%",
        "mean_drawdown":"Mean max DD (CU)","avg_abs_inventory":"Mean |inventory|","mean_fills":"Mean fills"})
    st.dataframe(table.style.format(precision=2),hide_index=True,width="stretch")
    st.caption("P&L 5%–95% describes individual-path dispersion, not a confidence interval. Drawdown uses step-end marks and includes time zero.")
    a,b=st.tabs(["P&L distribution","Inventory / outcome"])
    with a:
        fig=px.box(selected_raw,x="strategy",y="pnl",color="strategy",color_discrete_map=COLORS,points=False,
                   category_orders={"strategy":list(STRATEGIES)},labels={"strategy":"Strategy","pnl":"Net P&L (CU)"})
        fig.update_layout(showlegend=False,title="Outcome distribution")
        st.plotly_chart(chart_style(fig),width="stretch")
    with b:
        fig=px.scatter(selected_raw,x="avg_abs_inventory",y="pnl",color="strategy",color_discrete_map=COLORS,
                       hover_data=["seed","fills","max_drawdown"],opacity=.6,
                       labels={"avg_abs_inventory":"Mean absolute inventory (units)","pnl":"Net P&L (CU)"})
        fig.update_layout(title="Inventory exposure and outcome",hovermode="closest")
        st.plotly_chart(chart_style(fig),width="stretch")
    pairs=paired_comparisons(selected_raw)
    st.markdown("**Paired differences · 95% intervals for the mean**")
    st.caption("Student t intervals across matched seeds. Negative inventory/drawdown differences mean less exposure/risk. Intervals are unadjusted for multiple comparisons.")
    metric=st.selectbox("Compare metric",["pnl","avg_abs_inventory","max_drawdown","fills"])
    st.dataframe(pairs[pairs.metric==metric][["contrast","n","mean_difference","ci_low","ci_high"]].style.format(precision=3),hide_index=True,width="stretch")
    with st.expander("Example trajectory and drawdown",expanded=False):
        if "research" in st.session_state:
            used,_=st.session_state.research
            ec=Config(**used["config"]); eseed=used["seed_start"]
            ew,es=used["half_spread"],used["skew"]
        else:
            ec=Config(); eseed=10000; ew=.05; es=.015
        from arena.engine import simulate
        tape=make_tape(ec,selected,eseed)
        fig=make_subplots(rows=2,cols=1,shared_xaxes=True,subplot_titles=("Inventory","Drawdown from running equity peak (CU)"))
        for name in STRATEGIES:
            tr=pd.DataFrame(simulate(ec,tape,Strategy(name,ew,es)).history)
            fig.add_trace(go.Scatter(x=tr.time_s,y=tr.inventory,name=name,line=dict(color=COLORS[name],shape="hv")),row=1,col=1)
            dd=tr.equity.cummax()-tr.equity
            fig.add_trace(go.Scatter(x=tr.time_s,y=dd,name=name,showlegend=False,line=dict(color=COLORS[name])),row=2,col=1)
        fig.update_xaxes(title_text="Elapsed seconds",row=2,col=1)
        st.caption(f"Unselected first seed: {eseed}. One path illustrates mechanics; it is not the average result.")
        st.plotly_chart(chart_style(fig,500),width="stretch")
    a,b=st.columns(2)
    a.download_button("Download seed-level results",raw.to_csv(index=False),"research_runs.csv","text/csv")
    # Export the applied configuration, never the pending controls.
    export=st.session_state.research[0] if "research" in st.session_state else json.loads((ROOT/"RESULTS/config.json").read_text())
    b.download_button("Download applied configuration",json.dumps(export,indent=2),"research_config.json","application/json")

else:
    st.subheader("A transparent toy market")
    st.write("Every quote buys or sells one unit. One synthetic customer may arrive each second. More distant quotes are less likely to fill. Prices evolve after the fill, so new inventory immediately carries risk.")
    st.markdown("""
- **Fixed:** symmetric quotes around the current reference.
- **Inventory:** shift the centre down when long and up when short.
- **Adaptive:** also widen quotes when trailing price changes grow, and strengthen the inventory skew.
- **Fair comparison:** all dealers face the same reference prices, customer direction, arrival draws and acceptance draws. Each dealer trades in a separate counterfactual market; they do not compete for the same unit.
- **Causal information:** policies see the current reference and past prices only. The adaptive policy has a fixed warm-up estimate and a 30-return trailing window.
- **Real adverse selection:** in the stress scenario a customer buy predicts an upward next-price shock; the dealer sells before the price rises. This information link is absent in the ordinary high-volatility scenario.
- **Accounting:** equity = cash + inventory × reference. P&L = equity − initial cash. Fees are charged on every filled notional. Terminal inventory stays open and is marked to reference.
""")
    st.latex(r"p_{arrival}=1-e^{-A\Delta t},\qquad p_{accept}=e^{-k\delta}")
    st.caption("A = 0.8 per second; k = 15 per CU; δ is distance from reference. At most one fill per step: a deliberately capped Bernoulli arrival model, not a full Poisson matching engine.")
    st.warning("No order book, queue position, competition, latency, partial fills, financing or strategy impact. Reference prices are synthetic marks. Historical bars cannot prove fills. Profits here are model outputs, not evidence of a tradable edge.")
    st.markdown("**Primary references**")
    st.markdown("""[Market making · Citadel Securities](https://www.citadelsecurities.com/what-we-do/what-is-a-market-maker/) · [Avellaneda & Stoikov (2008)](https://math.nyu.edu/inmemoriam/avellaneda/HighFrequencyTrading.pdf) · [Fill assumptions · HftBacktest](https://hftbacktest.readthedocs.io/en/latest/order_fill.html) · [Public data · Binance](https://github.com/binance/binance-public-data)""")
    st.write("The strategies borrow the intuition of inventory-sensitive reservation prices; this project does not solve the Avellaneda–Stoikov control problem.")
    st.markdown("**Saved research and learning materials**")
    for filename in ("RESEARCH_REPORT.md","MODEL.md","LEARNING_GUIDE_ZH.md","INTERVIEW_PREP.md"):
        p=ROOT/filename
        if p.exists():
            with st.expander(filename):
                text=p.read_text()
                text=re.sub(r"(?<!!)\[([^]]+)\]\((?!https?://)([^)]+)\)",r"\1",text)
                for part in re.split(r"(!\[[^]]*\]\([^)]+\))",text):
                    match=re.fullmatch(r"!\[([^]]*)\]\(([^)]+)\)",part)
                    if match and (ROOT/match[2]).is_file():
                        st.image(str(ROOT/match[2]),caption=match[1])
                    elif part:
                        st.markdown(part)
                st.download_button(f"Download {filename}",p.read_text(),filename,"text/markdown")
