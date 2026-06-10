.PHONY: install run run-prod test clean

install:
	conda run -n olp pip install -r requirements.txt

run:
	conda run -n olp uvicorn serve:app --host 0.0.0.0 --port 8000 --reload

run-prod:
	conda run -n olp uvicorn serve:app --host 0.0.0.0 --port 8000 --workers 4 --no-access-log

test:
	conda run -n olp python -m pytest -v

clean:
	find . -name "__pycache__" -exec rm -rf {} +
	rm -rf .pytest_cache
	rm -f rca_llm_trace.log
