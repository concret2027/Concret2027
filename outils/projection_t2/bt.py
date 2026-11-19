import json,collections,re,unicodedata,numpy as np
from scipy.optimize import minimize
B=['OWN','FI','AG','C','D','ED','XD','NE']; k=len(B)
def fit(S):
    X=np.array([[o['x'].get(b,0)/o['ins1'] for b in B] for o in S]); Y=np.array([np.array(o['y'])/o['ins2'] for o in S]); w=np.array([o['ins1'] for o in S],float); w/=w.sum()
    f=lambda p:(w[:,None]*(X@p.reshape(k,3)-Y)**2).sum()
    cons=[{'type':'eq','fun':(lambda p,i=i:p.reshape(k,3)[i].sum()-1)} for i in range(k)]
    M=minimize(f,np.full(k*3,1/3),bounds=[(0,1)]*(k*3),constraints=cons,method='SLSQP',options={'maxiter':1000,'ftol':1e-13}).x.reshape(k,3)
    return M,w@X
def n(s): return re.sub(r'[^A-Z]','',''.join(c for c in unicodedata.normalize('NFD',s.upper()) if unicodedata.category(c)!='Mn'))
# ---------- législatives 2017 (même format que 2022)
B17={'FI':'FI','COM':'FI','SOC':'AG','ECO':'AG','RDG':'AG','DVG':'AG','EXG':'AG','DIV':'AG','REG':'AG','REM':'C','MDM':'C','UDI':'C','LR':'D','DVD':'D','FN':'ED','DLF':'XD','EXD':'XD'}
def rows17(f):
    for l in open('bt/'+f,encoding='latin1').read().splitlines()[1:]:
        r=l.split(';'); c=[]
        for i in range(21,len(r)-7,8):
            if r[i+4]: c.append((r[i+4],r[i+2],r[i+3],int(r[i+5] or 0)))
        yield (r[0],r[2],r[4],r[6]),int(r[7]),int(r[18]),c
T1={k:(ins,exp,c) for k,ins,exp,c in rows17('l17t1.txt')}
D17=collections.defaultdict(list)
for kk,ins2,exp2,c in rows17('l17t2.txt'):
    if len(c)!=2 or kk not in T1: continue
    e=[x for x in c if x[0]=='FN']; o=[x for x in c if x[0]!='FN']
    if len(e)!=1 or len(o)!=1: continue
    typ=B17.get(o[0][0]);  
    ins,exp,c1=T1[kk]; x=collections.Counter()
    for nu,nom,pre,v in c1: x['OWN' if (n(nom)==n(o[0][1]) and n(pre)==n(o[0][2])) else B17.get(nu,'AG')]+=v
    if not x['OWN'] or not ins or not ins2: continue
    x['NE']=ins-exp; D17[typ].append(dict(ins1=ins,x=dict(x),ins2=ins2,y=[o[0][3],e[0][3],ins2-exp2],circ=kk[0]+kk[1]))
print('2017 duels contre le FN :',{t:(len(v),len({o['circ'] for o in v})) for t,v in D17.items()})
# ---------- législatives 2012
B12={'FG':'FI','SOC':'AG','VEC':'AG','ECO':'AG','RDG':'AG','DVG':'AG','EXG':'AG','AUT':'AG','REG':'AG','CEN':'C','NCE':'C','ALLI':'C','PRV':'C','UMP':'D','DVD':'D','FN':'ED','EXD':'XD'}
R=collections.defaultdict(lambda:{1:[],2:[]})
for l in open('bt/l12.txt',encoding='latin1').read().splitlines():
    if l.startswith('--') or not l.strip(): continue
    r=l.split(';')
    if len(r)<15: continue
    kk=(r[1],r[2],r[4],r[6]); t=int(r[0]); R[kk][t].append((r[13],r[11],r[12],int(r[14]),int(r[7]),int(r[9])))
D12=collections.defaultdict(list)
for kk,d in R.items():
    c2=d[2]; c1=d[1]
    if len(c2)!=2 or not c1: continue
    e=[x for x in c2 if x[0]=='FN']; o=[x for x in c2 if x[0]!='FN']
    if len(e)!=1 or len(o)!=1: continue
    typ=B12.get(o[0][0]); ins,exp=c1[0][4],c1[0][5]; ins2,exp2=c2[0][4],c2[0][5]
    x=collections.Counter()
    for nu,nom,pre,v,_,_ in c1: x['OWN' if (n(nom)==n(o[0][1]) and n(pre)==n(o[0][2])) else B12.get(nu,'AG')]+=v
    if not x['OWN'] or not ins or not ins2: continue
    x['NE']=ins-exp; D12[typ].append(dict(ins1=ins,x=dict(x),ins2=ins2,y=[o[0][3],e[0][3],ins2-exp2],circ=kk[0]+kk[2]))
print('2012 duels contre le FN :',{t:(len(v),len({o['circ'] for o in v})) for t,v in D12.items()})
out={}
for lab,S in [('2017-C',D17['C']),('2017-D',D17['D']),('2017-AG',D17['AG']+D17['FI']),('2012-D',D12['D']),('2012-AG',D12['AG']+D12['FI'])]:
    if len(S)<30: print(lab,'trop peu'); continue
    M,px=fit(S); out[lab]=dict(M=M.tolist(),poids=px.tolist(),n_bv=len(S),n_circ=len({o['circ'] for o in S}))
    print('==',lab,out[lab]['n_circ'],'circ.',len(S),'bureaux'); [print(f'  {b:4s} ({px[i]*100:4.1f}%) '+' | '.join(f'{M[i,j]*100:5.1f}' for j in range(3))) for i,b in enumerate(B)]
json.dump(out,open('bt_reg.json','w'))
