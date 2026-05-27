from default_config.DefaultOperationConfig import *
from default_config.DefaultUtilsConfig import *
from default_config.DefaultGlobalConfig import *

DEFAULT_ZEPMEMORY = {
    "name": "ZepMemory",
    "is_multimodal": False,
    "zep": {
        "api_key": "z_1dWlkIjoiMDViNDFhM2UtMzkxNy00MDY1LWEzNzEtZGI0Y2ZiZjY0M2RhIn0.Ej29AMDkCh-wzrP4zUf20omJw7gdrAG-Z41F4JEtrtnbrU4frfJk09xTRKQAOAI3arK7JjZadVmfBg6VILO_4g",
        # "user_id": "mem_gallery_user",
        # "session_id": "mem_gallery_session",
        "user_id": "mem_gallery_user_run3",
        "session_id": "mem_gallery_ai_run3_session",
        "memory_type": "perpetual",
        "return_context_fallback": "None",
        "store_delay_seconds": 12,
        "max_retries": 5,
        "retry_fallback_seconds": 45,
        "max_query_chars": 380,
    },
    "display": DEFAULT_DISPLAY,
    "global_config": DEFAULT_GLOBAL_CONFIG,
}