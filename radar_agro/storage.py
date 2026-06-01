from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from radar_agro.classifiers.llm_classifier import infer_area_aplicacao, infer_tipo_oportunidade

from radar_agro.config.settings import (
    DATA_DIR,
    HISTORY_JSON,
    OPPORTUNITIES_CSV,
    OPPORTUNITIES_XLSX,
    RAW_RESULTS_JSON,
    REPORTS_DIR,
)


def ensure_directories() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def load_opportunities() -> pd.DataFrame:
    ensure_directories()
    if OPPORTUNITIES_XLSX.exists():
        return ensure_classification_columns(pd.read_excel(OPPORTUNITIES_XLSX))
    return ensure_classification_columns(pd.DataFrame())


def save_raw_results(results: list[dict[str, Any]]) -> None:
    ensure_directories()
    RAW_RESULTS_JSON.write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def save_opportunities(df: pd.DataFrame) -> None:
    ensure_directories()
    df = ensure_classification_columns(df)
    df = sort_opportunities(df)
    df.to_excel(OPPORTUNITIES_XLSX, index=False)
    df.to_csv(OPPORTUNITIES_CSV, index=False, encoding="utf-8-sig")


def merge_new_opportunities(classified: list[dict[str, Any]]) -> tuple[pd.DataFrame, int]:
    current = load_opportunities()
    incoming = pd.DataFrame(classified)
    if incoming.empty:
        return current, 0

    if current.empty:
        incoming["novo"] = True
        save_opportunities(incoming)
        return incoming, len(incoming)

    current = current.copy()
    current["novo"] = False
    existing_ids = set(current.get("id", pd.Series(dtype=str)).astype(str))
    incoming["novo"] = ~incoming["id"].astype(str).isin(existing_ids)
    new_count = int(incoming["novo"].sum())
    incoming_ids = set(incoming["id"].astype(str))
    unchanged = current[~current["id"].astype(str).isin(incoming_ids)]
    merged = pd.concat([incoming, unchanged], ignore_index=True)
    save_opportunities(merged)
    return merged, new_count


def sort_opportunities(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    sorted_df = ensure_classification_columns(df.copy())
    status_rank = {"ABERTA": 0, "SEM_PRAZO_IDENTIFICADO": 1, "ENCERRADA": 2, "NAO_E_CHAMADA": 3}
    potential_rank = {"ALTO": 0, "MEDIO": 1, "BAIXO": 2, "DESCARTAR": 3}
    status_series = sorted_df.get("status_chamada", pd.Series(dtype=str))
    category_series = sorted_df.get("categoria", pd.Series(dtype=str))
    sorted_df["_status_rank"] = status_series.map(status_rank).fillna(9)
    sorted_df["_cpsi_rank"] = (category_series != "CPSI - Contratação Pública de Soluções Inovadoras").astype(int)
    potential_series = sorted_df.get("potencial_negocio", pd.Series(dtype=str))
    sorted_df["_potencial_rank"] = potential_series.map(potential_rank).fillna(9)
    sorted_df["_score_rank"] = pd.to_numeric(
        sorted_df.get("score_aderencia", pd.Series(dtype=float)), errors="coerce"
    ).fillna(0)
    sorted_df["_dias_rank"] = pd.to_numeric(
        sorted_df.get("dias_restantes", pd.Series(dtype=float)), errors="coerce"
    ).fillna(99999)
    sorted_df = sorted_df.sort_values(
        by=["_status_rank", "_cpsi_rank", "_potencial_rank", "_dias_rank", "_score_rank"],
        ascending=[True, True, True, True, False],
    )
    return sorted_df.drop(
        columns=["_status_rank", "_cpsi_rank", "_potencial_rank", "_score_rank", "_dias_rank"]
    )


def ensure_classification_columns(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    normalized = df.copy()
    if "tipo_oportunidade" not in normalized.columns:
        normalized["tipo_oportunidade"] = None
    if "area_aplicacao" not in normalized.columns:
        normalized["area_aplicacao"] = None

    def build_text(row: pd.Series) -> str:
        fields = [
            row.get("nome_oportunidade", ""),
            row.get("descricao_resumida", ""),
            row.get("tecnologias_relacionadas", ""),
            row.get("motivo_classificacao", ""),
        ]
        return " ".join(str(value) for value in fields if pd.notna(value)).lower()

    normalized["tipo_oportunidade"] = normalized.apply(
        lambda row: infer_tipo_oportunidade(
            str(row.get("categoria", "")),
            build_text(row),
            current=row.get("tipo_oportunidade"),
        ),
        axis=1,
    )
    normalized["area_aplicacao"] = normalized.apply(
        lambda row: infer_area_aplicacao(build_text(row), current=row.get("area_aplicacao")),
        axis=1,
    )
    return normalized


def append_history(found_count: int, new_count: int, elapsed_seconds: float) -> None:
    ensure_directories()
    history = read_json(HISTORY_JSON, default=[])
    history.insert(
        0,
        {
            "executado_em": datetime.now().isoformat(timespec="seconds"),
            "quantidade_encontrada": found_count,
            "quantidade_nova": new_count,
            "tempo_execucao_segundos": round(elapsed_seconds, 2),
        },
    )
    HISTORY_JSON.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")


def load_history() -> list[dict[str, Any]]:
    ensure_directories()
    return read_json(HISTORY_JSON, default=[])


def clear_local_data() -> list[str]:
    ensure_directories()
    removed: list[str] = []
    data_files = [path for path in DATA_DIR.iterdir() if path.is_file()]
    for path in data_files:
        if path.exists():
            path.unlink()
            removed.append(path.name)
    return removed


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default
