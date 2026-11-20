# CaseDesk Live

An original duplicate-charge investigation demo with typed complaints, streamed workflow events, and human review. All transaction records and policies are fictional. Use synthetic complaints only.

## Quick start on Windows

With Python 3 installed, save CaseDesk-Live.zip in Downloads and paste into PowerShell:

```powershell
Set-Location "$env:USERPROFILE\Downloads"
Expand-Archive .\CaseDesk-Live.zip -DestinationPath .
Set-Location .\CaseDesk-Live
py -3 app.py
```

Open http://127.0.0.1:8000. If the Python launcher is unavailable, use `python app.py`. Ctrl+C stops the server.

## Enable the live LLM

Stop the server. Set a Groq API key for this PowerShell session and restart:

```powershell
$env:GROQ_API_KEY = Read-Host "Paste your Groq API key"
py -3 app.py
```

The workflow trace displays **Groq LLM** when the API classifies the complaint. It sends the complaint to Groq and validates the returned JSON before using it. The default model is llama-3.3-70b-versatile. Set GROQ_MODEL to override it with a compatible JSON-mode model. To return to the offline parser, stop the server, run `Remove-Item Env:GROQ_API_KEY`, and restart it.

## Run the evaluation

In a second PowerShell window, work from the extracted project folder and run `py -3 evaluate.py`. Run `py -3 evaluate.py --require-llm` to require live Groq results. The evaluation creates and approves synthetic records in the local SQLite database.

## Demo and architecture

1. Enter “I was charged $84.50 twice.” Run **Pending and posted**, then **Two posted charges**. Show how transaction evidence changes the retrieved policy and the outcome.
2. Run **Two matching merchants** with the same complaint. Select Cedar Market when prompted.
3. Approve or reject the resulting draft. The decision is saved locally in SQLite.

Groq extracts intent, amount, and merchant. Python branches on the transaction evidence, ranks fictional policy excerpts by keyword overlap, and builds a cited response from templates. A newline-delimited JSON stream displays observable workflow events as they occur. SQLite stores drafts and accepts only one decision per case. The offline parser is designed for common demo phrasing. CaseDesk uses simulated transactions and never submits a real dispute.
