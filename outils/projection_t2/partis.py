import re,glob,json,collections,sys
out=[];cnt=collections.Counter();misses=collections.Counter()
for f in glob.glob(sys.argv[1]+'/*.txt'):
    T=open(f,encoding='utf-8').read()
    dep=re.sub(r'.*Élections_législatives_de_2024_(?:dans_l_|dans_la_|dans_le_|dans_les_|en_|à_|au_|aux_|dans_)?','',f)[:-4].replace('_',' ')
    for r in re.split(r'\n\|-',T):
        cells=[c for c in r.split('\n') if c.startswith('|') and not c.startswith('|}')]
        for i,c in enumerate(cells):
            if re.search(r'abrd\|UG\||Abréviation discrète\|UG\||^\|\s*align="?center"?\s*\|\s*UG\s*$',c) and i>=2:
                name=cells[i-2]; party=cells[i-1]
                name=re.sub(r'<ref.*?(</ref>|/>)','',name); name=re.sub(r'<ref.*','',name)
                m=re.findall(r'\[\[([^\]|]+)(?:\|([^\]]+))?\]\]',name)
                nm=(m[-1][1] or m[-1][0]) if m else re.sub(r'.*\|','',name)
                nm=re.sub(r"'''|\(.*?\)",'',nm).strip()
                if nm in ('Union de la gauche',) or not nm: continue
                p=re.search(r'\[\[[^\]|]*\|([^\]]+)\]\]',party) or re.search(r'\[\[([^\]|]+)\]\]',party)
                pa=p.group(1).replace("'''",'').strip() if p else '?'
                if 'abrd|' in pa: pa=re.search(r'abrd\|([^|}]+)',party).group(1)
                out.append({'dep':dep,'nom':nm,'parti':pa}); cnt[pa]+=1
                break
print(cnt.most_common(25),len(out))
json.dump(out,open('ug_partis.json','w'),ensure_ascii=False,indent=0)
