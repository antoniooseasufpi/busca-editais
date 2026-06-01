from __future__ import annotations

import json
import re
from datetime import date, datetime, timedelta
from typing import Any

import requests

from radar_agro.config.settings import load_llm_config

CPSI_CATEGORY = "CPSI - Contratação Pública de Soluções Inovadoras"
STALE_PUBLICATION_DAYS = 180

TIPO_OPORTUNIDADE_VALUES = {
    "Edital/Fomento",
    "Open Innovation",
    "RFP",
    "RFI",
    "CPSI",
    "ETEC",
    "CPI",
    "Aceleração",
    "PoC/Piloto",
    "Licitação Tradicional",
    "Outro",
}

AREA_APLICACAO_VALUES = {
    "Saúde Animal",
    "Pecuária de Precisão",
    "Agricultura Digital",
    "Sensoriamento Remoto",
    "Drones e Monitoramento Aéreo",
    "Visão Computacional",
    "IA e Machine Learning",
    "GovTech",
    "Cooperativas Agroindustriais",
    "Meio Ambiente",
    "Rastreabilidade",
    "Automação e IoT",
    "Gestão Pública",
    "Outro",
}

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
    "govtech": 2,
    "geotecnologia": 2,
    "geotecnologias": 2,
    "dados": 1,
    "automação": 1,
    "automacao": 1,
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
    "cpsi": 4,
    "contrato público para solução inovadora": 4,
    "contrato publico para solucao inovadora": 4,
    "contratação pública de solução inovadora": 4,
    "contratacao publica de solucao inovadora": 4,
    "contratação pública de soluções inovadoras": 4,
    "contratacao publica de solucoes inovadoras": 4,
    "licitação especial": 3,
    "licitacao especial": 3,
    "solução inovadora": 2,
    "solucao inovadora": 2,
    "marco legal das startups": 2,
    "lei complementar 182/2021": 2,
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
    "manual",
    "guia",
    "artigo",
    "consulta pública",
    "consulta publica",
]

ENDED_TERMS = [
    "encerrado",
    "encerrada",
    "inscrições encerradas",
    "inscricoes encerradas",
    "prazo encerrado",
    "homologado",
    "finalizado",
    "suspenso",
    "revogado",
]

CPSI_STRONG_TERMS = [
    "cpsi",
    "contrato público para solução inovadora",
    "contrato publico para solucao inovadora",
    "contratação pública de solução inovadora",
    "contratacao publica de solucao inovadora",
    "contratação pública de soluções inovadoras",
    "contratacao publica de solucoes inovadoras",
]

CPSI_CANDIDATE_TERMS = [
    "licitação especial para solução inovadora",
    "licitacao especial para solucao inovadora",
    "seleção de proposta de solução inovadora",
    "selecao de proposta de solucao inovadora",
    "teste de solução inovadora",
    "teste de solucao inovadora",
    "marco legal das startups",
    "lei complementar nº 182/2021",
    "lei complementar 182/2021",
    "solução inovadora",
    "solucao inovadora",
]

CPSI_OPTIONAL_FIELDS = [
    "numero_edital",
    "orgao_publico",
    "modalidade",
    "objeto",
    "data_inicio_propostas",
    "data_limite_propostas",
    "link_edital",
    "link_anexos",
    "valor_estimado",
    "forma_envio_proposta",
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
    if _is_cpsi_candidate(_content_text(raw)):
        return False
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
  "recomendacao_acao": "",
  "tipo_oportunidade": "",
  "area_aplicacao": "",
  "numero_edital": null,
  "orgao_publico": null,
  "modalidade": null,
  "objeto": null,
  "data_inicio_propostas": null,
  "data_limite_propostas": null,
  "link_edital": null,
  "link_anexos": [],
  "valor_estimado": null,
  "forma_envio_proposta": null
}}

