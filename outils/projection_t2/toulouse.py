import csv,numpy as np
from scipy.optimize import minimize
def rd(f):
    o={}
    for r in list(csv.reader(open(f,encoding='utf-8-sig'),delimiter=';'))[1:]:
        v=r[16:]; d={v[k]:int(v[k+1] or 0) for k in range(0,len(v)-1,2)}
        o[r[6]]=(int(r[8]),int(r[14]),d)
    return o
A=rd('dl/tls_t1.csv'); B2=rd('dl/tls_t2.csv')
BL={'004':'Piquemal (LFI)','003':'Briançon (PS-écolo)','001':'XG','002':'XG','009':'XG','010':'XG','005':'Moudenc+centre','007':'Moudenc+centre','008':'RN+REC','011':'RN+REC'}
Bn=['Piquemal (LFI)','Briançon (PS-écolo)','XG','Moudenc+centre','RN+REC','NE']
X=[];Y=[];W=[]
for k,(ins,exp,d) in A.items():
    if k not in B2: continue
    x=dict.fromkeys(Bn,0)
    for c,v in d.items(): x[BL[c]]+=v
    x['NE']=ins-exp; ins2,exp2,d2=B2[k]
    X.append([x[b]/ins for b in Bn]); Y.append([d2.get('012',0)/ins2,d2.get('005',0)/ins2,(ins2-exp2)/ins2]); W.append(ins)
X=np.array(X);Y=np.array(Y);w=np.array(W,float);w/=w.sum();k=len(Bn)
def fit(X,Y,w):
    f=lambda p:(w[:,None]*(X@p.reshape(k,3)-Y)**2).sum()
    cons=[{'type':'eq','fun':(lambda p,i=i:p.reshape(k,3)[i].sum()-1)} for i in range(k)]
    return minimize(f,np.full(k*3,1/3),bounds=[(0,1)]*(k*3),constraints=cons,method='SLSQP',options={'maxiter':800,'ftol':1e-13}).x.reshape(k,3)
M=fit(X,Y,w); rng=np.random.default_rng(3); bs=[]
for _ in range(200):
    i=rng.integers(0,len(X),len(X)); ww=w[i]/w[i].sum(); bs.append(fit(X[i],Y[i],ww))
bs=np.array(bs); lo=np.percentile(bs,5,0); hi=np.percentile(bs,95,0)
print('Toulouse 2026, %d bureaux : électorat du 1er tour -> liste unie Piquemal / Moudenc / abstention-blanc-nul (intervalle 90 %%)'%len(X))
for i,b in enumerate(Bn): print(f'  {b:20s} ({(w@X[:,i])*100:4.1f}% des inscrits) : '+' | '.join(f'{M[i,j]*100:5.1f} [{lo[i,j]*100:3.0f}-{hi[i,j]*100:3.0f}]' for j in range(3)))
print('  observé',(w@Y*100).round(1),'prédit',(w@(X@M)*100).round(1))
