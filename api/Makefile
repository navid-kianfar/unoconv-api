.PHONY: help install dev test docker-build docker-run docker-stop clean

help:
	@echo "Available commands:"
	@echo "  make install       - Install dependencies"
	@echo "  make dev            - Run development server"
	@echo "  make test           - Run tests"
	@echo "  make docker-build   - Build Docker image"
	@echo "  make docker-run     - Run Docker container"
	@echo "  make docker-stop    - Stop Docker container"
	@echo "  make clean          - Clean up temp files"

install:
	pip install -r requirements.txt

dev:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:
	pytest tests/ -v

docker-build:
	docker build -t thumbnail-api:latest .

docker-run:
	docker run -p 8000:8000 --env-file .env thumbnail-api:latest

docker-build-multiarch:
	docker buildx create --name mybuilder --use || true
	docker buildx build --platform linux/amd64,linux/arm64 -t thumbnail-api:latest --push .

docker-stop:
	docker stop thumbnail-api || true

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache
	rm -rf /tmp/thumbnails/*
