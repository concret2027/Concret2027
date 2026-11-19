import json,collections
BL={'MÉLENCHON':'FI','ARTHAUD':'AG','ROUSSEL':'AG','HIDALGO':'AG','JADOT':'AG','POUTOU':'AG','MACRON':'OWN','PÉCRESSE':'D','LASSALLE':'D','DUPONT-AIGNAN':'XD','LE PEN':'ED','ZEMMOUR':'XD'}
def rd(f):
    o={}
    for l in open(f,encoding='latin1').read().splitlines()[1:]:
        r=l.split(';'); v={}
        for i in range(21,len(r)-6,7): v[r[i+2]]=int(r[i+4])
        o[(r[0],r[4],r[6])]=(r[0]+'-'+r[2],int(r[7]),int(r[18]),v)
    return o
A=rd('dl/p22b1.txt'); Bt=rd('dl/p22b2.txt'); S=[]
for k,(c,ins,exp,v) in A.items():
    if k not in Bt: continue
    x=collections.Counter()
    for nm,vv in v.items(): x[BL.get(nm,'AG')]+=vv
    x['NE']=ins-exp; _,ins2,exp2,v2=Bt[k]
    S.append(dict(circ=c,ins1=ins,x=dict(x),ins2=ins2,y=[v2.get('MACRON',0),v2.get('LE PEN',0),ins2-exp2]))
G=json.load(open('gen.json')); G['P2022-Macron']=S; json.dump(G,open('gen.json','w'))
print(len(S))
