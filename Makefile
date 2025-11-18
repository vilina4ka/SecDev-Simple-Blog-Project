.PHONY: help build up down dev lint test security-scan clean docker-lint image-scan sbom

help:
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

build: ## Build production image
	docker build -t simple-blog-app:latest .

build-dev: ## Build development image
	docker build -f Dockerfile.dev -t simple-blog-app:dev .

up: ## Start production services
	docker compose --profile production up -d

down: ## Stop all services
	docker compose down

dev: ## Start development services
	docker compose --profile dev up

logs: ## Show logs from production services
	docker compose --profile production logs -f

logs-dev: ## Show logs from development services
	docker compose --profile dev logs -f

test: ## Run tests
	docker run --rm -v $(PWD):/app -w /app simple-blog-app:dev pytest

lint: ## Run code linting
	docker run --rm -v $(PWD):/app -w /app simple-blog-app:dev ruff check .

format: ## Format code
	docker run --rm -v $(PWD):/app -w /app simple-blog-app:dev ruff format .

docker-lint: ## Lint Dockerfile with Hadolint
	docker run --rm -i hadolint/hadolint < Dockerfile

image-scan: ## Scan image for vulnerabilities with Trivy
	docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
		-v $(PWD):/workspace aquasec/trivy:latest image \
		--format table \
		--ignore-unfixed \
		--output /workspace/trivy-report.txt \
		simple-blog-app:latest

sbom: ## Generate SBOM with Trivy
	docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
		-v $(PWD):/workspace aquasec/trivy:latest image \
		--format spdx-json \
		--output /workspace/sbom.json \
		simple-blog-app:latest

health-check: ## Check application health
	curl -f http://localhost:8000/health || echo "Health check failed"

clean: ## Remove containers, images, and volumes
	docker compose down -v --remove-orphans
	docker image rm simple-blog-app:latest simple-blog-app:dev 2>/dev/null || true
	docker system prune -f

ci-build: build
ci-test: test
ci-lint: lint docker-lint
ci-security: image-scan sbom
ci-all: ci-build ci-lint ci-test ci-security