import re,glob,json,sys,collections
out=[]
for f in glob.glob(sys.argv[1]+'/*.txt'):
    T=open(f,encoding='utf-8').read()
    dep=re.sub(r'.*Élections_législatives_de_2024_(?:dans_l_|dans_la_|dans_le_|dans_les_|en_|à_|au_|aux_|dans_)?','',f)[:-4].replace('_',' ')
    L=T.split('\n')
    for i,l in enumerate(L[:-1]):
        m=re.match(r"\|\s*(?:rowspan=\S+\s*)?(?:style=\S+\s*)?\{\{Infobox Parti politique français/couleurs\|([^}]+)\}\}\s*\|\s*$",l.strip())
        if not m: continue
        nx=L[i+1]
        nx=re.sub(r'<ref.*?(</ref>|/>)','',nx); nx=re.sub(r'<ref.*','',nx)
        mm=re.findall(r'\[\[([^\]|]+)(?:\|([^\]]+))?\]\]',nx)
        nm=(mm[-1][1] or mm[-1][0]) if mm else nx.split('|')[-1]
        nm=re.sub(r"'''|\{\{[^}]*\}\}",'',nm).strip()
        if nm and len(nm)<60: out.append({'dep':dep,'nom':nm,'parti':m.group(1).strip()})
print(len(out),collections.Counter(x['parti'] for x in out).most_common(12))
json.dump(out,open('couleurs.json','w'),ensure_ascii=False)
