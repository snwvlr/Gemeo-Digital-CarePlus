"""Guardrails clínicos (determinísticos), inspirados no BluaDiagnostics.

Rodam ANTES do LLM. Detectam red flags de emergência e ideação suicida por
padrões de texto, para forçar a escalada (SAMU 192 / CVV 188) sem depender do
modelo se comportar bem. Transparente e auditável.
"""
from __future__ import annotations

import re
import unicodedata


def _normalizar(texto: str) -> str:
    sem_acento = "".join(
        c for c in unicodedata.normalize("NFD", texto or "") if unicodedata.category(c) != "Mn"
    )
    return sem_acento.lower()


PADROES_SAUDE_MENTAL = [
    # Autolesão
    r"me machucar", r"me cortar", r"me ferir",
    # "tirar a/minha (própria) vida"
    r"tirar (a |minha )*(propria )?vida",
    # "acabar com tudo / com a minha vida / comigo"
    r"acabar com (tudo|a (minha )?vida|comigo)",
    # "dar/pôr um fim a/na minha vida (ao sofrimento, etc.)"
    r"(dar|por) (um )?fim (a|na|em|aos) ?(minha |meu |meus )?(vida|sofrimento|tudo|dias)",
    # "não quero/aguento/consigo mais viver / continuar"
    r"(nao|num) (quero|aguento|consigo|vou aguentar) (mais )?(viver|vivendo|essa vida|continuar)",
    r"cansei de viver", r"cansad. de viver", r"nao aguento mais essa vida",
    # Querer morrer / estar morto
    r"me matar", r"(quero|queria|vou) (me )?(matar|morrer)", r"queria (estar )?mort",
    r"(melhor|seria melhor) (eu )?(estar )?mort", r"queria (nunca|nao) ter nascido",
    # Métodos
    r"me jogar", r"me atirar", r"me enforcar", r"me afogar",
    r"pular (da|do|de) (ponte|predio|janela|viaduto|laje|alto|telhado)",
    r"tomar (todos os |um monte de )?(remedios|comprimidos)", r"overdose",
    # Ideação genérica
    r"suicid", r"atentar (contra|a) ?(a )?(minha )?(propria )?vida",
    r"sumir (de vez|do mundo|para sempre|dessa vida)",
    r"nao vejo (mais )?(sentido|motivo|razao)", r"sem (sentido|razao) (de|para) viver",
    r"desistir (de tudo|de viver|da vida)", r"nao vale a pena (viver|continuar)",
]

PADROES_RED_FLAG = [
    r"dor.{0,15}peito", r"dor.{0,15}torac", r"aperto.{0,15}peito",
    r"falta de ar", r"nao consigo respirar", r"dificuldade.{0,15}respirar",
    r"perda.{0,15}forca", r"sem forca.{0,15}(braco|perna|lado)",
    r"fala enrolada", r"boca torta", r"desmai", r"convuls",
    r"sangramento.{0,15}(intenso|abundante|nao para)",
    r"pior dor de cabeca da vida", r"labios.{0,10}roxo", r"cianos",
    r"incha.{0,15}(boca|garganta|lingua)", r"reacao alergica grave",
]


def checar_red_flag(texto: str) -> dict:
    """Retorna {detectado, tipo, termo}. tipo ∈ {saude_mental, emergencia}."""
    t = _normalizar(texto)
    for p in PADROES_SAUDE_MENTAL:
        if re.search(p, t):
            return {"detectado": True, "tipo": "saude_mental", "termo": p}
    for p in PADROES_RED_FLAG:
        if re.search(p, t):
            return {"detectado": True, "tipo": "emergencia", "termo": p}
    return {"detectado": False, "tipo": None, "termo": None}


def resposta_escalada(tipo: str) -> str:
    """Mensagem de escalada determinística (não passa pelo LLM)."""
    if tipo == "saude_mental":
        return (
            "Sinto muito que você esteja passando por isso, e fico feliz que tenha "
            "falado comigo. Você não está sozinho. Por favor, ligue agora para o CVV "
            "no número 188 (ligação gratuita, 24h) ou acesse cvv.org.br. Se houver "
            "risco imediato, ligue para o SAMU 192. Quero que você fique em segurança."
        )
    return (
        "Esses sinais podem indicar uma emergência. NÃO espere: ligue agora para o "
        "SAMU 192 ou vá ao pronto-socorro mais próximo. Se possível, fique perto de "
        "alguém. Não sou capaz de diagnosticar, mas sua segurança vem primeiro."
    )
