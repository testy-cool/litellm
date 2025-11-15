import asyncio
import json
import re
import sys

from dotenv import load_dotenv
from litellm import completion, completion_cost

load_dotenv()

# ============================================================================
# CONFIGURATION
# ============================================================================

# --- Model Configuration ---
MODEL = "gpt-5"
# MODEL = "gpt-5.1"
# MODEL = "gpt-5-mini"
# MODEL = "gpt-5-nano"

# --- GPT-5 Parameters ---
REASONING_EFFORT = "low"  # none | minimal | low | medium | high
VERBOSITY = "low"  # low | medium | high
# Note: summary parameter is not available in completion() - only in responses()

# --- MCP Configuration ---
USE_MCP = True

# List of MCP servers to use (all tools from all servers will be available)
MCP_SERVERS = [
    {
        "url": "https://dify-prod.dpf.cloud/mcp/server/FJTm5xAW0tYxe9Nn/mcp",
        "transport": "http",  # http or sse
        "timeout": 60.0,
    },
    # Add more MCP servers here:
    # {
    #     "url": "http://localhost:3000/mcp",
    #     "transport": "http",
    #     "timeout": 30.0,
    # },
]

# --- Prompts ---
SYSTEM_PROMPT = """"""  # Your system / dev prompt

USER_PROMPT = """Search for latest AI news"""

# USER_PROMPT = """
# Give me some data points about target.com. Example:
#
# {
#   "name": "Target",
#   "founded": 1902,
#   "headquarters": "Minneapolis, Minnesota, USA",
# }
# """

# ============================================================================
# IMPLEMENTATION
# ============================================================================


def sanitize_tool_name(name):
    """Convert tool name to match OpenAI pattern ^[a-zA-Z0-9_-]+$"""
    sanitized = re.sub(r"[^a-zA-Z0-9_-]", "_", name)
    return sanitized.strip("_")


async def get_all_mcp_tools():
    """Fetch tools from all configured MCP servers."""
    from litellm.experimental_mcp_client.client import MCPClient
    from litellm.types.mcp import MCPTransport

    all_tools = []
    tool_mapping = {}  # Maps sanitized_name -> (server_config, original_name)

    for server_config in MCP_SERVERS:
        print(f"📡 Connecting to MCP server: {server_config['url']}")

        mcp_client = MCPClient(
            server_url=server_config["url"],
            transport_type=MCPTransport[server_config["transport"]],
            timeout=server_config["timeout"],
        )

        async with mcp_client:
            tools_response = await mcp_client.list_tools()
            print(f"   ✓ Found {len(tools_response)} tools")

            for tool in tools_response:
                sanitized_name = sanitize_tool_name(tool.name)

                # Handle name collisions by appending server index
                original_sanitized = sanitized_name
                counter = 1
                while sanitized_name in tool_mapping:
                    sanitized_name = f"{original_sanitized}_{counter}"
                    counter += 1

                openai_tool = {
                    "type": "function",
                    "function": {
                        "name": sanitized_name,
                        "description": tool.description or "",
                        "parameters": tool.inputSchema,
                    },
                }

                all_tools.append(openai_tool)
                tool_mapping[sanitized_name] = (server_config, tool.name)

    print(f"\n✓ Total tools available: {len(all_tools)}\n")
    return all_tools, tool_mapping


async def execute_mcp_tool_calls(tool_calls, tool_mapping):
    """Execute tool calls on their respective MCP servers."""
    from litellm.experimental_mcp_client.client import MCPClient
    from litellm.types.mcp import MCPTransport
    from mcp.types import CallToolRequestParams

    tool_results = []

    print(f"🔧 Executing {len(tool_calls)} tool call(s)\n")

    for tool_call in tool_calls:
        sanitized_name = tool_call["function"]["name"]
        server_config, original_name = tool_mapping[sanitized_name]
        arguments = json.loads(tool_call["function"]["arguments"])

        print(f"🔍 Calling: {original_name}")
        print(f"   Arguments: {arguments}")

        mcp_client = MCPClient(
            server_url=server_config["url"],
            transport_type=MCPTransport[server_config["transport"]],
            timeout=server_config["timeout"],
        )

        async with mcp_client:
            result = await mcp_client.call_tool(
                CallToolRequestParams(name=original_name, arguments=arguments)
            )

            tool_results.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": str(result.content[0].text),
                }
            )

            print(f"   ✓ Got {len(str(result.content[0].text))} chars\n")

    return tool_results


