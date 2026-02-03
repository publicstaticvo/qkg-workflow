GENERATE = """You are an expert research scientist in materials science.

Generate THREE multiple-choice questions based on the provided paper. Each question must test scientific reasoning under specific experimental conditions.

CORE PRINCIPLE:
Every option must be impossible to evaluate without considering the specific conditions in the question. Options should describe what happens "under these conditions" or "at this temperature/doping/thickness" rather than making general statements.

Question Requirements:
1. Include multiple specific conditions: material names, numerical values (temperature, doping, thickness), experimental parameters
2. Ask what mechanism/interpretation/outcome applies under THESE specific conditions
3. Self-contained (no references to figures, tables, or "the paper")

Option Requirements (10 options A-J):
1. EVERY option must reference the question's specific conditions
2. Use phrases like: "Under these conditions...", "At this temperature/doping...", "For this material/thickness...", "In this regime...", "Given these parameters..."
3. The correct option is right BECAUSE of the specific conditions
4. Each incorrect option would be correct under DIFFERENT conditions (different temperature, material, thickness, etc.)
5. Avoid general statements like "X always happens" or "Y is important" - tie everything to the specific conditions

Quality Checks:
- Can I evaluate any option without reading the question? → If YES, that option is BAD
- Do at least 8 options explicitly reference conditions? → If NO, add more references
- Are any options redundant? → If YES, make them distinct

Output JSON:
{
  "questions": [
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
      "required": ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J'],
      "properties": {k: {"type": "string", "minLength": 1} for k in ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']}
    },
    "answer": {"type": "string", "enum": ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']},
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
Increase option diversity while ensuring EVERY option depends on the question stem. Minimize redundancy, independent correctness, and question-irrelevant answer options.

CRITICAL REQUIREMENT - OPTION DEPENDENCY:
EVERY option (A through J) must be IMPOSSIBLE to evaluate as true or false without the specific conditions stated in the question stem. An expert should NOT be able to rule out or confirm any option based solely on general knowledge without considering the question context.

STRICT CONSTRAINTS:

1. Preserve the Core Question
- Do NOT change what is being asked.
- Do NOT introduce new physical mechanisms, materials, or experimental paradigms beyond what's in the original question.
- Keep the same specific conditions (temperature, doping, material, thickness, etc.) from the original question.

2. Correct Option
- The correct option must remain correct for the SAME reason as the original.
- It must require ALL the explicit conditions from the question stem to be true.

3. Incorrect Options — Structured Generation
When expanding from 4 to 10 options, create 6 NEW incorrect options that:
- Each explicitly references or depends on specific conditions from the question stem (temperature, doping level, material type, thickness, substrate, etc.)
- Each proposes a mechanism or interpretation that would be plausible under SLIGHTLY DIFFERENT conditions
- Each represents a competing explanation that an expert might consider before ruling it out based on the specific conditions

MANDATORY: ALL 10 options must reference or depend on at least one specific condition from the question stem.

4. Prohibited Patterns - STRICTLY ENFORCED
- Do NOT create paraphrases or near-synonyms of existing options.
- Do NOT include both a mechanism and its direct consequence as separate options.
- Do NOT include options that would be correct in most similar systems regardless of the specific conditions.
- Do NOT include options that are trivially true or false based on general knowledge alone.
- Do NOT include options that make standalone claims evaluable without the question context.
- Do NOT include options that contradict basic physics or chemistry (unless the question is about identifying such contradictions).

5. Reasoning Depth Control
- Each option must hinge on exactly ONE unstated assumption about how the stated conditions affect the outcome.
- Avoid multi-branch or conditional reasoning within a single option.

6. MANDATORY Self-Checks (perform these before finalizing):
For EACH option A through J, verify:
a) "Can I determine if this option is true or false without reading the question?" → If YES, REWRITE the option to depend on specific conditions from the question.
b) "Does this option reference or depend on at least one specific condition from the question (e.g., temperature, doping, material, thickness)?" → If NO, REWRITE to include such dependency.
c) "Is this option essentially saying the same thing as another option?" → If YES, make them clearly distinct or replace one.
d) "Would this option be obviously wrong in ANY similar system, regardless of the specific conditions?" → If YES, REWRITE to be plausible under different conditions.

7. Distribution Check:
- At least 8 out of 10 options should explicitly mention or depend on specific numerical values, material names, or experimental conditions from the question.
- At most 2 options may be more general, but they must still require the question context to evaluate.

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

