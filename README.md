# Used-car negotiation — KIUA2003 Compulsory 1

This project uses two local language-model agents, a Buyer and a Seller, to negotiate the price of a used car advertised at NOK 200,000. Only the price is negotiable. A Python dialogue engine controls turn-taking, prepares each agent's conversation view, checks budgets and agreement, and saves the results. A separate judge evaluates the completed conversation.

## Requirements

- Python 3.10 or newer.
- Python packages: `requests` and `PyYAML`.
- Ollama with `llama3.2:3b` for real-model runs.

## Installation

Open PowerShell in the project folder and run:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install requests PyYAML
ollama pull llama3.2:3b
```

Keep Ollama running. If the Ollama application is not already serving the model, run `ollama serve` in another terminal. The client connects to `http://localhost:11434`.

## Run the project

From the project folder:

```powershell
.\.venv\Scripts\python.exe run.py --config configs/negotiation_t05.yaml
```

With the Python environment already active, the equivalent command is:

```powershell
python run.py --config configs/negotiation_t05.yaml
```

This configuration uses temperature 0.5 for both agents and limits of 12 turns, 8,000 tokens and 120 seconds. After the dialogue finishes, the program prints the replies, evaluates the transcript and prints the judge result and stop summary. It saves the result to `transcripts/negotiation_t05.json`.

Output files are overwritten on reruns. Run from a working copy or set a fresh `output` filename in the YAML to preserve the original experiment evidence.

## Offline mock mode

```powershell
.\.venv\Scripts\python.exe run.py --config configs/negotiation_t05.yaml --mock
```

Mock mode works without Ollama but still requires the Python packages. The supplied mock client returns canned plain text, so the engine exercises JSON validation, one retry and fallback handling. Fallback replies have `offer=0` and `accepted=false`; the run ends on a budget limit. The mock judge returns invalid JSON and therefore produces `null` score and success values. These are expected properties of this mock client, not real-model experiment results. Mock mode writes to the same configured output path as real mode.

For a single-call smoke test:

```powershell
.\.venv\Scripts\python.exe run.py --mock
```

## Project files

| Path | Purpose |
| --- | --- |
| `run.py` | Loads YAML, runs the engine, checks agreement and adds the judge result. |
| `engine.py` | Role mapping, turn-taking, context truncation, JSON validation and transcript saving. |
| `agents.py` | Agent names, prompts, models and temperatures. |
| `budget.py` | Turn, token and elapsed-time limits and counters. |
| `llm_client.py` | Ollama HTTP client and offline mock client. |
| `judge.py` | Evaluation rubric and judge-response validation. |
| `ping_pong.py` | Earlier Week 1 implementation. |
| `configs/` | Main, temperature-experiment and failure configurations. |
| `transcripts/` | Saved JSON conversations and evaluation evidence. |
| `design.md` | Scenario, complete main-agent prompts and goal definition. |

Python modules use the filenames shown above, without upload suffixes such as `(2)`.

## Agreement and stopping

Agent replies contain `message`, `offer` and `accepted`. Agreement requires the latest reply to explicitly accept the preceding agent's exact positive offer. The program then stops with `goal_reached`. Otherwise, it stops on `max_turns`, `max_tokens` or `max_seconds`.

One turn is one agent message. An invalid reply receives one retry; both calls contribute to that turn's costs. Budget checks happen between turns and cannot interrupt an in-progress model call. The HTTP request timeout is 300 seconds.

The context policy keeps the system prompt and latest 19 conversation messages. The full transcript remains available for saving and judging. This limits message count, not token count, and can discard earlier commitments during longer conversations.

## Experiments and failure example

The temperature comparison uses `negotiation_t0.yaml`, `negotiation_t07.yaml` and `negotiation_t1.yaml`, with three saved runs per setting. The 0.5 configuration is an additional demonstration run. Select a configuration with `--config` and use a distinct output filename for each repetition.





The 0.7 and 0.5 configurations share an output path, so running either can replace that file. Use separate output names when collecting new evidence.

Run the failure configuration with:

```powershell
.\.venv\Scripts\python.exe run.py --config configs/fail-hallucination.yaml
```

It instructs the Buyer to start at NOK 130,000 and the Seller at NOK 200,000, with subsequent concessions limited by the prompts to NOK 5,000 per step. These bargaining rules are prompt instructions, not Python-enforced constraints. Both agents use temperature 1.7. The saved failure example demonstrates flawed reasoning and instruction-following despite reaching a price agreement.

The failure transcript's metadata retains the configuration path `configs/fail-drift.yaml`, and the supplied failure YAML retains the output name `fail-drift.json`. The files are presented under the `fail-hallucination` label; the historical transcript metadata is preserved.

## Saved results and evaluation

Each transcript contains run metadata, agent settings, budget information, aggregate costs and every message with its speaker, content, token counts, duration and turn index. Full prompts are stored in the configurations. The separate judge uses `llama3.2:3b` at temperature 0 and returns a reason, score from 1 to 5, and success flag. Invalid evaluations have `null` score and success values.

Token totals include prompt and completion tokens, including agent retries. `budget.seconds` measures elapsed negotiation time, while `totals.seconds` sums model-call durations. Negotiation metrics are saved before the judge call and exclude its costs. Judge scores are imperfect estimates; the deterministic acceptance check is the primary measure of agreement.

Exact configurations and saved transcripts document what was run and what it produced. Repeated runs can differ, including at temperature 0.

## Sources and assistance

The project builds on the course starter code. ChatGPT assisted with the implementation and explanation of role mapping, the dialogue loop, context truncation, structured-reply validation and retries, the agreement check, judge evaluation and integration, debugging, and documentation. The starter structures, including the Agent dataclass, Budget class and model-client scaffolding, were retained. This README and the design document were drafted with ChatGPT assistance from the project files.
