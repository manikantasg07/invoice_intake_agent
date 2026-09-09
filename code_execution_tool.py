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

# file_object = client.files.upload(file=Path("finance.xlsx"))
# print(f"File uploaded: {file_object}")

# messages = [
#         {
#             "role": "user",
#             "content": [
#                 {"type": "text", "text": "Analyze this excel data"},
#                 {"type": "container_upload", "file_id": file_object.id},
#             ],
#         }
#     ]

messages = [
        {
            "role": "user",
            "content": "Create a matplotlib visualization and save it as output.png",
        }
    ]




try:
    created_file_ids=[]
    while True:
        response = client.messages.create(
            model="claude-opus-5",
            max_tokens=4096,
            messages=messages,
            tools=[{"type": "code_execution_20250825", "name": "code_execution"}],
        )

        if response.stop_reason == "end_turn":
            for block in response.content:
                if block.type == "text":
                    print(f"Model response: {block.text}")
                elif block.type == "bash_code_execution_tool_result":
                    content_item = block.content
                    if content_item.type == "bash_code_execution_result":
                        for file in content_item.content:
                            if hasattr(file, "file_id"):
                                created_file_ids.append(file.file_id)
                # elif block.type == "server_tool_use":
                #     print(f"\n--- Code Claude ran ({block.name}) ---")
                #     print(block.input.get("command", block.input))
                # elif block.type == "bash_code_execution_tool_result":
                #     result = block.content
                #     print(f"\n--- Execution result ---")
                #     print("stdout:", result.stdout)
                #     print("stderr:", result.stderr)
                # elif block.type == "text_editor_code_execution_tool_result":
                #     print(f"\n--- File operation result ---")
                #     print(block.content)
            break
        elif response.stop_reason == "pause_turn":
            # server tool loop hit iteration cap — resend content to continue
            if messages[-1]["role"] == "assistant":
                messages[-1]["content"] = messages[-1]["content"] + response.content
            else:
                messages.append({"role": "assistant", "content": response.content})
            continue

        elif response.stop_reason == "max_tokens":
            if messages[-1]["role"] == "assistant":
                # merge with existing assistant content instead of adding a new turn
                messages[-1]["content"] = messages[-1]["content"] + response.content
            else:
                messages.append({"role": "assistant", "content": response.content})
            continue
        
        print(f"Model stopped reason: {response.stop_reason}")
        break
    print("Created file ids: ",created_file_ids)
except Exception as e:
    print(f"Error: {e}")