status_chamada deve ser ABERTA, ENCERRADA, SEM_PRAZO_IDENTIFICADO ou NAO_E_CHAMADA.
potencial_negocio deve ser ALTO, MEDIO, BAIXO ou DESCARTAR.
recomendacao_acao deve ser AVALIAR_EDITAL, ENTRAR_EM_CONTATO, MONITORAR ou DESCARTAR.
tipo_oportunidade deve ser um destes: Edital/Fomento, Open Innovation, RFP, RFI, CPSI, ETEC, CPI, Aceleração, PoC/Piloto, Licitação Tradicional, Outro.
area_aplicacao deve ser uma destas: Saúde Animal, Pecuária de Precisão, Agricultura Digital, Sensoriamento Remoto, Drones e Monitoramento Aéreo, Visão Computacional, IA e Machine Learning, GovTech, Cooperativas Agroindustriais, Meio Ambiente, Rastreabilidade, Automação e IoT, Gestão Pública, Outro.
Descarte noticias, cursos, eventos, webinars, mestrados e conteudos sem chamada ativa.
Use categoria "{CPSI_CATEGORY}" quando houver CPSI, Contrato Publico para Solucao Inovadora,
Contratacao Publica de Solucao Inovadora, Marco Legal das Startups, Lei Complementar 182/2021
ou edital para teste/contratacao de solucao inovadora pela administracao publica.

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
    content_text = _content_text(raw)
    deadline = _extract_deadline(text)
    cpsi_deadline = _extract_cpsi_deadline(text)
    deadline = cpsi_deadline or deadline
    publication_date = _normalize_date(raw.get("published_at"))
    techs = [term for term in TECH_TERMS if term in text]
    opportunity_score = sum(weight for term, weight in OPPORTUNITY_TERMS.items() if term in text)
    tech_score = sum(weight for term, weight in TECH_TERMS.items() if term in text)
    is_cpsi = _is_cpsi_candidate(content_text)
    if is_cpsi:
        opportunity_score += 3
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
    if _is_stale_without_deadline(deadline, publication_date, _normalize_date(raw.get("collected_at"))):
        status = "ENCERRADA"

    score = max(0, min(10, 2 + opportunity_score + tech_score - (4 if is_discard else 0)))
    potential = _infer_potential(status, score, opportunity_score, tech_score)
    recommendation = _infer_recommendation(status, potential)
    category = CPSI_CATEGORY if is_cpsi else raw.get("category_hint", "Não classificada")

    return {
        "organizacao": _guess_organization(raw),
        "nome_oportunidade": raw.get("title", ""),
        "categoria": category,
        "tipo_oportunidade": infer_tipo_oportunidade(category, text),
        "area_aplicacao": infer_area_aplicacao(text),
        "descricao_resumida": raw.get("snippet", "")[:500],
        "data_publicacao": publication_date,
        "prazo_inscricao": deadline,
        "data_limite_propostas": deadline if is_cpsi else None,
        "status_chamada": status,
        "dias_restantes": _days_remaining(deadline),
        "tecnologias_relacionadas": sorted(set(techs)),
        "score_aderencia": score,
        "potencial_negocio": potential,
        "motivo_classificacao": _classification_reason(status, potential, bool(deadline), techs),
        "recomendacao_acao": recommendation,
        "orgao_publico": _guess_organization(raw) if is_cpsi else None,
        "link_edital": raw.get("url", "") if is_cpsi else None,
    }


