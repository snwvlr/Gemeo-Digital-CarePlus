# CarePlus Health · Gêmeo Digital

Plataforma de acompanhamento remoto de saúde da Care Plus. O paciente possui um
"gêmeo digital": uma réplica do seu estado clínico que reflete, em tempo real,
como ele está com base nos dados dos wearables, no histórico de exames e nos
sintomas relatados. O gêmeo conversa com o paciente, sinaliza alterações,
orienta a procurar atendimento quando necessário e organiza as informações para
levar ao médico.

A inteligência artificial (Google Gemini 2.5 Flash) atua como apoio: ela
**orienta e alerta, mas não diagnostica nem prescreve**. A conduta final é
sempre de um profissional de saúde.

## Integrantes

Projeto desenvolvido por estudantes da FIAP.

| Integrante | RM | Atuação |
|------------|-----|---------|
| Isabela Marques de Oliveira | 567230 | Concepção do produto, pesquisa e apoio |
| Isabelle Ramos De Filippis | 566783 | Concepção do produto, pesquisa e apoio |
| João Vitor Anunciação Oliveira | 567539 | Desenvolvimento: integração de IA, backend, redesign e arquitetura |
| Paulo Ribeiro Marinho | 567459 | Apresentação e apoio ao desenvolvimento |
| Samy Tamires de Sousa Cruz | 566674 | Concepção do produto, pesquisa e apoio |

## Funcionalidades

O sistema reúne, em uma interface única e consistente:

**Gêmeo digital.** Avatar personalizável (aparência, sexo, nome) cuja expressão
e pontuação de saúde acompanham os sinais vitais. Conversa por chat em primeira
pessoa, conhecendo alergias, medicamentos e sintomas do paciente.

**Wearables.** Pareamento e leitura simulada de Apple Watch, Samsung Galaxy
Watch, Xiaomi, Amazon Halo, Garmin, Fitbit e sensores próprios em ESP32, com
fluxo de sinais vitais em tempo real.

**Exames.** Painéis laboratoriais com faixas de referência, classificação
automática (normal, alto, baixo) e leitura assistida pela IA. Suporte ao envio
de PDFs de exames para levar à consulta.

**Consultas.** Agendamento de teleconsulta ou atendimento presencial por
especialidade, médico, data e horário.

**Segurança clínica.** Guardrails determinísticos detectam sinais de emergência
(red flags) e escalam imediatamente para SAMU 192 ou, em sinais de sofrimento
mental, para o CVV 188, antes mesmo de a IA responder.

**Privacidade.** Os dados de saúde não são coletados nem armazenados pela
plataforma: ficam no dispositivo do usuário. As únicas informações
compartilhadas são as que o paciente leva ao seu médico.

## Segurança e privacidade

- **Portão de acesso por senha.** Para apresentar em um domínio público, o site
  pode exigir senha (`AUTH_ENABLED=true` + `SITE_PASSWORD` no `.env`). A senha
  vira um token guardado em cookie `httpOnly` — não acessível por JavaScript,
  resistente a XSS. Site e API ficam bloqueados (redireciona para `/login`) até
  a autenticação.
- **Limite anti-abuso da IA.** Os endpoints que conversam com o Gemini têm
  limite por IP (padrão: 20 requisições/min). Ao exceder, retornam `HTTP 429`
  com `Retry-After`. É um limite de frequência, não censura ao conteúdo.
- **Guardrails clínicos.** Sinais de emergência (red flags) escalam para o
  **SAMU 192** e sinais de sofrimento mental para o **CVV 188**, antes da IA
  responder.
- **Sem diagnóstico.** A IA orienta e alerta; a conduta é sempre do médico.
- **Dados no dispositivo.** A plataforma não coleta nem armazena dados de saúde.

Mais detalhes em [`SECURITY.md`](SECURITY.md).

## Estrutura do projeto

