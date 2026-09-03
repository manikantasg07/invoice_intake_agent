from decimal import Decimal
from dotenv import load_dotenv
import json
import os
import anthropic
from pydantic import BaseModel

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("API_KEY"))

class LineItem(BaseModel):
    description: str
    quantity: str
    unit_price: str
    total_price: str

class Invoice(BaseModel):
    vendor: str
    invoice_number: str
    date: str
    currency: str
    line_items : list[dict[str, str,str,str]]
    tax : Decimal
    total : Decimal

message = f"""
Invoice text:

ACME INDUSTRIAL SUPPLY CO.
1245 Warehouse Blvd, Suite 400
Columbus, OH 43215
support@acmeindustrial.com | (614) 555-0192

INVOICE

Invoice Number: INV-2026-04831
Invoice Date: August 14, 2026
Due Date: September 13, 2026
Currency: USD

Bill To:
Northgate Manufacturing LLC
88 Production Way
Detroit, MI 48201

------------------------------------------------------------
Description                      Qty     Unit Price    Amount
------------------------------------------------------------
Stainless Steel Bolts (M8x40)    500     $0.42         $210.00
Industrial Gasket Set             20     $14.75        $295.00
Hydraulic Hose, 10ft               8     $38.90        $311.20
Safety Goggles (Bulk Pack)        12     $22.00         $264.00
Freight & Handling                 1     $45.00          $45.00
------------------------------------------------------------

Subtotal:                                          $1,125.20
Sales Tax (7.25%):                                    $81.58
------------------------------------------------------------
TOTAL DUE:                                         $1,206.78

Payment Terms: Net 30
Please remit payment to Acme Industrial Supply Co.
Thank you for your business!

"""

total_tokens_used = 0
total_computed_cost = 0

try:
    messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that extracts invoice data from raw text and returns it in a structured JSON format."
                },
                {
                    "role": "user",
                    "content": message
                }
            ]
    max_tokens = 256
    while True:
        with client.messages.stream(
            model="claude-haiku-4-5-20251001",
            max_tokens=256,
            messages=messages,
            output_format=Invoice
        ) as stream:
            response = stream.get_final_message()
            total_tokens_used +=response.usage.input_tokens + response.usage.output_tokens
            total_computed_cost+=response.usage.input_tokens*1+response.usage.output_tokens*5
            print(f"Total Tokens Used: {total_tokens_used}")
            print(f"Total Computed Cost: ${total_computed_cost}")
            if response.stop_reason == "end_turn":
                print("Final Response: ")
                print(response.parsed_output)
                break
            if response.stop_reason == "max_tokens":
                print("Max tokens reached, continuing...")
                max_tokens += 256
                messages+=[
                    {
                        "role":"assistant",
                        "content": response.parsed_output
                    }
                ]
                continue
        break           
except Exception as e:
    print(f"Error occurred: {e}")