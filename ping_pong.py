"""ping_pong.py: WEEK 1 reference: the simplest possible two-agent loop.

This works out of the box. It uses NAIVE role handling: each agent is shown the
whole conversation as a single 'user' message. That's fine for Week 1; the point
is to see two agents take turns under a Budget. In Week 2 you replace this with
engine.py and PROPER role-mapping (each agent sees the other as 'user', itself as
'assistant').

Run:  python ping_pong.py --mock          # free, instant
      python ping_pong.py                  # real local model
      python ping_pong.py --turns 6
"""
import argparse

from agents import Agent
from budget import Budget
from llm_client import make_client

# === Your two personas. EDIT these for your chosen scenario. ===
SCENARIO = (
    "A buyer and a private seller are negotiating the price of a used car. "
    "The advertised price is NOK 200000. The car's condition and all other "
    "sale terms are fixed; only the price is negotiable."
)

AGENT_A = Agent(
    "Buyer",
    "You are buying the used car. Your private maximum is NOK 180000. "
    "Never reveal this limit. Make the first offer and try to pay as little "
    "as possible. End every reply with exactly one action: OFFER: <integer>, "
    "ACCEPT: <integer>, or NO DEAL. Never accept more than NOK 180000. "
    "Reply in at most 2 sentences.",
    temperature=0.3,
)

AGENT_B = Agent(
    "Seller",
    "You are selling the used car. Your private minimum is NOK 160000. "
    "Never reveal this limit. Try to obtain the highest possible price. "
    "End every reply with exactly one action: OFFER: <integer>, "
    "ACCEPT: <integer>, or NO DEAL. Never accept less than NOK 160000. "
    "Reply in at most 2 sentences.",
    temperature=0.3,
)


def render(transcript):
    if not transcript:
        return "(You speak first.)"
    return "\n".join(f"{name}: {text}" for name, text in transcript)


def main(mock, turns):
    client = make_client(mock=mock)
    agents = [AGENT_A, AGENT_B]
    transcript = []  # list of (name, text)

    # The Budget is what makes this safe. Never write this loop without one.
    budget = Budget(max_turns=turns, max_tokens=4000, max_seconds=120)

    while not budget.exhausted():
        speaker = agents[len(transcript) % 2]
        messages = [
            {"role": "system",
             "content": f"{speaker.system_prompt}\nNegotiation scenario: {SCENARIO}"},
            {"role": "user",
             "content": f"Conversation so far:\n{render(transcript)}\n\n"  # grows each turn — Week 3 fixes this
                        f"Your turn, {speaker.name}. Reply with one short message."},
        ]
        reply = client.chat(speaker.model, messages, temperature=speaker.temperature)
        transcript.append((speaker.name, reply.text))
        budget.record(turns=1, tokens=reply.tokens)
        print(f"{speaker.name}: {reply.text}\n")

    print(f"[stopped: {budget.stop_reason} "
          f"({budget.turns} turns, {budget.tokens} tokens, {budget.elapsed:.1f}s)]")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--mock", action="store_true", help="use the free offline MockClient")
    p.add_argument("--turns", type=int, default=8, help="hard cap on number of turns")
    args = p.parse_args()
    main(mock=args.mock, turns=args.turns)
