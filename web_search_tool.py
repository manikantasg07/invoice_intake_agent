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

tool_name = "web_search_20260209"
response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=4096,
    messages=[{"role": "user", "content": "What's the weather in NYC?"}],
    # tools=[{"type": "web_search_20260209", "name": "web_search","allowed_callers": ["direct"],"max_uses": 1}],
    tools=[{"type": "web_search_20260318", "name": "web_search", "response_inclusion": "excluded"}],
    # "response_inclusion": "excluded"
)
for block in response.content:
    # if block.type == "text":
    #     print(f"Model response: {block.text}")
    # elif block.type == "web_search_tool_result":
    #     content_item = block.content
    #     if content_item.type == "web_search_result":
    #         for result in content_item.content:
    #             print(f"Search result: {result.title} - {result.url}")
    print(f"Block : {block}")
    print()
    # if block.type =="text":
    #     print(f"Model response: {block.text}")
    #     if hasattr(block, "citations"):
    #         if not block.citations:
    #             print("No citations found.")
    #         else:
    #             for citation in block.citations:
    #                 print(f"Citation: {citation}")