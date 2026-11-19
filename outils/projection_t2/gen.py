# Duels X contre RN, législatives 2024 et 2022, par bureau de vote. Blocs du 1er tour :
# OWN (le candidat qualifié face au RN), FI (candidats LFI), AG (autre gauche), C (centre), D (droite), ED (RN et alliés), NE (non-exprimés).
import csv,json,re,unicodedata,collections,sys
def n(s): return re.sub(r'[^A-Z ]','',''.join(c for c in unicodedata.normalize('NFD',s.upper()) if unicodedata.category(c)!='Mn').replace('-',' ').replace("'",' ')).strip()
def nn(s): return n(s).replace(' ','')
out=collections.defaultdict(list)
# ---------- 2024
ug=json.load(open('ug_partis.json')); ugp=collections.defaultdict(list)
for x in ug: ugp[nn(x['dep'])].append((n(x['nom']),x['parti']))
def party(dep,nom,pre):
    L=ugp.get(nn(dep),[]); full=n(pre+' '+nom)
    h=[p for nm,p in L if nm==full or (n(nom) in nm and n(pre).split()[0] in nm)]
    return h[0] if h else None
B24={'DVG':'AG','ECO':'AG','EXG':'AG','REG':'AG','DIV':'AG','ENS':'C','DVC':'C','UDI':'C','HOR':'C','LR':'D','DVD':'D','RN':'ED','UXD':'ED','EXD':'XD','REC':'XD','DSV':'XD'}
CENTRE={'ENS','DVC','UDI','HOR'}
def rows24(f):
    R=csv.reader(open('dl/'+f,encoding='utf-8'),delimiter=';'); next(R)
    for r in R:
        c=[]
        for i in range(19,len(r)-5,9):
            if r[i+1]: c.append((r[i+1],r[i+2],r[i+3],int(r[i+5] or 0)))
        yield (r[0].lstrip('0'),r[2].lstrip('0'),r[4].lstrip('0')),r[1],int(r[5] or 0),int(r[10] or 0),c
def bloc24(dep,nu,nom,pre):
    if nu=='UG': return 'FI' if party(dep,nom,pre)=='LFI' else 'AG'
    return B24.get(nu,'AG')
T1={}
for k,dep,ins,exp,c in rows24('t1_bv.csv'): T1[k]=(ins,exp,dep,c)
for k,dep,ins2,exp2,c in rows24('t2_bv.csv'):
    if len(c)!=2 or k not in T1: continue
    e=[x for x in c if x[0] in ('RN','UXD')]; o=[x for x in c if x[0] not in ('RN','UXD')]
    if len(e)!=1 or len(o)!=1: continue
    o=o[0]; typ=('LFI' if party(dep,o[1],o[2])=='LFI' else 'AG') if o[0]=='UG' else ('C' if o[0] in CENTRE else ('D' if o[0] in ('LR','DVD') else None))
    if not typ: continue
    ins,exp,_,c1=T1[k]; x=collections.Counter()
    for nu,nom,pre,v in c1:
        x['OWN' if (n(nom)==n(o[1]) and n(pre)==n(o[2])) else bloc24(dep,nu,nom,pre)]+=v
    if not x['OWN']: continue
    x['NE']=ins-exp
    out['2024-'+typ].append(dict(circ=k[0]+'-'+'|'.join(sorted(n(z[1]) for z in c)),ins1=ins,x=dict(x),ins2=ins2,y=[o[3],e[0][3],ins2-exp2]))
# ---------- 2022
P={}
for r in csv.DictReader(open('l22/codage.csv',encoding='utf-8')):
    P[(r['DEP'].lstrip('0').upper(),r['NCIRCO'].lstrip('0'),n(r['Nom_candidat']),n(r['Prénom_candidat']))]=r['CODAGE_LEGIS2022']
B22={'DVG':'AG','ECO':'AG','DXG':'AG','RDG':'AG','REG':'AG','DIV':'AG','ENS':'C','DVC':'C','UDI':'C','LR':'D','DVD':'D','RN':'ED','REC':'XD','DSV':'XD','DXD':'XD'}
def rows22(f):
    for l in open('l22/'+f,encoding='latin1').read().splitlines()[1:]:
        r=l.split(';'); c=[]
        for i in range(21,len(r)-7,8):
            if r[i+4]: c.append((r[i+4],r[i+2],r[i+3],int(r[i+5] or 0)))
        yield (r[0].lstrip('0').upper(),r[2].lstrip('0'),r[4],r[6].lstrip('0')),int(r[7]),int(r[18]),c
T1={}
for k,ins,exp,c in rows22('t1.txt'): T1[k]=(ins,exp,c)
for k,ins2,exp2,c in rows22('t2.txt'):
    if len(c)!=2 or k not in T1: continue
    e=[x for x in c if x[0]=='RN']; o=[x for x in c if x[0]!='RN']
    if len(e)!=1 or len(o)!=1: continue
    o=o[0]; pp=P.get((k[0],k[1],n(o[1]),n(o[2])),'')
    typ=('LFI' if pp=='NUPES-LFI' else 'AG') if o[0]=='NUP' else ('C' if o[0] in ('ENS','DVC','UDI') else ('D' if o[0] in ('LR','DVD') else None))
    if not typ: continue
    ins,exp,c1=T1[k]; x=collections.Counter()
    for nu,nom,pre,v in c1:
        if n(nom)==n(o[1]) and n(pre)==n(o[2]): x['OWN']+=v
        elif nu=='NUP': x['FI' if P.get((k[0],k[1],n(nom),n(pre)))=='NUPES-LFI' else 'AG']+=v
        else: x[B22.get(nu,'AG')]+=v
    if not x['OWN']: continue
    x['NE']=ins-exp
    out['2022-'+typ].append(dict(circ=k[0]+'-'+k[1],ins1=ins,x=dict(x),ins2=ins2,y=[o[3],e[0][3],ins2-exp2]))
print({k:(len(v),len({o['circ'] for o in v})) for k,v in out.items()})
G=json.load(open('gen.json')); G.update(out); json.dump(G,open('gen.json','w'))
