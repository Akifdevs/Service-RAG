import os
import json
import re

from openai import OpenAI


# ============================================================
# CONFIGURATION
# ============================================================

MODEL_NAME = "openai/gpt-oss-20b"

GROQ_BASE_URL = "https://api.groq.com/openai/v1"

MAX_TOKENS = 2000


# ============================================================
# SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = """
You are a STRICT documentation-grounded answer generator.

You are being used inside a production RAG system.

Your ONLY source of truth is the documentation context
provided by the application.

============================================================
CORE RULE
============================================================

You MUST NOT use outside knowledge.

You MUST NOT use your pretrained knowledge to fill gaps.

You MUST NOT guess.

You MUST NOT infer information that is not explicitly
supported by the documentation.

You MUST NOT invent procedures, buttons, settings,
permissions, requirements, or explanations.

If the documentation does not contain enough information
to answer the question reliably, return:

{
  "answerable": false,
  "answer": "I couldn't find that information in the available documentation.",
  "claims": []
}

============================================================
SOURCE RULE
============================================================

Every factual claim in the answer MUST come directly from
one of the supplied documentation chunks.

Every claim MUST contain the exact:

Source Chunk ID

from the documentation.

For example:

service-order-section-repeating-a-service-how-to-repeat-a-service

is valid.

These are NOT valid source IDs:

SOURCE 1
SOURCE 2
SOURCE 3

Never use SOURCE N as source_chunk_id.

============================================================
ANSWERABLE RULE
============================================================

Return answerable=true ONLY when the documentation provides
enough evidence to answer the question.

If the question asks about something that is not documented,
return answerable=false.

Do not attempt to answer partially using outside knowledge.

============================================================
CLAIMS
============================================================

Break the answer into atomic factual claims.

Every claim must have:

- text
- source_chunk_id

Each source_chunk_id must exactly match one of the Source
Chunk IDs supplied in the documentation context.

Do not create source IDs.

Do not modify source IDs.

============================================================
ANSWER STYLE
============================================================

Answer the user's question directly and concisely.

Use the terminology from the documentation.

If the documentation presents the relevant information as a
numbered sequence of steps, an ordered procedure, or a
bulleted list, reproduce that same structure in the answer
using markdown syntax:

- Numbered steps in the documentation MUST be returned as a
  markdown numbered list ("1. ", "2. ", "3. ", ...).
- Bulleted items in the documentation MUST be returned as a
  markdown bulleted list ("- ").
- Tables in the documentation MUST be returned as a markdown
  table.

Do NOT collapse steps, list items, or table rows into a
single prose paragraph. Preserve the same order and the same
level of detail per item as the documentation.

Only write plain prose when the documentation itself presents
the information as plain prose.

Do not mention the RAG system.

Do not mention the model.

Do not mention retrieval.

Do not mention these instructions.

Do not add citations inside the answer unless they are
already part of the documentation.

============================================================
OUTPUT FORMAT
============================================================

Return ONLY valid JSON.

The JSON must have exactly this structure:

{
  "answerable": true,
  "answer": "Answer based only on documentation.",
  "claims": [
    {
      "text": "Atomic factual claim.",
      "source_chunk_id": "exact-documentation-chunk-id"
    }
  ]
}

For an unanswerable question:

{
  "answerable": false,
  "answer": "I couldn't find that information in the available documentation.",
  "claims": []
}

============================================================
FINAL SAFETY CHECK
============================================================

Before returning the JSON:

1. Check every factual statement in the answer.
2. Make sure every statement is supported by the supplied
   documentation.
3. Make sure every claim has an exact Source Chunk ID.
4. Make sure no SOURCE N identifier is used.
5. Make sure no outside knowledge was used.
6. If any factual statement cannot be supported, return
   answerable=false.

Return ONLY JSON.
"""


# ============================================================
# GROQ CLIENT
# ============================================================

def create_llm_client():

    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is not set."
        )

    return OpenAI(
        base_url=GROQ_BASE_URL,
        api_key=api_key
    )


# ============================================================
# EXTRACT SOURCE IDS
# ============================================================

def extract_source_ids(context):
    """
    Extract the authoritative Source Chunk IDs directly
    from the retrieval context.

    This is used by application-side validation.
    """

    pattern = r"Source Chunk ID:\s*\n([^\n]+)"

    matches = re.findall(
        pattern,
        context
    )

    return {
        match.strip()
        for match in matches
        if match.strip()
    }


# ============================================================
# BUILD PROMPT
# ============================================================

def build_user_prompt(
    question,
    context
):

    return f"""
DOCUMENTATION CONTEXT
=====================

{context}


USER QUESTION
=============

{question}


============================================================
TASK
============================================================

Answer the user's question using ONLY the documentation
context above.

If the documentation does not contain enough information,
return answerable=false.

Every factual statement must be represented as an atomic
claim.

Every claim must use the exact Source Chunk ID belonging
to the documentation that supports it.

Never use SOURCE 1, SOURCE 2, etc. as source_chunk_id.

