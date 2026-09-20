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
                "Important scenario rule: the car's condition and all other sale terms "
                "are fixed. Only the price may be negotiated. "
                "Introducing new conditions, inspections, warranties, documentation "
                "requirements, payment conditions, or other sale terms counts as "
                "deviating from the assigned role and should reduce the score. "
                # Give the Judge important scenario information.
                "The advertised price is NOK 200000"

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

                # -------------------------------------------------
                # SCORING RUBRIC
                # -------------------------------------------------
                #
                # The score and success value must agree logically.
                #
                # Scores 4 and 5 require a successful negotiation.
                # If there is no agreement, the highest possible
                # score is 3.
                "Use this scoring rubric strictly: "
                
                "5 = SUCCESS MUST BE TRUE. The Buyer and Seller clearly agree "
                "on the same final price, both agents follow their assigned roles, "
                "only price is negotiated, and the agreement is unambiguous. "
                
                "4 = SUCCESS MUST BE TRUE. The Buyer and Seller clearly agree "
                "on the same final price, but there are minor communication "
                "problems or small deviations from the assigned roles. "
                
                "3 = SUCCESS MUST BE FALSE. Meaningful negotiation progress is "
                "made, but no clear final agreement on one price is reached. "
                
                "2 = SUCCESS MUST BE FALSE. Little progress is made, or the "
                "dialogue becomes repetitive, inconsistent, or significantly "
                "deviates from the price-only negotiation. "
                
                "1 = SUCCESS MUST BE FALSE. The negotiation fails badly, becomes "
                "incoherent, or the agents substantially fail to follow their roles. "
                
                "If success is false, the score MUST NOT be higher than 3. "
                
                "If the agents introduce inspections, warranties, documentation "
                "requirements, payment conditions, or other new sale terms, mention "
                "that deviation in the reason and reduce the score as appropriate. "

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