"""Motor de estado do Gêmeo Digital.

Traduz os sinais vitais (vindos dos wearables) e o perfil clínico do paciente
em um "estado" do gêmeo: pontuação de saúde, humor, cor e alertas. É aqui que
mora a regra central: se o paciente está mal segundo as métricas, o gêmeo
reflete isso.

Mantém também o perfil do paciente em memória (demonstração / sessão única).
"""
from __future__ import annotations

from ..schemas import PatientProfile, TwinState, VitalSigns


class TwinEngine:
    """Calcula o estado do gêmeo digital e guarda o perfil do paciente."""

    def __init__(self) -> None:
        self.randomize()

    def randomize(self) -> PatientProfile:
        """Gera um novo paciente de demonstração (nome, idade, perfil)."""
        import random
        # João aparece 2x (prioridade 2x). Inclui nomes dos integrantes + outros.
        names_pool = [
            "João", "João", "Isabela", "Isabelle", "Paulo", "Samy",
            "Lucas", "Marina", "Carlos", "Ana", "Pedro", "Beatriz", "Rafael", "Sofia",
        ]
        name = random.choice(names_pool)
        age = 20 if name == "João" else random.randint(18, 72)
        sex = "Masculino" if name in ("João", "Paulo", "Lucas", "Carlos", "Pedro", "Rafael") else "Feminino"

        meds_pool = [
            "Losartana 50mg (1x ao dia)", "Atorvastatina 20mg (à noite)",
            "Metformina 850mg (2x ao dia)", "Omeprazol 20mg (em jejum)",
            "Vitamina D 2000UI (1x ao dia)", "AAS 100mg (após almoço)",
            "Sertralina 50mg (pela manhã)", "Levotiroxina 75mcg (em jejum)",
            "Enalapril 10mg (2x ao dia)", "Sinvastatina 40mg (à noite)",
            "Clonazepam 0,5mg (à noite)", "Ibuprofeno 400mg (se dor)",
        ]
        allergies_pool = ["Dipirona", "Poeira", "Penicilina", "Lactose", "Frutos do mar", "Ácaro", "Amendoim"]
        conditions_pool = ["Pré-hipertensão", "Pré-diabetes", "Rinite alérgica", "Ansiedade leve", "Enxaqueca"]
        self.profile = PatientProfile(
            name=name,
            age=age,
            sex=sex,
            weight_kg=round(random.uniform(55, 95), 1),
            height_cm=random.randint(158, 190),
            medications=random.sample(meds_pool, k=random.randint(1, 3)),
            allergies=random.sample(allergies_pool, k=random.randint(1, 2)),
            conditions=random.sample(conditions_pool, k=random.randint(1, 2)),
        )
        return self.profile

    # ------------------------------ perfil -------------------------------- #
    def update_profile(self, **fields) -> PatientProfile:
        data = self.profile.model_dump()
        data.update({k: v for k, v in fields.items() if v is not None})
        self.profile = PatientProfile(**data)
        return self.profile

    # --------------------------- avaliação clínica ------------------------ #
    @staticmethod
    def _score_vitals(v: VitalSigns) -> tuple[int, list[str]]:
        """Pontua os vitais (0-100) e coleta alertas. Quanto maior, melhor."""
        score = 100
        alerts: list[str] = []

        if v.heart_rate > 110:
            score -= 22
            alerts.append(f"Frequência cardíaca elevada ({v.heart_rate} bpm).")
        elif v.heart_rate > 95:
            score -= 8
        elif v.heart_rate < 50:
            score -= 15
            alerts.append(f"Frequência cardíaca baixa ({v.heart_rate} bpm).")

        if v.spo2 < 92:
            score -= 25
            alerts.append(f"Saturação de oxigênio baixa (SpO₂ {v.spo2}%).")
        elif v.spo2 < 95:
            score -= 10

        if v.body_temp >= 38.0:
            score -= 20
            alerts.append(f"Temperatura corporal elevada ({v.body_temp} °C).")
        elif v.body_temp >= 37.5:
            score -= 8

        if v.respiratory_rate > 20:
            score -= 12
            alerts.append(f"Frequência respiratória elevada ({v.respiratory_rate} rpm).")

        if v.stress > 75:
            score -= 12
            alerts.append(f"Nível de estresse alto ({v.stress}/100).")
        elif v.stress > 60:
            score -= 5

        if v.hrv < 30:
            score -= 8
            alerts.append("Variabilidade cardíaca (HRV) baixa, sinal de fadiga.")

        if v.sleep_hours < 6:
            score -= 8
            alerts.append(f"Sono insuficiente ({v.sleep_hours} h na última noite).")

        return max(0, min(100, score)), alerts

    @staticmethod
    def emergency_assessment(vitals: VitalSigns, symptoms: list[str]) -> dict:
        """Avaliação determinística de gravidade (estilo guardrail/Manchester).

        Decide a conduta recomendada SEM depender do LLM:
          - pronto_socorro: red flag, orientar SAMU 192 / emergência.
          - telemedicina: estado de alerta, teleconsulta urgente.
          - observar: acompanhar e, se piorar, procurar ajuda.
        """
        red_flags: list[str] = []
        if vitals.spo2 < 90:
            red_flags.append(f"Saturação muito baixa (SpO₂ {vitals.spo2}%).")
        if vitals.heart_rate >= 140:
            red_flags.append(f"Taquicardia acentuada ({vitals.heart_rate} bpm).")
        if vitals.heart_rate <= 40:
            red_flags.append(f"Bradicardia acentuada ({vitals.heart_rate} bpm).")
        if vitals.body_temp >= 39.5:
            red_flags.append(f"Febre muito alta ({vitals.body_temp} °C).")
        if vitals.respiratory_rate >= 26:
            red_flags.append(f"Frequência respiratória muito alta ({vitals.respiratory_rate} rpm).")

        if red_flags:
            return {
                "level": "critico",
                "recommendation": "pronto_socorro",
                "title": "Procure atendimento de emergência",
                "red_flags": red_flags,
                "instruction": "Sinais compatíveis com emergência. Ligue para o SAMU 192 "
                               "ou vá ao pronto-socorro mais próximo agora.",
            }

        # Sem red flag, mas estado geral ruim -> telemedicina urgente.
        score, alerts = TwinEngine._score_vitals(vitals)
        if symptoms:
            score = max(0, score - 6 * len(symptoms))
        if score < 50:
            return {
                "level": "alerta",
                "recommendation": "telemedicina",
                "title": "Recomendamos uma teleconsulta agora",
                "red_flags": alerts,
                "instruction": "Seus sinais estão fora do padrão. Uma teleconsulta com um "
                               "médico da Care Plus é recomendada para avaliar a situação.",
            }
        return {
            "level": "ok",
            "recommendation": "observar",
            "title": "Sem sinais de emergência",
            "red_flags": [],
            "instruction": "Continue se monitorando. Se algo piorar, procure ajuda médica.",
        }

    def compute_state(self, vitals: VitalSigns) -> TwinState:
        """Gera o estado completo do gêmeo a partir dos vitais."""
        score, alerts = self._score_vitals(vitals)

        # Sintomas declarados pelo paciente também reduzem a pontuação.
        if self.profile.symptoms:
            score = max(0, score - 6 * len(self.profile.symptoms))
            alerts.append(
                "Sintomas relatados: " + ", ".join(self.profile.symptoms) + "."
            )

        if score >= 85:
            mood, color = "ótimo", "#10b981"      # emerald
            summary = "Seu gêmeo está se sentindo ótimo. Sinais vitais estáveis."
        elif score >= 70:
            mood, color = "bem", "#1152d4"         # primary
            summary = "Seu gêmeo está bem, com pequenas variações dentro do normal."
        elif score >= 50:
            mood, color = "atenção", "#f59e0b"     # amber
            summary = "Atenção: algumas métricas estão fora do ideal. Vale observar."
        else:
            mood, color = "alerta", "#ef4444"      # red
            summary = "Alerta: seu gêmeo não está bem. Recomenda-se contatar seu médico."

        return TwinState(
            mood=mood,
            health_score=score,
            summary=summary,
            color=color,
            vitals=vitals,
            alerts=alerts,
        )


# Instância única (singleton).
twin_engine = TwinEngine()
