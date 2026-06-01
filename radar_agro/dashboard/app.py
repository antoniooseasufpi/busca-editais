from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from radar_agro.config.settings import OPPORTUNITIES_CSV, OPPORTUNITIES_XLSX
from radar_agro.pipeline import run_search_pipeline
from radar_agro.storage import clear_local_data, load_history, load_opportunities


st.set_page_config(page_title="Radar Agro", layout="wide")

st.title("Radar Agro")
st.caption("Monitor local de oportunidades abertas para prospecção comercial no agronegócio.")

history = load_history()
df = load_opportunities()
last_run = history[0]["executado_em"] if history else "Nunca executado"

if not df.empty:
    df["score_aderencia"] = pd.to_numeric(df.get("score_aderencia"), errors="coerce").fillna(0)
    df["dias_restantes"] = pd.to_numeric(df.get("dias_restantes"), errors="coerce")

status_series = df.get("status_chamada", pd.Series(dtype=str))
potential_series = df.get("potencial_negocio", pd.Series(dtype=str))
days_series = pd.to_numeric(df.get("dias_restantes", pd.Series(dtype=float)), errors="coerce")

total_open = int((status_series == "ABERTA").sum()) if not df.empty else 0
total_closed = int((status_series == "ENCERRADA").sum()) if not df.empty else 0
total_discarded = int((potential_series == "DESCARTAR").sum()) if not df.empty else 0
total_high = int((potential_series == "ALTO").sum()) if not df.empty else 0
total_medium = int((potential_series == "MEDIO").sum()) if not df.empty else 0
due_7 = int(((days_series >= 0) & (days_series <= 7)).sum()) if not df.empty else 0
due_30 = int(((days_series >= 0) & (days_series <= 30)).sum()) if not df.empty else 0

top_cols = st.columns(4)
top_cols[0].metric("Última execução", last_run)
top_cols[1].metric("Total salvo", len(df))
top_cols[2].metric("Encontradas na última execução", history[0]["quantidade_encontrada"] if history else 0)
top_cols[3].metric("Novas na última execução", history[0]["quantidade_nova"] if history else 0)

metric_cols = st.columns(4)
metric_cols[0].metric("Abertas", total_open)
metric_cols[1].metric("Encerradas", total_closed)
metric_cols[2].metric("Descartadas", total_discarded)
metric_cols[3].metric("Alto potencial", total_high)

deadline_cols = st.columns(3)
deadline_cols[0].metric("Médio potencial", total_medium)
deadline_cols[1].metric("Vencem em 7 dias", due_7)
deadline_cols[2].metric("Vencem em 30 dias", due_30)

if st.button("Executar Busca", type="primary"):
    status_box = st.status("Iniciando busca...", expanded=True)
    overall_bar = st.progress(0, text="Progresso geral: 0%")
    stage_bar = st.progress(0, text="Etapa atual: 0%")
    stage_placeholder = st.empty()
    log_placeholder = st.empty()
    progress_log: list[str] = []

    def update_progress(event: dict) -> None:
        stage = event.get("stage", "")
        message = event.get("message", "")
        current = event.get("current")
        total = event.get("total")
        stage_percent = event.get("stage_percent")
        overall_percent = event.get("overall_percent")

        stage_label = f"{stage_percent}%" if stage_percent is not None else "-"
        overall_label = f"{overall_percent}%" if overall_percent is not None else "-"
        progress_log.append(f"[{stage}] etapa={stage_label} geral={overall_label} | {message}")
        progress_log[:] = progress_log[-10:]
        stage_placeholder.write(
            f"Etapa atual: **{stage}**"
            + (f" | progresso da etapa: **{stage_percent}%**" if stage_percent is not None else "")
            + (f" | progresso geral: **{overall_percent}%**" if overall_percent is not None else "")
        )
        log_placeholder.code("\n".join(progress_log), language="text")
        status_box.update(label=message or "Executando...")

        if overall_percent is not None:
            overall_bar.progress(
                min(1.0, max(0.0, float(overall_percent) / 100.0)),
                text=f"Progresso geral: {overall_percent}%",
            )
        if stage_percent is not None:
            stage_bar.progress(
                min(1.0, max(0.0, float(stage_percent) / 100.0)),
                text=f"Etapa atual: {stage_percent}%",
            )
        elif current is not None and total:
            computed_percent = int(round((float(current) / float(total)) * 100))
            stage_bar.progress(
                min(1.0, max(0.0, float(current) / float(total))),
                text=f"Etapa atual: {computed_percent}%",
            )

    with st.spinner("Executando pipeline..."):
        result = run_search_pipeline(progress_callback=update_progress)
    overall_bar.progress(1.0, text="Progresso geral: 100%")
    stage_bar.progress(1.0, text="Etapa atual: 100%")
    status_box.update(label="Busca concluída", state="complete", expanded=False)
    st.success(
        f"Busca concluída: {result['found_count']} encontradas, "
        f"{result['new_count']} novas, {result['elapsed_seconds']}s."
    )
    st.rerun()

