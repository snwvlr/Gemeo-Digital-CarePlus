"""Raciocínio clínico determinístico (apoio à decisão / modo demo).

Este módulo é "puro" (depende apenas de re/unicodedata) para não criar ciclos
de importação. Ele concentra três responsabilidades:

  1. extract_symptoms(texto): lê o que o paciente escreveu (do jeito dele) e
     devolve uma lista de sintomas canônicos — para o painel do médico mostrar
     em "Sintomas" e para a prescrição ser coerente.
  2. suggest_prescription(...): monta um RASCUNHO de prescrição condizente com
     os sintomas, sinais vitais, alergias e condições — em vez de sugerir
     sempre o mesmo medicamento (ex.: paracetamol).
  3. clean_markdown / detecção de intenção: utilidades para limpar a saída da
     IA (asteriscos) e dar autonomia ao Gêmeo Digital (avisar médico/agendar).

Nada aqui substitui o julgamento clínico: é apoio e sempre rascunho.
"""
from __future__ import annotations

import re
import unicodedata


# --------------------------------------------------------------------------- #
# Normalização
# --------------------------------------------------------------------------- #
def _norm(texto: str) -> str:
    """minúsculas e sem acento (para casar padrões do jeito que o paciente digita)."""
    s = "".join(
        c for c in unicodedata.normalize("NFD", texto or "")
        if unicodedata.category(c) != "Mn"
    )
    return s.lower()


