import os
from dotenv import load_dotenv

load_dotenv()

from sarvamai import SarvamAI

api_key = os.getenv("SARVAM_API_KEY")
client = SarvamAI(api_subscription_key=api_key)

response = client.chat.completions(
    model="sarvam-105b-conversations",
    messages=[
        {"role": "user", "content": "Hello! Introduce yourself in one short sentence."}
    ],
)

print(response.choices[0].message.content)
