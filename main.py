import json
import os, glob
import asyncio
from typing import Any

from utils import skeleton_to_text
from generate import generate_workflow, config
from check import collect_valid_questions
from session_manager import SessionManager


async def generateloop(papers: list[dict[str, Any]]):
    generate_tasks = []
    for paper in papers:
        content = skeleton_to_text(paper['structure'])
        generate_tasks.append(asyncio.create_task(generate_workflow(content)))

    # We expect to generate 3 questions for each paper.
    generated = []
    for task in asyncio.as_completed(generate_tasks):
        try:
            result = await task
            if isinstance(result, list) and result:
                generated.extend(result)
        except Exception as e:
            print(f"Generate Workflow {type(e)} {e}")

    if not generated:
        print(f"No questions generated. 0.00%")
        return
    else:
        print(f"Questions preserved rate: {len(generated) / len(papers) / 3 * 100:.2f}%")

    with open("temp.jsonl", "w", encoding='utf-8') as f:
        for result in generated:
            f.write(json.dumps(result, ensure_ascii=False) + "\n")
    
    with open("temp.jsonl", encoding='utf-8') as f:
        generated = []
        for x in f:
            if x.strip(): generated.append(json.loads(x.strip()))
    valid = await collect_valid_questions(generated)

    print(f"{len(valid)} questions are valid. \nPass rate: {len(valid) / len(papers) / 3 * 100:.2f}%")

    with open(config.workflow_output, "w", encoding='utf-8') as f:
        for result in valid:
            f.write(json.dumps(result, ensure_ascii=False) + "\n")


async def main():
    try:
        await SessionManager.init()
        tasks = []
        for n in glob.glob(f"{config.input_file}/*.json"):
            with open(n, encoding='utf-8') as f: paper = json.load(f)
            tasks.append(paper)
        await generateloop(tasks)
    finally:
        await SessionManager.close()


if __name__ == "__main__":
    asyncio.run(main())
