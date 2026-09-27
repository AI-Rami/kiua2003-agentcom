# Design document: Used-car negotiation

KIUA2003 — Compulsory 1

## Scenario and rationale

A Buyer and a private Seller negotiate the price of a used car advertised at NOK 200,000. The car's condition and all other sale terms are fixed. Only the price is negotiable. The Buyer seeks the lowest possible price, and the Seller seeks the highest possible price. Their different objectives make negotiation observable, while explicit acceptance provides a measurable outcome.

## Agents and complete system prompts

The following complete system prompts are used in `configs/negotiation_t05.yaml`. Both agents use llama3.2:3b at temperature 0.5. The configured limits are 12 turns, 8,000 tokens and 120 seconds.

### Buyer

```text
You are a buyer negotiating with a private seller for a used car advertised at NOK 200000. The car's condition and all other sale terms are fixed; only the price is negotiable. Try to agree on the lowest possible price. Address the seller's latest message and make a concrete offer or counteroffer.
Respond ONLY with valid JSON in exactly this structure:
{
  "message": "your short negotiation reply",
  "offer": 180000,
  "accepted": false
}
"message" contains what you want to say to the Seller. "offer" contains your current price as an integer.
Set "accepted" to true only when you explicitly accept the Seller's latest offered price.
If "accepted" is true, "offer" must be exactly the same price as the Seller's latest offer.
If you are only making or repeating your own offer, "accepted" must be false, even if you call it your final offer.
Do not write anything outside the JSON object.
```

### Seller

```text
You are a private seller negotiating with a buyer for a used car advertised at NOK 200000. The car's condition and all other sale terms are fixed; only the price is negotiable. Try to agree on the highest possible price, using NOK 200000 as your asking price. Address the buyer's latest message and make a concrete offer or counteroffer.
Respond ONLY with valid JSON in exactly this structure:
{
  "message": "your short negotiation reply",
  "offer": 197500,
  "accepted": false
}
"message" contains what you want to say to the Buyer. "offer" contains your current price as an integer.
Set "accepted" to true only when you explicitly accept the Buyer's latest offered price.
If "accepted" is true, "offer" must be exactly the same price as the Buyer's latest offer.
If you are only making or repeating your own offer, "accepted" must be false, even if you call it your final offer.
Do not write anything outside the JSON object.
```

## Measurable goal and detection

The goal is agreement on one positive price: the latest reply must explicitly accept the previous agent's exact offer. Each reply is JSON with message (string), offer (integer, excluding booleans) and accepted (boolean).

negotiation_goal_reached() requires at least two entries, parses both with parse_agent_reply(), and returns true only when:

```python
return (
    current["accepted"] is True
    and current["offer"] == previous["offer"]
    and previous["offer"] > 0
)
```

Invalid replies do not count as agreement. The engine alternates Buyer and Seller, so consecutive entries come from opposite parties. Agreement stops the run with goal_reached. This detects structured acceptance, not factual accuracy, fairness or economic optimality. The configured agents have no enforced private ceiling or floor.

## Conversation control and evaluation

The Python engine stores a neutral transcript. view_for() gives each agent its own system prompt, marks its earlier messages as assistant and the other agent's messages as user. A sliding window retains the system prompt and the latest 19 conversation messages; the saved transcript remains complete. This avoids a summarisation call, but may forget old commitments and does not guarantee a token ceiling. With a 12-turn limit, normal runs do not reach the 20-message truncation threshold.

An invalid reply gets one retry. If that also fails, the engine saves the raw reply inside a valid fallback with offer=0 and accepted=false. Both calls' costs count toward the same turn. Budget checks occur between turns, so an in-progress call can exceed a time or token limit before the next check.

A separate judge call uses llama3.2:3b at temperature 0 and returns a reason, score (1–5) and success flag. Invalid judge output produces null score and success values. The deterministic goal check remains the primary agreement measure; judge evaluations can be wrong. JSON transcripts save messages, settings, costs, stopping information and the judge result. Negotiation metrics exclude the judge call.
