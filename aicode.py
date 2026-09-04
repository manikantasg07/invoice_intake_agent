"""
Invoice extraction CLI.

Reads plain-text invoice content from the console, sends it to Claude with
structured outputs (Pydantic schema), streams the response, and prints back
a validated Invoice object along with token usage and computed cost for
every API call.

Retries only on transient errors: HTTP 429 (rate limited) and 5xx (server
error), plus connection-level failures. Client errors (400, 401, 403, 404,
422, etc.) are NOT retried since retrying them wastes time and money without
any chance of succeeding.
"""

import os
import sys
from dataclasses import dataclass
from decimal import Decimal

import anthropic
from anthropic import Anthropic
from dotenv import load_dotenv
from pydantic import BaseModel
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_random_exponential,
)

load_dotenv()

client = Anthropic(api_key=os.getenv("API_KEY"))

MODEL = "claude-haiku-4-5-20251001"

# Pricing for Haiku 4.5, USD per million tokens (standard tier, global).
# Source: https://platform.claude.com/docs/en/about-claude/pricing
PRICE_INPUT_PER_MTOK = Decimal("1.00")
PRICE_OUTPUT_PER_MTOK = Decimal("5.00")
PRICE_CACHE_WRITE_5M_PER_MTOK = Decimal("1.25")
PRICE_CACHE_READ_PER_MTOK = Decimal("0.10")

SYSTEM_PROMPT = (
    "You are a helpful assistant that extracts invoice data from raw text "
    "and returns it in a structured JSON format."
)

MAX_TOKENS_START = 1024
MAX_TOKENS_CEILING = 4096
MAX_TOKENS_STEP = 512


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

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
    line_items: list[LineItem]
    tax: Decimal
    total: Decimal


# ---------------------------------------------------------------------------
# Usage / cost tracking
# ---------------------------------------------------------------------------

@dataclass
class UsageTracker:
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost: Decimal = Decimal("0")

    def add(self, usage) -> None:
        input_tokens = usage.input_tokens
        output_tokens = usage.output_tokens
        cache_write_tokens = usage.cache_creation_input_tokens or 0
        cache_read_tokens = usage.cache_read_input_tokens or 0

        cost = (
            input_tokens * PRICE_INPUT_PER_MTOK
            + output_tokens * PRICE_OUTPUT_PER_MTOK
            + cache_write_tokens * PRICE_CACHE_WRITE_5M_PER_MTOK
            + cache_read_tokens * PRICE_CACHE_READ_PER_MTOK
        ) / Decimal("1000000")

        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.total_cost += cost

        print(
            f"  [usage] input={input_tokens} output={output_tokens} "
            f"cache_write={cache_write_tokens} cache_read={cache_read_tokens} "
            f"call_cost=${cost:.6f} running_total=${self.total_cost:.6f}"
        )


# ---------------------------------------------------------------------------
# Retry policy: only retry rate limits (429) and server errors (5xx)
# ---------------------------------------------------------------------------

def _is_retryable(exception: BaseException) -> bool:
    if isinstance(exception, anthropic.APIStatusError):
        return exception.status_code == 429 or exception.status_code >= 500
    # Connection-level failures (DNS, timeout, reset) are also worth retrying.
    if isinstance(exception, anthropic.APIConnectionError):
        return True
    return False


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------

@retry(
    reraise=True,
    stop=stop_after_attempt(3),
    wait=wait_random_exponential(min=1, max=10),
    retry=retry_if_exception(_is_retryable),
)
def get_invoice_data(invoice_text: str, tracker: UsageTracker) -> Invoice:
    messages = [{"role": "user", "content": invoice_text}]
    max_tokens = MAX_TOKENS_START

    while True:
        with client.messages.stream(
            model=MODEL,
            max_tokens=max_tokens,
            system=SYSTEM_PROMPT,
            messages=messages,
            output_format=Invoice,
        ) as stream:
            for event in stream:
                if event.type == "text":
                    # Live-stream the raw JSON as it's generated.
                    print(event.text, end="", flush=True)
            response = stream.get_final_message()

        print()  # newline after the streamed text
        tracker.add(response.usage)

        if response.stop_reason == "end_turn":
            if response.parsed_output is None:
                raise ValueError(
                    "Model finished but returned output that didn't match "
                    "the Invoice schema."
                )
            return response.parsed_output

        if response.stop_reason == "max_tokens":
            max_tokens += MAX_TOKENS_STEP
            if max_tokens > MAX_TOKENS_CEILING:
                raise ValueError(
                    f"Invoice extraction exceeded {MAX_TOKENS_CEILING} max "
                    "tokens without completing."
                )
            print(f"  [info] hit max_tokens, retrying with max_tokens={max_tokens}")
            continue

        raise RuntimeError(f"Unexpected stop_reason: {response.stop_reason!r}")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def read_invoice_text_from_console() -> str:
    print(
        "Paste the invoice text below, then press Ctrl+Z and Enter (Windows) "
        "or Ctrl+D (macOS/Linux) to submit:\n"
    )
    return sys.stdin.read()


def main() -> None:
    invoice_text = read_invoice_text_from_console()
    if not invoice_text.strip():
        print("No invoice text provided.")
        return

    tracker = UsageTracker()

    try:
        invoice = get_invoice_data(invoice_text, tracker)
    except Exception as e:
        print(f"\nError extracting invoice data: {e}")
        return

    print("\nExtracted Invoice:")
    print(invoice.model_dump_json(indent=2))

    total_tokens = tracker.total_input_tokens + tracker.total_output_tokens
    print(f"\nTotal tokens used: {total_tokens}")
    print(f"Total computed cost: ${tracker.total_cost:.6f}")


if __name__ == "__main__":
    main()