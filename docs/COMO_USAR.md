# Como usar e testar o CarePlus Gêmeo Digital

Este guia explica o que é o projeto, por que ele foi pensado assim, como
colocar para rodar e como testar cada funcionalidade. A ideia é que qualquer
pessoa, mesmo sem conhecer o código, consiga abrir, navegar e entender a
proposta em poucos minutos.

## A ideia, em uma frase

A saúde hoje costuma ser reativa: a pessoa só procura ajuda quando já está mal,
e quando procura, chega na consulta com dados soltos. O CarePlus inverte isso
criando um "gêmeo digital" do paciente, uma réplica do seu estado de saúde que
acompanha os sinais vitais em tempo real, conversa, alerta quando algo foge do
padrão, organiza tudo para levar ao médico e ainda recebe de volta a prescrição
validada por ele.

## O que é (e o que não é)

O gêmeo digital monitora e orienta. Ele não diagnostica e não prescreve. Essa
fronteira é proposital e aparece o tempo todo no produto: quando a conversa
toca em um sinal de emergência, o próprio sistema interrompe e encaminha para o
SAMU 192 (ou para o CVV 188, em sinais de sofrimento mental), sem deixar a IA
"opinar". Essa triagem é um guardrail determinístico: regras de texto que
rodam antes da IA e reconhecem muitas formas de dizer a mesma coisa, então o
encaminhamento acontece sempre, não "às vezes". O gêmeo também entende
linguagem do dia a dia: expressões coloquiais como "me borrei" ou "tô fervendo"
são associadas aos sintomas clínicos (diarreia, febre) para alimentar o que o
médico verá. A prescrição existe, mas é atribuída ao médico, depois da
teleconsulta: a IA monta só um rascunho de apoio. Resumindo: a IA cuida do
monitoramento e do acolhimento; o médico cuida do diagnóstico e da conduta.

Outra decisão central é a privacidade. Os dados de saúde não são coletados nem
armazenados pela plataforma; a proposta é que eles fiquem no dispositivo do
usuário e que as únicas informações que saem dali sejam as que o paciente leva
ao seu médico (e a prescrição que volta), sempre em memória, sem persistir em
servidor central.

## Como colocar para rodar

Pré-requisito: Python 3.11 ou mais novo.

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env          # Windows: copy .env.example .env
# abra o .env e preencha GEMINI_API_KEY (https://aistudio.google.com/apikey)

python run.py
```

Abra `http://127.0.0.1:8000`. É só isso: o próprio backend serve o site.

Se você não tiver uma chave do Gemini, tudo bem. O sistema entra em modo
demonstração, com respostas locais, e todo o resto (wearables, exames,
consultas, prescrição e histórico) continua funcionando para você navegar e
apresentar.

## Documentação da API

Dois caminhos, escolha o que preferir:

- `http://127.0.0.1:8000/scalar` — referência da API com o visual do Scalar
  (mais bonito e organizado). É a recomendada para explorar os endpoints.
- `http://127.0.0.1:8000/docs` — Swagger UI padrão do FastAPI, caso queira
  testar chamadas direto pelo navegador.

Ambas leem o mesmo contrato gerado automaticamente em `/openapi.json`.

## Roteiro de teste (passo a passo)

A ordem abaixo conta uma história e cobre todos os recursos. Leva uns 5 minutos.

1. **Dashboard.** Ao abrir, aparece um aviso de que o paciente é gerado
   aleatoriamente para demonstração (nome, idade, medicamentos e exames mudam a
   cada Ctrl+F5). Repare na saudação por horário, no avatar e na pontuação de
   saúde.

2. **Gêmeo Digital.** Clique em "Personalizar" e mude nome, sexo, aparência e
   barba; o avatar atualiza na hora. O painel fica "vivo": os sinais vitais e o
   humor do gêmeo se atualizam sozinhos a cada poucos segundos. Mande uma
   mensagem no chat, como "posso fazer exercício hoje?", e veja a resposta
   considerar alergias e medicamentos, com o texto formatado (negrito, listas),
   não com asteriscos crus. A conversa fica salva ao trocar de aba e só zera no
   Ctrl+F5.

3. **Ele entende como você fala.** Ainda no chat, escreva algo coloquial, como
   "passei a noite me borrei toda e acho que tô fervendo". O sistema associa a
   linguagem informal aos sintomas clínicos (diarreia, febre) e os agrega ao
   perfil. Guarde isso: esses sintomas vão aparecer depois no Painel do Médico.

4. **Simular evento e voltar ao normal (mostre isto na banca).** Ainda na tela
   do gêmeo, clique em "Simular evento (demo)": os vitais disparam, o avatar
   fica vermelho e o alerta de teleconsulta aparece **na hora**, sem recarregar.
   A partir daí você tem duas saídas: esperar (a anomalia se dissipa sozinha e o
   quadro volta ao normal de forma gradual em alguns minutos) ou clicar em
   "Voltar ao normal", que normaliza os sinais instantaneamente. Esse botão é o
   "plano B" da apresentação: recupera o estado sem precisar reiniciar o
   servidor.

