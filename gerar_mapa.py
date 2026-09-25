"""Gera o objeto DATA do Mapa de Competências MetLife a partir do dump da plataforma rhapsody.

Uso:  python3 gerar_mapa.py DUMP.json SAIDA.json [--ate AAAA-MM-DD]

Regras (as mesmas descritas em "Como o mapa é calculado" no relatório):
- Sessões avaliadas: conversas com avaliação (nota) e debriefing escrito, excluindo a equipe rhapsody e testes.
- O debriefing é dividido em "pontos fortes" e "pontos de melhoria"; uma competência conta uma vez por
  sessão em cada lado quando uma palavra-chave dela aparece no início de uma palavra da seção.
- Domínio = fortes ÷ (fortes + melhorias); exibido com 3+ menções (2+ para pessoas).
- Evolução compara a 1ª metade (n//2 mais antigas) com a 2ª metade das sessões, em ordem de data.
- Frequência de uso (novo): todas as conversas iniciadas (runs), avaliadas ou não.
"""
import json, re, sys, unicodedata, collections
from datetime import datetime, timedelta, date

ARGS = [a for a in sys.argv[1:] if not a.startswith('--')]
ATE = None
if '--ate' in sys.argv:
    ATE = date.fromisoformat(sys.argv[sys.argv.index('--ate') + 1])

DUMP, OUT = ARGS[0], ARGS[1]
d = json.load(open(DUMP, encoding='utf-8'))

def norm(s):
    s = unicodedata.normalize('NFD', str(s or '').lower())
    return ''.join(c for c in s if unicodedata.category(c) != 'Mn')

