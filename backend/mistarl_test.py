import os
from mistralai.client import Mistral

api_key = os.getenv("MISTRAL_API_KEY")

if not api_key:
    raise ValueError("MISTRAL_API_KEY is not set")

client = Mistral(api_key=api_key)

response = client.chat.complete(
    model="mistral-small-latest",
    messages=[
        {
            "role": "system",
            "content": "You are a helpful AI assistant."
        },
        {
            "role": "user",
            "content": "Explain what an LLM is in simple words."
        }
    ],
)

print("\n===== LLM RESPONSE =====\n")
print(response.choices[0].message.content)
print("\n========================\n")
