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
        '"recursos não reembolsáveis" "inovação"',
        '"subvenção econômica" "agro"',
        '"programa de fomento" "agritech"',
        "edital agtech",
        "edital agro 2026",
        "edital inovação 2026",
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
        '"desafio tecnológico" "agro"',
        "programa de conexão startup agro",
        '"venture client" "agro"',
        '"corporate innovation" "agriculture"',
        '"open innovation" "livestock"',
    ],
    "RFP e Demandas Comerciais": [
        "RFP agriculture",
        "request for proposal agtech",
        "contratação inteligência artificial agro",
        "contratação visão computacional",
        "contratação sensoriamento remoto",
        "licitação drone agricultura",
        "licitação imagens de satélite",
        '"termo de referência" "inteligência artificial"',
        '"termo de referência" "sensoriamento remoto"',
        '"termo de referência" "geoprocessamento"',
        '"contratação" "solução tecnológica" "agro"',
        '"pregão eletrônico" "drone"',
        '"pregão eletrônico" "geoprocessamento"',
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
        "Contrato Público de Solução Inovadora",
        "Contrato Público para Soluções Inovadoras",
        '"CPSI" "edital aberto"',
        '"CPSI" "recebimento de propostas"',
        '"CPSI" "envio de propostas"',
        '"CPSI" "contrato público"',
    ],
    "ETEC - Encomenda Tecnológica": [
        "ETEC",
        "Encomenda Tecnológica",
        "Encomenda Tecnológica agro",
        "Encomenda Tecnológica inteligência artificial",
        "Encomenda Tecnológica sensoriamento remoto",
        "Encomenda Tecnológica drones",
        "Encomenda Tecnológica solução inovadora",
        "Encomenda de P&D",
        "Contratação de Pesquisa e Desenvolvimento",
        "Risco Tecnológico",
        '"Lei da Inovação" "Encomenda Tecnológica"',
        '"Art. 20" "Lei da Inovação" "Encomenda Tecnológica"',
        '"Marco Legal de Ciência Tecnologia e Inovação" "Encomenda Tecnológica"',
    ],
    "CPI - Compra Pública de Inovação": [
        "Compra Pública de Inovação",
        "Compras Públicas de Inovação",
        "Public Procurement of Innovation",
        '"PPI" "public procurement innovation"',
        "Aquisição de Solução Inovadora",
        "Contratação Pública de Inovação",
        "Contratação de Inovação",
        "Innovative Procurement",
        "Inovação para Governo",
        '"compra pública" "solução inovadora"',
    ],
    "RFI e Consulta ao Mercado": [
        '"RFI" "agro"',
        '"Request for Information" "agriculture"',
        '"Request for Information" "agtech"',
        '"Consulta ao Mercado" "tecnologia"',
        '"Consulta ao Mercado" "inovação"',
        '"Consulta ao Mercado" "solução tecnológica"',
        '"Tomada de Subsídios" "tecnologia"',
        '"Tomada de Subsídios" "inovação"',
        "Manifestação de Interesse Tecnológico",
        "Chamamento de Ideias",
        '"Sondagem de Mercado" "tecnologia"',
        '"market consultation" "agriculture"',
    ],
    "Saúde Animal": [
        '"saúde animal" "inovação aberta"',
        '"saúde animal" "startup"',
        '"saúde animal" "edital"',
        '"animal health" "innovation challenge"',
        '"animal health" "startup challenge"',
        '"animal health" "open innovation"',
        '"livestock monitoring" "challenge"',
        '"animal welfare" "technology"',
        "animal analytics",
        "parasite monitoring",
        '"verminosis" "technology"',
        "animal disease detection",
        '"weight estimation" "livestock"',
        '"Zoetis" "innovation"',
        '"MSD Saúde Animal" "inovação"',
        '"Elanco" "innovation"',
        '"Alta Genetics" "innovation"',
        '"CRV Lagoa" "inovação"',
        '"ABS Global" "innovation"',
    ],
    "Pecuária de Precisão": [
        '"pecuária de precisão" "edital"',
        '"pecuária de precisão" "inovação"',
        '"pecuária de precisão" "startup"',
        '"precision livestock farming" "challenge"',
        '"precision livestock" "open innovation"',
        '"digital livestock" "technology"',
        '"cattle monitoring" "technology"',
        '"smart livestock" "innovation"',
        '"animal behavior" "livestock technology"',
        '"feed efficiency" "technology"',
        '"bovine monitoring" "AI"',
        "predição de peso animal",
        '"monitoramento de rebanho" "IA"',
        '"JBS" "inovação aberta"',
        '"BRF" "startup challenge"',
        '"Marfrig" "inovação"',
        '"Minerva Foods" "inovação"',
    ],
    "Agricultura Digital": [
        '"agricultura digital" "edital"',
        '"agricultura digital" "inovação aberta"',
        '"agricultura digital" "startup"',
        '"precision agriculture" "challenge"',
        '"digital agriculture" "open innovation"',
        '"smart farming" "innovation"',
        "crop intelligence",
        '"farm management" "AI"',
        "agricultural analytics",
        "agtech challenge",
        '"Raízen" "inovação aberta"',
        '"Suzano" "inovação aberta"',
        '"Bayer" "agtech"',
        '"Syngenta" "innovation challenge"',
        '"BASF" "agriculture innovation"',
        '"Corteva" "innovation"',
        '"SLC Agrícola" "inovação"',
        '"Amaggi" "inovação"',
    ],
    "Sensoriamento Remoto e Satélites": [
        '"sensoriamento remoto" "edital"',
        '"sensoriamento remoto" "licitação"',
        '"sensoriamento remoto" "inovação"',
        '"remote sensing" "agriculture" "challenge"',
        '"earth observation" "agriculture"',
        '"satellite imagery" "agriculture" "RFP"',
        '"geospatial analytics" "agriculture"',
        '"geospatial intelligence" "agriculture"',
        '"monitoramento por satélite" "contratação"',
        '"monitoramento por satélite" "licitação"',
        '"imagem orbital" "agro"',
        '"geoprocessamento" "agricultura"',
        '"NDVI" "edital"',
        '"NDWI" "monitoramento"',
        '"observação da Terra" "agro"',
    ],
    "Drones e Monitoramento Aéreo": [
        '"drone" "agricultura" "licitação"',
        '"drone" "agro" "edital"',
        '"drones" "inovação aberta"',
        '"drone analytics" "agriculture"',
        '"UAV analytics" "agriculture"',
        '"aerial monitoring" "agriculture"',
        '"drone monitoring" "agro"',
        '"drone mapping" "agriculture"',
        '"aerial inspection" "agro"',
        "computer vision drone",
        '"VANT" "agricultura"',
        '"VANT" "licitação"',
        '"mapeamento aéreo" "agricultura"',
    ],
    "Cooperativas Agroindustriais": [
        '"cooperativa agroindustrial" "inovação aberta"',
        '"cooperativa agroindustrial" "startup"',
        '"cooperativa agroindustrial" "tecnologia"',
        '"cooperativismo" "inovação" "agro"',
        '"agro cooperative" "innovation"',
        '"cooperative innovation" "agriculture"',
        '"Coamo" "inovação"',
        '"Cocamar" "inovação"',
        '"Frísia" "inovação"',
        '"Integrada Cooperativa" "inovação"',
        '"Copacol" "inovação"',
        '"Lar Cooperativa" "inovação"',
    ],
    "Empresas Estratégicas AgroTech": [
        '"EMBRAPA" "inovação aberta"',
        '"EMBRAPA" "edital inovação"',
        '"EMBRAPA" "startup"',
        '"EMBRAPII" "agro"',
        '"FINEP" "agro"',
        '"SENAI" "agro inovação"',
        '"Sebrae" "agtech"',
        '"BNDES" "inovação agronegócio"',
        '"Raízen" "startup"',
        '"Suzano" "startup"',
        '"JBS" "startup"',
        '"BRF" "inovação"',
        '"Bayer" "startup challenge"',
        '"Syngenta" "startup"',
        '"BASF" "startup"',
        '"Corteva" "startup"',
        '"Zoetis" "startup"',
        '"MSD Saúde Animal" "startup"',
        '"Elanco" "startup"',
    ],
}

# RSS institucionais variam com frequencia. A lista fica centralizada para facilitar manutencao.
RSS_FEEDS = [
    "https://www.finep.gov.br/noticias/todas-noticias?format=feed&type=rss",
    "https://embrapii.org.br/feed/",
    "https://www.embrapa.br/rss",
    "https://www.sebrae.com.br/sites/PortalSebrae/rss",
]