async def run_with_mcp():
    """Run completion with MCP tool calling."""
    # Build messages
    messages = []
    if SYSTEM_PROMPT.strip():
        messages.append({"role": "system", "content": SYSTEM_PROMPT.strip()})
    messages.append({"role": "user", "content": USER_PROMPT.strip()})

    # Step 1: Get all tools from all MCP servers
    print("=" * 80)
    print("🔧 Fetching tools from MCP servers...")
    print("=" * 80)
    openai_tools, tool_mapping = await get_all_mcp_tools()

    # Step 2: First completion - let model decide which tools to call
    print("=" * 80)
    print("🤖 Asking model...")
    print("=" * 80)

    response = completion(
        model=MODEL,
        messages=messages,
        tools=openai_tools,
        tool_choice="auto",
        reasoning_effort=REASONING_EFFORT,
        verbosity=VERBOSITY,
    )

    # Check if model wants to use tools
    if not response["choices"][0]["message"].get("tool_calls"):
        print("\n✓ Model responded without using tools\n")
        print_response_and_usage(response)
        return

    # Step 3: Execute tool calls
    tool_calls = response["choices"][0]["message"]["tool_calls"]
    tool_results = await execute_mcp_tool_calls(tool_calls, tool_mapping)

    # Step 4: Send results back for final answer
    messages.append(response["choices"][0]["message"])
    messages.extend(tool_results)

    print("=" * 80)
    print("📤 Sending tool results back to model for final answer...")
    print("=" * 80)

    final_response = completion(
        model=MODEL,
        messages=messages,
        reasoning_effort=REASONING_EFFORT,
        verbosity=VERBOSITY,
    )

    print_response_and_usage(final_response)


def run_without_mcp():
    """Run simple completion without MCP."""
    # Build messages
    messages = []
    if SYSTEM_PROMPT.strip():
        messages.append({"role": "system", "content": SYSTEM_PROMPT.strip()})
    messages.append({"role": "user", "content": USER_PROMPT.strip()})

    print("=" * 80)
    print("🤖 Running completion...")
    print("=" * 80)

    response = completion(
        model=MODEL,
        messages=messages,
        reasoning_effort=REASONING_EFFORT,
        verbosity=VERBOSITY,
    )

    print_response_and_usage(response)


def print_response_and_usage(response):
    """Print response content and usage statistics."""
    print("\n" + "=" * 80)
    print("🤖 Response:")
    print("=" * 80)

    message = response["choices"][0]["message"]

    # Print content
    if message.get("content"):
        print(message["content"])
    elif message.get("tool_calls"):
        print("⚠️ Model wants to make more tool calls:")
        for tc in message["tool_calls"]:
            print(f"  - {tc['function']['name']}: {tc['function']['arguments']}")
    else:
        print("⚠️ No content in response")
        print(json.dumps(message, indent=2, default=str))

    # Print usage statistics
    usage = response.get("usage")
    if usage:
        print("\n" + "=" * 80)
        print("📊 USAGE:")
        print("=" * 80)

        input_tokens = getattr(usage, "input_tokens", 0) or getattr(
            usage, "prompt_tokens", 0
        )
        output_tokens = getattr(usage, "output_tokens", 0) or getattr(
            usage, "completion_tokens", 0
        )
        total_tokens = getattr(usage, "total_tokens", input_tokens + output_tokens)

        # Reasoning tokens
        reasoning_tokens = 0
        details_out = getattr(usage, "output_tokens_details", None)
        if details_out and getattr(details_out, "reasoning_tokens", None) is not None:
            reasoning_tokens = details_out.reasoning_tokens or 0

        # Cached tokens
        cached_in = 0
        details_in = getattr(usage, "input_tokens_details", None) or getattr(
            usage, "prompt_tokens_details", None
        )
        if details_in and getattr(details_in, "cached_tokens", None) is not None:
            cached_in = details_in.cached_tokens or 0

        print(f"  Input tokens:         {input_tokens}")
        print(f"  Output tokens:        {output_tokens}")
        if reasoning_tokens > 0:
            print(f"    ↳ Reasoning tokens: {reasoning_tokens}")
        if cached_in > 0:
            print(f"  Cached input tokens:  {cached_in}")
        print(f"  Total tokens:         {total_tokens}")

        # Calculate cost
        PRICES = {
            "gpt-5": {"in": 1.25, "cached_in": 0.125, "out": 10.0},
            "gpt-5.1": {"in": 1.25, "cached_in": 0.125, "out": 10.0},
            "gpt-5-mini": {"in": 0.25, "cached_in": 0.025, "out": 2.0},
            "gpt-5-nano": {"in": 0.05, "cached_in": 0.005, "out": 0.4},
        }

        # Strip "openai/" prefix if present
        model_key = MODEL.replace("openai/", "")
        p = PRICES.get(model_key, PRICES["gpt-5"])

        billable_in = max(input_tokens - cached_in, 0)
        cost = (
            billable_in * p["in"]
            + cached_in * p["cached_in"]
            + output_tokens * p["out"]
        ) / 1_000_000

        print(f"\n💰 COST (Manual calculation): ${cost:.6f}")

        # Try LiteLLM's cost helper
        try:
            litellm_cost = completion_cost(completion_response=response, model=MODEL)
            print(f"💰 COST (LiteLLM helper):    ${float(litellm_cost):.6f}")
        except Exception as e:
            print(f"💰 COST (LiteLLM helper):    error -> {e}")

    print("=" * 80 + "\n")


def main():
    if USE_MCP:
        asyncio.run(run_with_mcp())
    else:
        run_without_mcp()


if __name__ == "__main__":
    main()
