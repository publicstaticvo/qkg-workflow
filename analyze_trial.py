import json

# Read all generated questions
with open("temp.jsonl", encoding='utf-8') as f:
    all_questions = [json.loads(line.strip()) for line in f if line.strip()]

# Read valid questions
with open("sample_queries.jsonl", encoding='utf-8') as f:
    valid_questions = [json.loads(line.strip()) for line in f if line.strip()]

valid_texts = {q['query']['question'] for q in valid_questions}

print(f"Total generated: {len(all_questions)}")
print(f"Valid: {len(valid_questions)}")
print(f"Pass rate: {len(valid_questions)/len(all_questions)*100:.2f}%")

print("\n=== Example of a FAILED question ===")
for q in all_questions:
    if q['question'] not in valid_texts:
        print(f"\nQuestion: {q['question'][:250]}...")
        print(f"\nFirst 3 options:")
        for i, (k, v) in enumerate(list(q['options'].items())[:3]):
            print(f"{k}: {v[:150]}...")
        break
