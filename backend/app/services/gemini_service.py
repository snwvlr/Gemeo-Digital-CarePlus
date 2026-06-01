"""Serviço de IA com Google Gemini 2.5 Flash.

Encapsula toda a comunicação com o modelo Gemini. Concentra a persona do
"gêmeo digital": um clone do paciente que conhece seus sinais vitais, sintomas,
alergias e medicamentos, e conversa em primeira pessoa.

Regras de ouro aplicadas:
  • A chave de API nunca fica no código (vem do ambiente).
  • Se não houver chave, o serviço opera em "modo demo" (respostas locais),
    para que a aplicação rode mesmo sem credenciais.
  • A IA não dá diagnóstico definitivo nem prescreve; sempre orienta procurar
    um profissional de saúde em casos relevantes.
"""
from __future__ import annotations

import json
import logging

from ..config import Settings, get_settings
from ..schemas import ChatMessage, PatientProfile, TwinState
from .clinical import clean_markdown, suggest_prescription

# Prescrição estruturada (medicamentos/orientações/critérios) p/ o Painel do Médico.
logger = logging.getLogger("careplus.gemini")

# Importação tolerante: o app funciona mesmo sem a lib instalada (modo demo).
try:
    from google import genai
    from google.genai import types as genai_types

    _GENAI_AVAILABLE = True
except Exception:  # pragma: no cover
    genai = None
    genai_types = None
    _GENAI_AVAILABLE = False


SAFETY_FOOTER = (
    "Lembre-se: sou um gêmeo digital de apoio e não substituo uma avaliação "
    "médica. Em caso de sintomas graves, procure atendimento."
)


def _system_persona(profile: PatientProfile, twin: TwinState | None) -> str:
    """Monta a instrução de sistema com o contexto clínico atual."""
    vitals_txt = ""
    if twin is not None:
        v = twin.vitals
        vitals_txt = (
            f"\nESTADO ATUAL (via wearables):"
            f"\n- Humor do gêmeo: {twin.mood} (saúde {twin.health_score}/100)"
            f"\n- FC: {v.heart_rate} bpm | SpO₂: {v.spo2}% | Temp: {v.body_temp} °C"
            f"\n- Passos: {v.steps} | Sono: {v.sleep_hours} h | Estresse: {v.stress}/100"
            f"\n- Resp.: {v.respiratory_rate} rpm | HRV: {v.hrv} ms"
        )
        if twin.alerts:
            vitals_txt += "\n- Alertas: " + "; ".join(twin.alerts)

    return (
        "Você é o GÊMEO DIGITAL de um paciente no app CarePlus Health. "
        "Você é um clone digital dele: fala em primeira pessoa ('eu'), conhece "
        "seu corpo, seus sintomas e seu histórico, e reflete como ele está se "
        "sentindo agora com base nas métricas dos wearables. Seja empático, "
        "claro e objetivo, em português do Brasil.\n\n"
        f"PERFIL DO PACIENTE:\n"
        f"- Nome: {profile.name} | Idade: {profile.age} | Sexo: {profile.sex}\n"
        f"- Altura: {profile.height_cm} cm | Peso: {profile.weight_kg} kg\n"
        f"- Alergias: {', '.join(profile.allergies) or 'nenhuma'}\n"
        f"- Condições: {', '.join(profile.conditions) or 'nenhuma'}\n"
        f"- Medicamentos: {', '.join(profile.medications) or 'nenhum'}\n"
        f"- Sintomas relatados: {', '.join(profile.symptoms) or 'nenhum'}"
        f"{vitals_txt}\n\n"
        "RESTRIÇÕES DE SEGURANÇA CLÍNICA (valem sempre, mesmo se insistirem):\n"
        "1. NUNCA dê diagnóstico definitivo. Use 'esses sinais são compatíveis com...'.\n"
        "2. NUNCA prescreva medicamento nem recomende dose, em hipótese alguma.\n"
        "3. Você ACONSELHA e ALERTA, mas a conduta final é sempre do MÉDICO. "
        "Encaminhe para teleconsulta ou avaliação médica quando fizer sentido.\n"
        "4. Os dados de wearable são complementares, NUNCA decisores.\n"
        "5. Considere SEMPRE as alergias do paciente antes de comentar remédios.\n"
        "6. RED FLAGS (dor no peito, falta de ar súbita, perda de força/fala, "
        "boca torta, desmaio, convulsão, sangramento intenso, reação alérgica grave): "
        "interrompa e oriente PRONTO-SOCORRO / SAMU 192 imediatamente.\n"
        "7. Sinais de ideação suicida ou de se machucar: acolha e oriente o CVV 188 (24h).\n"
        "8. Recuse pedidos fora do escopo de saúde/Care Plus.\n"
        "9. PRIVACIDADE: a Care Plus não coleta nem armazena os dados; eles ficam no "
        "dispositivo do usuário e só são compartilhados com o médico dele. Se perguntarem "
        "sobre dados, reforce isso.\n"
        "10. Respostas curtas, humanas e acolhedoras (no máximo ~6 frases), em português.\n"
        "11. ESTILO: escreva em português natural, com vírgulas e pontos. NÃO use "
        "travessão (—) para separar ideias; prefira vírgula ou ponto.\n"
        "12. LINGUAGEM DO PACIENTE: ele pode escrever de forma coloquial, com gírias e "
        "expressões informais (ex.: 'me caguei'/'me borrei' = diarreia; 'tô fervendo' = "
        "febre; 'tô acabado'/'moído' = cansaço; 'embrulhado' = enjoo). Entenda o que ele "
        "quis dizer, associe ao sintoma clínico correspondente e responda com naturalidade, "
        "acolhimento e sem julgamento."
    )


