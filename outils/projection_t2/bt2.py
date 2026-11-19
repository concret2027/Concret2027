import json,numpy as np
R=json.load(open('bt_reg.json')); G=json.load(open('genreg.json')); B=['OWN','FI','AG','C','D','ED','XD','NE']
def M(key,src=R): return {b:np.array(src[key]['M'][i]) for i,b in enumerate(B)}
def proj(x,Mx):
    m=sum(x[b]*Mx[b][0] for b in x); l=sum(x[b]*Mx[b][1] for b in x); return 100*m/(m+l)
# 1er tour 2022 (ministère, circonscriptions)
v={};ins=exp=0
for l in open('dl/p22t1.txt',encoding='latin1').read().splitlines()[1:]:
    r=l.split(';'); ins+=int(r[5]); exp+=int(r[16])
    for i in range(19,len(r)-6,7): v[r[i+2]]=v.get(r[i+2],0)+int(r[i+4])
BL22={'MÉLENCHON':'FI','ARTHAUD':'AG','ROUSSEL':'AG','HIDALGO':'AG','JADOT':'AG','POUTOU':'AG','MACRON':'OWN','PÉCRESSE':'D','LASSALLE':'D','LE PEN':'ED','ZEMMOUR':'XD','DUPONT-AIGNAN':'XD'}
x22={b:0.0 for b in B}
for c,n in v.items(): x22[BL22[c]]+=n/ins
x22['NE']=1-exp/ins
# 1er tour 2017 (ministère)
p=json.load(open('bt/p17t1.json')); ins17=47565637; exp17=p['Exprimés']
BL17={'MACRON':'OWN','LE PEN':'ED','FILLON':'D','MÉLENCHON':'FI','HAMON':'AG','DUPONT-AIGNAN':'XD','LASSALLE':'D','POUTOU':'AG','ASSELINEAU':'XD','ARTHAUD':'AG','CHEMINADE':'AG'}
x17={b:0.0 for b in B}
for kk,n in p.items():
    for c,b in BL17.items():
        if c in kk: x17[b]+=n/ins17
x17['NE']=1-exp17/ins17
print('contrôle 2017 :',round(sum(x17[b] for b in B if b!='NE')*ins17),'exprimés',exp17)
# 2022 : reports des législatives 2017, duels centre contre FN (connus avant la présidentielle 2022)
a=proj(x22,M('2017-C'))
# 2017 : reports des législatives 2012 (connus avant 2017) ; pas de duel centre-FN en 2012 : électeurs de gauche comme face à un candidat de droite, électeurs de droite comme face à un candidat de gauche
m12={b:np.array(R['2012-D']['M'][B.index(b)]) for b in B}; m12['D']=np.array(R['2012-AG']['M'][B.index('D')]); m12['OWN']=np.array([1,0,0])
b17=proj(x17,m12)
# en complément, les reports postérieurs (pas un vrai test)
c22=proj(x22,M('2022-C',G)); c17=proj(x17,M('2017-C'))
print(f'2022 Macron–Le Pen : réel 58,55 ; avec les reports des législatives 2017 : {a:.1f} ; (avec ceux des législatives 2022, après coup : {c22:.1f})')
print(f'2017 Macron–Le Pen : réel 66,10 ; avec les reports des législatives 2012 : {b17:.1f} ; (avec ceux des législatives 2017, après coup : {c17:.1f})')
print(f'2022 avec les reports des législatives 2024 (participation proche d\'une présidentielle) : {proj(x22,M("2024-C",G)):.1f} ; 2017 : {proj(x17,M("2024-C",G)):.1f}')
print(f'2022 avec les reports de la présidentielle 2022 elle-même (contrôle) : {proj(x22,M("P2022-Macron",G)):.1f}')
