from __future__ import annotations

from radar_agro.pipeline import run_search_pipeline


if __name__ == "__main__":
    result = run_search_pipeline()
    print(
        "Busca concluida: "
        f"{result['found_count']} encontradas, "
        f"{result['new_count']} novas, "
        f"{result['elapsed_seconds']}s."
    )

