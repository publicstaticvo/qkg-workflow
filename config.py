"""
config.py - config file
"""

import yaml
from dataclasses import dataclass, field


@dataclass(frozen=True)
class LLMServerInfo:
    base_url: str
    api_key: str | None = None
    model: str = "whatever"
    

@dataclass(frozen=True)
class Config:
    input_file: str = "chem.txt"
    workflow_output: str = "workflow.json"
    generate_model: LLMServerInfo = field(default_factory=LLMServerInfo)
    critic_models: list[LLMServerInfo] = field(default_factory=list)

    @classmethod
    def from_yaml(cls, config_path):
        with open(config_path, encoding='utf-8') as f: config = yaml.safe_load(f)
        return cls(
            input_file=config['input_file'],
            workflow_output=config['workflow_output'],
            generate_model=LLMServerInfo(**config['generate_model']),
            critic_models=[LLMServerInfo(**c) for c in config['critic_model']],
        )
