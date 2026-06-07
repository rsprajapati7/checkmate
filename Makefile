.PHONY: dev test lint docker-build

dev:
	docker-compose up

test:
	pytest tests/

lint:
	ruff check backend/
