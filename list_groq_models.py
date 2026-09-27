import requests
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.environ.get("GROQ_API_KEY")
url = "https://api.groq.com/openai/v1/models"

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

try:
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    models = response.json()

    print("Available Groq Models:")
    for model in models.get('data', []):
        print(f"- {model['id']}")
except Exception as e:
    print(f"Error fetching models: {e}")
    if 'response' in locals():
        print(f"Response: {response.text}")
