# CaseDesk Credit Union Voice Assistant

CaseDesk Live investigates duplicate card charges using synthetic transactions and fictional policies. It streams investigation steps to the browser and sends possible disputes to a human reviewer.

## Quick start

Requires Git and Python 3. The offline demo needs no API key or extra Python packages.

```powershell
git clone https://github.com/gireeshvuyyuru501-design/casedesk-live.git
cd casedesk-live
py -3 app.py
```

Open [CaseDesk Live](http://127.0.0.1:8000) while the server is running. If `py` is unavailable, run `python app.py`.

## Try the demo

Enter **I was charged $84.50 twice.** Run each scenario with the same complaint.

| Scenario | What CaseDesk does |
| --- | --- |
| Pending and posted | Explains the authorization hold and cites `SIM-01`. |
| Two posted charges | Cites `SIM-02` and prepares a draft. Approve or reject it to save your decision locally. |
| Two matching merchants | Asks which purchase to investigate before continuing. |

## Try voice input

Open the demo in a browser that supports Web Speech recognition and choose **Use microphone**. Say “I was charged eighty-four dollars and fifty cents twice.” Review the transcript and adjust the amount to `$84.50` if your browser spells it out. Select **Investigate**, then **Read result aloud** to hear the result when speech synthesis is available. Typed input remains available. Speech recognition may send audio to the browser provider. Use fictional details.

This independent portfolio demo uses simulated records. It was inspired by [public descriptions of credit-union voice assistants](https://www.cutx.org/learn/sam-your-virtual-assistant).

## Tools used

| Tool | Role |
| --- | --- |
| Python standard library | HTTP server, transaction rules, keyword policy retrieval, and streamed JSON events |
| SQLite | Local storage for dispute drafts and reviewer decisions |
| HTML, CSS, and JavaScript | Interactive dashboard and workflow trace |
| Groq API | Optional LLM extraction of complaint intent, amount, and merchant |

## Project files

- `app.py` runs the server and investigation workflow.
- `intent.py` handles offline parsing and optional Groq routing.
- `index.html` contains the browser interface.
- `policies.json` contains the fictional policies.
- `evaluate.py` runs seven workflow checks.

## Optional Groq mode

Stop the server, then restart it with a Groq API key. Use only fictional complaints because Groq receives the complaint text in this mode.

```powershell
$env:GROQ_API_KEY = Read-Host "Enter your Groq API key"
py -3 app.py
```

The workflow trace shows **Groq LLM** when model routing is active. Python rules determine the case outcome from the transaction evidence.

## Evaluation

With the server running, open a second terminal in the project folder and run `py -3 evaluate.py`. To require live Groq routing, run `py -3 evaluate.py --require-llm`. The evaluation saves synthetic cases in the local database.

## License

[MIT](LICENSE)