5. **Segurança clínica.** No chat, escreva algo como "estou com uma dor forte no
   peito". O sistema não tenta adivinhar nada: escala imediatamente para o SAMU
   192. Em sinais de sofrimento mental, o encaminhamento é para o CVV 188, com
   um aviso destacado em vermelho. É o guardrail determinístico em ação, antes
   da IA.

6. **Wearables.** Em "Parear", conecte dispositivos (Apple, Samsung, Xiaomi,
   Amazon, Garmin, Fitbit e até um ESP32 caseiro) e veja os sinais ao vivo.
   Todos os aparelhos leem do mesmo "estado do paciente" simulado no backend, e
   é nesse estado que o "Simular evento" injeta a anomalia, por isso o gêmeo e
   os wearables reagem juntos.

7. **Exames.** Abra um painel e clique em "Interpretar com IA" para a leitura em
   linguagem simples. Note as barras: ficam verdes quando normal e vermelhas
   quando o valor está alto. Você também pode enviar um PDF de exame (ele fica
   no seu dispositivo; a IA não lê o arquivo, ele serve para levar ao médico).

8. **Medicamentos.** Adicione um remédio que interage com os atuais (ex.:
   "Ibuprofeno" com quem usa Losartana). Antes de salvar, a IA mostra
   "analisando interações" e, se houver risco, um alerta para consultar o
   médico. Em "Biometria", mude peso/sintomas e veja a saúde do gêmeo recalcular.

9. **Consultas.** Se você vier do gêmeo em estado de atenção, o campo "Motivo"
   já chega preenchido com o resumo da IA e a especialidade sugerida: a máquina
   "passa o bastão" para o médico. Agende e confirme.

10. **Painel do Médico (a outra ponta da teleconsulta).** No Dashboard, clique
    em "Painel do Médico". É o **mesmo gêmeo**: o médico vê o avatar, os sinais
    vitais ao vivo, o perfil clínico e o **relato do paciente**, inclusive o que
    você escreveu de forma coloquial lá no passo 3. Clique em "Sugerir
    Prescrição com IA": o rascunho vem estruturado e coerente com o quadro
    (escolhe o medicamento pelo sintoma, respeita alergias e interações, em vez
    de receitar sempre a mesma coisa). Edite se quiser e clique em "Assinar e
    Enviar ao Paciente".

11. **A prescrição chega ao paciente.** Volte ao Dashboard: o aviso "Nova
    prescrição do seu médico" aparece na hora (entrega instantânea no mesmo
    navegador). Abra, veja os medicamentos e orientações em cartões, clique em
    "Baixar prescrição em PDF" e em "Marcar como lida". Nada disso é salvo em
    servidor central: a prescrição vive só na memória da sessão (Zero-Data
    Footprint) e o PDF é gerado no próprio dispositivo.

12. **Histórico.** Tudo o que você fez aparece aqui, numa linha do tempo que
    distingue claramente quem fez o quê: ações da IA (monitoramento e alertas) e
    ações médicas (consulta e prescrição validada). Baixe a prescrição ou o
    laudo em PDF.

## Detalhes que economizam recurso

As respostas da IA (análise e relatório) são guardadas por sessão e só são
geradas de novo quando os dados mudam. Enquanto o quadro é o mesmo, a aplicação
reaproveita o resultado e indica "em cache", evitando chamadas desnecessárias.
A atualização ao vivo do gêmeo lê apenas o estado dos sinais vitais, que é
calculado localmente e não consome a IA. A entrega da prescrição ao paciente
também não custa IA: é só uma checagem rápida do estado em memória.

## Ajustes rápidos (se quiser calibrar)

- Velocidade da recuperação automática da anomalia: constante `_REVERSION` em
  `backend/app/services/wearables.py` (menor = mais lenta).
- Frequência da atualização ao vivo do gêmeo: o intervalo (em ms) no
  `setInterval` de `frontend/assets/js/gemeo.js`.
- Vocabulário coloquial que o sistema entende: dicionário `SYMPTOM_PATTERNS` em
  `backend/app/services/clinical.py` (é onde "me borrei", "tô fervendo" etc.
  viram sintomas clínicos).

## Limites e próximos passos

Este é um protótipo acadêmico. Os wearables, exames e agendamentos são
simulados, e os dados do paciente são fictícios. Para um uso real seriam
necessários validação clínica com profissionais, conformidade com a LGPD e a
substituição das simulações por integrações reais com autenticação. O `SECURITY.md`
detalha as decisões de segurança e privacidade.
