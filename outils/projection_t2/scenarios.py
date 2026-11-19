exec(open('proj.py').read().split("res=[]")[0])
HYP=ifop+yg+el
M24=np.array(json.load(open('reports_bv.json'))['LFI'][0]); M22=np.array(json.load(open('reports22.json'))['LFI'][0])
Mmoy=(M24+M22)/2
names=['G (électeurs Mélenchon)','AG (Glucksmann, Tondelier, Roussel…)','C (Philippe, Attal, Villepin…)','D (Retailleau, Lisnard)','ED (Le Pen, Zemmour, Dupont-Aignan)','NE (abstention au 1er tour)']
def run(M):
    v=[proj(h,M) for h in HYP]; return np.mean([x[0] for x in v]),min(x[0] for x in v),max(x[0] for x in v)
for nom,M in (('Pessimiste : reports des législatives 2022',M22),('Moyenne 2022-2024',Mmoy),('Optimiste : reports des législatives 2024',M24)):
    a=run(M); print(f'{nom:45s} Mélenchon {a[0]:4.1f} %  ({a[1]:.1f} à {a[2]:.1f} selon l\'hypothèse)')
print('\nReports utilisés (Mélenchon / Le Pen / abstention), 2022 → 2024 :')
for i,nm in enumerate(names): print(f'  {nm:42s} {M22[i,0]*100:3.0f}/{M22[i,1]*100:3.0f}/{M22[i,2]*100:3.0f}  →  {M24[i,0]*100:3.0f}/{M24[i,1]*100:3.0f}/{M24[i,2]*100:3.0f}')
Mg=np.array(json.load(open('reports_bv.json'))['autre'][0]); Mg[0]=[1,0,0]
a=run(Mg); print(f'\nTrès optimiste : Mélenchon reçoit les reports d\'un candidat PS/écolo/PCF de 2024  Mélenchon {a[0]:4.1f} % ({a[1]:.1f} à {a[2]:.1f})')
for i,nm in enumerate(names): print(f'  {nm:42s} {Mg[i,0]*100:3.0f}/{Mg[i,1]*100:3.0f}/{Mg[i,2]*100:3.0f}')
