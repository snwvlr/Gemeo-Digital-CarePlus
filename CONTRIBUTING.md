# Guia de Contribuição

Este documento descreve como trabalhar no código do CarePlus Gêmeo Digital de
forma organizada.

## Ambiente

O projeto tem duas partes. O backend, em `backend/`, é uma API FastAPI em
Python. O frontend, em `frontend/`, é servido pelo próprio backend e usa HTML,
Tailwind CSS e JavaScript, com os arquivos separados por página.

Para subir o ambiente, siga as instruções de execução do `README.md`. Com o
servidor rodando, a documentação interativa da API fica em `/docs`.

## Organização do código

O backend separa responsabilidades em camadas: `routers/` expõe as rotas,
`services/` concentra a lógica (IA, simulador de wearables, motor do gêmeo,
guardrails, exames) e `schemas.py` define os contratos de entrada e saída com
Pydantic. A configuração vem de variáveis de ambiente, em `config.py`.

No frontend, `assets/css/base.css` reúne o design system (cores, cartões,
grid). Cada página tem o seu CSS e o seu JS próprios. O `api.js` centraliza as
chamadas HTTP e o estado de sessão; o `shell.js` injeta o cabeçalho padrão,
o avatar e o alerta de emergência em todas as páginas.

## Padrões

Escreva em português do Brasil, de forma clara e direta. Funções e variáveis
com nomes descritivos. Comente o porquê, não o óbvio. Nunca inclua chaves ou
segredos no código. Respeite os limites clínicos: a IA não diagnostica nem
prescreve, e os guardrails de emergência não devem ser contornados.

## Fluxo de trabalho

Trabalhe em um branch por tarefa, com mensagens de commit objetivas que
descrevam a mudança. Antes de abrir um merge, confira que o backend sobe sem
erros (`python run.py`) e que as páginas afetadas carregam corretamente.

## Reportando problemas

Descreva o que aconteceu, o que era esperado e os passos para reproduzir. Para
falhas de segurança ou privacidade, siga o `SECURITY.md` em vez de abrir uma
issue pública.
