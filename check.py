import asyncio
import jsonschema
from typing import Any
from tenacity import RetryError
from config import Config
from valid_prompts import *
from utils import extract_json
from llm_client import AsyncLLMClient, LLMServerInfo

GREEDY_PARAMS = {
    'temperature': 0.0, "max_tokens": 8192, "seed": 42,
    "top_p": 1.0, "top_k": 1, "repetition_penalty": 1.0,
    "length_penalty": 1.0, "no_repeat_ngram_size": 0,
}
    

class Filter(AsyncLLMClient):

    KEY = 'eliminate'
    PROMPT = FILTER
    OPTIONS = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']

    def __init__(self, info, sampling_params, timeout=300):
        super().__init__(info, sampling_params, timeout)

    def _availability(self, response: str, context: dict):
        response = extract_json(response)
        result = response[self.KEY]
        if isinstance(result, str):
            if result.lower() == "true": result = True
            elif result.lower() == "false": result = False
        return result
    
    def _organize_inputs(self, inputs):
        question = f"Question: {inputs['question']}" if 'question' in inputs else ""
        options = f"Options:{''.join(f'\n{k}. {inputs['options'][k]}' for k in self.OPTIONS if k in inputs['options'])}" if 'options' in inputs else ""
        if question and options: string = f"{question}\n\n{options}"
        else: string = question or options
        return [{'role': 'system', 'content': self.PROMPT}, {'role': 'user', 'content': string}], {}


class SelfContradictFilter(Filter):
    PROMPT = SELF_CONTRADICT
    KEY = "self_contradictory"


class RedundantFilter(Filter):
    PROMPT = REDUNDANT
    KEY = "contains_redundant_information"


class ImplausibleFilter(Filter):
    PROMPT = IMPLAUSIBLE
    KEY = "physically_implausible"


class JointOptionFilter(Filter):
    PROMPT = OPTION_CHECK
    
    def _availability(self, response: str, context: dict):
        response = extract_json(response)
        jsonschema.validate(response, OPTION_SCHEMA)
        return response


class Tester(AsyncLLMClient):

    OPTIONS = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K']
    PROMPT = TEST

    def _availability(self, response: str, context: dict):
        text = extract_json(response)
        jsonschema.validate(text, TEST_SCHEMA)
        return text['selected_answer']
    
    def _organize_inputs(self, inputs):
        options = {**inputs['options'], "K": "None of the above. / The question is not answerable."}
        inputs = f"Question: {inputs['question']}\n\nOptions:{''.join(f'\n{k}. {options[k]}' for k in self.OPTIONS)}"
        prompt = [{'role': 'system', 'content': self.PROMPT}, {'role': 'user', 'content': inputs}]
        return prompt, {}
    

async def valid_check(i, generated: dict[str, Any], model_chair: list[LLMServerInfo]):
    async def _valid(critic: LLMServerInfo):
        global message_count
        # whether the question requires information from the paper (which is not given in question)
        try:
            specific = await Filter(critic, GREEDY_PARAMS).call(inputs={"question": generated['question']})
        except RetryError as e:
            print(f"self-contained filter {e.last_attempt}")  
            return {"drop": True, "reason": f"self-contained test has an error: {e.last_attempt}"}       
        if specific: return {"drop": True, "reason": "not self-contained"}

        # whether the question is not self-contradicted
        try:
            self_contradict = await SelfContradictFilter(critic, GREEDY_PARAMS).call(inputs={"question": generated['question']})
        except RetryError as e:
            print(f"self_contradict {e.last_attempt}")
            self_contradict = False
        if self_contradict: return {"drop": True, "reason": "self-contradicted"}
        
        # whether the question has no redundant information
        try:
            redundant = await RedundantFilter(critic, GREEDY_PARAMS).call(inputs=generated)
        except RetryError as e:
            print(f"redundant {e.last_attempt}")
            redundant = False
        if redundant: return {"drop": True, "reason": "redundant"}
        
        # whether the question has implausible assumptions
        try:
            implausible = await ImplausibleFilter(critic, GREEDY_PARAMS).call(inputs={"question": generated['question']})
        except RetryError as e:
            print(f"implausible {e.last_attempt}")
            implausible = False
        if implausible == True: return {"drop": True, "reason": "implausible"}
        
        # whether the options can be judged without the question
        # A good option should be judged using BOTH the question and the option itself.
        try:
            option_check = await JointOptionFilter(critic, GREEDY_PARAMS).call(inputs=generated)
            if option_check["trivially_true_without_question"]:
                return {"drop": True, "reason": "correct without question"}
            does_not_depend = set(option_check["trivially_false_without_question"] + option_check["does_not_depend_on_question"])
            if len(does_not_depend) >= 4:
                return {"drop": True, "reason": "too many independent"}
            redundant_options = set()
            for x in option_check["redundant_options"]: redundant_options.update(x)
        except RetryError as e:
            print(f"joint option filter {e.last_attempt}")
            return {"drop": True, "reason": "joint option filter error"}
        
        # The final check
        try:
            answer = await Tester(critic, GREEDY_PARAMS).call(inputs=generated)
            if answer == "K":
                return {"answer": answer, "drop": True, "reason": "K"}
            if answer in does_not_depend:
                return {"answer": answer, "drop": True, "reason": "select independent answer"}
            if answer in redundant_options:
                return {"answer": answer, "drop": True, "reason": "multiple correct answers"}
        except RetryError as e:
            print(f"tester {e.last_attempt}")
            answer = "Error"
        return {"critic": critic.model, "answer": answer, "drop": False, "independent": list(does_not_depend)}
    
    tasks = [asyncio.create_task(_valid(c)) for c in model_chair]
    answers = []
    try:
        for task in asyncio.as_completed(tasks):
            try:
                result = await task
                if result['drop']: 
                    for other_task in tasks: 
                        if not other_task.done(): other_task.cancel()
                    return
                answers.append(result)
            except asyncio.CancelledError:
                pass
            except KeyboardInterrupt:
                raise
            except Exception as e:
                print(f"CriticNode {e}")    
    finally:
        for other_task in tasks: 
            if not other_task.done(): other_task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
    return {"query": generated, "answers": answers} 


async def collect_valid_questions(generated: list[dict[str, Any]]):
    config = Config.from_yaml("config.yaml")
    tasks = [asyncio.create_task(valid_check(i, g, config.critic_models)) for i, g in enumerate(generated)]
    valid_questions = []
    for task in asyncio.as_completed(tasks):
        result = await task
        if result: valid_questions.append(result)
    return valid_questions
