from default_config.DefaultGlobalConfig import *

# ----- LLM Judge Configuration -----
DEFAULT_LLM_JUDGE_CONFIG = {
    'method': 'APILLM',
    'name': 'Qwen2.5-VL-7B-Instruct',  # Default judge model, can be overridden via command line [Replace with your model path]
    'api_key': 'EMPTY', # [Replace with your api key]
    'base_url': 'http://127.0.0.1:8000/v1', # [Replace with your model's base url]
    'temperature': 0,  # Use 0 for deterministic judgments
    'max_retries': 5,  # Maximum number of retries for API calls
    'timeout': 60,  # Timeout in seconds for API calls
}

# Prompt template path (relative to evaluate directory)
DEFAULT_LLM_JUDGE_PROMPT_PATH = 'llm_judge.txt'