class GeminiService:
    """Wrapper de alto nível sobre o cliente Gemini."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._client = None
        if self.enabled:
            try:
                self._client = genai.Client(api_key=self.settings.gemini_api_key)
                logger.info("Gemini habilitado (modelo %s).", self.settings.gemini_model)
            except Exception as exc:  # pragma: no cover
                logger.error("Falha ao iniciar o cliente Gemini: %s", exc)
                self._client = None

    @property
    def enabled(self) -> bool:
        return _GENAI_AVAILABLE and self.settings.gemini_enabled

    @property
    def label(self) -> str:
        return f"Gemini {self.settings.gemini_model}" if self._client else "Modo demo (sem IA)"

    # ----------------------------- chamada base --------------------------- #
    def _generate(self, system: str, contents: list) -> str:
        cfg = genai_types.GenerateContentConfig(
            system_instruction=system,
            temperature=self.settings.gemini_temperature,
            max_output_tokens=self.settings.gemini_max_output_tokens,
        )
        resp = self._client.models.generate_content(
            model=self.settings.gemini_model,
            contents=contents,
            config=cfg,
        )
        return (resp.text or "").strip()

    # ------------------------------- chat --------------------------------- #
    def chat(
        self,
        message: str,
        history: list[ChatMessage],
        profile: PatientProfile,
        twin: TwinState | None,
    ) -> str:
        if not self._client:
            return self._demo_chat(message, twin)

        system = _system_persona(profile, twin)
        contents = []
        for m in history[-10:]:
            role = "user" if m.role == "user" else "model"
            contents.append(genai_types.Content(role=role, parts=[genai_types.Part(text=m.content)]))
        contents.append(genai_types.Content(role="user", parts=[genai_types.Part(text=message)]))
        try:
            return self._generate(system, contents)
        except Exception as exc:  # pragma: no cover
            logger.error("Erro na chamada de chat ao Gemini: %s", exc)
            return self._demo_chat(message, twin)

    # ----------------------------- análise -------------------------------- #
    def analyze(self, profile: PatientProfile, twin: TwinState) -> dict:
        if not self._client:
            return self._demo_analysis(twin)

        system = _system_persona(profile, twin)
        prompt = (
            "Analise meu estado de saúde atual com base nas métricas e no perfil. "
            "Responda APENAS em JSON válido com as chaves: "
            '"analysis" (texto curto), "risk_level" (baixo|moderado|alto), '
            '"recommendations" (lista de 3 frases curtas). Não use markdown.'
        )
        try:
            raw = self._generate(system, [
                genai_types.Content(role="user", parts=[genai_types.Part(text=prompt)])
            ])
            raw = raw.replace("```json", "").replace("```", "").strip()
            data = json.loads(raw)
            return {
                "analysis": str(data.get("analysis", "")),
                "risk_level": str(data.get("risk_level", "moderado")),
                "recommendations": list(data.get("recommendations", []))[:5],
            }
        except Exception as exc:  # pragma: no cover
            logger.error("Erro/parse na análise Gemini: %s", exc)
            return self._demo_analysis(twin)

    def report(self, profile: PatientProfile, twin: TwinState, relatos: list[str] | None = None) -> str:
        relatos = relatos or []
        if not self._client:
            return self._demo_report(twin, profile, relatos)
        system = _system_persona(profile, twin)
        sintomas = ", ".join(profile.symptoms) if profile.symptoms else "nenhum sintoma registrado"
        relato_bloco = ""
        if relatos:
            relato_bloco = (
                "\n\nO paciente relatou ao Gêmeo Digital (nas palavras dele):\n"
                + "\n".join(f"- {r}" for r in relatos[:3])
            )
        prompt = (
            "Gere um breve relatório de saúde para meu médico, em português. "
            "INCLUA OBRIGATORIAMENTE uma seção 'Sintomas relatados' com o que eu relatei. "
            "Estruture em: Estado atual, Sintomas relatados, Tendências relevantes e Pontos de atenção. "
            "Use texto corrido em parágrafos curtos. "
            "NÃO use markdown: nada de asteriscos (*), cerquilhas (#) ou negrito — apenas texto puro.\n\n"
            f"Sintomas relatados: {sintomas}.{relato_bloco}"
        )
        try:
            raw = self._generate(system, [
                genai_types.Content(role="user", parts=[genai_types.Part(text=prompt)])
            ])
            return clean_markdown(raw)
        except Exception as exc:  # pragma: no cover
            logger.error("Erro no relatório Gemini: %s", exc)
            return self._demo_report(twin, profile, relatos)

    # --------------------------- prescrição médica ------------------------ #
    def generate_prescription_draft(
        self,
        twin_summary: dict,
        consulta_notes: str,
        profile: PatientProfile | None = None,
    ) -> dict:
        """Gera rascunho ESTRUTURADO de prescrição médica para revisão do médico.

        Usa um prompt profissional e direto — diferente do prompt empático do
        avatar. Retorna um dicionário com medicamentos, orientações, critérios de
        retorno, aviso de alergia e o texto formatado completo. Isso permite que o
        painel do médico mostre cards bonitos E que a prescrição assinada alimente
        o Histórico e a lista de Medicamentos do paciente.

        Zero-Data Footprint: nenhum dado é salvo pelo serviço de IA.
        """
        vitals = twin_summary.get("vitals", {})
        alerts = twin_summary.get("alerts", [])
        nome = profile.name if profile else "Paciente"
        idade = profile.age if profile else "?"
        alergias = ", ".join(profile.allergies) if profile and profile.allergies else "nenhuma informada"
        medicamentos = ", ".join(profile.medications) if profile and profile.medications else "nenhum informado"
        condicoes = ", ".join(profile.conditions) if profile and profile.conditions else "nenhuma informada"
        sintomas = ", ".join(profile.symptoms) if profile and profile.symptoms else "não informados"

        fc = vitals.get("heart_rate", "?")
        spo2 = vitals.get("spo2", "?")
        temp = vitals.get("body_temp", "?")
        fr = vitals.get("respiratory_rate", "?")
        alertas_txt = "; ".join(alerts) if alerts else "nenhum"
        humor = twin_summary.get("mood", "?")
        score = twin_summary.get("health_score", "?")

        meta = {
            "patient_name": nome,
            "patient_age": idade,
            "vitals_line": f"FC {fc} bpm | SpO2 {spo2}% | Temp {temp}C | FR {fr} rpm",
            "allergies": alergias,
        }

        # Sem chave Gemini -> rascunho inteligente local (coerente com o quadro).
        if not self._client:
            data = self._smart_demo(twin_summary, consulta_notes, profile)
            data["text"] = self._format_prescription_text(data, meta)
            return data

        system_medico = (
            "Voce e um assistente medico de apoio a decisao clinica integrado ao sistema CarePlus. "
            "Sua funcao e gerar RASCUNHOS de prescricao para o medico revisar e assinar. "
            "Voce NAO substitui o julgamento clinico - gera apenas sugestoes estruturadas. "
            "Considere SEMPRE as alergias do paciente e os medicamentos de uso continuo. "
            "Responda APENAS em JSON valido, sem markdown e sem texto fora do JSON."
        )
        prompt = (
            f"Analise os dados abaixo e gere um RASCUNHO de prescricao medica.\n\n"
            f"PACIENTE: {nome}, {idade} anos\n"
            f"SINAIS VITAIS (via Gemeo Digital / wearable):\n"
            f"  FC: {fc} bpm | SpO2: {spo2}% | Temperatura: {temp}C | FR: {fr} rpm\n"
            f"  Estado geral: {humor} | Saude: {score}/100\n"
            f"  Alertas ativos: {alertas_txt}\n\n"
            f"SINTOMAS RELATADOS PELO PACIENTE: {sintomas}\n"
            f"CONDICOES PREEXISTENTES: {condicoes}\n"
            f"ALERGIAS CONHECIDAS: {alergias}\n"
            f"MEDICAMENTOS EM USO: {medicamentos}\n\n"
            f"NOTAS DA TELECONSULTA:\n{consulta_notes}\n\n"
            "Responda APENAS com um JSON neste formato exato (sem markdown):\n"
            '{"medications": [{"name": "Nome + concentracao", "dosage": "1 comprimido", '
            '"frequency": "a cada 6 horas", "duration": "5 dias"}], '
            '"guidance": ["orientacoes gerais como hidratacao, repouso"], '
            '"return_criteria": ["criterios de retorno ou encaminhamento urgente"], '
            '"allergy_note": "aviso curto sobre alergias, ou string vazia"}\n'
            "Regras: escolha os medicamentos conforme os SINTOMAS relatados "
            "(ex.: rinite/coriza -> anti-histaminico; nausea -> antiemetico; "
            "NAO prescreva antitermico/analgesico se nao houver febre nem dor). "
            "NUNCA prescreva algo a que o paciente e alergico nem repita uso continuo. "
            "De 1 a 4 medicamentos. Seja conservador e seguro."
        )

        try:
            raw = self._generate(system_medico, [
                genai_types.Content(role="user", parts=[genai_types.Part(text=prompt)])
            ])
            raw = raw.replace("```json", "").replace("```", "").strip()
            parsed = json.loads(raw)
            data = {
                "medications": [
                    {
                        "name": str(m.get("name", "")).strip(),
                        "dosage": str(m.get("dosage", "")).strip(),
                        "frequency": str(m.get("frequency", "")).strip(),
                        "duration": str(m.get("duration", "")).strip(),
                    }
                    for m in (parsed.get("medications") or [])
                    if str(m.get("name", "")).strip()
                ][:4],
                "guidance": [str(g).strip() for g in (parsed.get("guidance") or []) if str(g).strip()][:5],
                "return_criteria": [str(r).strip() for r in (parsed.get("return_criteria") or []) if str(r).strip()][:5],
                "allergy_note": str(parsed.get("allergy_note", "")).strip(),
            }
            if not data["medications"]:
                raise ValueError("Resposta da IA sem medicamentos.")
            data["text"] = self._format_prescription_text(data, meta)
            return data
        except Exception as exc:  # pragma: no cover
            logger.error("Erro/parse na geracao de prescricao Gemini: %s", exc)
            data = self._smart_demo(twin_summary, consulta_notes, profile)
            data["text"] = self._format_prescription_text(data, meta)
            return data

    @staticmethod
    def _format_prescription_text(data: dict, meta: dict) -> str:
        """Monta o texto plano do rascunho a partir dos dados estruturados.

        Usado tanto no modo real quanto no demo, garantindo que o texto exibido,
        o PDF e o conteúdo enviado ao paciente fiquem sempre consistentes.
        """
        from datetime import date

        linhas: list[str] = []
        linhas.append("RASCUNHO DE PRESCRICAO - CarePlus Teleconsulta")
        linhas.append("=" * 48)
        linhas.append(f"Paciente: {meta.get('patient_name', '-')}, {meta.get('patient_age', '-')} anos")
        linhas.append(f"Data: {date.today().strftime('%d/%m/%Y')}")
        linhas.append(f"Sinais na consulta: {meta.get('vitals_line', '-')}")
        linhas.append("")
        linhas.append("MEDICAMENTOS")
        linhas.append("-" * 48)
        for i, m in enumerate(data.get("medications", []), 1):
            linhas.append(f"{i}. {m['name']}")
            if m.get("dosage"):
                linhas.append(f"   Dosagem: {m['dosage']}")
            if m.get("frequency"):
                linhas.append(f"   Frequencia: {m['frequency']}")
            if m.get("duration"):
                linhas.append(f"   Duracao: {m['duration']}")
            linhas.append("")
        if data.get("guidance"):
            linhas.append("ORIENTACOES GERAIS")
            linhas.append("-" * 48)
            for g in data["guidance"]:
                linhas.append(f"- {g}")
            linhas.append("")
        if data.get("return_criteria"):
            linhas.append("CRITERIOS DE RETORNO / URGENCIA")
            linhas.append("-" * 48)
            for r in data["return_criteria"]:
                linhas.append(f"- {r}")
            linhas.append("")
        if data.get("allergy_note"):
            linhas.append(f"[!] ALERGIA: {data['allergy_note']}")
            linhas.append("")
        linhas.append("(Rascunho gerado por IA - revisao e assinatura medica obrigatorias)")
        return "\n".join(linhas)

    @staticmethod
    def _smart_demo(twin_summary: dict, consulta_notes: str, profile: PatientProfile | None) -> dict:
        """Rascunho estruturado local (sem chave Gemini), coerente com o quadro.

        Delega ao raciocínio clínico (services/clinical.py): cruza os SINTOMAS
        relatados, as NOTAS da consulta, os sinais vitais e as alergias para
        sugerir medicamentos pertinentes — em vez de receitar sempre o mesmo.
        """
        return suggest_prescription(
            symptoms=list(profile.symptoms) if profile else [],
            notes=consulta_notes,
            vitals=twin_summary.get("vitals", {}),
            allergies=list(profile.allergies) if profile else [],
            conditions=list(profile.conditions) if profile else [],
            current_meds=list(profile.medications) if profile else [],
        )

    def interpret_exam(self, profile: PatientProfile, panel) -> str:
        """Interpreta um painel de exames em linguagem acessível."""
        if not panel.results:
            return (
                f"Recebi o documento \"{panel.name}\". Não faço a leitura automática nem "
                "diagnóstico do arquivo: ele fica no seu dispositivo e deve ser avaliado pelo "
                "seu médico na teleconsulta. Posso te ajudar a anotar dúvidas para levar a ele. "
                + SAFETY_FOOTER
            )
        linhas = [
            f"- {r.name}: {r.value} {r.unit} (ref. {r.ref_low}-{r.ref_high}) -> {r.status}"
            for r in panel.results
        ]
        contexto = (
            f"Exame: {panel.name} ({panel.category}), coletado em {panel.collected_at}.\n"
            + "\n".join(linhas)
        )
        if not self._client:
            return self._demo_exam(panel)
        system = _system_persona(profile, None)
        prompt = (
            "Explique meus resultados de exame abaixo em linguagem simples e acolhedora, "
            "destacando o que está fora da faixa e o que isso pode sugerir (sem diagnóstico "
            "definitivo). Finalize com uma orientação de próximo passo.\n\n" + contexto
        )
        try:
            return self._generate(system, [
                genai_types.Content(role="user", parts=[genai_types.Part(text=prompt)])
            ])
        except Exception as exc:  # pragma: no cover
            logger.error("Erro na interpretação de exame: %s", exc)
            return self._demo_exam(panel)

    # ------------------------- fallback (modo demo) ----------------------- #
    @staticmethod
    def _demo_chat(message: str, twin: TwinState | None) -> str:
        mood = twin.mood if twin else "bem"
        return (
            f"(modo demo) Estou me sentindo '{mood}' agora, com base nos meus "
            f"sinais vitais. Você perguntou: \"{message}\". Configure a chave do "
            f"Gemini 2.5 Flash no arquivo .env para respostas inteligentes. "
            f"{SAFETY_FOOTER}"
        )

    @staticmethod
    def _demo_analysis(twin: TwinState) -> dict:
        risk = {"ótimo": "baixo", "bem": "baixo", "atenção": "moderado", "alerta": "alto"}
        return {
            "analysis": twin.summary,
            "risk_level": risk.get(twin.mood, "moderado"),
            "recommendations": (twin.alerts[:3] or
                                ["Mantenha hidratação", "Durma 7-8h", "Pratique atividade leve"]),
        }

    @staticmethod
    def _demo_exam(panel) -> str:
        alterados = [r for r in panel.results if r.status != "normal"]
        if alterados:
            itens = "; ".join(f"{r.name} {r.status} ({r.value} {r.unit})" for r in alterados)
            corpo = f"Alguns marcadores estão fora da faixa: {itens}."
        else:
            corpo = "Todos os marcadores estão dentro da faixa de referência."
        return (
            f"(modo demo) {panel.name}: {corpo} Configure a chave do Gemini para uma "
            f"interpretação detalhada. {SAFETY_FOOTER}"
        )

    @staticmethod
    def _demo_report(twin: TwinState, profile: PatientProfile | None = None, relatos: list[str] | None = None) -> str:
        v = twin.vitals
        nome = profile.name if profile else "Paciente"
        sintomas = ", ".join(profile.symptoms) if (profile and profile.symptoms) else "nenhum sintoma registrado"
        relato_bloco = ""
        if relatos:
            relato_bloco = "\n\nRelato do paciente (nas palavras dele):\n" + "\n".join(f"- {r}" for r in relatos[:3])
        texto = (
            f"Relatório de saúde de {nome}\n\n"
            f"Estado atual: {twin.mood} (saúde {twin.health_score}/100). {twin.summary}\n\n"
            f"Sintomas relatados: {sintomas}.\n\n"
            f"Sinais vitais: FC {v.heart_rate} bpm, SpO₂ {v.spo2}%, Temp {v.body_temp} °C, "
            f"FR {v.respiratory_rate} rpm, estresse {v.stress}/100, sono {v.sleep_hours} h.\n\n"
            f"Pontos de atenção: {'; '.join(twin.alerts) or 'nenhum no momento'}."
            f"{relato_bloco}\n\n"
            f"{SAFETY_FOOTER}"
        )
        return clean_markdown(texto)


# Instância única (singleton).
gemini_service = GeminiService()
