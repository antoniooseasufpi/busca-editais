from __future__ import annotations

import json
import re
from datetime import date, datetime
from typing import Any

import requests

from radar_agro.config.settings import load_llm_config

DATE_PATTERNS = [
    r"(?:inscri[cç][oõ]es?|submiss[oõ]es?|propostas?|prazo|deadline|apply by|applications close|encerramento)\s+(?:abertas?\s+)?(?:at[eé]|ate|until|by|em)?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
    r"(?:at[eé]|ate|until|by)\s+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
    r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b",
]

MONTHS_PT = {
    "janeiro": 1,
    "fevereiro": 2,
    "março": 3,
    "marco": 3,
    "abril": 4,
    "maio": 5,
    "junho": 6,
    "julho": 7,
    "agosto": 8,
    "setembro": 9,
    "outubro": 10,
    "novembro": 11,
    "dezembro": 12,
}

TECH_TERMS = {
    "inteligência artificial": 2,
    "inteligencia artificial": 2,
    "machine learning": 2,
    "deep learning": 2,
    "visão computacional": 2,
    "visao computacional": 2,
    "processamento de imagens": 2,
    "sensoriamento remoto": 2,
    "satélite": 2,
    "satelite": 2,
    "satélites": 2,
    "satelites": 2,
    "drone": 2,
    "drones": 2,
    "pecuária": 2,
    "pecuaria": 2,
    "agricultura digital": 2,
    "agtech": 2,
}

OPPORTUNITY_TERMS = {
    "inscrições abertas": 3,
    "inscricoes abertas": 3,
    "chamada aberta": 3,
    "edital aberto": 3,
    "chamada pública": 2,
    "chamada publica": 2,
    "inovação aberta": 2,
    "inovacao aberta": 2,
    "open innovation": 2,
    "challenge": 2,
    "desafio tecnológico": 2,
    "desafio tecnologico": 2,
    "startup challenge": 2,
    "poc": 2,
    "prova de conceito": 2,
    "venture client": 2,
    "corporate venture": 2,
    "subvenção": 2,
    "subvencao": 2,
    "fomento": 2,
    "contratação": 2,
    "contratacao": 2,
    "projeto piloto": 2,
    "programa de aceleração": 2,
    "programa de aceleracao": 2,
    "rfp": 2,
    "request for proposal": 2,
}

DISCARD_TERMS = [
    "curso",
    "pós-graduação",
    "pos-graduacao",
    "mestrado",
    "doutorado",
    "seleção de professor",
    "selecao de professor",
    "processo seletivo acadêmico",
    "processo seletivo academico",
    "evento",
    "congresso",
    "feira",
    "webinar",
    "palestra",
    "notícia",
    "noticia",
    "relatório de mercado",
    "relatorio de mercado",
    "matéria jornalística",
    "materia jornalistica",
    "previsão de mercado",
    "previsao de mercado",
]

ENDED_TERMS = [
    "encerrado",
    "encerrada",
    "inscrições encerradas",
    "inscricoes encerradas",
    "prazo encerrado",
]


def classify_opportunity(raw: dict[str, Any]) -> dict[str, Any]:
    """Classifica com Ollama local e valida com regras deterministicas."""

    rules_result = _classify_with_rules(raw)
    if _should_skip_ollama(raw, rules_result):
        return _normalize_result(raw, rules_result, classified_by="heuristica")

    classified = _classify_with_ollama(raw)
    if classified:
        return _normalize_result(raw, classified, classified_by="ollama")
    return _normalize_result(raw, rules_result, classified_by="heuristica")


