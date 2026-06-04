.PHONY: install dev seed run test lint format migrate

install:
	pip install -e ".[dev]"

seed:
	python -m app.db.seed

run:
	uvicorn app.main:app --reload

test:
	pytest

lint:
	ruff check app tests

format:
	ruff format app tests

migrate:
	alembic revision --autogenerate -m "$(m)"

upgrade:
	alembic upgrade head
