# Mapa de Competências · MetLife × rhapsody

Relatório em uma página (`index.html`) com a evolução das competências de venda consultiva dos corretores MetLife nas simulações da rhapsody.

## Acesso privado (sem senha)

A página fica no **Cloudflare Pages**, protegida pelo **Cloudflare Access**. Só entram os e-mails que você liberar: a pessoa digita o e-mail, recebe um código de 6 dígitos e entra. Não há senha para criar. O plano gratuito cobre até 50 pessoas.

### 1. GitHub: deixar tudo privado

1. No repositório `skill-metlife`: **Settings → General → Danger Zone → Change repository visibility → Make private**.
2. **Settings → Pages**: em *Source*, escolha **None** (ou *Unpublish site*) para desligar o `bada09.github.io/skill-metlife`.
3. Faça o mesmo no `dashboard_metlife` se ele também tiver dados de corretores.

### 2. Cloudflare Pages: publicar a partir do repositório privado

1. Crie uma conta gratuita em https://dash.cloudflare.com.
2. **Workers & Pages → Create → Pages → Connect to Git** → autorize o GitHub e escolha `bada09/skill-metlife`.
3. Configuração do build: *Framework preset* **None**, *Build command* vazio, *Build output directory* `/`. Clique em **Save and Deploy**.
4. O endereço fica `https://skill-metlife.pages.dev`. Cada `git push` publica a versão nova sozinho.

### 3. Cloudflare Access: liberar só os e-mails autorizados

1. No painel da Cloudflare, abra **Zero Trust** (escolha o plano **Free**; pode pedir um cartão, mas não cobra até 50 usuários).
2. **Access → Applications → Add an application → Self-hosted**.
3. *Application name*: `Mapa MetLife`. *Application domain*: `skill-metlife.pages.dev`. Adicione também `*.skill-metlife.pages.dev`, que cobre as versões de pré-visualização.
4. *Identity providers*: deixe **One-time PIN** (código por e-mail).
5. Crie a política: *Policy name* `Autorizados`, *Action* **Allow**, *Include* → **Emails** → digite os e-mails, começando por `taba.dias@rhapsody.run`. Se quiser liberar todo mundo de um domínio, use **Emails ending in** (por exemplo, `@metlife.com.br`).
6. Salve. Abra `https://skill-metlife.pages.dev` numa janela anônima para testar: deve pedir o e-mail e mandar o código.

### Autorizar ou tirar alguém

**Zero Trust → Access → Applications → Mapa MetLife → Policies → Autorizados → Edit** → adicione ou remova o e-mail → **Save**. Vale na hora. Para derrubar quem já está logado: **Zero Trust → My Team → Users → Revoke**.

## Atualizar os dados com um dump novo

Requisitos: Python 3 e `openpyxl` (`pip install openpyxl`).

```bash
python3 gerar_mapa.py dump-Metlife-DDmesAA.json novo.json   # indicadores a partir do dump da plataforma
python3 integrar.py novo.json usuarios.xlsx index.html       # nomes, cidade e equipe da planilha
git commit -am "Atualiza dados até DD/MM" && git push         # a Cloudflare publica sozinha
```

## Regras do cálculo

- **Sessões avaliadas:** conversas com nota e debriefing escrito pela IA, sem a equipe rhapsody e sem testes. Nota 0 com debriefing estruturado vale 58.
- **Competências:** o debriefing é dividido em "pontos fortes" e "pontos de melhoria" (4 primeiras linhas de cada seção). Uma competência conta uma vez por sessão em cada lado quando uma palavra-chave dela aparece no início de uma palavra.
- **Domínio** = fortes ÷ (fortes + melhorias), exibido com 3+ menções (2+ por corretor).
- **Evolução:** 1ª metade × 2ª metade das sessões em ordem de data.
- **Frequência de uso:** runs (todas as simulações iniciadas). Por semana = runs ÷ semanas do programa. Uso frequente ≥ 2/semana; moderado de 1 a 2; baixo < 1.
- **Nota média por mês:** só corretores (sem a liderança) e só os meses com sessões de corretores.
