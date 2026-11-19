import json,numpy as np,collections
from scipy.optimize import minimize
G=json.load(open('gen.json')); B=['OWN','FI','AG','C','D','ED','NE']; k=len(B)
def mats(S):
    X=np.array([[o['x'].get(b,0)/o['ins1'] for b in B] for o in S]); Y=np.array([np.array(o['y'])/o['ins2'] for o in S]); w=np.array([o['ins1'] for o in S],float); return X,Y,w/w.sum()
def fit(X,Y,w):
    f=lambda p:(w[:,None]*(X@p.reshape(k,3)-Y)**2).sum()
    cons=[{'type':'eq','fun':(lambda p,i=i:p.reshape(k,3)[i].sum()-1)} for i in range(k)]
    return minimize(f,np.full(k*3,1/3),bounds=[(0,1)]*(k*3),constraints=cons,method='SLSQP',options={'maxiter':1000,'ftol':1e-13}).x.reshape(k,3)
import sys
ONLY=sys.argv[1:] 
R=json.load(open('genreg.json')) if ONLY else {}
for key,S in sorted(G.items()):
    if ONLY and key not in ONLY: continue
    X,Y,w=mats(S); M=fit(X,Y,w); by=collections.defaultdict(list)
    for i,o in enumerate(S): by[o['circ']].append(i)
    cs=list(by); rng=np.random.default_rng(2); bs=[]
    for _ in range(30 if len(S)>30000 else 60):
        idx=[i for c in rng.choice(cs,len(cs)) for i in by[c]]; bs.append(fit(X[idx],Y[idx],w[idx]/w[idx].sum()))
    bs=np.array(bs); lo=np.percentile(bs,5,0); hi=np.percentile(bs,95,0); poids=w@X
    print(f'== {key} : {len(cs)} circonscriptions, {len(S)} bureaux ; observé {np.round(w@Y*100,1)} prédit {np.round(w@(X@M)*100,1)}')
    for i,b in enumerate(B): print(f'  {b:4s} ({poids[i]*100:4.1f}%) '+' | '.join(f'{M[i,j]*100:5.1f} [{lo[i,j]*100:3.0f}-{hi[i,j]*100:3.0f}]' for j in range(3)))
    R[key]=dict(M=M.tolist(),lo=lo.tolist(),hi=hi.tolist(),poids=poids.tolist(),n_circ=len(cs),n_bv=len(S))
json.dump(R,open('genreg.json','w'))