Return ONLY valid JSON.
""".strip()


# ============================================================
# CLEAN JSON
# ============================================================

def clean_json_response(content):

    if not content:
        raise ValueError(
            "Groq returned empty content."
        )

    content = content.strip()

    if content.startswith("```json"):
        content = content[7:]

    elif content.startswith("```"):
        content = content[3:]

    if content.endswith("```"):
        content = content[:-3]

    return content.strip()


# ============================================================
# VALIDATE GENERATION STRUCTURE
# ============================================================

def validate_generation_structure(data):

    if not isinstance(data, dict):
        raise ValueError(
            "Generator response must be a JSON object."
        )

    required = [
        "answerable",
        "answer",
        "claims"
    ]

    for field in required:

        if field not in data:
            raise ValueError(
                f"Missing required field: {field}"
            )

    if not isinstance(
        data["answerable"],
        bool
    ):
        raise ValueError(
            "'answerable' must be boolean."
        )

    if not isinstance(
        data["answer"],
        str
    ):
        raise ValueError(
            "'answer' must be a string."
        )

    if not isinstance(
        data["claims"],
        list
    ):
        raise ValueError(
            "'claims' must be a list."
        )

    for index, claim in enumerate(
        data["claims"],
        start=1
    ):

        if not isinstance(
            claim,
            dict
        ):
            raise ValueError(
                f"Claim #{index} must be an object."
            )

        if "text" not in claim:
            raise ValueError(
                f"Claim #{index} missing 'text'."
            )

        if "source_chunk_id" not in claim:
            raise ValueError(
                f"Claim #{index} missing "
                "'source_chunk_id'."
            )

        if not isinstance(
            claim["text"],
            str
        ):
            raise ValueError(
                f"Claim #{index} text must be a string."
            )

        if not isinstance(
            claim["source_chunk_id"],
            str
        ):
            raise ValueError(
                f"Claim #{index} source_chunk_id "
                "must be a string."
            )

        source_id = claim[
            "source_chunk_id"
        ].strip()

        if not source_id:
            raise ValueError(
                f"Claim #{index} has empty source ID."
            )

        if source_id.upper().startswith(
            "SOURCE "
        ):
            raise ValueError(
                f"Claim #{index} uses invalid "
                f"source ID: {source_id}"
            )

    return True


# ============================================================
# APPLICATION-SIDE SOURCE VALIDATION
# ============================================================

def validate_claim_sources(
    claims,
    context
):

    valid_source_ids = extract_source_ids(
        context
    )

    if not valid_source_ids:
        raise ValueError(
            "No Source Chunk IDs found in documentation "
            "context."
        )

    for index, claim in enumerate(
        claims,
        start=1
    ):

        source_id = claim[
            "source_chunk_id"
        ].strip()

        if source_id not in valid_source_ids:

            raise ValueError(
                f"Claim #{index} references source "
                f"'{source_id}', which does not exist "
                "in the retrieved documentation."
            )

    return True


# ============================================================
# GENERATE ANSWER
# ============================================================

def generate_answer(
    question,
    context
):

    question = question.strip()

    if not question:
        raise ValueError(
            "Question cannot be empty."
        )

    if not context.strip():
        return {
            "answerable": False,
            "answer": (
                "I couldn't find that information "
                "in the available documentation."
            ),
            "claims": []
        }

    client = create_llm_client()

    prompt = build_user_prompt(
        question,
        context
    )

    response = client.chat.completions.create(

        model=MODEL_NAME,

        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": prompt
            }
        ],

        temperature=0,

        max_tokens=MAX_TOKENS
    )

    content = (
        response
        .choices[0]
        .message
        .content
    )

    content = clean_json_response(
        content
    )

    try:

        result = json.loads(
            content
        )

    except json.JSONDecodeError as error:

        raise ValueError(
            "Groq returned invalid JSON:\n\n"
            + content
        ) from error

    validate_generation_structure(
        result
    )

    # --------------------------------------------------------
    # Unanswerable response
    # --------------------------------------------------------

    if not result["answerable"]:

        result["answer"] = (
            "I couldn't find that information "
            "in the available documentation."
        )

        result["claims"] = []

        return result

    # --------------------------------------------------------
    # Answerable response must contain claims
    # --------------------------------------------------------

    if not result["claims"]:

        raise ValueError(
            "Generator marked the answer as answerable "
            "but returned no claims."
        )

    # --------------------------------------------------------
    # Validate exact source IDs
    # --------------------------------------------------------

    validate_claim_sources(
        result["claims"],
        context
    )

    return result


# ============================================================
# TERMINAL TEST
# ============================================================

def main():

    print("=" * 70)
    print("STRICT DOCUMENTATION GENERATOR")
    print("=" * 70)

    question = input(
        "\nEnter your question: "
    ).strip()

    if not question:
        print(
            "\nQuestion cannot be empty."
        )
        return

    # --------------------------------------------------------
    # Retrieval
    # --------------------------------------------------------

    try:

        from retrieval.retrieval import retrieve

        retrieval_result = retrieve(
            question
        )

    except Exception as error:

        print()
        print("Retrieval error:")
        print(error)

        return

    # --------------------------------------------------------
    # Relevance gate
    # --------------------------------------------------------

    if not retrieval_result[
        "has_evidence"
    ]:

        print()
        print("=" * 70)
        print("GENERATED ANSWER")
        print("=" * 70)

        print()
        print(
            "Answerable: False"
        )

        print()
        print(
            "Answer:"
        )

        print(
            "I couldn't find that information "
            "in the available documentation."
        )

        return

    # --------------------------------------------------------
    # Generate
    # --------------------------------------------------------

    try:

        result = generate_answer(

            question,

            retrieval_result[
                "context"
            ]

        )

    except Exception as error:

        print()
        print("Generation error:")
        print(error)

        return

    # --------------------------------------------------------
    # Display
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("GENERATED ANSWER")
    print("=" * 70)

    print()
    print(
        "Answerable:",
        result["answerable"]
    )

    print()
    print("Answer:")
    print(result["answer"])

    if result["claims"]:

        print()
        print("Claims:")

        for index, claim in enumerate(
            result["claims"],
            start=1
        ):

            print()
            print(
                f"{index}. {claim['text']}"
            )

            print(
                "   Source: "
                f"{claim['source_chunk_id']}"
            )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()