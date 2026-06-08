import os
from google import genai

# Simple .env loader fallback
if os.path.exists(".env"):
    with open(".env") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ[key.strip()] = val.strip()

client = genai.Client(api_key=os.getenv("GEMMA_API_KEY"))
r = client.models.generate_content(model='gemma-4-31b-it', contents='hi')
print(r.text)