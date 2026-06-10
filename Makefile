.PHONY: dev test lint docker-build cli cli-py

dev:
	docker-compose up

test:
	pytest tests/

lint:
	ruff check backend/

cli:
	cd checkmate-cli && npm start

cli-py:
	python -m checkmate_cli.main
