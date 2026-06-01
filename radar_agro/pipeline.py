from __future__ import annotations

import time
from typing import Callable

from radar_agro.classifiers.llm_classifier import classify_opportunity
from radar_agro.crawlers.search import AgroOpportunityCrawler
from radar_agro.storage import append_history, merge_new_opportunities, save_raw_results


def run_search_pipeline(progress_callback: Callable[[dict], None] | None = None) -> dict:
    started = time.perf_counter()
    _emit(progress_callback, "inicio", "Iniciando busca de oportunidades", overall_percent=0)

    crawler = AgroOpportunityCrawler(progress_callback=progress_callback)
    raw_results = crawler.run()
    _emit(
        progress_callback,
        "salvamento",
        f"Salvando {len(raw_results)} resultado(s) brutos",
        stage_percent=0,
        overall_percent=35,
    )
    save_raw_results(raw_results)

    classified = []
    total_results = len(raw_results)
    _emit(
        progress_callback,
        "classificacao",
        f"Iniciando classificação de {total_results} resultado(s)",
        current=0,
        total=total_results,
        stage_percent=0,
        overall_percent=40,
    )
    for index, item in enumerate(raw_results, start=1):
        stage_percent = _percent(index, total_results)
        _emit(
            progress_callback,
            "classificacao",
            f"Classificando {index}/{total_results}: {item.get('title', '')[:90]}",
            current=index,
            total=total_results,
            stage_percent=stage_percent,
            overall_percent=40 + int(stage_percent * 0.55),
        )
        classified.append(classify_opportunity(item))

    _emit(
        progress_callback,
        "salvamento",
        "Consolidando Excel, CSV e histórico",
        stage_percent=80,
        overall_percent=95,
    )
    df, new_count = merge_new_opportunities(classified)

    elapsed = time.perf_counter() - started
    append_history(len(raw_results), new_count, elapsed)
    _emit(
        progress_callback,
        "concluido",
        f"Busca concluída em {round(elapsed, 2)}s",
        stage_percent=100,
        overall_percent=100,
    )

    return {
        "found_count": len(raw_results),
        "new_count": new_count,
        "elapsed_seconds": round(elapsed, 2),
        "total_count": len(df),
    }


def _emit(
    progress_callback: Callable[[dict], None] | None,
    stage: str,
    message: str,
    current: int | None = None,
    total: int | None = None,
    stage_percent: int | None = None,
    overall_percent: int | None = None,
) -> None:
    if progress_callback:
        progress_callback(
            {
                "stage": stage,
                "message": message,
                "current": current,
                "total": total,
                "stage_percent": stage_percent,
                "overall_percent": overall_percent,
            }
        )


def _percent(current: int, total: int) -> int:
    if total <= 0:
        return 100
    return min(100, max(0, int(round((current / total) * 100))))
