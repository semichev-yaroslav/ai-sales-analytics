.PHONY: install run api test backfill

install:
	python3 -m pip install -e .[dev]

run:
	ai-sales-analytics run-daily

api:
	ai-sales-analytics serve

test:
	python3 -m pytest

backfill:
	ai-sales-analytics backfill --start-date 2026-03-01 --end-date 2026-03-10
