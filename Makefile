.PHONY: install run dev test lint fmt

install:
	pip install -r requirements.txt

run:
	python app.py

dev:
	uvicorn app:app --reload --port 8000

test:
	pytest

lint:
	ruff check .

fmt:
	black .
