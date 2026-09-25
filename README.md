# Mapa de Competências · MetLife × rhapsody

Relatório em uma página (`index.html`) com a evolução das competências de venda consultiva dos corretores MetLife nas simulações da rhapsody:

- filtros por cidade, equipe, corretor e nome ou e-mail;
- mapa de localização dos corretores (SVG embutido, funciona sem internet);
- nota média por mês dos corretores (sem a liderança), com linha de evolução e tendência;
- linha de ataque, funil das 6 fases da venda e mapa de competências por área e por corretor;
- resumo executivo por corretor: frequência de uso (runs), pontos fortes, o que evoluiu, o que precisa melhorar e a fase da venda a trabalhar.

## Como atualizar com um dump novo

Requisitos: Python 3 e `openpyxl` (`pip install openpyxl`).

```bash
# 1. calcula os indicadores a partir do dump exportado da plataforma rhapsody
python3 gerar_mapa.py dump-Metlife-DDmesAA.json novo.json

# 2. aplica nomes, cidade e equipe da planilha de usuários e grava no index.html
python3 integrar.py novo.json usuarios.xlsx index.html

# 3. publica
git commit -am "Atualiza dados até DD/MM" && git push
```

Para recalcular só até uma data: `python3 gerar_mapa.py dump.json novo.json --ate 2026-09-18`.

## Regras do cálculo

- **Sessões avaliadas:** conversas com nota e debriefing escrito pela IA, sem a equipe rhapsody e sem testes. Nota 0 com debriefing estruturado vale 58 (mesma regra do dashboard).
- **Competências:** o debriefing é dividido em "pontos fortes" e "pontos de melhoria" (4 primeiras linhas de cada seção). Uma competência conta uma vez por sessão em cada lado quando uma palavra-chave dela aparece no início de uma palavra.
- **Domínio** = fortes ÷ (fortes + melhorias), exibido com 3+ menções (2+ para corretores).
- **Evolução:** 1ª metade × 2ª metade das sessões em ordem de data.
- **Frequência de uso:** runs (todas as simulações iniciadas). Por semana = runs ÷ semanas do programa. Uso frequente ≥ 2/semana; moderado 1 a 2; baixo < 1.
- **Nota média por mês:** só corretores (sem Sabrina, Juliana e Carolina) e só os meses com sessões de corretores.

## Privacidade

O `index.html` contém nomes, e-mails e trechos de feedback dos corretores. Mantenha o repositório **privado**. O GitHub Pages no plano gratuito publica a página de forma **pública**, mesmo com o repositório privado. O dump (`.json`) e a planilha (`.xlsx`) ficam fora do Git pelo `.gitignore`.
