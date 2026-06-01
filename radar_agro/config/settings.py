from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
REPORTS_DIR = BASE_DIR / "reports"
APP_CONFIG_YAML = BASE_DIR / "config" / "app_config.yaml"

OPPORTUNITIES_XLSX = DATA_DIR / "opportunities.xlsx"
OPPORTUNITIES_CSV = DATA_DIR / "opportunities.csv"
RAW_RESULTS_JSON = DATA_DIR / "raw_results.json"
HISTORY_JSON = DATA_DIR / "history.json"

USER_AGENT = os.getenv("USER_AGENT", "RadarAgroBot/0.1 (+contato@suaempresa.com)")
REQUEST_TIMEOUT_SECONDS = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "20"))
RATE_LIMIT_SECONDS = float(os.getenv("RATE_LIMIT_SECONDS", "1.2"))
MAX_RESULTS_PER_QUERY = int(os.getenv("MAX_RESULTS_PER_QUERY", "8"))

LLM_CONFIG = {
    "provider": "ollama",
    "model": "qwen3:8b",
    "host": "http://localhost:11434",
    "timeout_seconds": 90,
}


def load_llm_config() -> dict:
    """Le um YAML simples sem adicionar dependencia extra de parser."""

    config = LLM_CONFIG.copy()
    if not APP_CONFIG_YAML.exists():
        return config

    in_llm_block = False
    for line in APP_CONFIG_YAML.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped == "llm:":
            in_llm_block = True
            continue
        if in_llm_block and ":" in stripped:
            key, value = stripped.split(":", 1)
            value = value.strip().strip('"').strip("'")
            if key == "timeout_seconds":
                config[key] = float(value)
            else:
                config[key] = value
    return config

CATEGORIES = {
    "Editais e Fomento": [
        "edital inovação agronegócio",
        "chamada pública agro",
        "agricultura digital edital",
        "inteligência artificial edital",
        "pecuária de precisão edital",
        "subvenção econômica inovação",
        "FINEP agro edital",
        "EMBRAPII agronegócio chamada",
        "EMBRAPA chamada pública inovação",
        "SENAI edital inovação agro",
        "Sebrae agronegócio edital inovação",
        "BNDES inovação agronegócio",
    ],
    "Inovação Aberta": [
        "open innovation agro",
        "inovação aberta agronegócio",
        "startup challenge agro",
        "innovation challenge agtech",
        "venture client agro",
        "corporate venture agtech",
        "proof of concept agronegócio",
        "PoC agro",
    ],
    "RFP e Demandas Comerciais": [
        "RFP agriculture",
        "request for proposal agtech",
        "contratação inteligência artificial agro",
        "contratação visão computacional",
        "contratação sensoriamento remoto",
        "licitação drone agricultura",
        "licitação imagens de satélite",
    ],
    "CPSI - Contratação Pública de Soluções Inovadoras": [
        "CPSI",
        "Contrato Público para Solução Inovadora",
        "Contratação Pública de Solução Inovadora",
        "Contratação Pública de Soluções Inovadoras",
        "edital CPSI",
        "edital de CPSI",
        "chamamento público CPSI",
        "licitação especial solução inovadora",
        '"Marco Legal das Startups" "solução inovadora"',
        '"Lei Complementar 182/2021" "CPSI"',
        '"proposta de solução inovadora" "administração pública"',
        '"teste de solução inovadora" "edital"',
        '"contratação de solução inovadora" "startup"',
        '"govtech" "CPSI"',
        '"CPSI" "inscrições abertas"',
        '"CPSI" "propostas até"',
        '"CPSI" "prazo de inscrição"',
        '"CPSI" "apresentação das propostas"',
    ],
}

# RSS institucionais variam com frequencia. A lista fica centralizada para facilitar manutencao.
RSS_FEEDS = [
    "https://www.finep.gov.br/noticias/todas-noticias?format=feed&type=rss",
    "https://embrapii.org.br/feed/",
    "https://www.embrapa.br/rss",
    "https://www.sebrae.com.br/sites/PortalSebrae/rss",
]
