# Radar Agro

Aplicação local em Python + Streamlit para monitorar oportunidades de negócio no agronegócio.

## O que a aplicação faz

- Busca oportunidades por RSS, Google News RSS e scraping simples do DuckDuckGo.
- Consolida e remove duplicidades por URL.
- Classifica oportunidades com LLM local via Ollama.
- Usa `qwen3:8b` por padrão, com modelo configurável em YAML.
- Aplica um pré-filtro determinístico antes do LLM para evitar gastar tempo com notícias, cursos, eventos e chamadas encerradas.
- Usa um classificador heurístico local como fallback operacional se o Ollama não estiver em execução.
- Prioriza chamadas abertas, editais, PoCs, inovação aberta e oportunidades comerciais.
- Marca notícias, cursos, eventos, mestrados e chamadas encerradas como baixa prioridade ou descarte.
- Persiste tudo em arquivos locais dentro de `radar_agro/data/`.
- Exibe dashboard com filtros e exportação em Excel/CSV.
- Permite limpar oportunidades, resultados brutos e histórico pelo painel de manutenção.
- Mostra acompanhamento das etapas de execução com percentual geral e percentual da etapa atual.

## Estrutura

```text
radar_agro/
  config/
  crawlers/
  classifiers/
  dashboard/
  data/
  reports/
main.py
requirements.txt
README.md
```

## Instalação

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configuração do LLM local

Instale o Ollama e baixe o modelo padrão:

```bash
ollama pull qwen3:8b
ollama serve
```

A configuração fica em `radar_agro/config/app_config.yaml`:

```yaml
llm:
  provider: ollama
  model: qwen3:8b
  host: http://localhost:11434
  timeout_seconds: 90
```

Para trocar o modelo futuramente, altere apenas o campo `model`, por exemplo `llama3:8b` ou `mistral`.

## Campos principais

O arquivo final inclui os campos de prospecção:

- `data_encontrada`
- `data_publicacao`
- `prazo_inscricao`
- `status_chamada`
- `dias_restantes`
- `potencial_negocio`
- `motivo_classificacao`
- `recomendacao_acao`

Valores de `status_chamada`:

- `ABERTA`
- `ENCERRADA`
- `SEM_PRAZO_IDENTIFICADO`
- `NAO_E_CHAMADA`

Valores de `potencial_negocio`:

- `ALTO`
- `MEDIO`
- `BAIXO`
- `DESCARTAR`

Por padrão, o dashboard mostra somente `ABERTA` com potencial `ALTO` ou `MEDIO`. Os filtros permitem visualizar também encerradas e descartadas.

## Executar busca pela linha de comando

```bash
python main.py
```

## Executar dashboard

```bash
streamlit run radar_agro/dashboard/app.py
```

## Arquivos gerados

- `radar_agro/data/opportunities.xlsx`
- `radar_agro/data/opportunities.csv`
- `radar_agro/data/raw_results.json`
- `radar_agro/data/history.json`

## Decisões arquiteturais

- Não há banco de dados: Excel, CSV e JSON são suficientes para um único usuário local.
- Não há API própria, autenticação, filas ou serviços externos pagos.
- O crawler é modular para permitir novas fontes no futuro.
- A classificação por IA roda localmente no Ollama, preservando privacidade e evitando custo por API.
- O classificador tem fallback determinístico para manter a aplicação utilizável se o Ollama estiver desligado.
- O dashboard lê diretamente os arquivos locais, reduzindo pontos de falha.
