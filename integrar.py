"""Coloca o DATA novo (gerar_mapa.py) no HTML, com nomes, cidade e equipe da planilha de usuários (casados por e-mail).

Uso:  python3 integrar.py novo.json usuarios.xlsx [index.html]
A planilha tem as colunas: Cidade, email, Equipe, Nome.
"""
import re, json, unicodedata, openpyxl, sys
if len(sys.argv) < 3: sys.exit(__doc__)
NOVO, PLAN = sys.argv[1], sys.argv[2]
HTML = sys.argv[3] if len(sys.argv) > 3 else 'index.html'
norm = lambda x: unicodedata.normalize('NFD', str(x or '').lower()).encode('ascii', 'ignore').decode()
D = json.load(open(NOVO, encoding='utf-8')); E = D['empresas'][0]
rows = [dict(zip(['cidade', 'email', 'equipe', 'nome'], r)) for r in list(openpyxl.load_workbook(PLAN).active.iter_rows(values_only=True))[1:] if r[0]]
por_email = {r['email'].lower(): r for r in rows}
mapa, info = {}, {}
for p in E['pessoas'] + E['semAvaliacao']:
    em = (p.get('email') or '').lower()
    r = por_email.get(em) or next((x for x in rows if em and x['email'].lower().split('@')[0] == em.split('@')[0]), None)
    old = p['nome']
    if r:
        # nome da planilha; se a planilha só tem o primeiro nome e o dump tem o nome completo, fica o completo
        login = re.sub(r'[^a-z0-9]', '', norm(em.split('@')[0]))
        novo = old if norm(old).startswith(norm(r['nome']) + ' ') and re.sub(r'[^a-z0-9]', '', norm(old)) != login else r['nome']
        mapa[old] = novo; info[novo] = {'cidade': r['cidade'], 'equipe': r['equipe'], 'email': r['email']}
    else:
        info[old] = {'cidade': None, 'equipe': 'Liderança MetLife' if p.get('segmento') == 'Liderança' else None, 'email': p.get('email')}
def walk(o):
    if isinstance(o, dict): return {k: walk(v) for k, v in o.items()}
    if isinstance(o, list): return [walk(v) for v in o]
    if isinstance(o, str): return mapa.get(o, o)
    return o
D = walk(D); E = D['empresas'][0]
for p in E['pessoas'] + E['semAvaliacao']: p.update(info[p['nome']])
sem = {s['email'].lower(): s for s in E['semAvaliacao'] if s.get('email')}
for r in rows:
    loc = lambda e: (e or '').lower().split('@')[0]
    r['nomeMapa'] = next((p['nome'] for p in E['pessoas'] if loc(p.get('email')) == loc(r['email'])), None)
    s = next((v for k, v in sem.items() if loc(k) == loc(r['email'])), None)
    if s: r['runs'], r['ultimoRun'] = s['runs'], s['ultimoRun']
E['planilha'] = rows
for o, n in mapa.items(): print(f'{o:26} → {n:20} {info[n]["cidade"]} / {info[n]["equipe"]}')
print('fora da planilha:', [p['nome'] for p in E['pessoas'] if not p.get('cidade')])
h = open(HTML, encoding='utf-8').read()
m = re.search(r'const DATA = (\{.*?\});\n', h, re.S)
h = h[:m.start(1)] + json.dumps(D, ensure_ascii=False) + h[m.end(1):]
open(HTML, 'w', encoding='utf-8').write(h)
