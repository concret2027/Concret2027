import json,numpy as np
R=json.load(open('reports.json'))
B=['G','AG','C','D','ED','NE']
Mlfi=np.array(R['LFI'][0]); lo=np.array(R['LFI'][1]); hi=np.array(R['LFI'][2]); Maut=np.array(R['autre'][0])
BL={'Mélenchon':'G','Glucksmann':'AG','Tondelier':'AG','Roussel':'AG','Arthaud':'AG','Ruffin':'AG','Hollande':'AG','Polony':'AG',
    'Philippe':'C','Attal':'C','Villepin':'C','Riner':'C','Lagarde':'C','Retailleau':'D','Lisnard':'D',
    'Le Pen':'ED','Zemmour':'ED','Dupont-Aignan':'ED'}
ifop=json.load(open('../ifop18b/hypfr.json')); ifop[5]['Dupont-Aignan']=2.0
yg=[dict(Retailleau=6,Philippe=8,Zemmour=3,Roussel=2,Attal=5,Mélenchon=19,**{'Le Pen':32},Tondelier=4,Arthaud=1,**{'Dupont-Aignan':2},Glucksmann=9,Lisnard=9),
   dict(Retailleau=8,Zemmour=3,Roussel=2,Attal=7,Mélenchon=19,**{'Le Pen':34},Tondelier=6,Arthaud=1,**{'Dupont-Aignan':1},Glucksmann=10,Lisnard=10),
   dict(Retailleau=7,Zemmour=3,Roussel=3,Philippe=9,Mélenchon=19,**{'Le Pen':33},Tondelier=4,Arthaud=1,**{'Dupont-Aignan':2},Glucksmann=10,Lisnard=10),
   dict(Zemmour=4,Roussel=3,Philippe=16,Mélenchon=22,**{'Le Pen':40},Arthaud=1,**{'Dupont-Aignan':2},Glucksmann=12),
   dict(Retailleau=6,Philippe=7,Zemmour=3,Roussel=2,Attal=4,Mélenchon=17,**{'Le Pen':32},Tondelier=5,Arthaud=1,**{'Dupont-Aignan':2},Glucksmann=9,Lisnard=9,Villepin=2,Riner=3)]
el=[dict(Arthaud=.5,Mélenchon=17,Roussel=2,Tondelier=3,Glucksmann=13.5,Philippe=15,Retailleau=6,**{'Dupont-Aignan':3,'Le Pen':33},Zemmour=4.5,Villepin=2.5),
    dict(Arthaud=1,Mélenchon=17.5,Roussel=2.5,Tondelier=3,Glucksmann=14,Attal=10,Retailleau=9,**{'Dupont-Aignan':2.5,'Le Pen':33},Zemmour=4.5,Villepin=3),
    dict(Arthaud=.5,Mélenchon=17.5,Roussel=2,Tondelier=3.5,Glucksmann=13,Attal=5.5,Philippe=12,Retailleau=6,**{'Dupont-Aignan':3,'Le Pen':33},Zemmour=4),
    dict(Arthaud=.5,Mélenchon=17.5,Roussel=1.5,Glucksmann=14,Attal=8.5,Lisnard=10.5,Retailleau=6,**{'Dupont-Aignan':2.5,'Le Pen':32},Zemmour=4,Ruffin=3),
    dict(Arthaud=.5,Mélenchon=18.5,Roussel=2.5,Glucksmann=13.5,Philippe=13,Lisnard=9,Retailleau=4,**{'Dupont-Aignan':3,'Le Pen':32.5},Zemmour=3.5),
    dict(Arthaud=.5,Mélenchon=17,Roussel=1.5,Tondelier=3,Glucksmann=10.5,Attal=4,Philippe=9.5,Lisnard=8,Retailleau=4,**{'Dupont-Aignan':2,'Le Pen':31},Zemmour=3,Polony=1.5,Riner=4.5)]
EXP=float(__import__('sys').argv[1])  # exprimés / inscrits au 1er tour
def proj(h,M):
    t=sum(h.values()); x=dict.fromkeys(B,0.0)
    for c,v in h.items(): x[BL[c]]+=v/t*EXP
    x['NE']=1-EXP; X=np.array([x[b] for b in B]); Y=X@M
    return 100*Y[0]/(Y[0]+Y[1]), 100*(Y[0]+Y[1])
res=[]
for nom,L in (('Ifop 13-16 nov.',ifop),('YouGov 12-17 nov.',yg),('Elabe 12-13 nov.',el)):
    for i,h in enumerate(L):
        a=proj(h,Mlfi); b=proj(h,Maut); l=proj(h,lo/lo.sum(1,keepdims=True)) 
        res.append((nom,i+1,a,b))
        print(f'{nom:18s} hyp.{i+1}: Mélenchon {a[0]:4.1f} % (participation exprimée {a[1]:4.1f} % des inscrits) | si reports d\'un PS/écolo : {b[0]:4.1f} %')
A=np.array([r[2][0] for r in res]); Bb=np.array([r[3][0] for r in res])
print('Ensemble des 17 hypothèses : Mélenchon %.1f %% en moyenne (de %.1f à %.1f) ; avec les reports d\'un candidat PS/écologiste : %.1f %%'%(A.mean(),A.min(),A.max(),Bb.mean()))
# incertitude des reports : bootstrap
import random
print('\nSensibilité (moyenne des 17 hypothèses) : part des électeurs du centre ET de la droite qui, parmi ceux qui choisissent, votent Mélenchon')
for s in (0.25,0.31,0.40,0.50,0.60,0.725):
  vals=[]
  for nom,L in (('i',ifop),('y',yg),('e',el)):
    for h in L:
      M=Mlfi.copy()
      for i in (2,3):
        ex=M[i,0]+M[i,1]; M[i,0]=ex*s; M[i,1]=ex*(1-s)
      vals.append(proj(h,M)[0])
  print(f'  {s*100:4.0f} % -> Mélenchon {np.mean(vals):4.1f} %')
