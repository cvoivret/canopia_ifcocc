import pandas as pd
import numpy as np
from collections import defaultdict
import itertools
from array import array
import matplotlib.pyplot as plt
import seaborn as sns

window_tagname={
'Ref':257076,
'A1':257738,
'A2':256772,
'A3':257901,
'B':256912,
'C60':257017,
'C45':266662
}
res=pd.read_csv('Results_article3.csv')


N=np.unique(res.Nray)
v_angles=np.unique(res.v_angle)
N=np.unique(res.Nray)

markerwin=list(window_tagname.keys())
markerlist=['o','v','^','<','s','D','d']# for window ID
markerdict=dict(zip(markerwin,markerlist))

prop_cycle = plt.rcParams['axes.prop_cycle']
colors = prop_cycle.by_key()['color']
colorlistN=colors[:len(N)-1]+['k']# for each ray number (including 0)

colordictN=dict(zip(N,colorlistN))#colorlist[:-1]+['k']))

colordictAngle=dict(zip(v_angles,colors[:len(v_angles)]))

linestyle=['-','--','-.',':']


resext=res[res.Nray==0]

resext2=resext[ resext.name !='B']
col_order=["Ref",'C45','C60','A1','A2','A3']
grid=sns.FacetGrid(resext2,col='name',hue='v_angle',col_wrap=3,col_order=col_order)#, height=1.5)
grid.set_titles(col_template="{col_name}", row_template="{row_name}")
grid.map(plt.plot,"h_angle", "shad_ratio", marker="None",linestyle="-")
grid.set_xlabels(r"$\alpha$")
grid.set_ylabels(r"$C_m$")
grid.add_legend()
grid.legend.set_title(r"$\theta$")
plt.savefig("figure1.eps")
plt.close()


# data creation : Error and duration
grouped=res.groupby(['Nray','name'])

ltemp=[]
Ntoplot=N[1:]
for i,n in enumerate(Ntoplot):
    color=colordictN[n]
    #print(n)
    for name in window_tagname.keys():
        #print(name)
        extvalues=grouped.get_group((0,name))['shad_ratio'].values
        rayvalues=grouped.get_group((n,name))['shad_ratio'].values
        
        extduration=grouped.get_group((0,name))['duration'].values
        rayduration=grouped.get_group((n,name))['duration'].values
        
        toplot=(rayvalues/extvalues)
        mask= toplot!=1.
        
        temp=pd.DataFrame(grouped.get_group((n,name)))
        temp['Rel_error']=toplot
        temp['Ext_value']=extvalues
        temp['duration_norm']=rayduration/extduration
        
        ltemp.append(temp[mask])
        


res3=pd.concat(ltemp)

fig, (ax1, ax2) = plt.subplots(1, 2,  sharey=True,width_ratios=[3,1])

fake_data1=[]
fake_data2=[]


for name,m in zip(markerdict.keys(),markerdict.values()):
    fake_data1+=plt.plot([],[],marker=m,label=name,color='k',linestyle='None',figure=fig)
    
#for n,color in zip(colordictN.keys(),colordictN.values()):
for n in Ntoplot:
    fake_data2+=plt.plot([],[],
                            marker='s',
                            markersize=10,
                            label=str(n),
                            color=colordictN[n],
                            figure=fig,
                            linestyle='None')
  

scat=sns.scatterplot(data=res3,x="Ext_value",y="Rel_error",
                               hue="Nray",style="name",
                               palette=colordictN,
                               markers=markerdict,
                               ax=fig.axes[0],
                               legend=False)
scat.set_ylabel(r"$E$")
scat.set_xlabel(r"$C_m$")                               
kde=sns.kdeplot(data=res3,y='Rel_error',hue='Nray',
                            palette=colorlistN[1:],
                            ax=fig.axes[1],
                            legend=False)
                            
l1=plt.legend(fake_data1,markerdict.keys(),
                        loc='upper left',
                        bbox_to_anchor=(1.,1.),
                        frameon=False,
                        title='Window')
l2=plt.legend(fake_data2,Ntoplot,
                loc='lower left',
                bbox_to_anchor=(1.,0.),
                frameon=False,
                title='N')
                
plt.gca().add_artist(l1)
fig.tight_layout()
plt.savefig("figure2.eps")
plt.clf()
#plt.show()



lab_dur=r"$<t_N>$"
lab_err=r"$\sigma_E$"

res3['abs_error']=res3.Rel_error
grouped=res3.groupby('Nray')
deviation=grouped['abs_error'].std()
durationmean=grouped['duration_norm'].mean()
#line=sns.lineplot(x=durationmean.index,y=durationmean.values,label='duration',err_style="band",errorbar='sd')
line =sns.lineplot(data=res3,x='Nray',y='duration_norm',err_style="bars",errorbar='sd',label=lab_dur)
line.set_ylabel(lab_dur)
line.set_xlabel('N')
plt.hlines(1,0,50,'gray',linestyle='solid')
ax2=line.twinx()
color='red'
ax2.set_ylabel(lab_err)  # we already handled the x-label with ax1
line2=ax2.plot(deviation.index, deviation.values, color=color,label=lab_err,ls='--')

l, labels = line.get_legend_handles_labels()
l2, labels2 = ax2.get_legend_handles_labels()
ax2.legend(l + l2, labels + labels2, loc=0)
plt.savefig("figure3.eps")


