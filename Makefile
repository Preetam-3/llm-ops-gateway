.PHONY: setup run stop test lint build chat logs clean install help

setup:           ## First-time setup: check deps, configure .env, create venv
	@bash setup.sh

run:             ## Start all services with Docker Compose
	docker compose up -d
	@echo "Gateway: http://localhost:8000"
	@echo "Grafana: http://localhost:4000 (admin/admin)"
	@echo "Metrics: http://localhost:8000/metrics"

stop:            ## Stop all services
	docker compose down

logs:            ## View service logs
	docker compose logs -f

test:            ## Run test suite
	.venv/bin/pytest -v

lint:            ## Run linter
	.venv/bin/ruff check app/ tests/ chat.py

build:           ## Build Docker image
	docker build -t llm-ops-gateway .

chat:            ## Send a chat message: make chat MSG="hello"
	.venv/bin/python chat.py $(MSG)

shell:           ## Open a shell in the venv
	@echo "Run: source .venv/bin/activate"

clean:           ## Remove containers, volumes, and temp files
	docker compose down -v
	rm -rf .venv __pycache__ .pytest_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; true

install:         ## Install 'chat' command system-wide (symlink to ~/.local/bin)
	mkdir -p $(HOME)/.local/bin
	ln -sf $(PWD)/chat.py $(HOME)/.local/bin/chat
	@echo "Installed: $(HOME)/.local/bin/chat -> $(PWD)/chat.py"
	@echo "Make sure ~/.local/bin is in your PATH."
	@echo "Then use: chat \"your message\""

help:            ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-12s\033[0m %s\n", $$1, $$2}'
