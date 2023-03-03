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
res=pd.read_csv('Results.csv')

N=np.unique(res.Nray)
v_angles=np.unique(res.v_angle)
N=np.unique(res.Nray)

markerwin=list(window_tagname.keys())
markerlist=['o','v','^','<','s','+','x']# for window ID
markerdict=dict(zip(markerwin,markerlist))

prop_cycle = plt.rcParams['axes.prop_cycle']
colors = prop_cycle.by_key()['color']
colorlist=colors[:len(N)]# for each ray number (including 0)

colordictN=dict(zip(N,colorlist[:-1]+['k']))

colordictAngle=dict(zip(v_angles,colors[:len(v_angles)]))

linestyle=['-','--','-.',':']


#change to groupby
resext=res[res.Nray==0]
grouped=resext.groupby(['v_angle','name'])

for i,(key,group) in enumerate(grouped):
    
    plt.plot(group.h_angle,group.shad_ratio,
                    marker=markerdict[key[1]],
                    color=colordictAngle[key[0]],
                    
                    #linestyle=linestyle[i]
                    )
fake_data1=[]
fake_data2=[]
wlabels=[ str(n) for n in window_tagname.keys()]
alabels=[ str() for n in N]

for name,m in zip(markerdict.keys(),markerdict.values()):
    fake_data1+=plt.plot([],[],marker=m,label=name,color='k',linestyle='None')
    
for angle,color in zip(colordictAngle.keys(),colordictAngle.values()):
    fake_data2+=plt.plot([],[],marker='s',markersize=10,label=str(angle),color=color,linestyle='None')

plt.xlabel('H_angle')
plt.ylabel('SR_Extrusion')
l1=plt.legend(fake_data1,markerdict.keys(),loc='lower right', frameon=False)
l2=plt.legend(fake_data2,colordictAngle.keys(),loc='lower left', frameon=False)    
plt.gca().add_artist(l1)
plt.show()


grouped=res.groupby('Nray')
for n,group in grouped:
    if name==0:
        continue
    extvalues=grouped.get_group(0)['shad_ratio'].values
    rayvalues=grouped.get_group(n)['shad_ratio'].values
    mask = rayvalues/extvalues!=1.0
    toplot= rayvalues/extvalues
    #plt.hist(group[mask].shad_ratio)
    plt.hist(toplot[mask],
                                                label=name,
                                                density=True,
                                                histtype='step',
                                                bins=30,
                                                range=(0.5,2))

plt.legend()
plt.show()

    
#ext_ratio = np.array([ sof._ratio_vector for sof in lsof])
#ray_ratio = np.array([ [sofr._ratio_vector for n,sofr in list ] for list in llsofr])

markerlist=['o','v','^','<','s','+','x']
prop_cycle = plt.rcParams['axes.prop_cycle']
colors = prop_cycle.by_key()['color']
colorlist=colors[:len(N)]
# average error

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
        
        toplot=(rayvalues/extvalues)
        
        temp=pd.DataFrame(grouped.get_group((n,name)))
        temp['Rel_error']=toplot
        ltemp.append(temp)
        
        mask= toplot!=1.
        plt.plot(extvalues[mask],toplot[mask],
                    marker=markerdict[name],
                    color=color,
                    linestyle="None",
                    )
fake_data1=[]
fake_data2=[]


for name,m in zip(markerdict.keys(),markerdict.values()):
    fake_data1+=plt.plot([],[],marker=m,label=name,color='k',linestyle='None')
    
#for n,color in zip(colordictN.keys(),colordictN.values()):
for n in Ntoplot:
    fake_data2+=plt.plot([],[],
                            marker='s',
                            markersize=10,
                            label=str(n),
                            color=colordictN[n],
                            linestyle='None')

plt.xlabel('SR_extrusion')
plt.ylabel('SR_ray / SR_Extrusion')
l1=plt.legend(fake_data1,markerdict.keys(),loc='upper right', frameon=False)
l2=plt.legend(fake_data2,Ntoplot,loc='upper center', frameon=False)
plt.gca().add_artist(l1)

plt.show()

res2=pd.concat(ltemp)
#sns.relplot(data=res2,x='shad_ratio',y='Rel_error',hue='Nray',style='name')
#plt.show()