```
Dash_Avatar_CarePlus/
├── frontend/                       # Interface (HTML, CSS e JS separados)
│   ├── index.html                  # Dashboard
│   ├── gemeo.html                  # Gêmeo digital e chat
│   ├── exames.html                 # Exames e leitura por IA
│   ├── consultas.html              # Agendamento
│   ├── medicamentos.html           # Medicamentos e biometria
│   ├── wearables.html              # Pareamento e stream de wearables
│   └── assets/
│       ├── css/                    # base.css (design system) + estilos por página
│       ├── js/                     # api, shell, avatar e lógica por página
│       └── img/                    # logo e imagens
│
├── backend/                        # API em Python (FastAPI)
│   ├── app/
│   │   ├── main.py                 # Aplicação, CORS e serve o frontend
│   │   ├── config.py               # Configuração via variáveis de ambiente
│   │   ├── schemas.py              # Contratos da API (Pydantic)
│   │   ├── services/
│   │   │   ├── gemini_service.py   # Integração com o Gemini 2.5 Flash
│   │   │   ├── guardrails.py       # Detecção de red flags (SAMU 192 / CVV 188)
│   │   │   ├── wearable...          # wearables.py (simulador de dispositivos)
│   │   │   ├── twin_state.py       # Motor de estado do gêmeo digital
│   │   │   └── exams.py            # Catálogo de exames
│   │   ├── auth.py · ratelimit.py  # portão de senha e limite anti-abuso
│   │   └── routers/                # twin, wearables, ai, exams, records, auth
│   ├── requirements.txt
│   ├── .env.example
│   └── run.py
│
├── app.py                          # entrypoint para deploy (Pterodactyl)
├── requirements.txt                # dependências para o deploy
├── README.md · SECURITY.md · CONTRIBUTING.md · LICENSE
└── docs/COMO_USAR.md               # guia de uso e teste
```

## Tecnologias

Frontend em HTML5, Tailwind CSS (via CDN) e JavaScript puro, com os arquivos
separados por página. Backend em Python com FastAPI, Pydantic e Uvicorn.
Inteligência artificial via Google Gemini 2.5 Flash (biblioteca `google-genai`).
Os avatares são gerados pela API pública DiceBear.

## Como executar

Pré-requisito: Python 3.14.5 ou superior.

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
pip install -r requirements.txt

# configure a chave da API
cp .env.example .env          # Windows: copy .env.example .env
# edite o .env e preencha GEMINI_API_KEY (https://aistudio.google.com/apikey)
# (opcional) para exigir senha no site: AUTH_ENABLED=true e SITE_PASSWORD=suasenha

python run.py
```

Acesse `http://127.0.0.1:8000`. O próprio backend serve o site.

Sem a chave do Gemini configurada, a aplicação roda em modo demonstração, com
respostas locais, permitindo testar toda a interface e a simulação de wearables.

### Deploy (Pterodactyl e similares)

O `app.py` na raiz é o ponto de entrada: sobe a API com Uvicorn em `0.0.0.0` na
porta do painel (`SERVER_PORT`). No painel, aponte **APP PY FILE** para `app.py`
e **REQUIREMENTS FILE** para `requirements.txt` (ambos na raiz). As variáveis de
ambiente (`GEMINI_API_KEY`, `AUTH_ENABLED`, `SITE_PASSWORD`, `AUTH_SECRET`) podem
ser definidas em um `.env` em `/home/container/`.

## Documentação da API

| Endereço | O que é |
|----------|---------|
| `http://127.0.0.1:8000/docs` | Documentação interativa com o visual do **Scalar** |
| `http://127.0.0.1:8000/scalar` | Alias de `/docs` |
| `http://127.0.0.1:8000/openapi.json` | Contrato OpenAPI gerado automaticamente |

Há também um botão "Documentação da API" no rodapé de qualquer página do app.

Os endpoints que se comunicam com o Gemini têm **limite de uso por IP**
(anti-abuso): por padrão, 20 requisições por minuto. Ao exceder, a API responde
com `429` e um cabeçalho `Retry-After`.

Guia do projeto:

- [`docs/COMO_USAR.md`](docs/COMO_USAR.md) — guia detalhado de uso e teste, com o passo a passo de cada tela.

## Principais endpoints

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/health` | Status do serviço e da IA |
| POST | `/api/auth/login` | Login do portão de senha (quando ativado) |
| GET | `/api/twin/state` | Estado atual do gêmeo digital |
| GET | `/api/twin/emergency` | Avaliação de gravidade (pronto-socorro ou telemedicina) |
| PUT | `/api/twin/profile` | Atualiza perfil (recalcula a saúde) |
| GET | `/api/wearables/catalog` | Dispositivos disponíveis |
| GET | `/api/wearables/stream` | Sinais vitais ao vivo |
| POST | `/api/ai/chat` | Conversa com o gêmeo (com guardrails) |
| POST | `/api/ai/analyze` | Análise de risco pela IA |
| GET | `/api/exams` | Painéis de exames |
| POST | `/api/exams/{id}/interpret` | Leitura do exame pela IA |

## Aviso

Projeto acadêmico. Não substitui avaliação médica. Antes de qualquer uso real
seriam necessárias validação clínica, auditoria de conformidade com a LGPD e a
substituição dos dados e integrações simulados por serviços reais.
