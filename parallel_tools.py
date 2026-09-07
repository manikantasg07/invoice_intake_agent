from decimal import Decimal
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

tools = [
    {
        "name": "get_weather",
        "description": "Get the current weather for a given location.",
        "input_schema": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City and state, e.g. San Francisco, CA",
                }
            },
            "required": ["location"],
        },
    }
]

async def execute_get_weather(location: str) -> str:
    # In a real implementation, you'd call a weather API here.
    # if location.lower() == "san francisco, ca":
    #     return "15 degrees Celsius, partly cloudy"
    # elif location.lower() == "new york, ny":
    #     return "10 degrees Celsius, sunny"
    # return "Weather data not available for this location." 
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


messages = [{"role": "user", "content": "What's the weather in San Francisco and  New York?"}]

async def main():
    response = client.messages.create(
        model="claude-opus-5",
        max_tokens=1024,
        tools=tools,
        # tool_choice={"type": "auto", "disable_parallel_tool_use": True},
        messages=messages,
    )
    # for block in response.content:
    #     if block.type == "tool_use":
    #         tool_name = block.name
    #         tool_args = block.input
    #         print(f"Claude wants to use the tool '{tool_name}' with arguments: {tool_args}")
    while response.stop_reason == "tool_use":
        messages.append({"role": "assistant", "content": response.content})
        inputs_tobe_executed = []
        tool_output_content = []
        for block in response.content:
            if block.type == "tool_use":
                tool_name = block.name
                tool_args = block.input
                print(f"Claude wants to use the tool '{tool_name}' with arguments: {tool_args}")
                if tool_name == "get_weather":
                    location = tool_args.get("location")
                    # weather_result = asyncio.run(execute_get_weather(location))
                    # tool_inputs.append({"name": tool_name, "output": weather_result})
                    inputs_tobe_executed.append(execute_get_weather(location))
        if len(inputs_tobe_executed)>0:
            tool_outputs = await asyncio.gather(*inputs_tobe_executed,return_exceptions=True)
            for block in response.content:
                if block.type == "tool_use":
                    tool_name = block.name
                    tool_args = block.input
                    if tool_name == "get_weather":
                        weather_result = tool_outputs.pop(0)
                        if isinstance(weather_result,Exception):
                            tool_output_content.append({"type":"tool_result","tool_use_id":block.id,"content":str(weather_result),"is_error":True})
                        else:
                            tool_output_content.append({"type":"tool_result","tool_use_id":block.id,"content":weather_result})
        messages.append({"role": "user", "content": tool_output_content})
        response = client.messages.create(
            model="claude-opus-5",
            max_tokens=1024,
            tools=tools,
            messages=messages,
        )

    final_text = next(
        block.text for block in response.content if block.type == "text"
    )
    print(f"\nClaude's response:\n{final_text}")

asyncio.run(main())