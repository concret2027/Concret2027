import csv,json,collections,unicodedata,re
def n(s): return re.sub(r'[^A-Z]','',''.join(c for c in unicodedata.normalize('NFD',s.upper()) if unicodedata.category(c)!='Mn'))
P={}
for r in csv.DictReader(open('l22/codage.csv',encoding='utf-8')):
    P[(r['DEP'].lstrip('0').upper(),r['NCIRCO'].lstrip('0'),n(r['Nom_candidat']),n(r['Prénom_candidat']))]=r['CODAGE_LEGIS2022']
BL={'NUP':'G','DVG':'AG','ECO':'AG','DXG':'AG','RDG':'AG','SOC':'AG','COM':'AG','FI':'AG','VEC':'AG','REG':'AG','DIV':'AG',
    'ENS':'C','DVC':'C','UDI':'C','LR':'D','DVD':'D','RN':'RN','REC':'RN','DSV':'RN','DXD':'RN'}
def rows(f):
    for l in open(f,encoding='latin1').read().splitlines()[1:]:
        r=l.split(';'); c=[]
        for i in range(21,len(r)-7,8):
            if r[i+4]: c.append((r[i+4],r[i+2],r[i+3],int(r[i+5] or 0)))
        yield r,c
key=lambda r:(r[0].lstrip('0').upper(),r[2].lstrip('0'),r[4],r[6].lstrip('0'))
t1={}
for r,c in rows('l22/t1.txt'):
    b=collections.Counter()
    for nu,nom,pre,v in c: b[BL.get(nu,'AG')]+=v
    ins=int(r[7]); b['NE']=ins-int(r[18]); t1[key(r)]=(ins,dict(b))
out=[];cnt=collections.Counter()
for r,c in rows('l22/t2.txt'):
    if len(c)!=2: cnt['pas duel']+=1; continue
    nus={x[0] for x in c}
    if not('NUP' in nus and 'RN' in nus): cnt['autre']+=1; continue
    g=[x for x in c if x[0]=='NUP'][0]; rn=[x for x in c if x[0]=='RN'][0]
    p=P.get((r[0].lstrip('0').upper(),r[2].lstrip('0'),n(g[1]),n(g[2])),'?')
    k=key(r)
    if k not in t1: cnt['t1?']+=1; continue
    ins=int(r[7]); exp=int(r[18])
    out.append(dict(circ=r[0]+'-'+r[2],parti='LFI' if p=='NUPES-LFI' else p,ins1=t1[k][0],t1=t1[k][1],ins2=ins,G2=g[3],RN2=rn[3],NE2=ins-exp))
    cnt['LFI' if p=='NUPES-LFI' else p]+=1
print(cnt)
print({p:len({o['circ'] for o in out if o['parti']==p}) for p in {o['parti'] for o in out}})
json.dump(out,open('duels22.json','w'))
