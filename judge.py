"""
judge.py: evaluate a completed dialogue run.

The judge is a separate LLM call that reads the finished transcript
after the Buyer-Seller negotiation has ended.

The judge does NOT participate in the negotiation.

Its job is to evaluate the completed dialogue using a fixed rubric
and return three values:

    reason  - a short explanation of the evaluation
    score   - negotiation quality from 1 to 5
    success - True only if both agents clearly agreed on one final price

The judge uses temperature=0 to reduce randomness and make
evaluations more consistent between runs.
"""

import json

from llm_client import make_client


def judge(transcript, client=None, model="llama3.2:3b"):
    """
    Evaluate a completed Buyer-Seller negotiation.

    Parameters
    ----------
    transcript:
        The finished dialogue transcript.
        It is a list of Entry objects from engine.py.

    client:
        The LLM client used to call the judge.
        If no client is supplied, a new normal client is created.

    model:
        The model used by the judge.
        By default we use llama3.2:3b.

    Returns
    -------
    A Python dictionary such as:

        {
            "reason": "Both agents agreed clearly on NOK 175000.",
            "score": 5,
            "success": True
        }

    If the judge returns invalid JSON, the function returns
    a safe fallback instead of crashing the program.
    """

    # ---------------------------------------------------------
    # 1. CREATE A CLIENT IF WE DO NOT ALREADY HAVE ONE
    # ---------------------------------------------------------
    #
    # Sometimes we may call:
    #
    #     judge(transcript, client=my_client)
    #
    # In that case we use the supplied client.
    #
    # If client is None, make_client() creates one for us.
    client = client or make_client()


    # ---------------------------------------------------------
    # 2. CONVERT THE TRANSCRIPT INTO TEXT FOR THE JUDGE
    # ---------------------------------------------------------
    #
    # The transcript contains Entry objects such as:
    #
    # Entry(
    #     speaker="Buyer",
    #     content="I offer NOK 170000.",
    #     ...
    # )
    #
    # The judge does not need token counts, timing information,
    # or turn indexes to evaluate the dialogue.
    #
    # We therefore convert the transcript into simple readable text:
    #
    # Buyer: I offer NOK 170000.
    # Seller: I can accept NOK 180000.
    # Buyer: I agree to NOK 180000.
    #
    # "\n".join(...) puts each message on a new line.
    conversation = "\n".join(
        f"{entry.speaker}: {entry.content}"
        for entry in transcript
    )


    # ---------------------------------------------------------
    # 3. CREATE THE JUDGE'S MESSAGE LIST
    # ---------------------------------------------------------
    #
    # Just like the Buyer and Seller, the Judge gets:
    #
    #   system -> its instructions and evaluation rubric
    #   user   -> the actual transcript it must evaluate
    #
    # The Judge has its OWN system prompt.
    # It is separate from the Buyer and Seller personas.
    messages = [
        {
            "role": "system",
            "content":
                # Tell the model what role it has.
                "You are an impartial judge evaluating a used-car "
                "price negotiation between a Buyer and a Seller. "

                # Give the Judge important scenario information.
                "The advertised price is NOK 200000, and only the "
                "price is negotiable. "

                # Define exactly what SUCCESS means.
                "Success means that the Buyer and Seller clearly "
                "agree on the same final price. "

                # -------------------------------------------------
                # SCORING RUBRIC
                # -------------------------------------------------
                #
                # Without a rubric, the model would have to invent
                # its own meaning for scores 1-5.
                #
                # We define the meaning ourselves so different runs
                # are evaluated using the same criteria.
                "Use this scoring rubric: "

                "5 = A clear agreement is reached on one final price, "
                "both agents follow their roles, and the result is "
                "unambiguous. "

                "4 = A clear agreement is reached, but there are minor "
                "inconsistencies or communication problems. "

                "3 = Meaningful negotiation progress is made, but no "
                "clear final agreement is reached. "

                "2 = Little progress is made, or the dialogue becomes "
                "repetitive or inconsistent. "

                "1 = The negotiation fails badly, becomes incoherent, "
                "or the agents do not follow their roles. "

                # Define the boolean success field separately
                # from the quality score.
                "Set success to true only if both parties clearly "
                "agree on the same final price. Otherwise set it to false. "

                # -------------------------------------------------
                # REASON BEFORE SCORE
                # -------------------------------------------------
                #
                # Week 3 recommends asking for the justification
                # before asking for the numerical score.
                #
                # The Judge should therefore first determine WHY
                # the negotiation deserves a particular evaluation,
                # and only then assign the score.
                "First determine a short reason for your evaluation. "
                "After determining the reason, assign the score and "
                "success value. "

                # -------------------------------------------------
                # REQUIRED OUTPUT FORMAT
                # -------------------------------------------------
                #
                # We request JSON because Python can parse it
                # reliably using json.loads().
                #
                # The reason is deliberately placed before score
                # in the requested output.
                "Respond ONLY with valid JSON in exactly this format: "
                "{\"reason\": \"short explanation\", "
                "\"score\": 1, "
                "\"success\": false}"
        },

        # The actual finished conversation is given to the Judge
        # as the user message.
        {
            "role": "user",
            "content": conversation
        },
    ]


    # ---------------------------------------------------------
    # 4. CALL THE JUDGE MODEL
    # ---------------------------------------------------------
    #
    # temperature=0 makes the output less random.
    #
    # This is useful for evaluation because we would like the
    # same transcript to receive approximately the same judgment
    # if we evaluate it again.
    reply = client.chat(
        model,
        messages,
        temperature=0
    )


    # ---------------------------------------------------------
    # 5. PARSE THE JUDGE'S JSON RESPONSE
    # ---------------------------------------------------------
    #
    # The LLM returns TEXT.
    #
    # For example:
    #
    # '{"reason": "They agreed at NOK 175000.",
    #   "score": 5,
    #   "success": true}'
    #
    # json.loads() converts that JSON text into a Python dictionary:
    #
    # {
    #     "reason": "They agreed at NOK 175000.",
    #     "score": 5,
    #     "success": True
    # }
    try:
        return json.loads(reply.text)


    # ---------------------------------------------------------
    # 6. HANDLE INVALID JSON SAFELY
    # ---------------------------------------------------------
    #
    # LLMs do not always follow formatting instructions perfectly.
    #
    # If the Judge returns something that is not valid JSON,
    # json.loads() raises JSONDecodeError.
    #
    # Instead of allowing the whole program to crash,
    # we catch the error and return a safe fallback.
    except json.JSONDecodeError:
        return {
            "reason": "invalid JSON from judge",
            "score": 0,
            "success": False
        }