"""
test_saved_judge.py

Load a real saved negotiation transcript,
print it so we can verify its content,
and then evaluate it with the judge.
"""

import json

from engine import Entry
from judge import judge


# Load the saved transcript file.
with open("transcripts/negotiation.json") as f:
    data = json.load(f)


# Rebuild Entry objects from the JSON messages.
transcript = [
    Entry(**message)
    for message in data["messages"]
]


# ---------------------------------------------------------
# PRINT THE REAL TRANSCRIPT FIRST
# ---------------------------------------------------------
#
# Before trusting the judge, we verify exactly what dialogue
# it is being asked to evaluate.
print("SAVED TRANSCRIPT:")
print("-" * 50)

for entry in transcript:
    print(f"{entry.speaker}: {entry.content}")

print("-" * 50)


# ---------------------------------------------------------
# NOW ASK THE JUDGE
# ---------------------------------------------------------
result = judge(transcript)

print("\nJUDGE RESULT:")
print(json.dumps(result, indent=2))