import asyncio
import json, jsonschema
from typing import Any
from config import Config
from generate_prompts import *
from llm_client import AsyncLLMClient
from utils import extract_json

config = Config.from_yaml("config.yaml")
SAMPLE_PARAMS = {'temperature': 0.8, "max_tokens": 8192, "top_p": 0.95}


class Generate(AsyncLLMClient):

    def _availability(self, response: str, context: dict):
        text = extract_json(response)
        assert text, response
        jsonschema.validate(text, GENERATE_SCHEMA)
        questions = []
        STOP_WORDS = ['fig.', 'tbl.', 'see fig', 'shown in fig', 
                      'see section', 'this section', 'sec.', 'appendix', 'eq.', 'the paper', 'this paper']
        for x in text['questions']:
            if any(y in x['question'].lower() for y in STOP_WORDS): continue
            questions.append(x)
        return questions
    
    def _organize_inputs(self, inputs):
        inputs = json.dumps(inputs, indent=2)
        return [{'role': 'system', 'content': GENERATE}, {'role': 'user', 'content': inputs}], {}


class Rewrite(AsyncLLMClient):

    PROMPT = REVISE
    SCHEMA = REVISE_SCHEMA
    
    def _organize_inputs(self, inputs):
        inputs = json.dumps(inputs, indent=2)
        return [{'role': 'system', 'content': self.PROMPT}, {'role': 'user', 'content': inputs}], {}
    

async def generate(content: dict[str, Any]):
    model = Generate(config.generate_model, SAMPLE_PARAMS, 1800)
    try:
        generated = await model.call(inputs=content)
        return generated
    except Exception as e:
        print(f"GenerateNode {e}")


async def rewrite(generated: list[dict[str, any]]):
    tasks = [asyncio.create_task(Rewrite(config.generate_model, SAMPLE_PARAMS).call(inputs=g)) for g in generated]
    refine = []
    for task in asyncio.as_completed(tasks):
        try:
            result = await task
            if result: refine.append(result)
        except Exception as e:
            print(f"RewriteNode {e}")
    return refine


async def generate_workflow(content: str):
    # generate
    generated = await generate(content)
    if not generated: return []

    # refine
    refine = await rewrite(generated)
    if not refine: return []

    return refine
