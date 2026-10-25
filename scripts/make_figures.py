"""Static research figures from reviewed CSV rows; no network resources."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
R=ROOT/"RESULTS"; F=R/"figures"; F.mkdir(exist_ok=True)
NAMES=["Fixed","Inventory","Adaptive"]
COLORS=["#728399","#245E87","#724B88"]
SCENARIOS=["Stable","Trend","High volatility","Jump","Adverse selection"]
plt.rcParams.update({"font.size":10,"axes.spines.top":False,"axes.spines.right":False,
                     "axes.titleweight":"bold","figure.facecolor":"white","axes.labelcolor":"#172B40",
                     "text.color":"#172B40","axes.edgecolor":"#A1ACB6","savefig.dpi":170})
raw=pd.read_csv(R/"main_runs.csv"); summary=pd.read_csv(R/"summary.csv")
pairs=pd.read_csv(R/"paired_comparisons.csv")


def save(fig,name):
    fig.savefig(F/name,bbox_inches="tight")
    plt.close(fig)


fig,axes=plt.subplots(2,3,figsize=(12,7.2))
for ax,scenario in zip(axes.flat,SCENARIOS):
    g=raw[raw.scenario==scenario]
    box=ax.boxplot([g[g.strategy==n].pnl for n in NAMES],tick_labels=NAMES,patch_artist=True,
                   showmeans=True,meanprops=dict(marker="D",markerfacecolor="#172B40",markeredgecolor="#172B40",markersize=4),
                   flierprops=dict(marker=".",markersize=3,alpha=.5))
    for patch,color in zip(box["boxes"],COLORS): patch.set_facecolor(color); patch.set_alpha(.65)
    for median in box["medians"]: median.set_color("#172B40")
    ax.axhline(0,color="#A1ACB6",linewidth=.8); ax.set_title(scenario)
    ax.set_ylabel("Net terminal P&L (CU)"); ax.grid(axis="y",alpha=.15)
axes.flat[-1].axis("off")
axes.flat[-1].text(.03,.85,"100 paired seeds per scenario\n600 one-second steps per path\n0.5 bps fee per fill\nTerminal inventory marked to reference\n\nBox: quartiles; line: median\nDiamond: mean; whiskers: 1.5 × IQR\nDots: remaining observations\n\nIndependent panel scales reveal dispersion.\nSynthetic fills; no real trading results.",va="top",linespacing=1.6)
fig.suptitle("P&L distributions across simulated markets",fontsize=16,x=.07,ha="left")
fig.tight_layout(rect=[0,0,1,.94]); save(fig,"pnl_distributions.png")

fig,axes=plt.subplots(1,2,figsize=(11,4.4),sharey=True)
for ax,contrast,color in zip(axes,["Inventory - Fixed","Adaptive - Inventory"],COLORS[1:]):
    p=pairs[(pairs.metric=="pnl") & (pairs.contrast==contrast)].set_index("scenario").loc[SCENARIOS]
    y=np.arange(len(p)); mean=p.mean_difference.to_numpy()
    ax.errorbar(mean,y,xerr=np.array([mean-p.ci_low,p.ci_high-mean]),fmt="o",color=color,capsize=4)
    ax.axvline(0,color="#A1ACB6",linewidth=1); ax.set_yticks(y,SCENARIOS)
    ax.set_title(contrast); ax.set_xlabel("Mean paired net P&L difference (CU)")
    ax.grid(axis="x",alpha=.15)
    ax.set_xlim(-5.6,5.6)
axes[0].invert_yaxis()
fig.suptitle("95% Student t intervals across 100 matched seeds",fontsize=14)
fig.tight_layout(); save(fig,"paired_pnl.png")

fig,axes=plt.subplots(1,2,figsize=(12,4.8))
markers=["o","s","^","D","P"]
for scenario,marker in zip(SCENARIOS,markers):
    for name,color in zip(NAMES,COLORS):
        row=summary[(summary.scenario==scenario)&(summary.strategy==name)].iloc[0]
        axes[0].scatter(row.mean_drawdown,row.pnl_mean,color=color,marker=marker,s=65)
        axes[1].scatter(row.avg_abs_inventory,row.mean_fills,color=color,marker=marker,s=65)
axes[0].axhline(0,color="#A1ACB6",linewidth=.8)
axes[0].set(xlabel="Mean maximum drawdown (CU)",ylabel="Mean net P&L (CU)",title="Outcome and drawdown")
axes[1].set(xlabel="Mean absolute inventory (units)",ylabel="Mean fills per path",title="Execution opportunity and inventory")
from matplotlib.lines import Line2D
handles=[Line2D([0],[0],marker="o",color=c,linestyle="",label=n) for n,c in zip(NAMES,COLORS)]
handles += [Line2D([0],[0],marker=m,color="#172B40",linestyle="",label=s) for s,m in zip(SCENARIOS,markers)]
fig.legend(handles=handles,loc="lower center",ncol=4,frameon=False,bbox_to_anchor=(.5,-.04))
for ax in axes: ax.grid(alpha=.15)
fig.suptitle("Scenario means · 100 paths per point (descriptive, no uncertainty encoded)",fontsize=14)
fig.tight_layout(rect=[0,.12,1,.95]); save(fig,"risk_opportunity.png")

paths=pd.read_csv(R/"representative_paths.csv")
g=paths[paths.scenario=="High volatility"]
fig,axes=plt.subplots(3,1,figsize=(10,8),sharex=True)
first=g[g.strategy=="Fixed"]
axes[0].plot(first.time_s,first.mid,color="#172B40",linewidth=1)
axes[0].set(ylabel="Reference (CU)",title="High volatility · predetermined example seed 10000")
for name,color in zip(NAMES,COLORS):
    tr=g[g.strategy==name]
    axes[1].step(tr.time_s,tr.inventory,where="post",label=name,color=color,linewidth=1)
    axes[2].plot(tr.time_s,tr.equity.cummax()-tr.equity,label=name,color=color,linewidth=1)
axes[1].axhline(10,color="#A1ACB6",linestyle=":");axes[1].axhline(-10,color="#A1ACB6",linestyle=":")
axes[1].set(ylabel="Inventory (units)",ylim=(-11,11));axes[1].legend(ncol=3,frameon=False)
axes[2].set(ylabel="Drawdown (CU)",xlabel="Elapsed seconds")
for ax in axes:
    ax.grid(alpha=.15)
    for left,right in ((150,300),(450,600)): ax.axvspan(left,right,color="#E6EAF0",alpha=.5,zorder=-1)
fig.text(.1,.01,"Shaded blocks have higher exogenous volatility. One path illustrates mechanics; it is not an average.",fontsize=9)
fig.tight_layout(rect=[0,.03,1,1]);save(fig,"example_path.png")

sens=pd.read_csv(R/"sensitivity_summary.csv")
settings=list(sens.setting.unique())
fig,axes=plt.subplots(1,2,figsize=(10,6))
from matplotlib.colors import TwoSlopeNorm
norm=TwoSlopeNorm(vmin=min(sens.pnl_mean.min(),-.001),vcenter=0,vmax=max(sens.pnl_mean.max(),.001))
for ax,scenario in zip(axes,["Stable","Adverse selection"]):
    values=sens[sens.scenario==scenario].pivot(index="setting",columns="strategy",values="pnl_mean").loc[settings,NAMES]
    im=ax.imshow(values.to_numpy(),cmap="PuOr",norm=norm,aspect="auto")
    for y in range(len(settings)):
        for x in range(3):
            val=values.iloc[y,x]
            rgb=plt.get_cmap("PuOr")(norm(val))[:3]
            luminance=.299*rgb[0]+.587*rgb[1]+.114*rgb[2]
            ax.text(x,y,f"{val:+.2f}",ha="center",va="center",color="white" if luminance<.5 else "#172B40",fontsize=9)
    ax.set_xticks(range(3),NAMES);ax.set_yticks(range(len(settings)),settings);ax.set_title(scenario)
    if scenario=="Adverse selection":
        ax.set_yticklabels([]); ax.tick_params(axis="y",left=False)
fig.suptitle("Sensitivity · mean net P&L (CU), 30 paired seeds per setting",fontsize=13)
fig.tight_layout(rect=[0,0,.92,.95]);fig.colorbar(im,ax=axes,shrink=.6,label="Mean net P&L (CU)")
save(fig,"sensitivity.png")
(F/"sources.json").write_text(json.dumps({"pnl_distributions.png":"main_runs.csv","paired_pnl.png":"paired_comparisons.csv",
 "risk_opportunity.png":"summary.csv","example_path.png":"representative_paths.csv; scenario=High volatility; seed=10000",
 "sensitivity.png":"sensitivity_summary.csv"},indent=2)+"\n")
print("Generated 5 research figures")
