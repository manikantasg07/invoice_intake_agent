from decimal import Decimal
from dotenv import load_dotenv
import json
import os
import anthropic 
from anthropic import beta_tool,beta_async_tool
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_random_exponential
from datetime import date
import asyncio
import python_weather


load_dotenv()

client = anthropic.AsyncAnthropic(api_key=os.getenv("API_KEY"))

# tools = [
#     {
#         "name": "get_weather",
#         "description": "Get the current weather for a given location.",
#         "input_schema": {
#             "type": "object",
#             "properties": {
#                 "location": {
#                     "type": "string",
#                     "description": "City and state, e.g. San Francisco, CA",
#                 }
#             },
#             "required": ["location"],
#         },
#     }
# ]

@beta_async_tool
async def execute_get_weather(location: str) -> str:
    """Get the current weather for a given location.
    Args:
        location: City and state, e.g. San Francisco, CA
    Returns:
        JSON string with current temperature, description, and daily forecasts. 
    """
    if location.lower() == "new york, ny":
        raise ValueError("Simulated API failure fo0r testing")
    async with python_weather.Client(unit=python_weather.IMPERIAL) as client:
        # Fetch weather forecast for a city
        weather = await client.get(location)
        result = {
            "location": location,
            "current_temperature": weather.temperature,
            "description": weather.description,
            "daily_forecasts": [
                {
                    "date": str(daily.date),
                    "high": daily.highest_temperature,
                    "low": daily.lowest_temperature,
                }
                for daily in weather.daily_forecasts
            ],
        }
        return json.dumps(result)


messages = [{"role": "user", "content": "What's the weather in San Francisco and  New York and Visakhapatnam?"}]

async def main():
    runner = client.beta.messages.tool_runner(
        model="claude-opus-5",
        max_tokens=1024,
        tools=[execute_get_weather],
        # tool_choice={"type": "auto", "disable_parallel_tool_use": True},
        messages=messages,
    )
    final_text = await runner.until_done()
    for block in final_text.content:
        if block.type == "text":
            print(f"Model response: {block.text}")

asyncio.run(main())