import re,sys
def rows(L):
    out=[];cur=[]
    for l in L:
        s=l.strip()
        if s.startswith('|-'):
            if cur: out.append(cur); cur=[]
            continue
        if s.startswith('|') and not s.startswith('|}'): cur.append(s[1:])
    if cur: out.append(cur)
    return out
def num(c):
    m=re.findall(r"(\d+(?:[,.]\d+)?)\s*%",c); return float(m[-1].replace(',','.')) if m else None
def inst(c):
    m=re.search(r'Sondeur\|([^}]+)\}\}',c); return m.group(1) if m else None
for f,a,b,cols in [('fr2017.txt',27,465,5),('fr2022.txt',9561,11303,3)]:
    L=open(f,encoding='utf-8').read().split('\n')[a:b]
    R=[]
    for r in rows(L):
        if len(r)<cols+2: continue
        i=inst(r[0]); 
        if not i: continue
        R.append((i,re.sub(r'\{\{date\|([^}]*)\}\}',r'\1',r[1]).replace('|',' ').strip(),num(r[cols]),num(r[cols+1])))
    print(f,len(R)); 
    for x in R[:14]: print('  ',x)
import statistics
def dernier(R,mots):
    vu={};
    for i,d,m,l in R:
        if any(w in d for w in mots) and m and i.lower() not in vu: vu[i.lower()]=m
    return vu
L=open('fr2017.txt',encoding='utf-8').read().split('\n')[27:465]; R17=[(inst(r[0]),r[1],num(r[5]),num(r[6])) for r in rows(L) if len(r)>=7 and inst(r[0])]
L=open('fr2022.txt',encoding='utf-8').read().split('\n')[9561:11303]; R22=[(inst(r[0]),r[1],num(r[3]),num(r[4])) for r in rows(L) if len(r)>=5 and inst(r[0])]
a=dernier(R17,['mai']); b=dernier(R22,['20 avril 2022','21 avril 2022','22 avril 2022','19 avril','18 avril'])
print('2017 derniers sondages',a,statistics.mean(a.values()))
print('2022 derniers sondages',b,statistics.mean(b.values()))
for mois in ['novembre 2021','décembre 2021']:
    v=[m for i,d,m,l in R22 if mois in d and m]; print(mois,len(v),round(statistics.mean(v),1) if v else None)