# ── Competências (mesma lista e palavras-chave do dashboard MetLife) ──
SKILLS = [
    ('escuta', '👂', 'Escuta Ativa', 'Manter a calma e ouvir genuinamente o prospect antes de responder.',
     ['escuta', 'escutar', 'ouvi', 'ouvir', 'ecoute', 'ecouter', 'atento', 'atenta', 'calma', 'calme', 'paciencia', 'paciente']),
    ('qualificacao', '🎯', 'Qualificação Rápida e Fina', 'Diagnosticar rápido a real necessidade e o tipo de objeção em jogo.',
     ['qualific', 'necessidade', 'besoin', 'diagnostic', 'perfil', 'identificar a objec', 'tipo de objec', "type d'objection"]),
    ('roteiro', '📋', 'Domínio do Roteiro Consultivo', 'Dominar o roteiro de 8 etapas e manter o controle da conversa.',
     ['roteiro', 'script', 'etapa', 'étape', 'controle da ligacao', 'controle du call', 'agenda', 'estrutura da ligacao']),
    ('objeccoes', '🔧', 'Tratamento de Objeções ("Sim, Mas")', 'Acolher a objeção com o "Sim, mas..." e redirecionar sem confronto.',
     ['objec', 'sim mas', 'oui mais', 'yes but', 'contorna', 'contourne', 'rebate']),
    ('neutralizacao', '🪃', 'Neutralização de Adiamento', 'Sequência Sim Mas · Bumerangue · Recapitulação · CLOSE contra o "vou pensar".',
     ['bumerangue', 'boomerang', 'recapitul', 'récapitul', 'close', 'adiamento', 'report', 'vou pensar', 'je vais reflechir',
      'esta caro', "c'est cher", 'power phrase', 'cruz vossa', 'cruz nossa', 'tecnica gorilla', 'technique gorilla', 'tecnica russa',
      'obligation', 'swap']),
    ('assertividade', '💬', 'Assertividade', 'Transmitir confiança e energia na voz, conduzindo com firmeza.',
     ['assertiv', 'confianca', 'confiance', 'energia na voz', 'energie dans la voix', 'firmeza', 'fermete']),
    ('fechamento', '🤝', 'Fechamento por Eleição Forçada', 'Oferecer duas opções de horário para travar o agendamento.',
     ['eleicao forcada', 'escolha forcada', 'choix force', 'concordancia tacita', 'accord tacite', 'fechar', 'conclure', 'agendar',
      'prise de rendez-vous', 'fechamento', 'conclusion']),
    ('personalizacao', '📄', 'Recusa de Material Genérico', 'Trocar o "me manda um documento" por uma reunião.',
     ['material generico', 'materiel generique', 'envie um documento', 'envoyez-moi un document', 'redirecionar', 'rediriger']),
    ('sensibilizacao', '🕊️', 'Abordagem Ética de Temas Sensíveis', 'Dedramatizar a cobertura por morte com tato e empatia.',
     ['dedramatiz', 'dédramatis', 'morte', 'deces', 'proteger a familia', 'proteger os entes', 'proteger ses proches', 'sensivel', 'sensible']),
    ('reconexao', '🧭', 'Reconexão com o Propósito de Proteção', 'Reconectar o prospect ao motivo que o levou a considerar o seguro.',
     ['proposito', 'but', 'motivo original', 'raison initiale', 'protecao da familia', 'protecao familiar', 'protection familiale',
      'reconectar', 'reconnecter']),
    ('indicacoes', '🔗', 'Ativação de Indicações (Momento UAU)', 'Aproveitar o momento UAU pós-venda para pedir indicações.',
     ['indicac', 'recommand', 'recomendac', 'momento uau', 'moment wow', 'momento wow', 'momento de ouro', 'a.s.k.t.h.e.m.a.n', 'ask them man']),
    ('consultiva', '🎓', 'Postura Consultiva', 'Vender como consultor que educa e recomenda, sem pressão.',
     ['postura consultiva', 'posture consultative', 'consultor', 'consultant', 'sem pressao', 'sans pression']),
]
KEYS = [s[0] for s in SKILLS]
KW_RE = {k: re.compile(r'(?<![a-z0-9])(?:' + '|'.join(re.escape(norm(w)) for w in kws) + ')') for k, *_, kws in SKILLS}
ACAO = {
    'escuta': 'Deixar o prospect terminar, reformular o que ouviu e só então responder.',
    'qualificacao': 'Nos primeiros 60 segundos, identificar necessidade e tipo de objeção (explícita, vaga ou pergunta).',
    'roteiro': 'Seguir o roteiro de 8 etapas e retomar o controle da conversa a cada desvio.',
    'objeccoes': 'Responder toda objeção com "Sim, mas..." + pergunta de redirecionamento, sem rebater diretamente.',
    'neutralizacao': 'Treinar a sequência Sim Mas · Bumerangue · Recapitulação · CLOSE nos cenários de adiamento e preço.',
    'assertividade': 'Falar com energia e firmeza, com frases curtas e afirmativas, sem pedir desculpas pela ligação.',
    'fechamento': 'Terminar toda ligação com eleição forçada: duas opções de horário, nunca "quando puder".',
    'personalizacao': 'Recusar o envio de material genérico e propor uma reunião curta para personalizar.',
    'sensibilizacao': 'Tratar a cobertura por morte com tato, falando de proteção da família e não de morte.',
    'reconexao': 'Relembrar ao cliente o motivo que o levou a pensar em se proteger antes de discutir preço.',
    'indicacoes': 'No momento UAU pós-venda, pedir 2 ou 3 indicações nominais usando a técnica A.S.K.T.H.E.M.A.N.',
    'consultiva': 'Recomendar como consultor: perguntar, explicar e sugerir, sem pressionar.',
}

# ── Cenários → área (títulos dos use cases, todas as versões) ──
def cenario_de(titulo):
    t = norm(titulo)
    if 'document' in t: return 'Prospecção · "Envie-me um documento" → reunião', 'Prospecção'
    if 'prospect frio' in t or 'prospect froid' in t: return 'Prospecção · Prospect frio → reunião qualificada', 'Prospecção'
    if 'financeiro' in t or 'financier' in t: return 'Argumentação · Objeção financeira', 'Argumentação de Venda'
    if 'adiar' in t or 'report' in t: return 'Argumentação · Objeção de adiamento', 'Argumentação de Venda'
    if 'deces' in t or 'morte' in t or 'vida' in t: return 'Argumentação · Cobertura de vida', 'Argumentação de Venda'
    if 'recomend' in t or 'recommand' in t: return 'Fidelização · Ativar recomendações', 'Fidelização & Indicações'
    return 'Outros · ' + titulo.strip()[:40], 'Outros'
UC = {u['id']: cenario_de(u['title']) for u in d['usecases']}

# ── Quem entra ──
def excluido(nome, email):
    n, e = norm(nome), norm(email)
    return (e.endswith('@rhapsody.run') or 'rhapsody' in n or 'teste' in n or 'tabajara' in n
            or 'philippe lepeuple' in n or 'philippe de langlais' in n or 'sophie geraud' in n)
