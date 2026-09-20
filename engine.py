"""engine.py: WEEK 2 target: a reusable two-agent dialogue engine.

The guardrails (Budget) and the bookkeeping (Entry, save) are DONE.
The two WEEK 2 parts are implemented:
  1. view_for(...)      - render the conversation from one agent's point of view
  2. DialogueEngine.run - the orchestration loop

In WEEK 3 you also implement the `manage_context` hook (truncation/summarisation).

Read the Week 2 handout alongside this file.
"""
import json
from dataclasses import asdict, dataclass

from budget import Budget  # used by DialogueEngine's constructor parameter


@dataclass
class Entry:
    """One message in the conversation, with its measured cost."""
    speaker: str
    content: str
    prompt_tokens: int
    completion_tokens: int
    seconds: float
    turn_index: int


def view_for(agent, transcript):
    """Build the message list to send to `agent`, from ITS point of view.

    Requirements (this is the key idea of Week 2):
      - first message: {"role": "system", "content": agent.system_prompt}
      - for each Entry in transcript:
            role = "assistant" if it was spoken by THIS agent
            role = "user"      if it was spoken by the OTHER agent
      - if the transcript is empty (turn 0), add a user message like
            {"role": "user", "content": "You speak first."}
        so the model always gets at least system + user.
      - return the list of {"role", "content"} dicts.

    Tip: test it by hand-building a 3-entry transcript and printing the view for
    each of your two agents; the roles should be mirror images.
    """
    messages = [{"role": "system", "content": agent.system_prompt}]

    for entry in transcript:
        role = "assistant" if entry.speaker == agent.name else "user"
        messages.append({"role": role, "content": entry.content})

    if not transcript:
        messages.append({"role": "user", "content": "You speak first."})

    return messages





def truncate_context(messages, max_messages=20):
    """
    Keep the system prompt and only the most recent messages.

    This prevents the conversation history sent to the LLM
    from growing indefinitely and eventually exceeding the
    model's context window.

    Important:
    This does NOT delete anything from self.transcript.
    It only reduces what is sent to the LLM for this call.
    """

    # If the message list is still small enough,
    # return it unchanged.
    if len(messages) <= max_messages:
        return messages

    # LOG:
    # This line runs only when truncation actually happens.
    # It lets us see in the terminal that context management
    # has been activated.
    print(
        f"[context] truncating from {len(messages)} "
        f"to {max_messages} messages"
    )

    # messages[0] is the system prompt.
    # We always keep it because it contains the agent's persona/instructions.
    system_prompt = messages[0]

    # Keep the newest messages from the conversation.
    # We subtract 1 because one place is already used
    # by the system prompt.
    recent_messages = messages[-(max_messages - 1):]

    # Return:
    # system prompt + most recent conversation messages.
    return [system_prompt] + recent_messages







def parse_agent_reply(text):
    """
    Convert an agent's JSON reply from text into a Python dictionary.

    Expected LLM reply:

        {
            "message": "I accept NOK 196500.",
            "offer": 196500,
            "accepted": true
        }

    Python can then directly read:

        data["message"]
        data["offer"]
        data["accepted"]

    This means Python does not need to understand the natural-language
    negotiation message itself.
    """

    # The LLM response arrives as text.
    # json.loads() converts valid JSON text into a Python dictionary.
    data = json.loads(text)

    # Make sure the model returned a JSON object/dictionary.
    if not isinstance(data, dict):
        raise ValueError("Agent reply must be a JSON object.")

    # Check that all fields required by our protocol are present.
    if "message" not in data:
        raise ValueError("Agent reply is missing 'message'.")

    if "offer" not in data:
        raise ValueError("Agent reply is missing 'offer'.")

    if "accepted" not in data:
        raise ValueError("Agent reply is missing 'accepted'.")

    # Validate the type of each field.
    if not isinstance(data["message"], str):
        raise ValueError("'message' must be text.")

    if isinstance(data["offer"], bool) or not isinstance(data["offer"], int):
        raise ValueError("'offer' must be an integer.")

    if not isinstance(data["accepted"], bool):
        raise ValueError("'accepted' must be true or false.")

    return data





