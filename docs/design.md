# Week 1 Design: Used-Car Price Negotiation

## Scenario and rationale

Two agents negotiate the price of a used car advertised for NOK 200000. I chose negotiation because it gives the agents clearly opposing objectives and produces a numerical outcome that can be evaluated automatically.

## Agent A: Buyer

System prompt:

> You are buying the used car. Your private maximum is NOK 180000. Never reveal this limit. Make the first offer and try to pay as little as possible. End every reply with exactly one action: OFFER: <integer>, ACCEPT: <integer>, or NO DEAL. Never accept more than NOK 180000. Reply in at most 2 sentences.

## Agent B: Seller

System prompt:

> You are selling the used car. Your private minimum is NOK 160000. Never reveal this limit. Try to obtain the highest possible price. End every reply with exactly one action: OFFER: <integer>, ACCEPT: <integer>, or NO DEAL. Never accept less than NOK 160000. Reply in at most 2 sentences.

## Measurable goal

The negotiation is resolved when one agent accepts the other agent's immediately preceding offer at the same price between NOK 160000 and NOK 180000, or when an agent explicitly declares NO DEAL.

## Planned detection

A later goal-checking function will extract OFFER and ACCEPT amounts from the transcript and verify that an accepted amount matches the immediately preceding offer and satisfies both agents' price limits. NO DEAL will be recorded as an unsuccessful but valid resolution.

## Initial observation

In the first real test, the Buyer offered NOK 150000 and the Seller countered with NOK 175000. The Seller followed the required output format but described its price as non-negotiable while simultaneously making a concession, showing that format compliance does not guarantee logically consistent reasoning.