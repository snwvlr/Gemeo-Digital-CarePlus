# Política de Segurança e Privacidade

O CarePlus Gêmeo Digital lida com dados de saúde, uma categoria sensível.
Mesmo sendo um projeto acadêmico, a segurança e a privacidade foram tratadas
como requisitos centrais.

## Privacidade dos dados (LGPD)

A premissa do produto é simples: os dados de saúde são do paciente.

A plataforma não coleta nem armazena os dados de saúde do usuário. As leituras
dos wearables, os exames e o estado do gêmeo permanecem no dispositivo do
usuário. As únicas informações que saem desse contexto são as que o próprio
paciente decide levar ao seu médico, por exemplo no laudo gerado para a
teleconsulta.

Em um cenário de produção, o roadmap prevê processar o modelo de linguagem em
infraestrutura controlada pela operadora e pseudonimizar qualquer dado antes de
enviá-lo a serviços externos, em conformidade com a LGPD.

## Chaves e segredos

Nenhuma chave de API fica no código ou no histórico do repositório. A chave do
Gemini vem sempre de variável de ambiente, lida do arquivo `.env`, que está no
`.gitignore`. O arquivo `.env.example` serve apenas de modelo, sem valores
reais.

## Portão de acesso por senha

Para apresentações em domínio público, o site pode ser protegido por senha
(`AUTH_ENABLED=true` e `SITE_PASSWORD` no `.env`). A senha é convertida em um
token via HMAC com um segredo do servidor (`AUTH_SECRET`) e guardada em um
cookie `httpOnly` — ou seja, o JavaScript da página (inclusive um eventual
script malicioso injetado) não consegue lê-lo, o que mitiga roubo de sessão via
XSS. Um middleware no servidor valida o cookie a cada requisição; sem ele, o
site e a API ficam bloqueados (redireciona para `/login`). A senha real nunca é
gravada no código nem no repositório, apenas no `.env`.

## Proteção do código publicado

O código de front-end distribuído no repositório público é **ofuscado**. A
versão legível (fonte de desenvolvimento) não é publicada — fica fora do
repositório (listada no `.gitignore`). O projeto é de propriedade exclusiva de
João Vitor (snwvlr); a desofuscação, a engenharia reversa e o uso sem
autorização são proibidos (ver `LICENSE`). Vale o princípio honesto: proteção
client-side é uma camada de **dissuasão**, não uma garantia absoluta — a
proteção forte é a soma da licença (jurídica), do backend (server-side) e do
portão de senha.

## Proteção da API de IA (anti-abuso)

Os endpoints que se comunicam com o Google Gemini (chat, análise, relatório e
interpretação de exames) têm um limite de frequência por IP, para evitar que a
chave da API seja abusada e gere custo indevido. O padrão é 20 requisições por
minuto por IP; ao exceder, a API responde com HTTP 429 e um cabeçalho
`Retry-After`. Os valores são configuráveis em `config.py`
(`ai_rate_max` e `ai_rate_window_seconds`). Importante: este é um limite de
frequência da API, não uma censura ao conteúdo da conversa. Em produção, o
ideal seria um limite por usuário autenticado e um armazenamento compartilhado
(ex.: Redis).

## Limites clínicos do sistema

O sistema foi desenhado para não ultrapassar o seu papel:

A IA nunca afirma diagnóstico definitivo e nunca prescreve medicamento ou dose.
Ela orienta, organiza informações e encaminha ao médico. Antes de a IA
responder, guardrails determinísticos verificam a mensagem: sinais de
emergência clínica (red flags) escalam imediatamente para o SAMU 192, e sinais
de sofrimento mental encaminham ao CVV 188. Dados de wearable são tratados como
complementares, nunca como decisores.

## Como reportar um problema

Encontrou uma falha de segurança ou de privacidade? Não abra uma issue pública.
Entre em contato pelo GitHub do autor (https://github.com/snwvlr) descrevendo o
problema, para que possa ser avaliado e corrigido.

## O que ainda não está pronto para produção

Validação clínica formal com profissionais de saúde, auditoria de conformidade
com a LGPD e substituição das ferramentas simuladas (wearables, exames,
agendamento) por integrações reais com autenticação adequada.
