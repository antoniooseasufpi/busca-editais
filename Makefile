SHELL := /bin/zsh

PYTHON ?= .venv/bin/python
PIP ?= .venv/bin/pip
STREAMLIT ?= .venv/bin/streamlit

OLLAMA ?= ollama
OLLAMA_HOST ?= http://localhost:11434
OLLAMA_MODEL ?= qwen3:8b
OLLAMA_LOG ?= radar_agro/data/ollama.log
OLLAMA_PID ?= radar_agro/data/ollama.pid

STREAMLIT_APP ?= radar_agro/dashboard/app.py
STREAMLIT_PORT ?= 8502

.PHONY: help up setup check-ollama ollama-start ollama-pull ollama-status streamlit run-search stop-ollama logs

help:
	@echo "Radar Agro - comandos locais"
	@echo ""
	@echo "  make up             Prepara ambiente, sobe Ollama, baixa modelo e abre Streamlit"
	@echo "  make setup          Cria .venv se necessario e instala requirements"
	@echo "  make ollama-start   Sobe o servidor local do Ollama em background"
	@echo "  make ollama-pull    Baixa/atualiza o modelo configurado em OLLAMA_MODEL"
	@echo "  make ollama-status  Mostra modelos disponiveis no Ollama local"
	@echo "  make streamlit      Inicia o dashboard Streamlit"
	@echo "  make run-search     Executa a busca pela linha de comando"
	@echo "  make stop-ollama    Para o processo do Ollama iniciado pelo Makefile"
	@echo "  make logs           Mostra o log local do Ollama"
	@echo ""
	@echo "Variaveis uteis:"
	@echo "  OLLAMA_MODEL=qwen3:8b|llama3:8b|mistral"
	@echo "  STREAMLIT_PORT=8502"

up: setup check-ollama ollama-start ollama-pull streamlit

setup:
	@if [ ! -x "$(PYTHON)" ]; then \
		echo "Criando ambiente virtual .venv..."; \
		python3 -m venv .venv; \
	fi
	@$(PIP) install -r requirements.txt

check-ollama:
	@command -v "$(OLLAMA)" >/dev/null 2>&1 || { \
		echo "Ollama nao encontrado no PATH."; \
		echo "Instale em https://ollama.com/download ou via Homebrew: brew install ollama"; \
		exit 1; \
	}
	@$(OLLAMA) --version

ollama-start:
	@mkdir -p radar_agro/data
	@if curl -fsS "$(OLLAMA_HOST)/api/tags" >/dev/null 2>&1; then \
		echo "Ollama ja esta rodando em $(OLLAMA_HOST)."; \
	else \
		echo "Subindo Ollama em background..."; \
		nohup "$(OLLAMA)" serve > "$(OLLAMA_LOG)" 2>&1 & echo $$! > "$(OLLAMA_PID)"; \
		for i in {1..30}; do \
			if curl -fsS "$(OLLAMA_HOST)/api/tags" >/dev/null 2>&1; then \
				echo "Ollama pronto em $(OLLAMA_HOST)."; \
				exit 0; \
			fi; \
			sleep 1; \
		done; \
		echo "Ollama nao respondeu em ate 30s. Veja o log com: make logs"; \
		exit 1; \
	fi

ollama-pull:
	@echo "Garantindo modelo local: $(OLLAMA_MODEL)"
	@$(OLLAMA) pull "$(OLLAMA_MODEL)"

ollama-status:
	@curl -fsS "$(OLLAMA_HOST)/api/tags" || { \
		echo ""; \
		echo "Ollama nao esta respondendo em $(OLLAMA_HOST). Rode: make ollama-start"; \
		exit 1; \
	}

streamlit:
	@echo "Abrindo dashboard em http://localhost:$(STREAMLIT_PORT)"
	@$(STREAMLIT) run "$(STREAMLIT_APP)" --server.port "$(STREAMLIT_PORT)"

run-search:
	@$(PYTHON) main.py

stop-ollama:
	@if [ -f "$(OLLAMA_PID)" ]; then \
		PID=$$(cat "$(OLLAMA_PID)"); \
		if kill -0 "$$PID" >/dev/null 2>&1; then \
			echo "Parando Ollama iniciado pelo Makefile: $$PID"; \
			kill "$$PID"; \
		else \
			echo "PID salvo nao esta mais ativo: $$PID"; \
		fi; \
		rm -f "$(OLLAMA_PID)"; \
	else \
		echo "Nenhum PID local encontrado em $(OLLAMA_PID)."; \
	fi

logs:
	@if [ -f "$(OLLAMA_LOG)" ]; then \
		tail -n 80 "$(OLLAMA_LOG)"; \
	else \
		echo "Log ainda nao existe: $(OLLAMA_LOG)"; \
	fi
