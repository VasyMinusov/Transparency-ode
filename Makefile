# ══════════════════════════════════════════════════════════════════
#  Код прозрачности — управление проектом из корня репозитория
#  Запуск: make          (покажет список команд)
# ══════════════════════════════════════════════════════════════════
SHELL := /bin/bash

API_DIR   := transparency-api
CLIENT_DIR := transparency-client

.PHONY: help install install-api install-client dev demo server client web test lint tui reset-db stego-check clean clean-all

help: ## Список команд
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  make %-18s %s\n", $$1, $$2}'

# ── Установка ────────────────────────────────────────────────────
install: install-api install-client ## Установить всё (uv sync + pnpm install)

install-api:
	cd $(API_DIR) && uv sync

install-client:
	cd $(CLIENT_DIR) && pnpm install

# ── Запуск ───────────────────────────────────────────────────────
server: ## Запустить сервер данных (терминал 1)
	cd $(API_DIR) && uv run uvicorn app.main:app --port 8000 --reload

client: ## Запустить оконное приложение (терминал 2, нужен server)
	cd $(CLIENT_DIR) && pnpm tauri dev

web: ## Интерфейс в браузере без Tauri (терминал 2, нужен server)
	cd $(CLIENT_DIR) && pnpm dev

demo: ## Одной командой: сервер в фоне + приложение (Ctrl+C остановит всё)
	@echo "Запускаем сервер данных…"
	cd $(API_DIR) && uv run uvicorn app.main:app --port 8000 & SERVER_PID=$$!; \
	trap "kill $$SERVER_PID 2>/dev/null" EXIT; \
	sleep 3; \
	cd $(CLIENT_DIR) && pnpm tauri dev

# ── Проверки и инструменты ───────────────────────────────────────
test: ## Запустить тесты бэкенда
	cd $(API_DIR) && uv run pytest -v

lint: ## Проверить код линтером
	cd $(API_DIR) && uv run ruff check .

tui: ## Терминальный клиент (нужен запущенный server)
	cd $(API_DIR) && uv run python tools/tui_client.py

eval: ## Оценка качества правил (precision/recall, пишет data/eval_report.json)
	cd $(API_DIR) && uv run python tools/eval_rules.py

reset-db: ## Пересоздать базу данных (удалить transparency.db)
	rm -f $(API_DIR)/data/transparency.db
	@echo "База удалена. Она создастся заново при следующем запуске сервера."

stego-check: ## Извлечь скрытую фразу из иконки (LSB)
	cd $(CLIENT_DIR)/tools && python stego_lsb.py extract ../src-tauri/icons/icon.png

# ── Сборка и очистка ─────────────────────────────────────────────
build: ## Собрать дистрибутив приложения
	cd $(CLIENT_DIR) && pnpm tauri build

clean: ## Убрать артефакты сборки (dist, target, кэши)
	rm -rf $(CLIENT_DIR)/dist $(CLIENT_DIR)/src-tauri/target
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

clean-all: clean reset-db ## Полная очистка + удаление базы (зависимости не трогает)
