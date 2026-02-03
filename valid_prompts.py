FILTER = """You are a strict scientific benchmark filter. Your task is to decide whether the given multiple-choice question should be eliminated because answering it would require access to paper-specific details rather than scientific reasoning.

A question MUST be eliminated if correct answering requires:
- Referring to a specific figure, table, equation, or section
- Recalling exact numerical values, sample labels, or device configurations
- Remembering experimental conditions not stated in the question
- Concluding "insufficient information is given" as the main reasoning step

A question MUST be retained if it can be answered through:
- Logical consequences of stated assumptions
- Conceptual reasoning about physical mechanisms
- Comparing competing interpretations
- High-level domain knowledge without paper recall

Output ONLY in JSON format:

```json
{
  "eliminate": true | false,
  "reason": "brief explanation"
}
```
"""

SELF_CONTRADICT = """You are a strict scientific benchmark filter. You are given a scientific multiple-choice question stem. Your task is to judge whether the question stem itself is internally self-contradictory.

Definition:
A stem is self-contradictory if it simultaneously assumes statements that cannot all be true under any reasonable scientific or theoretical interpretation.

Instructions:
- Do NOT evaluate answer options.
- Do NOT judge realism or probability.
- Only check whether the assumptions in the stem can logically and coherently coexist.

Output format:
{
  "self_contradictory": true | false,
  "reason": "brief explanation"
}
"""

REDUNDANT = """You are a strict scientific benchmark filter. You are given a scientific multiple-choice question. Your task is to judge whether the question stem contains information that:
- Is not required to determine the correct answer, AND
- Does not meaningfully function as a distractor for any option.

Instructions:
- Do NOT assume perfect exam design.
- Only flag information that is clearly irrelevant to all options.
- If unsure, answer "no".

Output format:
{
  "contains_redundant_information": true | false,
  "reason": "brief explanation"
}
"""

IMPLAUSIBLE = """You are a strict scientific benchmark filter. You are given a scientific question. Your task is to judge whether the combination of assumptions described in the question is considered:
- Extremely atypical, or
- Violating well-established physical or scientific principles.

Instructions:
- Judge the combination of assumptions, not individual statements.
- Do NOT require absolute impossibility; extreme implausibility is sufficient.
- Ignore purely hypothetical or philosophical framing.

Output format:
{
  "physically_implausible": true | false,
  "reason": "brief explanation"
}
"""

OPTION_CHECK = """You are a strict scientific benchmark filter. You are reviewing a multiple-choice question for quality control. Your task is to identify structural issues that can be judged WITHOUT solving the problem.

Given the question and options below, analyze them under the following rules:

Definitions:
- "Trivially true without the question" means the option is obviously correct based on general knowledge alone.
- "Trivially false without the question" means the option is obviously incorrect or nonsensical based on general knowledge alone.
- "Does not depend on the question" means the option makes a standalone claim so that a knowledgeable reader can decide whether the option is true or false even if the question context is removed.
- "Semantically redundant options" are options that express essentially the same idea or mechanism, even if worded differently.

Instructions:
- Do NOT judge which option is correct given the question.
- Do NOT use information outside the text unless it is general domain knowledge.
- Be conservative: only label cases that are clear and unambiguous.

Output a JSON object with the following fields:
```json
{
  "trivially_true_without_question": <list of option letters>,
  "trivially_false_without_question": <list of option letters>,
  "does_not_depend_on_question": <list of option letters>,
  "redundant_options": <list of lists of option letters>
}
```
"""

OPTION_SCHEMA = {
    "type": "object", 
    "required": [
        "trivially_true_without_question",
        "trivially_false_without_question",
        "does_not_depend_on_question",
        "redundant_options"
    ],
    "properties": {
        "trivially_true_without_question": {
            "type": "array",
            "items": {
                "type": "string", 
                "enum": ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']
            }
        },
        "trivially_false_without_question": {
            "type": "array",
            "items": {
                "type": "string", 
                "enum": ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']
            }
        },
        "does_not_depend_on_question": {
            "type": "array",
            "items": {
                "type": "string", 
                "enum": ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']
            }
        },
        "redundant_options": {
            "type": "array",
            "items": {
                "type": "array",
                "minItems": 2,
                "items": {
                    "type": "string",
                    "enum": ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']
                }
            }
        }    
    }
}

TEST = """You are an expert on material science. You are asked to answer the following multiple-choice question.

If you determine that:
- the assumptions are internally contradictory,
- the question cannot be meaningfully adjudicated given its stated assumptions,
- or the question is ill-posed as a scientific query,

you MUST select option K: "None of the above. / This question is unanswerable".

Otherwise, select the single best answer.

Do NOT explain your reasoning. Output only the selected option letter, in the following JSON format:

```json
{ "selected_answer": "A" | "B" | "C" | "D" | "E" | "F" | "G" | "H" | "I" | "J" | "K" }
```
"""

TEST_SCHEMA = {
  "type": "object",
  "required": ["selected_answer"],
  "properties": {"selected_answer": {"type": "string", "enum": ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K']}},
  "additionalProperties": False
}
