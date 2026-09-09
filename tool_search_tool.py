import json
import logging
import os

import anthropic
import python_weather
from anthropic import beta_async_tool
from dotenv import load_dotenv
import asyncio

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("tool_search_debug")

client = anthropic.AsyncAnthropic(api_key=os.getenv("API_KEY"))


@beta_async_tool(defer_loading=True)
async def execute_get_weather(location: str) -> str:
    """Get the current weather for a given location.
    Args:
        location: City and state, e.g. San Francisco, CA
    Returns:
        JSON string with current temperature, description, and daily forecasts.
    """
    if location.lower() == "new york, ny":
        raise ValueError("Simulated API failure fo0r testing")
    async with python_weather.Client(unit=python_weather.IMPERIAL) as wclient:
        weather = await wclient.get(location)
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


messages = [
    {
        "role": "user",
        "content": "What's the weather in San Francisco and New York and Visakhapatnam?",
    }
]


def log_tool_search_activity(turn_number: int, message) -> None:
    """Inspect a single turn's content blocks and log anything tool-search related."""
    for block in message.content:
        block_type = getattr(block, "type", None)

        # The model explicitly invoking tool_search_tool_bm25 to discover tools.
        if block_type == "tool_use" and getattr(block, "name", None) == "tool_search_tool_bm25":
            logger.info(
                "[turn %d] tool_search_tool_bm25 INVOKED — query args: %s",
                turn_number, block.input,
            )

        # Some SDK versions surface server-executed search tools as server_tool_use.
        if block_type == "server_tool_use" and "tool_search" in getattr(block, "name", ""):
            logger.info(
                "[turn %d] server-side tool_search executed — name=%s input=%s",
                turn_number, block.name, block.input,
            )

        # Catch-all: log any block whose type/name mentions tool_search, in case
        # naming differs across SDK/model versions.
        name = getattr(block, "name", "") or ""
        if "tool_search" in str(block_type or "") or "tool_search" in name:
            logger.debug("[turn %d] raw tool_search-related block: %r", turn_number, block)


async def main():
    runner = client.beta.messages.tool_runner(
        model="claude-opus-5",
        max_tokens=1024,
        tools=[
            {"type": "tool_search_tool_bm25_20251119", "name": "tool_search_tool_bm25"},
            execute_get_weather,
        ],
        messages=messages,
    )

    turn_number = 0
    async for message in runner:
        turn_number += 1
        logger.info(
            "[turn %d] stop_reason=%s | block_types=%s",
            turn_number,
            message.stop_reason,
            [getattr(b, "type", None) for b in message.content],
        )
        log_tool_search_activity(turn_number, message)

    final_message = await runner.until_done()
    for block in final_message.content:
        if block.type == "text":
            print(f"\nModel response: {block.text}")


asyncio.run(main())