class DialogueEngine:
    """Runs two (or more) agents in turn until a Budget stop fires.

    agents:        list of Agent; turn order follows the list, then wraps.
    client:        an OllamaClient or MockClient.
    budget:        a Budget instance (your three guardrails).
    goal_reached:  optional fn(transcript) -> bool; return True when the
                   scenario goal is met (engine then stops with 'goal_reached').
    manage_context: optional fn(messages) -> messages; WEEK 3 hook to keep the
                   message list inside the context window. Default: no-op.
    """

    def __init__(self, agents, client, budget, goal_reached=None, manage_context=None):
        self.agents = agents
        self.client = client
        self.budget = budget
        self.transcript = []  # list[Entry]
        self.goal_reached = goal_reached or (lambda t: False)
        self.manage_context = manage_context or (lambda messages: messages)

    def next_speaker(self):
        return self.agents[len(self.transcript) % len(self.agents)]

    def run(self):
        """Run the dialogue to completion. Return the final transcript.

        Loop shape:
            while not self.budget.exhausted():
                speaker = self.next_speaker()
                messages = self.manage_context(view_for(speaker, self.transcript))
                reply = self.client.chat(speaker.model, messages, speaker.temperature)
                append Entry(speaker.name, reply.text, reply.prompt_tokens,
                             reply.completion_tokens, reply.seconds,
                             len(self.transcript)) to self.transcript
                self.budget.record(turns=1, tokens=reply.tokens)
                if self.goal_reached(self.transcript):
                    self.budget.stop("goal_reached")
            return self.transcript
        """
        while not self.budget.exhausted():
            speaker = self.next_speaker()
            messages = self.manage_context(view_for(speaker, self.transcript))
            reply = self.client.chat(
                speaker.model,
                messages,
                speaker.temperature
            )
            # Keep track of the total cost of this turn.
            # Normally there is one LLM call.
            # If we need a retry, we will add the retry cost too.
            total_prompt_tokens = reply.prompt_tokens
            total_completion_tokens = reply.completion_tokens
            total_seconds = reply.seconds

            # ---------------------------------------------------------
            # WEEK 3: CHECK THE STRUCTURED JSON
            # ---------------------------------------------------------
            #
            # The agent is required to return valid JSON.
            # First, try to parse the reply.
            try:
                parse_agent_reply(reply.text)

            # If the JSON is invalid, ask the same agent to try once again.
            except (json.JSONDecodeError, ValueError) as error:

                print(
                    f"[structure] Invalid JSON from {speaker.name}. "
                    f"Retrying once. Error: {error}"
                )

                retry_messages = messages + [
                    {
                        "role": "assistant",
                        "content": reply.text,
                    },
                    {
                        "role": "user",
                        "content":
                            "Your previous response was not valid JSON. "
                            f"Error: {error}. "
                            "Reply again using ONLY valid JSON in this format: "
                            '{"message": "your short negotiation reply", '
                            '"offer": 195000, "accepted": false}.'
                    },
                ]

                reply = self.client.chat(
                    speaker.model,
                    retry_messages,
                    speaker.temperature
                )
                # A retry is another LLM call, so include its cost.
                total_prompt_tokens += reply.prompt_tokens
                total_completion_tokens += reply.completion_tokens
                total_seconds += reply.seconds

            # ---------------------------------------------------------
            # FINAL STRUCTURE CHECK
            # ---------------------------------------------------------
            #
            # Check the reply one last time.
            # This may be either the original reply or the retry reply.
            try:
                parse_agent_reply(reply.text)

                # JSON is valid, so save it normally.
                reply_content = reply.text

            except (json.JSONDecodeError, ValueError) as error:

                print(
                    f"[structure] Retry also failed for {speaker.name}. "
                    f"Using safe fallback. Error: {error}"
                )

                # Create valid JSON ourselves.
                #
                # accepted=False is important:
                # malformed output must never accidentally end the negotiation.
                reply_content = json.dumps({
                    "message": reply.text,
                    "offer": 0,
                    "accepted": False
                })

            entry = Entry(
                speaker=speaker.name,
                content=reply_content,
                prompt_tokens=total_prompt_tokens,
                completion_tokens=total_completion_tokens,
                seconds=total_seconds,
                turn_index=len(self.transcript),
            )
            self.transcript.append(entry)
            self.budget.record(
                turns=1,
                tokens=total_prompt_tokens + total_completion_tokens
            )

            if self.goal_reached(self.transcript):
                self.budget.stop("goal_reached")

        return self.transcript

    # === bookkeeping below is DONE ===

    def save(self, path, meta=None):
        """Write a structured JSON transcript: a run header + every message."""
        import os
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        record = {
            "meta": meta or {},
            "agents": [
                {"name": a.name, "model": a.model, "temperature": a.temperature}
                for a in self.agents
            ],
            "budget": self.budget.summary(),
            "totals": {
                "turns": len(self.transcript),
                "prompt_tokens": sum(e.prompt_tokens for e in self.transcript),
                "completion_tokens": sum(e.completion_tokens for e in self.transcript),
                "seconds": round(sum(e.seconds for e in self.transcript), 3),
            },
            "messages": [asdict(e) for e in self.transcript],
        }
        with open(path, "w") as f:
            json.dump(record, f, indent=2)
        return path
