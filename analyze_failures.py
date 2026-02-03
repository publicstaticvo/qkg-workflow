import json

# Read generated questions
with open("temp.jsonl", encoding='utf-8') as f:
    questions = [json.loads(line.strip()) for line in f if line.strip()]

print(f"Total questions generated: {len(questions)}")
print(f"\nFirst 3 questions:")
for i, q in enumerate(questions[:3]):
    print(f"\n--- Question {i+1} ---")
    print(f"Question: {q['question'][:150]}...")
    print(f"Answer: {q['answer']}")
    print(f"Number of options: {len(q['options'])}")
