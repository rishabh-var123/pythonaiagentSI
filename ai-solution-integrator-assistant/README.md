# AI Solution Integrator Assistant

Python 3.12 application using FastAPI, Streamlit, and SQLite for flow validation and RCA reporting.

## Project Structure

```text
app/
api/
services/
parsers/
models/
utils/
ui/
flows/
uploads/
reports/
tests/
requirements.txt
README.md
```

## FastAPI

Run locally:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open:

```text
http://localhost:8000
http://localhost:8000/docs
```

## Streamlit

Run the dashboard while the FastAPI service is running:

```bash
streamlit run ui/dashboard.py
```

Set `API_BASE_URL` if the API runs somewhere other than `http://localhost:8000`.

## Docker

Build the image:

```bash
docker build -t ai-solution-integrator-assistant .
```

Run the application:

```bash
docker run --rm -p 8000:8000 ai-solution-integrator-assistant
```

Open:

```text
http://localhost:8000
http://localhost:8000/docs
```