def _to_float(value, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


# --------------------------------------------------------------------------- #
# 1) Extração de sintomas (PT-BR, tolerante à escrita do paciente)
# --------------------------------------------------------------------------- #
# canônico -> padrões (já normalizados, sem acento)
SYMPTOM_PATTERNS: dict[str, list[str]] = {
    "febre": [r"febre", r"febril", r"\bfebr", r"temperatura alta", r"3[89]\s*graus", r"de febre",
              r"fervendo", r"queimando de febre", r"ardendo (de|em) febre", r"corpo quente"],
    "dor de cabeça": [r"dor de cabeca", r"dor na cabeca", r"cefaleia", r"enxaqueca",
                      r"cabeca.{0,12}(doend|latej|estour|explod|rach|martel)"],
    "dor no corpo": [r"dor no corpo", r"dores no corpo", r"dor muscular", r"dores musculares", r"mialgia", r"corpo doendo", r"corpo dolorido", r"dor nas costas", r"corpo moido", r"corpo quebrado"],
    "tosse": [r"tosse", r"tossindo", r"tossir", r"pigarro"],
    "dor de garganta": [r"dor de garganta", r"garganta inflamada", r"garganta doendo", r"garganta arranhando", r"dor (pra|para|ao) engolir"],
    "congestão nasal": [r"coriza", r"nariz escorrendo", r"nariz entupido", r"nariz tapado", r"nariz tampado", r"congestao nasal", r"espirr", r"rinite", r"catarro no nariz", r"\branho\b"],
    "falta de ar": [r"falta de ar", r"dispneia", r"sem folego", r"sem ar", r"dificuldade (para|de|pra) respirar", r"cansaco para respirar", r"nao consigo respirar", r"ofegante"],
    "náusea": [r"nausea", r"enjoo", r"enjoad", r"enjoei", r"vontade de vomitar", r"embrulho no estomago", r"estomago embrulhad", r"embrulhad"],
    "vômito": [r"vomit", r"botando para fora", r"botar para fora", r"botei tudo (pra|para) fora", r"boto tudo (pra|para) fora", r"coloquei (tudo )?(pra|para) fora", r"\bgolfei\b", r"\bgolfar\b"],
    "diarreia": [r"diarreia", r"diarreic", r"intestino solto", r"evacuacoes liquidas",
                 r"indo (muito )?(ao|no|pro|pra) banheiro", r"me caguei", r"me borrei",
                 r"\bborrei\b", r"\bcaguei\b", r"\bcagando\b", r"caganeira", r"\bcagueira\b",
                 r"caga mole", r"desarranjo", r"barriga solta", r"soltou o intestino"],
    "dor abdominal": [r"dor de barriga", r"dor abdominal", r"dor na barriga", r"colica",
                      r"dor no estomago", r"barriga doendo", r"barriga embrulhada", r"estomago doendo"],
    "tontura": [r"tontura", r"tont[oa]\b", r"vertigem", r"zonz[oa]", r"cabeca rodando", r"cabeca leve"],
    "cansaço": [r"cansaco", r"fadiga", r"cansad[oa]", r"exaust", r"sem energia", r"moleza",
                r"prostracao", r"indispost", r"acabad[oa]", r"\bmoid[oa]\b", r"sem pique",
                r"sem disposicao", r"arrebentad[oa]"],
    "calafrios": [r"calafrio", r"tremedeira", r"tremendo de frio", r"batendo o queixo"],
    "azia": [r"azia", r"queimacao no estomago", r"refluxo", r"queimacao no peito", r"ma digestao"],
    "insônia": [r"insonia", r"nao (consigo|estou conseguindo|to conseguindo) dormir", r"sem dormir", r"nao durmo", r"nao consigo pegar no sono"],
    "ansiedade": [r"ansiedade", r"ansios[oa]", r"\bpanico", r"angustia", r"crise de ansiedade", r"muito nervos"],
    "coceira/alergia de pele": [r"coceira", r"urticaria", r"placas vermelhas", r"alergia na pele", r"empol", r"manchas na pele", r"\bcocando\b", r"\bcocei\b"],
    "dor no peito": [r"dor no peito", r"aperto no peito", r"dor toracica"],
    "pressão alta": [r"pressao alta", r"pressao subiu", r"hipertens"],
    "incontinência urinária": [r"me mijei", r"\bmijei\b", r"nao (consigo|consegui) segurar (o |a )?(xixi|urina)",
                               r"escapou (o )?xixi", r"perda de urina", r"incontinencia"],
}


# Cues de negação: "sem febre", "não tenho tosse", "nega dispneia"…
_NEG_CUE = re.compile(
    r"(?:\bsem\b|\bnao\b|\bnega\b|\bnegou\b|\bnego\b|ausencia de|\bnenhum\b|\bnenhuma\b|livre de)\s+(?:\w+\s+){0,2}$"
)


def _negado(texto_norm: str, ini: int) -> bool:
    """True se a ocorrência em `ini` vem logo após uma negação (sem/não/nega…)."""
    return bool(_NEG_CUE.search(texto_norm[max(0, ini - 20):ini]))


def extract_symptoms(texto: str) -> list[str]:
    """Devolve os sintomas canônicos detectados no texto (sem duplicar).

    Ignora ocorrências negadas ("sem febre", "nega tosse") para não inventar
    sintomas que o paciente disse NÃO ter.
    """
    t = _norm(texto)
    found: list[str] = []
    for canon, pats in SYMPTOM_PATTERNS.items():
        achou = False
        for p in pats:
            for m in re.finditer(p, t):
                if not _negado(t, m.start()):
                    achou = True
                    break
            if achou:
                break
        if achou:
            found.append(canon)
    return found


# --------------------------------------------------------------------------- #
# 2) Sugestão de prescrição inteligente (rascunho)
# --------------------------------------------------------------------------- #
_ENV_ALLERGENS = (
    "poeira", "acaro", "lactose", "frutos do mar", "amendoim",
    "polen", "pelo de animal", "pelo de gato", "gluten",
)


def _allergic_to(allergies: list[str] | None, *terms: str) -> bool:
    a = _norm(", ".join(allergies or []))
    return any(t in a for t in terms)


def _nsaid_blocked(allergies, conditions, current_meds) -> bool:
    """Anti-inflamatório (AINE) contraindicado por alergia, condição ou interação."""
    if _allergic_to(allergies, "aine", "anti-inflam", "ibuprofeno", "diclofenaco",
                    "naproxeno", "nimesulida", "aas", "aspirina", "cetoprofeno"):
        return True
    c = _norm(", ".join(conditions or []))
    if any(x in c for x in ("hipertens", "renal", "rim", "ulcera", "gastrite", "insuficiencia cardiaca")):
        return True
    m = _norm(" | ".join(current_meds or []))
    if any(x in m for x in ("losartana", "enalapril", "captopril", "valsartana", "ramipril",
                            "aas", "varfarina", "clopidogrel")):
        return True
    return False


def _pick_analgesic(allergies, conditions, current_meds, prefer_nsaid: bool = False) -> dict | None:
    """Escolhe um analgésico/antitérmico respeitando alergias e contraindicações."""
    nsaid_ok = not _nsaid_blocked(allergies, conditions, current_meds)
    para_ok = not _allergic_to(allergies, "paracetamol", "acetaminofen")
    dipi_ok = not _allergic_to(allergies, "dipirona", "metamizol")

    nsaid = {"name": "Ibuprofeno 400 mg", "dosage": "1 comprimido",
             "frequency": "a cada 8 horas após as refeições", "duration": "3 dias"}
    para = {"name": "Paracetamol 750 mg", "dosage": "1 comprimido",
            "frequency": "a cada 6 horas se dor ou febre", "duration": "até 5 dias"}
    dipi = {"name": "Dipirona 1 g", "dosage": "1 comprimido (ou 40 gotas)",
            "frequency": "a cada 6 horas se dor ou febre", "duration": "até 5 dias"}

    if prefer_nsaid and nsaid_ok:
        return nsaid
    if para_ok:
        return para
    if dipi_ok:
        return dipi
    if nsaid_ok:
        return nsaid
    return None  # tudo contraindicado -> só orientação


def suggest_prescription(
    *,
    symptoms: list[str] | None,
    notes: str,
    vitals: dict | None,
    allergies: list[str] | None,
    conditions: list[str] | None,
    current_meds: list[str] | None,
) -> dict:
    """Monta um rascunho estruturado coerente com o quadro clínico.

    Regra de ouro: o medicamento só entra quando o sintoma justifica. Ou seja,
    rinite não vira paracetamol; náusea vira antiemético; e assim por diante.
    """
    notes = notes or ""
    syms = list(dict.fromkeys((symptoms or []) + extract_symptoms(notes)))
    vitals = vitals or {}
    temp = _to_float(vitals.get("body_temp"), 0.0)
    spo2 = _to_float(vitals.get("spo2"), 99.0)

    meds: list[dict] = []
    guidance: list[str] = []
    return_criteria: list[str] = []
    seen: set[str] = set()

    def add_med(m: dict | None) -> None:
        if not m:
            return
        key = _norm(m["name"]).split()[0]
        if key in seen:
            return
        seen.add(key)
        meds.append(m)

    has_fever = ("febre" in syms) or (temp >= 37.8)
    pain = any(s in syms for s in ("dor de cabeça", "dor no corpo", "dor de garganta"))

    # --- Febre / dor / mal-estar gripal -------------------------------------
    if has_fever or pain:
        add_med(_pick_analgesic(
            allergies, conditions, current_meds,
            prefer_nsaid=("dor de garganta" in syms and not has_fever),
        ))
        if has_fever:
            guidance.append("Hidratação reforçada (água, soro caseiro) e repouso enquanto houver febre.")
            return_criteria.append("Febre acima de 39,5 °C ou que não cede com a medicação por mais de 3 dias.")

    # --- Vias aéreas: congestão / alergia -----------------------------------
    if "congestão nasal" in syms or "coceira/alergia de pele" in syms:
        if not _allergic_to(allergies, "loratadina", "anti-histaminico", "antialergico"):
            add_med({"name": "Loratadina 10 mg", "dosage": "1 comprimido",
                     "frequency": "1x ao dia", "duration": "7 dias"})
        if "congestão nasal" in syms:
            add_med({"name": "Solução nasal de cloreto de sódio 0,9%", "dosage": "2–3 jatos por narina",
                     "frequency": "3–4x ao dia", "duration": "conforme necessidade"})
            guidance.append("Lavagem nasal com soro fisiológico; manter ambientes arejados e evitar poeira.")

    # --- Tosse ---------------------------------------------------------------
    if "tosse" in syms:
        if "seca" in _norm(notes):
            add_med({"name": "Dropropizina 30 mg/mL (xarope)", "dosage": "conforme bula (ex.: 10 mL)",
                     "frequency": "3x ao dia", "duration": "5 dias"})
        else:
            add_med({"name": "Ambroxol 30 mg/5 mL (xarope)", "dosage": "10 mL",
                     "frequency": "3x ao dia", "duration": "5 dias"})
        guidance.append("Aumente a ingestão de líquidos para fluidificar secreções; evite ar muito seco.")

    # --- Garganta ------------------------------------------------------------
    if "dor de garganta" in syms:
        guidance.append("Gargarejos com água morna e sal; pastilhas para garganta podem aliviar.")

    # --- Náusea / vômito -----------------------------------------------------
    if "náusea" in syms or "vômito" in syms:
        add_med({"name": "Metoclopramida 10 mg", "dosage": "1 comprimido",
                 "frequency": "até 3x ao dia, 30 min antes das refeições", "duration": "3 dias"})
        guidance.append("Alimentação leve e fracionada; reidratação em pequenos goles.")
        return_criteria.append("Vômitos persistentes (>24h), com sangue, ou sinais de desidratação.")

    # --- Diarreia ------------------------------------------------------------
    if "diarreia" in syms:
        add_med({"name": "Sais de reidratação oral (SRO)", "dosage": "1 sachê diluído em 1 L de água",
                 "frequency": "após cada evacuação", "duration": "enquanto durar o quadro"})
        guidance.append("Reidratação oral contínua; evite alimentos gordurosos e laticínios temporariamente.")
        return_criteria.append("Diarreia com sangue, febre alta ou sinais de desidratação (boca seca, urina escura).")

    # --- Dor abdominal / cólica ----------------------------------------------
    if "dor abdominal" in syms:
        add_med({"name": "Butilbrometo de escopolamina 10 mg", "dosage": "1 comprimido",
                 "frequency": "a cada 8 horas se cólica", "duration": "3 dias"})
        return_criteria.append("Dor abdominal intensa, contínua ou no quadrante inferior direito.")

    # --- Azia / refluxo ------------------------------------------------------
    if "azia" in syms:
        on_ppi = any(("omeprazol" in _norm(x) or "pantoprazol" in _norm(x)) for x in (current_meds or []))
        if not on_ppi:
            add_med({"name": "Omeprazol 20 mg", "dosage": "1 cápsula em jejum",
                     "frequency": "1x ao dia", "duration": "14 dias"})
        guidance.append("Evite frituras, café, refrigerante e deitar logo após as refeições.")

    # --- Tontura -------------------------------------------------------------
    if "tontura" in syms:
        guidance.append("Evite mudanças bruscas de posição; hidrate-se e verifique a pressão arterial.")
        return_criteria.append("Tontura com desmaio, fala enrolada, perda de força ou visão dupla.")

    # --- Ansiedade / insônia (a IA NÃO prescreve controlados) ----------------
    if "ansiedade" in syms or "insônia" in syms:
        guidance.append("Higiene do sono e técnicas de respiração; reduza cafeína à noite. Avaliar acompanhamento psicológico.")
        return_criteria.append("Crise de ansiedade incapacitante ou pensamentos de se machucar — buscar ajuda imediata (CVV 188).")

    # --- Cansaço isolado -----------------------------------------------------
    if "cansaço" in syms and not meds:
        guidance.append("Priorize sono adequado, hidratação e alimentação equilibrada; reavaliar se persistir.")

    # --- Red flags viram critério de retorno (NÃO se prescreve) --------------
    if "falta de ar" in syms or "dor no peito" in syms or spo2 < 94:
        return_criteria.insert(0, "Falta de ar, dor no peito ou saturação < 94% → procurar pronto-socorro imediatamente.")

    # --- Defaults coerentes --------------------------------------------------
    if not guidance:
        guidance.append("Repouso relativo, hidratação adequada e observação dos sintomas.")
    return_criteria.append("Reavaliar em teleconsulta em 48–72h se os sintomas não melhorarem ou piorarem.")

    # --- Aviso de alergia (ignora alérgenos ambientais/alimentares) ----------
    allergy_note = ""
    drug_allergies = [a for a in (allergies or []) if _norm(a) not in _ENV_ALLERGENS]
    if drug_allergies:
        allergy_note = (
            "Paciente alérgico a: " + ", ".join(drug_allergies)
            + ". Conferir princípios ativos e classes relacionadas antes de dispensar."
        )
    elif allergies:
        allergy_note = "Alergias registradas: " + ", ".join(allergies) + " (não medicamentosas)."

    return {
        "medications": meds[:4],
        "guidance": list(dict.fromkeys(guidance))[:5],
        "return_criteria": list(dict.fromkeys(return_criteria))[:5],
        "allergy_note": allergy_note,
    }


# --------------------------------------------------------------------------- #
# 3) Limpeza de markdown (asteriscos da IA) e detecção de intenção
# --------------------------------------------------------------------------- #
def clean_markdown(s: str) -> str:
    """Remove marcação markdown deixando texto limpo (sem ** ou * soltos)."""
    s = s or ""
    s = re.sub(r"(?m)^\s{0,3}#{1,6}\s*", "", s)      # cabeçalhos ###
    s = s.replace("**", "").replace("__", "")          # negrito
    s = re.sub(r"(?m)^(\s*)[\*\-]\s+", r"\1• ", s)     # listas -> •
    s = s.replace("*", "")                              # itálico/sobras
    s = re.sub(r"`{1,3}", "", s)                        # crases
    s = re.sub(r"\s*—\s*", ", ", s)                     # travessão (—) -> vírgula
    s = re.sub(r"[ \t]+\n", "\n", s)                    # espaços no fim da linha
    s = re.sub(r"\n{3,}", "\n\n", s)                    # quebras múltiplas
    return s.strip()


_APPT_PATTERNS = [
    r"marca(r)? (uma )?(tele)?consulta", r"agenda(r)? (uma )?(tele)?consulta", r"\bagendar\b",
    r"quero (falar com|ver|consultar) (um |uma )?medic", r"preciso (de |falar com )?(um |uma )?medic",
    r"teleconsulta", r"consulta com (o |um )?medic", r"chamar (o |um )?medico", r"quero (uma )?consulta",
]
_DISTRESS_PATTERNS = [
    r"nao (estou|to) bem", r"me sinto mal", r"passando mal", r"(estou|to) mal",
    r"piorei", r"(estou|to) doente", r"preocupad", r"com medo", r"nao melhorei", r"continuo mal",
]


def wants_appointment(texto: str) -> bool:
    t = _norm(texto)
    return any(re.search(p, t) for p in _APPT_PATTERNS)


def reports_distress(texto: str) -> bool:
    t = _norm(texto)
    return any(re.search(p, t) for p in _DISTRESS_PATTERNS)