def _normalize_result(raw: dict[str, Any], result: dict[str, Any], classified_by: str) -> dict[str, Any]:
    technologies = result.get("tecnologias_relacionadas", [])
    if isinstance(technologies, str):
        technologies = [item.strip() for item in technologies.split(",") if item.strip()]

    text = _combined_text(raw)
    cpsi_candidate = _is_cpsi_candidate(_content_text(raw))
    cpsi_deadline = _normalize_date(result.get("data_limite_propostas")) or _extract_cpsi_deadline(text)
    deadline = _normalize_date(result.get("prazo_inscricao")) or cpsi_deadline or _extract_deadline(text)
    publication_date = _normalize_date(result.get("data_publicacao")) or _normalize_date(raw.get("published_at"))
    category = result.get("categoria") or raw.get("category_hint", "Não classificada")
    if cpsi_candidate:
        category = CPSI_CATEGORY
    tipo_oportunidade = _normalize_choice(
        result.get("tipo_oportunidade"),
        TIPO_OPORTUNIDADE_VALUES,
        infer_tipo_oportunidade(category, text),
    )
    area_text = f"{text} {' '.join(technologies)} {result.get('motivo_classificacao', '')}".lower()
    area_aplicacao = _normalize_choice(
        result.get("area_aplicacao"),
        AREA_APLICACAO_VALUES,
        infer_area_aplicacao(area_text, category=category),
    )
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

    found_date = _normalize_date(raw.get("collected_at")) or date.today().isoformat()
    status, potential, recommendation = _post_validate(
        raw, deadline, publication_date, found_date, status, potential, recommendation, score, category
    )
    tipo_oportunidade = infer_tipo_oportunidade(category, text, current=tipo_oportunidade)
    area_aplicacao = infer_area_aplicacao(area_text, current=area_aplicacao, category=category)

    normalized = {
        "id": raw.get("id"),
        "data_encontrada": found_date,
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
        "categoria": category,
        "tipo_oportunidade": tipo_oportunidade,
        "area_aplicacao": area_aplicacao,
        "descricao_resumida": result.get("descricao_resumida") or raw.get("snippet", ""),
        "tecnologias_relacionadas": ", ".join(technologies),
        "score_aderencia": score,
        "url": raw.get("url", ""),
        "fonte": raw.get("source", ""),
        "query": raw.get("query", ""),
        "coletado_em": raw.get("collected_at", datetime.now().isoformat(timespec="seconds")),
        "classificado_por": classified_by,
    }
    for field in CPSI_OPTIONAL_FIELDS:
        value = result.get(field)
        if field in {"data_inicio_propostas", "data_limite_propostas"}:
            value = _normalize_date(value)
        if field == "link_anexos" and isinstance(value, list):
            value = ", ".join(str(item) for item in value if item)
        normalized[field] = value
    if cpsi_candidate:
        normalized["data_limite_propostas"] = normalized.get("data_limite_propostas") or deadline
        normalized["orgao_publico"] = normalized.get("orgao_publico") or normalized["organizacao"]
        normalized["link_edital"] = normalized.get("link_edital") or normalized["url"]
    return normalized


def _post_validate(
    raw: dict[str, Any],
    deadline: str | None,
    publication_date: str | None,
    found_date: str,
    status: str,
    potential: str,
    recommendation: str,
    score: int,
    category: str,
) -> tuple[str, str, str]:
    text = _combined_text(raw)
    if deadline and _parse_iso_date(deadline) < date.today():
        status = "ENCERRADA"
    if _is_stale_without_deadline(deadline, publication_date, found_date):
        status = "ENCERRADA"
    if status in {"ENCERRADA", "NAO_E_CHAMADA"} or _has_any(text, ENDED_TERMS):
        return status, "DESCARTAR", "DESCARTAR"
    if category == CPSI_CATEGORY and status == "ABERTA":
        recommendation = "AVALIAR_EDITAL"
        if score >= 8:
            potential = "ALTO"
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


def _is_stale_without_deadline(
    deadline: str | None,
    publication_date: str | None,
    found_date: str | None,
) -> bool:
    if deadline or not publication_date:
        return False
    try:
        published = _parse_iso_date(publication_date)
        reference = _parse_iso_date(found_date or date.today().isoformat())
    except ValueError:
        return False
    return published < reference - timedelta(days=STALE_PUBLICATION_DAYS)


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


def _is_cpsi_candidate(text: str) -> bool:
    return _has_any(text, CPSI_STRONG_TERMS) or (
        _has_any(text, CPSI_CANDIDATE_TERMS)
        and _has_any(text, ["edital", "chamada", "proposta", "administração pública", "administracao publica"])
    )


