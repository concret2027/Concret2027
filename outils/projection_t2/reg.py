import json,numpy as np,sys,collections
from scipy.optimize import minimize
O=json.load(open('duels.json'))
B=['G','AG','C','D','ED','NE']   # gauche du duel, autre gauche (+EXG,+DIV), centre, droite, RN+REC, non-exprimés
def X(o):
    t=o['t1'];ins=o['ins1']
    v={'G':t.get('G',0),'AG':t.get('AG',0)+t.get('EXG',0)+t.get('DIV',0),'C':t.get('C',0),'D':t.get('D',0),'ED':t.get('RN',0)+t.get('REC',0),'NE':t.get('NE',0)}
    return np.array([v[b]/ins for b in B])
def Y(o): return np.array([o['G2'],o['RN2'],o['NE2']])/o['ins2']
def fit(S):
    Xm=np.array([X(o) for o in S]); Ym=np.array([Y(o) for o in S]); w=np.array([o['ins1'] for o in S],float); w/=w.sum()
    k=len(B)
    def f(p):
        M=p.reshape(k,3); R=Xm@M-Ym; return (w[:,None]*R*R).sum()
    cons=[{'type':'eq','fun':(lambda p,i=i:p.reshape(k,3)[i].sum()-1)} for i in range(k)]
    p0=np.full(k*3,1/3)
    r=minimize(f,p0,bounds=[(0,1)]*(k*3),constraints=cons,method='SLSQP',options={'maxiter':500,'ftol':1e-12})
    return r.x.reshape(k,3)
def report(nom,S,boot=200):
    M=fit(S); circs=sorted({o['circ'] for o in S}); rng=np.random.default_rng(1); bs=[]
    by=collections.defaultdict(list)
    for o in S: by[o['circ']].append(o)
    for _ in range(boot):
        smp=[o for c in rng.choice(circs,len(circs)) for o in by[c]]
        bs.append(fit(smp))
    bs=np.array(bs); lo=np.percentile(bs,5,axis=0); hi=np.percentile(bs,95,axis=0)
    # poids des blocs
    ins=sum(o['ins1'] for o in S); poids={b:sum(X(o)[i]*o['ins1'] for o in S)/ins for i,b in enumerate(B)}
    print(f'== {nom} : {len(circs)} circonscriptions, {len(S)} communes')
    print('bloc (part des inscrits au 1er tour) -> % vers la gauche du duel / RN / abstention-blanc-nul (intervalle 90 %)')
    for i,b in enumerate(B):
        print(f'  {b:3s} ({poids[b]*100:4.1f}%) : ' + ' | '.join(f'{M[i,j]*100:5.1f} [{lo[i,j]*100:4.0f}-{hi[i,j]*100:4.0f}]' for j in range(3)))
    # ajustement
    Xm=np.array([X(o) for o in S]); Ym=np.array([Y(o) for o in S]); P=Xm@M
    w=np.array([o['ins1'] for o in S],float)
    print('  total observé G/RN/NE :',(w@Ym/w.sum()*100).round(1),' prédit :',(w@P/w.sum()*100).round(1))
    return M,lo,hi
res={}
res['LFI']=report('Duels LFI contre RN',[o for o in O if o['parti']=='LFI'])
res['autre']=report('Duels autre gauche (PS, écologistes, PCF…) contre RN',[o for o in O if o['parti'] not in ('LFI','?')])
json.dump({k:[v[0].tolist(),v[1].tolist(),v[2].tolist()] for k,v in res.items()},open('reports.json','w'))