def _classify_with_ollama(raw: dict[str, Any]) -> dict[str, Any] | None:
    config = load_llm_config()
    if config.get("provider") != "ollama":
        return None

    try:
        response = requests.post(
            f"{config['host'].rstrip('/')}/api/chat",
            json={
                "model": config["model"],
                "stream": False,
                "format": "json",
                "think": False,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Voce classifica oportunidades comerciais para uma empresa de IA, "
                            "visao computacional, sensoriamento remoto, drones e agro. "
                            "Retorne exclusivamente JSON valido, sem markdown, sem explicacoes "
                            "e sem blocos de codigo."
                        ),
                    },
                    {"role": "user", "content": _build_prompt(raw)},
                ],
                "options": {
                    "temperature": 0.0,
                    "num_ctx": 2048,
                    "num_predict": 450,
                },
            },
            timeout=float(config.get("timeout_seconds", 60)),
        )
        response.raise_for_status()
        payload = response.json()
        content = payload.get("message", {}).get("content", "")
        return json.loads(_extract_json(content))
    except (requests.RequestException, json.JSONDecodeError, KeyError, TypeError):
        return None


def _should_skip_ollama(raw: dict[str, Any], rules_result: dict[str, Any]) -> bool:
    text = _combined_text(raw)
    if rules_result["status_chamada"] in {"NAO_E_CHAMADA", "ENCERRADA"}:
        return True
    if rules_result["potencial_negocio"] == "DESCARTAR":
        return True
    if not rules_result.get("prazo_inscricao") and rules_result["score_aderencia"] < 5:
        return True
    if _has_any(text, DISCARD_TERMS) and not _has_any(text, ["edital aberto", "chamada aberta", "inscrições abertas"]):
        return True
    return False


def _build_prompt(raw: dict[str, Any]) -> str:
    title = str(raw.get("title", ""))[:300]
    snippet = str(raw.get("snippet", ""))[:900]
    return f"""
Responda apenas JSON valido, sem markdown e sem texto adicional.
Classifique esta oportunidade comercial. JSON obrigatorio:
{{
  "organizacao": "",
  "nome_oportunidade": "",
  "categoria": "",
  "descricao_resumida": "",
  "data_publicacao": null,
  "prazo_inscricao": null,
  "status_chamada": "",
  "dias_restantes": null,
  "tecnologias_relacionadas": [],
  "score_aderencia": 0,
  "potencial_negocio": "",
  "motivo_classificacao": "",
  "recomendacao_acao": ""
}}

status_chamada deve ser ABERTA, ENCERRADA, SEM_PRAZO_IDENTIFICADO ou NAO_E_CHAMADA.
potencial_negocio deve ser ALTO, MEDIO, BAIXO ou DESCARTAR.
recomendacao_acao deve ser AVALIAR_EDITAL, ENTRAR_EM_CONTATO, MONITORAR ou DESCARTAR.
Descarte noticias, cursos, eventos, webinars, mestrados e conteudos sem chamada ativa.

Data atual: {date.today().isoformat()}
Categoria sugerida: {raw.get("category_hint", "")}
Data de publicacao da fonte: {raw.get("published_at")}
Titulo: {title}
URL: {raw.get("url", "")}
Resumo: {snippet}
Fonte: {raw.get("source", "")}
""".strip()


def _classify_with_rules(raw: dict[str, Any]) -> dict[str, Any]:
    text = _combined_text(raw)
    deadline = _extract_deadline(text)
    publication_date = _normalize_date(raw.get("published_at"))
    techs = [term for term in TECH_TERMS if term in text]
    opportunity_score = sum(weight for term, weight in OPPORTUNITY_TERMS.items() if term in text)
    tech_score = sum(weight for term, weight in TECH_TERMS.items() if term in text)
    is_discard = _has_any(text, DISCARD_TERMS)
    is_ended = _has_any(text, ENDED_TERMS)
    looks_like_call = opportunity_score > 0 or _has_any(
        text,
        ["edital", "chamada", "inscrição", "inscricao", "submissão", "submissao", "proposta"],
    )

    if is_discard and opportunity_score < 3:
        status = "NAO_E_CHAMADA"
    elif is_ended:
        status = "ENCERRADA"
    elif deadline:
        status = "ABERTA" if _parse_iso_date(deadline) >= date.today() else "ENCERRADA"
    elif looks_like_call:
        status = "SEM_PRAZO_IDENTIFICADO"
    else:
        status = "NAO_E_CHAMADA"

    score = max(0, min(10, 2 + opportunity_score + tech_score - (4 if is_discard else 0)))
    potential = _infer_potential(status, score, opportunity_score, tech_score)
    recommendation = _infer_recommendation(status, potential)

    return {
        "organizacao": _guess_organization(raw),
        "nome_oportunidade": raw.get("title", ""),
        "categoria": raw.get("category_hint", "Não classificada"),
        "descricao_resumida": raw.get("snippet", "")[:500],
        "data_publicacao": publication_date,
        "prazo_inscricao": deadline,
        "status_chamada": status,
        "dias_restantes": _days_remaining(deadline),
        "tecnologias_relacionadas": sorted(set(techs)),
        "score_aderencia": score,
        "potencial_negocio": potential,
        "motivo_classificacao": _classification_reason(status, potential, bool(deadline), techs),
        "recomendacao_acao": recommendation,
    }


