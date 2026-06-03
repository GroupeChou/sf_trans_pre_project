.PHONY: help install dev test run docker-build docker-up docker-down clean

help:
	@echo "中转场地在线预测智能体平台 — Development Commands"
	@echo "=============================================="
	@echo "make install      — Install dependencies"
	@echo "make dev          — Install dev dependencies"
	@echo "make test        — Run all tests"
	@echo "make test-cov    — Run tests with coverage"
	@echo "make run         — Run development server"
	@echo "make docker-build— Build Docker image"
	@echo "make docker-up   — Start all services"
	@echo "make docker-down — Stop all services"
	@echo "make lint        — Run linting"
	@echo "make clean       — Clean cache files"

install:
	pip install -r requirements.txt

dev:
	pip install -e ".[dev]"

test:
	pytest tests/ -v

test-cov:
	pytest tests/ -v --cov=src --cov-report=term-missing

run:
	uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

docker-build:
	docker compose build

docker-up:
	docker compose up -d

docker-down:
	docker compose down

lint:
	ruff check src/ tests/

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
