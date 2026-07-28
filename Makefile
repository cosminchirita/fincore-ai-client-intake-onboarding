.PHONY: up down logs test lint seed demo

up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f --tail=200

test:
	pytest

lint:
	ruff check .

demo:
	python scripts/send_demo_lead.py
