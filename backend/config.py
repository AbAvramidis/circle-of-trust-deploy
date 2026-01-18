"""Configuration for the Circle of Trust."""

import os
from dotenv import load_dotenv

load_dotenv()

# OpenRouter API key (kept for backward compatibility or if needed)
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Ollama API endpoint
OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://localhost:11434/api/chat")

# Council Advisors Configuration
# Default advisors if no config file exists
DEFAULT_ADVISORS = [
    {
        "id": "albert_bourla",
        "name": "Albert Bourla",
        "model": "gemma3:latest",
        "prompt_file": "prompts/albert_bourla.md",
        "description": "CEO of Pfizer, focused on pharmaceutical innovation and healthcare leadership."
    },
    {
        "id": "elon_musk",
        "name": "Elon Musk",
        "model": "gpt-oss:latest",
        "prompt_file": "prompts/elon_musk.md",
        "description": "CEO of Tesla and SpaceX, known for first-principles thinking and ambitious technological goals."
    },
    {
        "id": "fei_fei_li",
        "name": "Fei-Fei Li",
        "model": "deepseek-r1:latest",
        "prompt_file": "prompts/fei_fei_li.md",
        "description": "Computer Scientist and AI Researcher, pioneer in computer vision and human-centered AI."
    },
    {
        "id": "cassie_kozyrkov",
        "name": "Cassie Kozyrkov",
        "model": "llama3.2:latest",
        "prompt_file": "prompts/cassie_kozyrkov.md",
        "description": "Chief Decision Scientist, expert in data science, decision intelligence, and AI strategy."
    },
    {
        "id": "andrej_karpathy",
        "name": "Andrej Karpathy",
        "model": "mistral:latest",
        "prompt_file": "prompts/andrej_karpathy.md",
        "description": "AI Researcher and Engineer, focused on deep learning, computer vision, and autonomous systems."
    }
]

# Global variable to hold current advisors
ADVISORS = list(DEFAULT_ADVISORS)

def load_advisors():
    """Load advisors from config file or use defaults."""
    global ADVISORS
    import json
    
    config_path = os.path.join("data", "council_config.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                config = json.load(f)
                if "advisors" in config:
                    ADVISORS = config["advisors"]
        except Exception as e:
            print(f"Error loading council config: {e}")
            ADVISORS = list(DEFAULT_ADVISORS)
    else:
        ADVISORS = list(DEFAULT_ADVISORS)

def save_advisors(advisors):
    """Save advisors to config file."""
    global ADVISORS
    import json
    
    ADVISORS = advisors
    os.makedirs("data", exist_ok=True)
    config_path = os.path.join("data", "council_config.json")
    
    try:
        with open(config_path, "w") as f:
            json.dump({"advisors": ADVISORS}, f, indent=2)
    except Exception as e:
        print(f"Error saving council config: {e}")

# Load advisors on startup
load_advisors()

# Council members - list of model identifiers (for backward compatibility in some functions)
COUNCIL_MODELS = [advisor["model"] for advisor in ADVISORS]

# Chairman model - synthesizes final response
# Using Andrej Karpathy (mistral) as the default chairman for synthesis
CHAIRMAN_MODEL = "mistral:latest"

# OpenRouter API endpoint (kept for reference)
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Data directory for conversation storage
DATA_DIR = "data/conversations"