def _normalize_result(raw: dict[str, Any], result: dict[str, Any], classified_by: str) -> dict[str, Any]:
    technologies = result.get("tecnologias_relacionadas", [])
    if isinstance(technologies, str):
        technologies = [item.strip() for item in technologies.split(",") if item.strip()]

    deadline = _normalize_date(result.get("prazo_inscricao")) or _extract_deadline(_combined_text(raw))
    publication_date = _normalize_date(result.get("data_publicacao")) or _normalize_date(raw.get("published_at"))
    status = _normalize_choice(
        result.get("status_chamada"),
        {"ABERTA", "ENCERRADA", "SEM_PRAZO_IDENTIFICADO", "NAO_E_CHAMADA"},
        "SEM_PRAZO_IDENTIFICADO",
    )
    score = _coerce_score(result.get("score_aderencia", 0))
    potential = _normalize_choice(
        result.get("potencial_negocio"),
        {"ALTO", "MEDIO", "BAIXO", "DESCARTAR"},
        "BAIXO",
    )
    recommendation = _normalize_choice(
        result.get("recomendacao_acao"),
        {"AVALIAR_EDITAL", "ENTRAR_EM_CONTATO", "MONITORAR", "DESCARTAR"},
        "MONITORAR",
    )

    status, potential, recommendation = _post_validate(raw, deadline, status, potential, recommendation, score)

    return {
        "id": raw.get("id"),
        "data_encontrada": _normalize_date(raw.get("collected_at")) or date.today().isoformat(),
        "data_publicacao": publication_date,
        "prazo_inscricao": deadline,
        "status_chamada": status,
        "dias_restantes": _days_remaining(deadline),
        "potencial_negocio": potential,
        "motivo_classificacao": result.get("motivo_classificacao")
        or _classification_reason(status, potential, bool(deadline), technologies),
        "recomendacao_acao": recommendation,
        "organizacao": result.get("organizacao") or _guess_organization(raw),
        "nome_oportunidade": result.get("nome_oportunidade") or raw.get("title", ""),
        "categoria": result.get("categoria") or raw.get("category_hint", "Não classificada"),
        "descricao_resumida": result.get("descricao_resumida") or raw.get("snippet", ""),
        "tecnologias_relacionadas": ", ".join(technologies),
        "score_aderencia": score,
        "url": raw.get("url", ""),
        "fonte": raw.get("source", ""),
        "query": raw.get("query", ""),
        "coletado_em": raw.get("collected_at", datetime.now().isoformat(timespec="seconds")),
        "classificado_por": classified_by,
    }


def _post_validate(
    raw: dict[str, Any],
    deadline: str | None,
    status: str,
    potential: str,
    recommendation: str,
    score: int,
) -> tuple[str, str, str]:
    text = _combined_text(raw)
    if deadline and _parse_iso_date(deadline) < date.today():
        status = "ENCERRADA"
    if status in {"ENCERRADA", "NAO_E_CHAMADA"} or _has_any(text, ENDED_TERMS):
        return status, "DESCARTAR", "DESCARTAR"
    if _has_any(text, DISCARD_TERMS) and not _has_any(text, ["inscrições abertas", "chamada aberta", "edital aberto"]):
        return "NAO_E_CHAMADA", "DESCARTAR", "DESCARTAR"
    if not deadline and score >= 6 and status != "ABERTA":
        return "SEM_PRAZO_IDENTIFICADO", "MEDIO", "MONITORAR"
    return status, potential, recommendation


