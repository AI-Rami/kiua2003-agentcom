"""run.py: entry point.

Two modes:
  1. Smoke test (default): one model call, to prove your setup works.
        python run.py --mock      # free/offline
        python run.py             # real local model via Ollama
  2. Full run from a config (works once you've completed engine.py in Week 2):
        python run.py --config configs/debate.yaml
        python run.py --config configs/debate.yaml --mock
"""
import argparse
import json
from llm_client import make_client
from judge import judge

def smoke(mock):
    client = make_client(mock=mock)
    messages = [
        {"role": "system", "content": "You are terse."},
        {"role": "user", "content": "Say hello in exactly three words."},
    ]
    r = client.chat("llama3.2:3b", messages, temperature=0)
    print("Model replied:", r.text)
    print(f"(prompt={r.prompt_tokens} tokens, completion={r.completion_tokens} tokens, "
          f"{r.seconds:.2f}s)")



def negotiation_goal_reached(transcript):
    """
    Check whether the latest agent accepted the previous agent's offer.

    A deal is reached only when:
      1. There are at least two messages.
      2. The newest message has "accepted": true.
      3. The accepted price is exactly the same as the previous offer.
    """

    # We need at least one offer and one reply.
    if len(transcript) < 2:
        return False

    # Import here because parse_agent_reply is defined in engine.py.
    from engine import parse_agent_reply

    try:
        # Read the previous agent's structured reply.
        previous = parse_agent_reply(transcript[-2].content)

        # Read the newest agent's structured reply.
        current = parse_agent_reply(transcript[-1].content)

    # If either message contains invalid JSON,
    # do not stop the negotiation.
    except (json.JSONDecodeError, ValueError):
        return False

    # A deal exists only if the newest agent explicitly accepted
    # the exact price offered in the previous message.
    #the agreed price must be positive. Since both offers must match, this prevents accepting the fallback price of 0.
    return (
            current["accepted"] is True
            and current["offer"] == previous["offer"]
            and previous["offer"] > 0
    )






def run_config(path, mock):
    import yaml  # local import so the smoke test needs no extra deps

    from agents import Agent
    from budget import Budget
    from engine import DialogueEngine, truncate_context

    with open(path) as f:
        cfg = yaml.safe_load(f)
    agents = [Agent(**a) for a in cfg["agents"]]
    budget = Budget(**cfg.get("budget", {}))
    client = make_client(mock=mock)



    # Create the dialogue engine.
    #
    # manage_context tells the engine how to control
    # the size of the conversation history before it is
    # sent to the LLM.
    #
    # Here we use truncation and allow a maximum
    # of 20 messages per model call.
    engine = DialogueEngine(
        agents,
        client,
        budget,

        # Stop the conversation when one agent explicitly
        # accepts the previous agent's exact offer.
        goal_reached=negotiation_goal_reached,

        # Keep the system prompt and only the most recent
        # messages when the context becomes too large.
        manage_context=lambda messages: truncate_context(
            messages,
            max_messages=20
        ),
    )


    transcript = engine.run()

    for e in transcript:
        print(f"{e.speaker}: {e.content}\n")

    out = cfg.get("output", "transcripts/run.json")
    engine.save(out, meta={"topic": cfg.get("topic"), "config": path})
    # Evaluate the completed negotiation.
    evaluation = judge(transcript, client=client)

    # Read the transcript file we just saved.
    with open(out, "r", encoding="utf-8") as f:
        saved_run = json.load(f)

    # Add the judge's reason, score, and success flag.
    saved_run["judge"] = evaluation

    # Save the transcript together with its evaluation.
    with open(out, "w", encoding="utf-8") as f:
        json.dump(saved_run, f, indent=2)

    # Show the evaluation in the terminal.
    print("Judge:", json.dumps(evaluation, indent=2))
    print(f"[stopped: {budget.stop_reason} "
          f"({budget.turns} turns, {budget.tokens} tokens). Saved {out}]")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--mock", action="store_true", help="use the free offline MockClient")
    p.add_argument("--config", help="run a full dialogue from a YAML config")
    args = p.parse_args()
    if args.config:
        run_config(args.config, mock=args.mock)
    else:
        smoke(mock=args.mock)
