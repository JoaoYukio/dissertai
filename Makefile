run_api:
	@echo "Running API through UV"
	cd backend && uvicorn main:app --host 0.0.0.0 --port 5000 --reload