LIDERANCA = ['sabrina oliveira', 'juliana pedrao', 'carolina bandeliauskas']

# ── Divisão do debriefing em seções ──
HEAD = re.compile(r'^\s*(?:#{1,6}\s*)?[^\wÀ-ÿ\n]{0,6}\s*(pontos? fortes?|points? forts?|eixos? de melhoria|pontos? de melhoria|axes? d.?am[eé]lioration|axes? de melhoria|points? d.?am[eé]lioration|points? de d[eé]veloppement|pontos? de desenvolvimento|[a-zà-ÿ][^\n]{0,40})\s*:?\s*$', re.I | re.M)
def secoes(fb):
    """Devolve (texto de pontos fortes, texto de pontos de melhoria)."""
    linhas = fb.split('\n'); forte, melhora, atual = [], [], None
    for ln in linhas:
        l = norm(ln).strip()
        eh_titulo = ln.lstrip().startswith('#') or (len(l) < 60 and l.rstrip(':').strip() and not l.startswith(('-', '*', '•')) and
                    re.fullmatch(r'[^a-z0-9]*[a-z ][a-z \'’.-]*:?', l) is not None and len(l.split()) <= 5)
        if eh_titulo:
            t = re.sub(r'[^a-z \']', ' ', l)
            if re.search(r'pontos? fortes?|points? forts?', t): atual = 'f'; continue
            if re.search(r'melhoria|amelioration|developpement|desenvolvimento|a melhorar|a desenvolver', t): atual = 'm'; continue
            atual = None; continue  # qualquer outro título (Análise emocional, Momentos-chave…) encerra a seção
        # como no dashboard: só as 4 primeiras linhas com conteúdo de cada seção
        l2 = re.sub(r'^[\s\-•▶🟢🔴🟡➕⚠️#*]+', '', ln).strip()
        if len(l2) <= 12 or re.fullmatch(r'\[(linha em branco|ligne vide|linha vazia|lignes vides|\.\.\.)\]', l2, re.I): continue
        if atual == 'f': forte.append(l2)
        elif atual == 'm': melhora.append(l2)
    return '\n'.join(forte[:4]), '\n'.join(melhora[:4])

def tags(txt):
    t = norm(txt)
    return {k for k in KEYS if KW_RE[k].search(t)}

# ── Coleta ──
BRT = timedelta(hours=-3)
def dt(s): return datetime.fromisoformat(s.replace('Z', '+00:00')) + BRT
sessoes, runs = [], collections.defaultdict(list)
for m in d['members']:
    u = m['user']; nome = f"{(u.get('firstName') or '').strip()} {(u.get('lastName') or '').strip()}".strip()
    if excluido(nome, u.get('email')): continue
    for c in u.get('conversations', []):
        cv = c['conversation']; quando = dt(cv['createdAt'])
        if ATE and quando.date() > ATE: continue
        msgs = cv.get('messages') or []
        humanas = sum(1 for x in msgs if (x.get('participantType') or '').upper() == 'HUMAN')
        runs[nome].append({'q': quando, 'humanas': humanas, 'uc': cv['usecaseId']})
        ev = cv.get('evaluation')
        if not ev or ev.get('score') is None or not (ev.get('feedback') or '').strip(): continue
        cen, area = UC.get(cv['usecaseId'], ('Outros', 'Outros'))
        f_txt, m_txt = secoes(ev['feedback'])
        # mesma calibração do dashboard: nota 0 com debriefing estruturado vale 58
        nota = 58 if (not ev['score'] and len(ev['feedback']) > 100) else ev['score']
        sessoes.append({'nome': nome, 'email': u.get('email'), 'q': quando, 'score': nota, 'cen': cen, 'area': area,
                        'S': tags(f_txt), 'G': tags(m_txt), 'mtxt': m_txt})
sessoes.sort(key=lambda s: s['q'])

# ── Agregações ──
def dom(lista, minimo):
    out = {}
    for k in KEYS:
        S = sum(1 for s in lista if k in s['S']); G = sum(1 for s in lista if k in s['G'])
        out[k] = {'s': S, 'g': G, 'v': round(S / (S + G) * 100) if S + G >= minimo else None}
    return out
def media(xs): return round(sum(xs) / len(xs), 1) if xs else None
def exemplo(k, lista):
    for s in reversed(lista):
        if k not in s['G']: continue
        for ln in s['mtxt'].split('\n'):
            l = ln.strip(' -•*\t')
            if len(l) > 12 and KW_RE[k].search(norm(l)):
                l = re.sub(r'\*\*', '', l).strip()
                return l if len(l) <= 200 else l[:199].rstrip() + '…'
    return None