def _extract_cpsi_deadline(text: str) -> str | None:
    patterns = [
        r"(?:propostas?|envio de propostas?|apresenta[cç][aã]o das propostas?|recebimento de propostas?)\s+(?:at[eé]|ate|até|em)?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        r"(?:data limite de propostas?|limite para propostas?)\s*(?:at[eé]|ate|até|em)?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            parsed = _parse_loose_date(match.group(1))
            if parsed:
                return parsed.isoformat()
    return None


def infer_tipo_oportunidade(category: str, text: str = "", current: str | None = None) -> str:
    lowered_category = str(category or "").lower()
    lowered_text = str(text or "").lower()
    if "cpsi" in lowered_category:
        return "CPSI"
    if "etec" in lowered_category or "encomenda tecnológica" in lowered_category or "encomenda tecnologica" in lowered_category:
        return "ETEC"
    if "cpi" in lowered_category or "compra pública de inovação" in lowered_category or "compra publica de inovacao" in lowered_category:
        return "CPI"
    if "rfi" in lowered_category or "consulta ao mercado" in lowered_category:
        return "RFI"
    if "inovação aberta" in lowered_category or "inovacao aberta" in lowered_category:
        return "Open Innovation"
    if "editais" in lowered_category or "fomento" in lowered_category:
        return "Edital/Fomento"
    if "rfp" in lowered_category or "demandas comerciais" in lowered_category:
        return "RFP"
    if _has_any(
        lowered_category,
        [
            "saúde animal",
            "saude animal",
            "pecuária de precisão",
            "pecuaria de precisao",
            "agricultura digital",
            "sensoriamento remoto",
            "drones",
            "cooperativas agroindustriais",
            "empresas estratégicas agrotech",
            "empresas estrategicas agrotech",
        ],
    ):
        return "Outro"
    if _has_any(lowered_text, ["etec", "encomenda tecnológica", "encomenda tecnologica"]):
        return "ETEC"
    if _has_any(lowered_text, ["rfi", "request for information", "consulta ao mercado", "tomada de subsídios"]):
        return "RFI"
    if _has_any(lowered_text, ["compra pública de inovação", "compra publica de inovacao", "public procurement of innovation"]):
        return "CPI"
    if _has_any(lowered_text, ["aceleração", "aceleracao", "incubação", "incubacao", "mentoria"]):
        return "Aceleração"
    if _has_any(lowered_text, ["poc", "prova de conceito", "piloto", "teste de solução", "validacao de solução"]):
        return "PoC/Piloto"
    if _has_any(lowered_text, ["pregão", "pregao", "concorrência", "concorrencia", "dispensa", "licitação", "licitacao"]):
        return "Licitação Tradicional"
    if current in TIPO_OPORTUNIDADE_VALUES:
        return current
    return "Outro"


def infer_area_aplicacao(text: str, current: str | None = None, category: str = "") -> str:
    lowered = str(text or "").lower()
    lowered_category = str(category or "").lower()
    category_mapping = [
        ("Saúde Animal", ["saúde animal", "saude animal"]),
        ("Pecuária de Precisão", ["pecuária de precisão", "pecuaria de precisao"]),
        ("Agricultura Digital", ["agricultura digital"]),
        ("Sensoriamento Remoto", ["sensoriamento remoto", "satélites", "satelites"]),
        ("Drones e Monitoramento Aéreo", ["drones", "monitoramento aéreo", "monitoramento aereo"]),
        ("Cooperativas Agroindustriais", ["cooperativas agroindustriais"]),
        ("GovTech", ["cpsi", "etec", "compra pública de inovação", "compra publica de inovacao", "consulta ao mercado"]),
    ]
    for area, terms in category_mapping:
        if _has_any(lowered_category, terms):
            return area

    rules = [
        (
            "Saúde Animal",
            [
                "verminose",
                "sanidade animal",
                "saúde animal",
                "saude animal",
                "bem-estar animal",
                "doença animal",
                "doenca animal",
                "diagnóstico animal",
                "diagnostico animal",
                "medicamento veterinário",
                "medicamento veterinario",
            ],
        ),
        (
            "Pecuária de Precisão",
            [
                "pecuária",
                "pecuaria",
                "bovino",
                "caprino",
                "ovino",
                "suíno",
                "suino",
                "aves",
                "gado",
                "rebanho",
                "peso animal",
                "comportamento animal",
                "eficiência alimentar",
                "eficiencia alimentar",
            ],
        ),
        (
            "Sensoriamento Remoto",
            [
                "satélite",
                "satelite",
                "sensoriamento remoto",
                "imagem orbital",
                "geotecnologia",
                "geotecnologias",
                "geoprocessamento",
                "ndvi",
                "ndwi",
                "observação da terra",
                "observacao da terra",
                "monitoramento territorial",
            ],
        ),
        (
            "Drones e Monitoramento Aéreo",
            [
                "drone",
                "drones",
                "vant",
                "uav",
                "aeronave remotamente pilotada",
                "imagem aérea",
                "imagem aerea",
                "mapeamento aéreo",
                "mapeamento aereo",
                "inspeção aérea",
                "inspecao aerea",
            ],
        ),
        (
            "Visão Computacional",
            [
                "visão computacional",
                "visao computacional",
                "processamento de imagem",
                "processamento de imagens",
                "detecção automática",
                "deteccao automatica",
                "segmentação",
                "segmentacao",
                "classificação de imagens",
                "classificacao de imagens",
                "contagem automática",
                "contagem automatica",
                "inspeção visual",
                "inspecao visual",
            ],
        ),
        (
            "IA e Machine Learning",
            [
                "inteligência artificial",
                "inteligencia artificial",
                "machine learning",
                "deep learning",
                "modelo preditivo",
                "ia generativa",
                "aprendizado de máquina",
                "aprendizado de maquina",
            ],
        ),
        (
            "Cooperativas Agroindustriais",
            ["cooperativa", "cooperativas", "agroindustrial", "cooperativismo"],
        ),
        (
            "GovTech",
            [
                "governo",
                "prefeitura",
                "secretaria",
                "órgão público",
                "orgao publico",
                "serviço público",
                "servico publico",
                "govtech",
                "administração pública",
                "administracao publica",
            ],
        ),
        (
            "Meio Ambiente",
            [
                "meio ambiente",
                "sustentabilidade",
                "carbono",
                "desmatamento",
                "queimada",
                "recursos hídricos",
                "recursos hidricos",
                "clima",
                "biodiversidade",
            ],
        ),
        (
            "Rastreabilidade",
            ["rastreabilidade", "cadeia produtiva", "certificação", "certificacao", "origem do produto", "controle de qualidade"],
        ),
        (
            "Automação e IoT",
            [
                "sensor",
                "sensores",
                "iot",
                "internet das coisas",
                "telemetria",
                "automação",
                "automacao",
                "hardware",
                "dispositivo conectado",
            ],
        ),
        (
            "Agricultura Digital",
            [
                "agricultura digital",
                "agricultura de precisão",
                "agricultura de precisao",
                "lavoura",
                "lavouras",
                "mapa de produtividade",
                "produtividade agrícola",
                "produtividade agricola",
                "culturas agrícolas",
                "culturas agricolas",
            ],
        ),
        (
            "Gestão Pública",
            [
                "gestão municipal",
                "gestao municipal",
                "gestão estadual",
                "gestao estadual",
                "gestão pública",
                "gestao publica",
                "planejamento",
                "políticas públicas",
                "politicas publicas",
                "serviços públicos",
                "servicos publicos",
            ],
        ),
    ]
    for area, terms in rules:
        if _has_any(lowered, terms):
            return area
    if current in AREA_APLICACAO_VALUES:
        return current
    return "Outro"


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


def _content_text(raw: dict[str, Any]) -> str:
    return f"{raw.get('title', '')} {raw.get('snippet', '')} {raw.get('source', '')}".lower()


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
