GENERATE = """You are an expert research scientist in materials science.

Your task is to generate THREE multiple-choice questions that are implicitly or explicitly resolved by the provided academic paper. Each question must reflect a specific scientific judgment that becomes decidable ONLY under the concrete conditions stated in the question stem.

CRITICAL DESIGN OBJECTIVE:
The correct answer MUST rely on at least one explicit condition described in the question.
If the question were removed or generalized, the correct answer should no longer be obviously true.

Each question must satisfy ALL of the following:

1. Question construction
- The question must be answerable using the reasoning, evidence, or interpretation presented in the paper.
- The question must include at least one explicit condition, regime, comparison, or configuration (e.g., material pairing, bias polarity, interface structure, measurement context).
- Removing or altering this condition should make the answer ambiguous or debatable.
- The question must be understandable on its own and must NOT reference the paper, figures, or sections.

2. Prohibited question styles
- Do NOT ask purely canonical or textbook-style questions.
- Avoid questions phrased as “What is the primary reason/mechanism for X?” unless the mechanism is valid ONLY under the stated conditions.
- Do NOT ask questions whose correct answer would remain true in most closely related systems.

3. Options
- Provide exactly FOUR answer options (A–D).
- Exactly ONE option must be correct.
- Incorrect options must correspond to realistic alternative interpretations that would require additional assumptions NOT guaranteed by the stem.
- No option may be correct without explicitly using information from the question stem.

4. Answer & Explanation
- Clearly indicate the correct option letter.
- Explain why the correct option follows specifically from the stated conditions.
- Explain why the other options fail when those same conditions are applied.
- Do NOT explain answers by appealing to general textbook knowledge alone.

Important constraints
- Do NOT artificially increase difficulty.
- Do NOT introduce rare, pathological, or contrived scenarios.
- Keep reasoning depth shallow: each option should hinge on at most ONE unstated assumption.

Output ONLY in the following JSON format:

{
  "questions": [
    {
      "question": "...",
      "options": {
        "A": "...",
        "B": "...",
        "C": "...",
        "D": "..."
      },
      "answer": "A" | "B" | "C" | "D",
      "explanations": "..."
    }
  ]
}
"""

QUESTION_SCHEMA = {
  "type": "object",
  "required": ["question", "options", "answer", "explanations"],
  "properties": {
    "question": {"type": "string", "minLength": 1},
    "options": {
      "type": "object",
      "required": ['A', 'B', 'C', 'D'],
      "properties": {k: {"type": "string", "minLength": 1} for k in ['A', 'B', 'C', 'D']}
    },
    "answer": {"type": "string", "enum": ['A', 'B', 'C', 'D']},
    "explanations": {"type": "string"}
  }
}

GENERATE_SCHEMA = {
  "type": "object",
  "required": ['questions'],
  "properties": {
    "questions": {
      "type": "array",
      "items": QUESTION_SCHEMA
    }
  },
  "additionalProperties": False
}

REVISE = """You are an expert scientific question designer. You are given a well-formed multiple-choice question with 4 options and a single correct answer. Your task is to rewrite the question so that it has EXACTLY TEN answer options (A–J), while remaining a SINGLE-ANSWER multiple-choice question.

PRIMARY OBJECTIVE:
Increase option diversity while minimizing redundancy, independent correctness, and question-irrelevant answer options.

STRICT CONSTRAINTS:

1. Preserve the Core Question
- Do NOT change what is being asked.
- Do NOT introduce new physical mechanisms, materials, or experimental paradigms.

2. Correct Option
- The correct option must remain correct for the SAME reason.
- It must require at least one explicit condition from the question stem to be true.

3. Incorrect Options — Structured Generation
When expanding from 4 to 10 options, follow this distribution:
- At least FOUR options must explicitly reference a condition or regime stated in the question stem.
- At most TWO options may invoke general mechanisms without question-specific qualifiers.
- At most ONE option may involve idealized or limiting-case assumptions.

4. Prohibited Patterns
- Do NOT create paraphrases or near-synonyms.
- Do NOT include both a mechanism and its direct consequence as separate options.
- Do NOT include options that would be correct in most similar systems.

5. Reasoning Depth Control
- Each option must hinge on exactly ONE unstated assumption.
- Avoid multi-branch or conditional reasoning.

6. Redundancy Check (Self-check)
Before finalizing:
- Verify that removing any single option does NOT leave another option that says the same thing.
- Verify that no option is obviously true or false without using the question stem.

OUTPUT FORMAT (JSON ONLY):

{
  "question": "...",
  "options": {
    "A": "...",
    "B": "...",
    "C": "...",
    "D": "...",
    "E": "...",
    "F": "...",
    "G": "...",
    "H": "...",
    "I": "...",
    "J": "..."
  },
  "answer": "A" | "B" | "C" | "D" | "E" | "F" | "G" | "H" | "I" | "J",
  "explanations": "..."
}
"""

REVISE_SCHEMA = {
  "type": "object",
  "required": ["question", "options", "answer", "explanations"],
  "properties": {
    "question": {"type": "string", "minLength": 1},
    "options": {
      "type": "object",
      "required": ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J'],
      "properties": {k: {"type": "string", "minLength": 1} for k in ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']},
      "additionalProperties": False
    },
    "answer": {"type": "string", "enum": ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']},
    "explanations": {"type": "string"}
  },
  "additionalProperties": False
}

