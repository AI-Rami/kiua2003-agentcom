"""
test_judge.py

Simple sanity test for the Week 3 judge.

We create:
1. an obviously good negotiation
2. an obviously bad negotiation

The good negotiation should receive a higher judge score.
"""

from engine import Entry
from judge import judge


# ---------------------------------------------------------
# GOOD NEGOTIATION
# ---------------------------------------------------------
#
# Buyer and Seller clearly agree on the same final price.
good_transcript = [
    Entry(
        speaker="Buyer",
        content="I can offer NOK 170000.",
        prompt_tokens=0,
        completion_tokens=0,
        seconds=0,
        turn_index=0,
    ),
    Entry(
        speaker="Seller",
        content="I can accept NOK 175000.",
        prompt_tokens=0,
        completion_tokens=0,
        seconds=0,
        turn_index=1,
    ),
    Entry(
        speaker="Buyer",
        content="Agreed. I accept NOK 175000.",
        prompt_tokens=0,
        completion_tokens=0,
        seconds=0,
        turn_index=2,
    ),
    Entry(
        speaker="Seller",
        content="Agreed. The final price is NOK 175000.",
        prompt_tokens=0,
        completion_tokens=0,
        seconds=0,
        turn_index=3,
    ),
]


# ---------------------------------------------------------
# BAD NEGOTIATION
# ---------------------------------------------------------
#
# The agents do not reach an agreement and the conversation
# becomes irrelevant.
bad_transcript = [
    Entry(
        speaker="Buyer",
        content="I offer NOK 170000.",
        prompt_tokens=0,
        completion_tokens=0,
        seconds=0,
        turn_index=0,
    ),
    Entry(
        speaker="Seller",
        content="What is your favourite colour?",
        prompt_tokens=0,
        completion_tokens=0,
        seconds=0,
        turn_index=1,
    ),
    Entry(
        speaker="Buyer",
        content="Blue.",
        prompt_tokens=0,
        completion_tokens=0,
        seconds=0,
        turn_index=2,
    ),
    Entry(
        speaker="Seller",
        content="I like cats.",
        prompt_tokens=0,
        completion_tokens=0,
        seconds=0,
        turn_index=3,
    ),
]


# ---------------------------------------------------------
# ASK THE JUDGE TO EVALUATE BOTH
# ---------------------------------------------------------

print("GOOD TRANSCRIPT:")
good_result = judge(good_transcript)
print(good_result)

print("\nBAD TRANSCRIPT:")
bad_result = judge(bad_transcript)
print(bad_result)