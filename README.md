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

## Requirements

- Windows 10/11
- Python 3.11+ recommended (your environment uses 3.13)
- Node.js 18+ (only if you want the optional React UI)
- Ollama installed and running

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

## Setup (Python)

Create and activate a venv, then install requirements:

```powershell
cd D:\Projects\Lucio
python -m venv .venv
& .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Environment variables

Create a `.env` in the project root (or set env vars in PowerShell):

- `PICOVOICE_ACCESS_KEY` (required for Porcupine)

Example `.env`:

```env
PICOVOICE_ACCESS_KEY=your_key_here
```

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

## Optional: React UI (debug/dashboard)

If you want the optional frontend:

```powershell
cd D:\Projects\Lucio\frontend
npm install
npm run dev
```

Backend must be running too (the launcher already starts it).

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

