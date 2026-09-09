from decimal import Decimal
from pathlib import Path
from dotenv import load_dotenv
import json
import os
import anthropic 
from anthropic import beta_tool
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_random_exponential
from datetime import date
import asyncio
import python_weather


load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("API_KEY"))

response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=4096,
    messages=[
        {
            "role": "user",
            "content": "Fetch the content at https://www.eateam.com/ and give me overview about the company.",
        }
    ],
    tools=[{"type": "web_fetch_20260318", "name": "web_fetch","response_inclusion":"excluded"}],
)

for block in response.content:
    if block.type == "text":
        print("Model Response: ",block.text)