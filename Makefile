# -------------------------------------------
# File: Makefile
# -------------------------------------------
install:
	pip install -e .

run:
	ai-review

dashboard:
	cd web_dashboard && flask run

docker-build:
	docker build -t ai-code-reviewer .

docker-run:
	docker run --rm --env-file .env ai-code-reviewer