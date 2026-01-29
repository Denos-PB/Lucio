# Lucio

Voice-first local agent for summarizing the current webpage into a PDF.

## What it does (MVP)

- Runs in the background
- Wake word: **"Lucio"**
- Listens to your request (voice)
- Looks at your screen (browser)
- Extracts the current URL (vision)
- Scrapes the page
- Creates a readable PDF summary
- Stores each run in PostgreSQL as history

---

## Requirements

- Windows 10/11
- Python 3.11+ recommended (your environment uses 3.13)
- PostgreSQL 14+ (local or Docker)
- Ollama installed and running

---

## Models (Ollama)

You must have these models available:

- **Vision**: `llava:7b`
- **Text**: `llama3.2:latest`

Check installed models:

```powershell
ollama list
```

If missing, pull them:

```powershell
ollama pull llava:7b
ollama pull llama3.2:latest
```

---

## PostgreSQL setup

### 1. Create database and user

In `psql` (or any Postgres client), run:

```sql
CREATE DATABASE lucio;
CREATE USER lucio_user WITH PASSWORD 'your_strong_password';
GRANT ALL PRIVILEGES ON DATABASE lucio TO lucio_user;
```

### 2. `.env` configuration

In the project root, your `.env` should include:

```env
PICOVOICE_ACCESS_KEY=your_picovoice_key_here
DATABASE_URL=postgresql+psycopg2://lucio_user:your_strong_password@localhost:5432/lucio
```

Adjust host/port/user/password/db name to match your setup.

Lucio will:

- Connect to this DB on startup,
- Auto-create a `conversations` table,
- Insert one row per `/run` with prompt, URL, status, PDF path, and errors.

---

## Python setup

Create and activate a venv, then install requirements:

```powershell
cd D:\Projects\Lucio
python -m venv .venv
& .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

---

## Run (one command)

This starts both the backend API and the voice listener:

```powershell
cd D:\Projects\Lucio
& .\.venv\Scripts\Activate.ps1
python .\run_lucio.py
```

### How to use

1. Open a browser page on screen  
2. Say **"Lucio"**  
3. Say your request, e.g. **"Summarize this page and create a PDF"**  
4. The console prints the PDF path when done

PDFs are saved under `./outputs`.

Each run is also stored in the `conversations` table in your PostgreSQL `lucio` database.

Backend must be running too (`run_lucio.py` already starts it).

---

## Troubleshooting

### Listener says it can't connect to `127.0.0.1:8000`

The backend is not running. Use the one-command launcher:

```powershell
python .\run_lucio.py
```

### Perception node times out

`llava:7b` can be slow on CPU. Try warming it up:

```powershell
ollama run llava:7b "Say hi"
```

Also ensure Ollama server is running:

```powershell
ollama serve
```

### Model not found (404)

Your config must match model names shown in:

```powershell
ollama list
```

For example, your config uses `llama3.2:latest` and `llava:7b`.

### DATABASE_URL errors

If you see:

> `DATABASE_URL environment variable is not set`

make sure your `.env` has a valid `DATABASE_URL` and that PostgreSQL is running, e.g.:

```env
DATABASE_URL=postgresql+psycopg2://lucio_user:your_strong_password@localhost:5432/lucio
```