with st.expander("Manutenção"):
    confirm_clear = st.checkbox("Confirmo que quero apagar oportunidades, resultados brutos e histórico")
    if st.button("Limpar dados locais", disabled=not confirm_clear):
        removed_files = clear_local_data()
        if removed_files:
            st.success(f"Dados removidos: {', '.join(removed_files)}")
        else:
            st.info("Nenhum arquivo local de dados para remover.")
        st.rerun()

if df.empty:
    st.info("Nenhuma oportunidade encontrada ainda. Clique em Executar Busca para iniciar.")
    st.stop()

st.divider()

status_options = sorted(df["status_chamada"].dropna().unique()) if "status_chamada" in df else []
potential_options = sorted(df["potencial_negocio"].dropna().unique()) if "potencial_negocio" in df else []
categories = sorted(df["categoria"].dropna().unique()) if "categoria" in df else []

default_status = [status for status in ["ABERTA"] if status in status_options]
default_potential = [item for item in ["ALTO", "MEDIO"] if item in potential_options]
if not default_potential:
    default_potential = potential_options

filter_cols = st.columns([1.1, 1.1, 1.3, 0.9, 1.1])
selected_status = filter_cols[0].multiselect("Status da chamada", status_options, default=default_status)
selected_potential = filter_cols[1].multiselect(
    "Potencial de negócio", potential_options, default=default_potential
)
selected_categories = filter_cols[2].multiselect("Categoria", categories, default=categories)
min_score = filter_cols[3].slider("Score mínimo", 0, 10, 0)
deadline_window = filter_cols[4].number_input(
    "Prazo nos próximos X dias", min_value=0, max_value=365, value=0, step=1
)
text_query = st.text_input("Busca textual", placeholder="Digite termo, tecnologia, organização ou edital")

filtered = df.copy()
if selected_status:
    filtered = filtered[filtered["status_chamada"].isin(selected_status)]
if selected_potential:
    filtered = filtered[filtered["potencial_negocio"].isin(selected_potential)]
if selected_categories:
    filtered = filtered[filtered["categoria"].isin(selected_categories)]
filtered = filtered[filtered["score_aderencia"] >= min_score]
if deadline_window:
    filtered = filtered[
        (filtered["dias_restantes"].notna())
        & (filtered["dias_restantes"] >= 0)
        & (filtered["dias_restantes"] <= deadline_window)
    ]
if text_query:
    searchable = filtered.fillna("").astype(str).agg(" ".join, axis=1).str.lower()
    filtered = filtered[searchable.str.contains(text_query.lower(), regex=False)]

st.subheader("Oportunidades")
st.write(f"{len(filtered)} resultado(s) filtrado(s)")

visible_columns = [
    "novo",
    "status_chamada",
    "potencial_negocio",
    "score_aderencia",
    "dias_restantes",
    "prazo_inscricao",
    "data_publicacao",
    "categoria",
    "organizacao",
    "nome_oportunidade",
    "tecnologias_relacionadas",
    "recomendacao_acao",
    "motivo_classificacao",
    "url",
]
visible_columns = [column for column in visible_columns if column in filtered.columns]

st.dataframe(
    filtered[visible_columns],
    use_container_width=True,
    hide_index=True,
    column_config={
        "url": st.column_config.LinkColumn("URL"),
        "score_aderencia": st.column_config.ProgressColumn(
            "Score", min_value=0, max_value=10, format="%d"
        ),
    },
)

export_col1, export_col2 = st.columns(2)
if OPPORTUNITIES_XLSX.exists():
    export_col1.download_button(
        "Exportar Excel",
        data=OPPORTUNITIES_XLSX.read_bytes(),
        file_name="opportunities.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
if OPPORTUNITIES_CSV.exists():
    export_col2.download_button(
        "Exportar CSV",
        data=OPPORTUNITIES_CSV.read_bytes(),
        file_name="opportunities.csv",
        mime="text/csv",
    )

with st.expander("Histórico de execuções"):
    st.dataframe(pd.DataFrame(load_history()), use_container_width=True, hide_index=True)
