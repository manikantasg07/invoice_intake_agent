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
import re

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("API_KEY"))

SALES_DATA = {
    "West":    {"total_revenue": 482_300.00, "orders": 1204},
    "East":    {"total_revenue": 601_750.50, "orders": 1489},
    "Central": {"total_revenue": 398_920.25, "orders": 980},
}

def exeute_tool(name:str,sql:str)->str:
    match = re.search(r"region\s*=\s*'([^']+)'", sql, re.IGNORECASE)
    if not match:
        return "ERROR: could not determine region from query"
    region = match.group(1)
    row = SALES_DATA.get(region)
    if row is None:
        return f"ERROR: no data for region '{region}'"
    return f"region={region}, total_revenue={row['total_revenue']}, orders={row['orders']}"


# response = client.messages.create(
#     model="claude-sonnet-4-6",
#     max_tokens=4096,
#     messages=[
#         {
#             "role": "user",
#             "content": "Query sales data for the West, East, and Central regions, then tell me which region had the highest revenue",
#         }
#     ],
#     tools=[
#         # {"type": "code_execution_20260120", "name": "code_execution"},
#         {
#             "name": "query_database",
#             "description": "Execute a SQL query against the sales database. Returns a list of rows as JSON objects.",
#             "strict":True,
#             "input_schema": {
#                 "type": "object",
#                 "properties": {
#                     "sql": {"type": "string", "description": "SQL query to execute"}
#                 },
#                 "required": ["sql"],
#             },
#             "allowed_callers": ["code_execution_20260120"],
#         },
#     ],
# )

# container_id = response.container.id
# print()
# for block in response.content:
#     print("Block: ",block)
#     print()

messages= [
            {
                "role": "user",
                "content": "Query sales data for the West, East, and Central regions, then tell me which region had the highest revenue",
            }
        ]
tools= [
            {"type": "code_execution_20260120", "name": "code_execution"},
            {
                "name": "query_database",
                "description": "Execute a SQL query against the sales database. Returns a list of rows as JSON objects.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "sql": {"type": "string", "description": "SQL query to execute"}
                    },
                    "required": ["sql"],
                },
                "allowed_callers": ["code_execution_20260120"],
            },
        ]
response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        messages=messages,
        tools=tools,
    )

while True:
    if response.stop_reason =="end_turn":
        print("End Turn Response: ",response)
        for block in response.content:
            if block.type == "text":
                print("Model Response: ",block.text)
        break
    if response.stop_reason  == "tool_use":
        messages.append({
            "role":"assistant",
            "content":response.content
        })
        tool_results=[]
        print("tool Response : ",response)
        print()
        for block in response.content:
            if block.type == "tool_use":
                try:
                    tool_result = exeute_tool(block.name,block.input["sql"])
                    tool_results.append({
                        "type":"tool_result",
                        "tool_use_id":block.id,
                        "content":tool_result
                    })
                except Exception as e:
                    tool_results.append({
                        "type":"tool_result",
                        "tool_use_id":block.id,
                        "content":str(e),
                        "is_error":True
                    })
        messages.append({
            "role":"user",
            "content":tool_results
        })
        print("messages after tool result: ",messages)
        response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=4096,
                container=response.container.id,
                messages=messages,
                tools=tools,
            )
        continue
    if response.stop_reason == "pause_turn":
        messages.append({"role": "assistant", "content": response.content})
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            container=response.container.id,
            messages=messages,
            tools=tools,
        )
        continue
    break


print("Model Response: ")
for block in response.content:
    if block.type == "text":
        print(block.text)