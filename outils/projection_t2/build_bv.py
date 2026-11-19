import csv,json,re,unicodedata,collections
D='dl/'
def n(s): return re.sub(r'[^A-Z ]','',''.join(c for c in unicodedata.normalize('NFD',s.upper()) if unicodedata.category(c)!='Mn').replace('-',' ').replace("'",' ')).strip()
def num(s): return int(s) if s else 0
def rows(f,o=18):
    R=csv.reader(open(D+f,encoding='utf-8'),delimiter=';'); next(R)
    for r in R:
        r[0]=r[0].lstrip('0'); r[2]=r[2].lstrip('0'); r[4]=r[4].lstrip('0')
        c=[]
        for i in range(o,len(r)-5,9):
            if r[i+1]: c.append((r[i+1],r[i+2],r[i+3],num(r[i+5])))
        yield r,c
# candidate -> circ
cand2circ={}
for r,c in rows('t1_circ.csv'):
    for nu,nom,pre,v in c: cand2circ[(r[0],n(nom),n(pre))]=r[2]
# party of UG candidates (Wikipedia), keyed by dept name + surname tokens
ug=json.load(open('ug_partis.json'))
depn=lambda s:n(s).replace(' ','')
ugp=collections.defaultdict(list)
for x in ug: ugp[depn(x['dep'])].append((n(x['nom']),x['parti']))
def party(deplib,nom,pre):
    L=ugp.get(depn(deplib),[])
    full=n(pre+' '+nom); hits=[p for nm,p in L if nm==full or (n(nom) in nm and n(pre).split()[0] in nm)]
    return hits[0] if hits else None
BLOC={'UG':'G','DVG':'AG','ECO':'AG','COM':'AG','FI':'AG','SOC':'AG','VEC':'AG','RDG':'AG','EXG':'EXG','REG':'DIV','DIV':'DIV',
      'ENS':'C','DVC':'C','UDI':'C','HOR':'C','MDM':'C','REN':'C','LR':'D','DVD':'D','RN':'RN','UXD':'RN','EXD':'RN','REC':'REC'}
def circof(dep,c):
    S={cand2circ.get((dep,n(nom),n(pre))) for nu,nom,pre,v in c}
    return S.pop() if len(S)==1 and None not in S else None
t1={}
for r,c in rows('t1_bv.csv',19):
    ci=circof(r[0],c)
    if not ci: continue
    ins=num(r[5]); exp=num(r[10]); b=collections.Counter()
    for nu,nom,pre,v in c: b[BLOC.get(nu,'DIV')]+=v
    b['NE']=ins-exp; t1[(r[2],r[4])]=(ins,dict(b))
out=[];cnt=collections.Counter()
for r,c in rows('t2_bv.csv',19):
    ci=circof(r[0],c)
    if not ci or len(c)!=2: cnt['pas duel']+=1; continue
    nus={x[0] for x in c}
    if not ('UG' in nus and (nus & {'RN','UXD'})): cnt['autre duel']+=1; continue
    g=[x for x in c if x[0]=='UG'][0]; rn=[x for x in c if x[0]!='UG'][0]
    p=party(r[1],g[1],g[2]); k=(r[2],r[4])
    if k not in t1: cnt['t1 manquant']+=1; continue
    ins=num(r[5]); exp=num(r[10])
    out.append(dict(com=r[2],circ=ci,parti=p or '?',ins1=t1[k][0],t1=t1[k][1],ins2=ins,G2=g[3],RN2=rn[3],NE2=ins-exp,rnnu=rn[0]))
    cnt['duel '+(('LFI' if p=='LFI' else 'autre gauche') if p else 'parti inconnu')]+=1
print(cnt)
circs=collections.defaultdict(set)
for o in out: circs[o['parti']=='LFI' and 'LFI' or o['parti']].add(o['circ'])
print({k:len(v) for k,v in circs.items()})
json.dump(out,open('duels_bv.json','w'))
