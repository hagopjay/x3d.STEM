"""Plot executed coordinate-storage errors; no new scientific simulation."""
from pathlib import Path
import hashlib
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
source=ROOT/'private/probes/precision-control.json'
r=json.loads(source.read_text())
if r['status']!='pass':raise ValueError('Precision probe did not pass')
rows=r['cases']; labels=['ECEF-like coordinates','UTM-like coordinates']
direct=[v['direct_world_max_abs_error_m'] for v in rows]
local=[v['restored_world_max_abs_error_m'] for v in rows]
out=ROOT/'docs/assets';out.mkdir(exist_ok=True)
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'svg.fonttype':'none'})
fig,ax=plt.subplots(figsize=(9.4,4.4),facecolor='#0b1723');ax.set_facecolor('#0b1723')
y=np.arange(2)
ax.barh(y-.17,direct,height=.28,color='#eeae82',label='Direct global float32 storage')
ax.barh(y+.17,local,height=.28,color='#5ed3c0',label='Local origin, restored in binary64')
ax.set_xscale('log');ax.set_xlim(3e-7,2);ax.set_yticks(y,labels,color='#e0eaf2');ax.invert_yaxis()
ax.set_xlabel('Maximum absolute coordinate error · metres · logarithmic scale',color='#c3d1de',labelpad=12)
ax.tick_params(axis='x',colors='#c3d1de');ax.tick_params(axis='y',length=0)
for spine in ax.spines.values():spine.set_visible(False)
ax.grid(axis='x',color='#547084',alpha=.3);ax.set_axisbelow(True)
for i,(a,b) in enumerate(zip(direct,local)):
    ax.text(a*1.1,i-.17,f'{a:.3g} m',va='center',color='#eeae82',fontsize=10)
    ax.text(b*1.25,i+.17,f'{b*1e6:.3g} µm',va='center',color='#5ed3c0',fontsize=10)
legend=ax.legend(loc='lower right',frameon=False,labelcolor='#dce8ef',fontsize=9)
fig.suptitle('Keep the origin. Preserve the detail.',x=.05,y=.98,ha='left',color='#f1f6fa',fontsize=19,fontweight='bold')
fig.text(.05,.88,'Actual Blender 5.2.4 mesh vertices after save/reopen · two synthetic controls',color='#aabfce',fontsize=10)
fig.text(.05,.025,'Origin restoration occurs outside Blender world transforms. This is a bounded storage result.',color='#9eb4c3',fontsize=9)
fig.subplots_adjust(left=.25,right=.91,top=.78,bottom=.22)
description='Source SHA256 '+hashlib.sha256(source.read_bytes()).hexdigest()
fig.savefig(out/'Precision-Control.png',dpi=170,facecolor=fig.get_facecolor(),metadata={'Description':description})
fig.savefig(out/'Precision-Control.svg',facecolor=fig.get_facecolor(),metadata={'Description':description})
receipt={'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
         'tool_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
         'png_sha256':hashlib.sha256((out/'Precision-Control.png').read_bytes()).hexdigest(),
         'scope':'Plot of recorded measured values, not a new Blender run.'}
(out/'precision-plot.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt))
