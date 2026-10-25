"""Follow-up figures sourced from the complete seed-level mechanism study."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1];R=ROOT/'RESULTS/mechanisms';F=ROOT/'RESULTS/figures'
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,
                     'figure.facecolor':'white','axes.titleweight':'bold','savefig.dpi':170})
contrasts=['Width only - Inventory','Skew only - Inventory','Adaptive - Width only',
           'Adaptive - Skew only','Interaction (width x skew)']
labels=['Width effect (base skew)','Skew effect (base width)','Extra skew (adaptive width)',
        'Extra width (adaptive skew)','Width × skew interaction']
pairs=pd.read_csv(R/'ablation_pairs.csv').query("metric=='pnl'")
fig,axes=plt.subplots(1,3,figsize=(13,4.2),sharey=True,sharex=True)
for ax,scenario in zip(axes,['Stable','High volatility','Adverse selection']):
    p=pairs[pairs.scenario==scenario].set_index('contrast').loc[contrasts]
    m=p.mean_difference.to_numpy();ax.errorbar(m,np.arange(5),xerr=[m-p.ci_low,p.ci_high-m],fmt='o',capsize=3,color='#245E87')
    ax.axvline(0,color='#A1ACB6',linewidth=.8);ax.grid(axis='x',alpha=.15)
    ax.set_title(scenario);ax.set_yticks(range(5),labels);ax.set_xlabel('Mean paired P&L difference (CU)')
lo=min(-.5,float(pairs[pairs.contrast.isin(contrasts)].ci_low.min())-.3)
hi=max(.5,float(pairs[pairs.contrast.isin(contrasts)].ci_high.max())+.3)
axes[0].set_xlim(lo,hi);axes[0].invert_yaxis()
fig.suptitle('Width / skew ablation · 100 fresh matched seeds · 95% t intervals',fontsize=14)
fig.tight_layout();fig.savefig(F/'ablation_effects.png',bbox_inches='tight');plt.close(fig)

flow=pd.read_csv(R/'flow_control_summary.csv')
pairs=pd.read_csv(R/'flow_control_pairs.csv').query("metric=='pnl'")
names=['Fixed','Inventory','Adaptive','Width only','Skew only']
fig,axes=plt.subplots(1,2,figsize=(12,4.7))
y=np.arange(5)
for mode,offset,color,marker in [('Independent',-.10,'#728399','s'),('Informed',.10,'#A85F13','o')]:
    g=flow[flow.flow==mode].set_index('strategy').loc[names]
    m=g.pnl_mean.to_numpy()
    axes[0].errorbar(m,y+offset,xerr=[m-g.pnl_ci_low,g.pnl_ci_high-m],fmt=marker,color=color,capsize=3,label=mode)
p=pairs.set_index('strategy').loc[names];m=p.mean_difference.to_numpy()
axes[1].errorbar(m,y,xerr=[m-p.ci_low,p.ci_high-m],fmt='o',color='#245E87',capsize=4)
for ax in axes:
    ax.axvline(0,color='#A1ACB6',linewidth=.8);ax.set_yticks(y,names);ax.invert_yaxis();ax.grid(axis='x',alpha=.15)
axes[0].set_title('Mean net P&L · marginal 95% intervals');axes[0].set_xlabel('Mean net P&L (CU)')
handles,labels=axes[0].get_legend_handles_labels()
fig.legend(handles,labels,frameon=False,loc='lower center',bbox_to_anchor=(.29,-.03),ncol=2)
axes[1].set_title('Informed − independent · paired 95% intervals');axes[1].set_xlabel('Mean paired net P&L difference (CU)')
fig.suptitle('Information link control · identical price paths and uniform draws · 100 seeds',fontsize=14)
fig.tight_layout(rect=[0,.05,1,1]);fig.savefig(F/'flow_control.png',bbox_inches='tight');plt.close(fig)
source_path=F/'sources.json';sources=json.loads(source_path.read_text())
sources.update({'ablation_effects.png':'mechanisms/ablation_pairs.csv; metric=pnl',
                'flow_control.png':'mechanisms/flow_control_summary.csv and flow_control_pairs.csv; metric=pnl'})
source_path.write_text(json.dumps(sources,indent=2)+'\n')
print('Generated 2 follow-up research figures')
