import csv,collections,numpy as np,json
from scipy.optimize import minimize
GAUCHE={'LUG','LSOC','LDVG','LECO','LCOM','LVEC','LFI','LEXG'}
EXD={'LRN','LUXD','LEXD','LUDR','LREC'}
BL={'LFI':'FI','LEXG':'AG','LUG':'AG','LSOC':'AG','LDVG':'AG','LECO':'AG','LCOM':'AG','LVEC':'AG',
    'LDVC':'C','LENS':'C','LUC':'C','LUDI':'C','LHOR':'C','LMDM':'C','LREN':'C','LDVD':'D','LLR':'D','LUD':'D',
    'LRN':'ED','LUXD':'ED','LEXD':'ED','LUDR':'ED','LREC':'ED'}
def rows(f):
    R=csv.reader(open(f,encoding='utf-8'),delimiter=';'); next(R)
    for r in R:
        L=[]
        for i in range(19,len(r)-12,13):
            if r[i+4] or r[i+7]: L.append((r[i+4],r[i+1],int(r[i+7] or 0)))
        yield (r[2].lstrip('0'),r[4].lstrip('0')),int(r[5] or 0),int(r[10] or 0),L
T1={}
for k,ins,exp,L in rows('mun/t1_bv.csv'): T1[k]=(ins,exp,L)
B=['G','FI','AG','C','D','ED','DIV','NE']
data=[];cnt=collections.Counter()
DUELS=collections.Counter()
for k,ins2,exp2,L in rows('mun/t2_bv.csv'):
    if len(L)!=2: continue
    nus=[x[0] for x in L]
    g=[x for x in L if x[0] in GAUCHE]; e=[x for x in L if x[0] in EXD]
    if len(g)!=1 or len(e)!=1 or k not in T1: continue
    ins,exp,L1=T1[k]; x=dict.fromkeys(B,0.0)
    gn=g[0][1]
    for nu,nom,v in L1:
        if nu==g[0][0]: x['G']+=v
        else: x[BL.get(nu,'DIV')]+=v
    if x['G']==0: cnt['tête de liste gauche absente au 1er tour']+=1; continue
    x['NE']=ins-exp
    data.append((k[0],g[0][0],np.array([x[b]/ins for b in B]),np.array([g[0][2],e[0][2],ins2-exp2])/ins2,ins))
    cnt[g[0][0]]+=1; DUELS[k[0]]+=1
print(cnt,'communes',len({d[0] for d in data}),dict(DUELS))
def fit(D):
    X=np.array([d[2] for d in D]);Y=np.array([d[3] for d in D]);w=np.array([d[4] for d in D],float);w/=w.sum();k=len(B)
    f=lambda p:(w[:,None]*(X@p.reshape(k,3)-Y)**2).sum()
    cons=[{'type':'eq','fun':(lambda p,i=i:p.reshape(k,3)[i].sum()-1)} for i in range(k)]
    M=minimize(f,np.full(k*3,1/3),bounds=[(0,1)]*(k*3),constraints=cons,method='SLSQP',options={'maxiter':800,'ftol':1e-13}).x.reshape(k,3)
    return M,(w@X),(w@Y),(w@(X@M))
M,px,yo,yp=fit(data)
coms=sorted({d[0] for d in data}); by=collections.defaultdict(list)
for d in data: by[d[0]].append(d)
rng=np.random.default_rng(5); bs=[fit([d for c in rng.choice(coms,len(coms)) for d in by[c]])[0] for _ in range(100)]
lo=np.percentile(bs,5,0);hi=np.percentile(bs,95,0)
print('Municipales 2026, duels gauche contre RN/extrême droite, %d bureaux, %d communes'%(len(data),len(coms)))
for i,b in enumerate(B): print(f'  {b:3s} ({px[i]*100:4.1f}% des inscrits) : '+' | '.join(f'{M[i,j]*100:5.1f} [{lo[i,j]*100:3.0f}-{hi[i,j]*100:3.0f}]' for j in range(3)))
print('  observé',(yo*100).round(1),'prédit',(yp*100).round(1))
json.dump([M.tolist(),lo.tolist(),hi.tolist()],open('reports26.json','w'))
