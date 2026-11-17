.PHONY: install data test eval run docker

install:
	pip install -r requirements-dev.txt

data:
	python -m data.generate --rental 15 --service 15 --other 4 --seed 42

test:
	pytest -q

eval:
	python -m eval.run_eval --concurrency 4

run:
	uvicorn app.main:app --reload --port 8080

docker:
	docker build -t contract-extractor . && docker run --rm -p 8080:8080 --env-file .env contract-extractor