def perfil(lista, minimo, pessoas_de=None):
    n = len(lista); ini, rec = lista[: n // 2], lista[n // 2:]
    if n < 2: ini, rec = [], lista
    sc = [s['score'] for s in lista]; si, sr = media([s['score'] for s in ini]), media([s['score'] for s in rec])
    D, Di, Dr = dom(lista, minimo), dom(ini, minimo), dom(rec, minimo)
    evo = {k: {'ini': Di[k]['v'] if ini else None, 'rec': Dr[k]['v'] if ini else None,
               'delta': (Dr[k]['v'] - Di[k]['v']) if ini and Di[k]['v'] is not None and Dr[k]['v'] is not None else None} for k in KEYS}
    prios = []
    if n >= 2:
        cand = []
        for i, k in enumerate(KEYS):
            g = sum(1 for s in rec if k in s['G'])
            if g: cand.append((-(g / len(rec)), i, k, g))
        for _, _, k, g in sorted(cand)[:3]:
            cs = collections.Counter(s['cen'] for s in rec if k in s['G'])
            p = {'k': k, 'taxa': round(g / len(rec) * 100), 'g': g, 'dom': D[k]['v'], 'tend': evo[k]['delta'],
                 'cenario': cs.most_common(1)[0][0] if cs else None, 'acao': ACAO[k], 'exemplos': [x for x in [exemplo(k, rec)] if x]}
            if pessoas_de: p['pessoas'] = pessoas_de(k)
            prios.append(p)
    evoluiu = [{'k': k, 'ini': evo[k]['ini'], 'rec': evo[k]['rec'], 'delta': evo[k]['delta'], 'tipo': 'dominio'}
               for k in KEYS if evo[k]['delta'] is not None and evo[k]['delta'] >= 10]
    evoluiu.sort(key=lambda x: -x['delta'])
    if ini:
        for k in KEYS:
            if any(k in s['G'] for s in ini) and not any(k in s['G'] for s in rec) and not any(x['k'] == k for x in evoluiu):
                evoluiu.append({'k': k, 'tipo': 'resolvido'})
    fortes = [k for k in sorted(KEYS, key=lambda k: -(D[k]['v'] or -1)) if D[k]['v'] is not None and D[k]['v'] >= 60][:3]
    return {'n': n, 'score': media(sc), 'scoreIni': si, 'scoreRec': sr,
            'deltaScore': round(sr - si, 1) if si is not None and sr is not None else None,
            'deltaPct': round((sr - si) / si * 100, 1) if si else None,
            'dom': D, 'evo': evo, 'prios': prios, 'evoluiu': evoluiu, 'fortes': fortes}

todos_runs = sorted(sum(runs.values(), []), key=lambda r: r['q'])
INICIO, FIM = todos_runs[0]['q'], todos_runs[-1]['q']
SEMANAS_PROG = max(1, ((FIM - INICIO).days + 1) / 7)
EMAIL = {}
for m in d['members']:
    u = m['user']; EMAIL[f"{(u.get('firstName') or '').strip()} {(u.get('lastName') or '').strip()}".strip()] = u.get('email')
nomes = sorted({s['nome'] for s in sessoes}, key=lambda n: (-sum(1 for s in sessoes if s['nome'] == n), norm(n)))
def fmt(q): return q.strftime('%d/%m/%Y')
pessoas = []
for nome in nomes:
    ls = [s for s in sessoes if s['nome'] == nome]
    p = perfil(ls, 2)
    rs = sorted(runs[nome], key=lambda r: r['q'])
    dias = sorted({r['q'].date() for r in rs})
    p.update({'nome': nome, 'area': collections.Counter(s['area'] for s in ls).most_common(1)[0][0],
              'segmento': 'Liderança' if any(l in norm(nome) for l in LIDERANCA) else 'Corretor',
              'ultima': fmt(ls[-1]['q']), 'serie': [s['score'] for s in ls],
              'runs': len(rs), 'runsComFala': sum(1 for r in rs if r['humanas'] > 0),
              'primeiroRun': fmt(rs[0]['q']) if rs else None, 'ultimoRun': fmt(rs[-1]['q']) if rs else None,
              'diasAtivos': len(dias), 'email': EMAIL.get(nome),
              # frequência medida sobre todo o programa (do 1º run da operação até o último), para comparar todos na mesma régua
              'runsSemana': round(len(rs) / SEMANAS_PROG, 1),
              'semanasAtivas': len({(r['q'] - INICIO).days // 7 for r in rs}),
              'runs30': sum(1 for r in rs if (FIM - r['q']).days < 30),
              'cenarios': dict(collections.Counter(s['cen'] for s in ls))})
    pessoas.append(p)
# pessoas que treinaram mas ainda não têm sessão avaliada entram só na frequência
sem_aval = [{'nome': n, 'email': EMAIL.get(n), 'runs': len(r), 'ultimoRun': fmt(max(x['q'] for x in r))} for n, r in runs.items() if r and n not in nomes]

def recentes_com_gap(k, filtro=lambda s: True):
    out = []
    for p in pessoas:
        ls = [s for s in sessoes if s['nome'] == p['nome'] and filtro(s)]
        if len(ls) < 2: continue
        if any(k in s['G'] for s in ls[len(ls) // 2:]): out.append(p['nome'])
    return out

geral = perfil(sessoes, 3, pessoas_de=lambda k: recentes_com_gap(k))
areas = []
for area in [a for a, _ in collections.Counter(s['area'] for s in sessoes).most_common()]:
    ls = [s for s in sessoes if s['area'] == area]
    a = perfil(ls, 3, pessoas_de=lambda k, area=area: recentes_com_gap(k, lambda s: s['area'] == area))
    a.update({'nome': area, 'pessoas': len({s['nome'] for s in ls})})
    areas.append(a)
# Nota média por mês: só corretores (sem a liderança), cobrindo todo o período do dump,
# inclusive meses em que só houve testes da equipe rhapsody (ficam vazios).
todas = [dt(c['conversation']['createdAt']) for m in d['members'] for c in m['user'].get('conversations', [])]
if ATE: todas = [q for q in todas if q.date() <= ATE]
def lider(nome): return any(l in norm(nome) for l in LIDERANCA)
y, mth = min(todas).year, min(todas).month
meses = []
while (y, mth) <= (max(todas).year, max(todas).month):
    mm = f'{y}-{mth:02d}'
    ls = [s['score'] for s in sessoes if s['q'].strftime('%Y-%m') == mm and not lider(s['nome'])]
    rr = [r for n, rs_ in runs.items() if not lider(n) for r in rs_ if r['q'].strftime('%Y-%m') == mm]
    lid = sum(1 for s in sessoes if s['q'].strftime('%Y-%m') == mm and lider(s['nome']))
    motivo = None if ls else ('só sessões da liderança' if lid else 'só testes da equipe rhapsody' if any(q.strftime('%Y-%m') == mm for q in todas) else 'sem sessões')
    meses.append({'m': mm, 'score': media(ls), 'n': len(ls), 'runs': len(rr), 'lideranca': lid, 'motivo': motivo,
                  'corretores': len({s['nome'] for s in sessoes if s['q'].strftime('%Y-%m') == mm and not lider(s['nome'])})})
    y, mth = (y + 1, 1) if mth == 12 else (y, mth + 1)
out = {'gerado': (datetime.utcnow() + BRT).strftime('%d/%m/%Y %H:%M'), 'fonte': DUMP.split('/')[-1].split('_', 1)[-1],
       'empresas': [{'id': 'metlife', 'nome': 'MetLife',
                     'skills': [{'k': k, 'emoji': e, 'nome': n, 'desc': ds} for k, e, n, ds, _ in SKILLS],
                     'sessoes': len(sessoes), 'pessoasTotal': len(pessoas),
                     'periodo': [fmt(sessoes[0]['q']), fmt(sessoes[-1]['q'])], 'periodoDump': [fmt(min(todas)), fmt(max(todas))],
                     'runsTotal': len(todos_runs), 'semanasPrograma': round(SEMANAS_PROG, 1), 'inicioRuns': fmt(INICIO), 'ultimoRun': fmt(todos_runs[-1]['q']) if todos_runs else None,
                     'geral': geral, 'areas': areas, 'pessoas': pessoas, 'meses': meses, 'semAvaliacao': sem_aval}]}
json.dump(out, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False)
print('sessões', len(sessoes), 'pessoas', len(pessoas), 'runs', len(todos_runs), 'período', out['empresas'][0]['periodo'])