def _extract_deadline(text: str) -> str | None:
    for pattern in DATE_PATTERNS:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            parsed = _parse_loose_date(match.group(1))
            if parsed:
                return parsed.isoformat()

    month_match = re.search(
        r"(?:at[eé]|ate|prazo|deadline|encerramento)\s+(?:dia\s+)?(\d{1,2})\s+de\s+([a-zç]+)\s+de\s+(\d{4})",
        text,
        flags=re.IGNORECASE,
    )
    if month_match:
        day, month_name, year = month_match.groups()
        month = MONTHS_PT.get(month_name.lower())
        if month:
            return date(int(year), month, int(day)).isoformat()
    return None


def _parse_loose_date(value: str) -> date | None:
    normalized = value.strip().replace("-", "/")
    parts = normalized.split("/")
    if len(parts) != 3:
        return None
    try:
        day, month, year = [int(part) for part in parts]
        if year < 100:
            year += 2000
        return date(year, month, day)
    except ValueError:
        return None


def _normalize_date(value: Any) -> str | None:
    if value in {None, "", "null", "None"}:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = str(value).strip()
    if re.match(r"^\d{4}-\d{2}-\d{2}", text):
        return text[:10]
    parsed = _parse_loose_date(text)
    return parsed.isoformat() if parsed else None


def _parse_iso_date(value: str) -> date:
    return date.fromisoformat(value)


def _days_remaining(deadline: str | None) -> int | None:
    if not deadline:
        return None
    return (_parse_iso_date(deadline) - date.today()).days


def _infer_potential(status: str, score: int, opportunity_score: int, tech_score: int) -> str:
    if status in {"ENCERRADA", "NAO_E_CHAMADA"}:
        return "DESCARTAR"
    if status == "ABERTA" and score >= 8 and opportunity_score >= 3 and tech_score >= 2:
        return "ALTO"
    if status == "ABERTA" and score >= 5:
        return "MEDIO"
    if status == "SEM_PRAZO_IDENTIFICADO" and score >= 6:
        return "MEDIO"
    return "BAIXO"


def _infer_recommendation(status: str, potential: str) -> str:
    if potential == "DESCARTAR" or status in {"ENCERRADA", "NAO_E_CHAMADA"}:
        return "DESCARTAR"
    if potential == "ALTO":
        return "AVALIAR_EDITAL"
    return "MONITORAR"


def _classification_reason(status: str, potential: str, has_deadline: bool, technologies: list[str]) -> str:
    if potential == "DESCARTAR":
        return f"Classificado como {status}; item nao indica oportunidade comercial aberta relevante."
    if has_deadline:
        return f"Chamada com prazo identificado e potencial {potential}; tecnologias: {', '.join(technologies) or 'nao claras'}."
    return f"Parece oportunidade, mas sem prazo identificado; potencial {potential} exige monitoramento."


def _combined_text(raw: dict[str, Any]) -> str:
    return f"{raw.get('title', '')} {raw.get('snippet', '')} {raw.get('query', '')}".lower()


def _has_any(text: str, terms: list[str]) -> bool:
    return any(term in text for term in terms)


def _normalize_choice(value: Any, allowed: set[str], default: str) -> str:
    text = str(value or "").strip().upper()
    return text if text in allowed else default


def _extract_json(text: str) -> str:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE).strip()
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    return match.group(0) if match else text


def _coerce_score(value: Any) -> int:
    try:
        return max(0, min(10, int(round(float(value)))))
    except (TypeError, ValueError):
        return 0


def _guess_organization(raw: dict[str, Any]) -> str:
    source = raw.get("source") or ""
    title = raw.get("title") or ""
    known = ["FINEP", "EMBRAPII", "EMBRAPA", "SENAI", "Sebrae", "BNDES", "CNPq", "FAPESP"]
    combined = f"{source} {title}".lower()
    for org in known:
        if org.lower() in combined:
            return org
    return source or "Não informado"
