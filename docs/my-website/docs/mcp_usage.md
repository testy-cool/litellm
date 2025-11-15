
import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';
import Image from '@theme/IdealImage';

# Using your MCP

This document covers how to use LiteLLM as an MCP Gateway. You can see how to use it with Responses API, Cursor IDE, and OpenAI SDK.

### Use on LiteLLM UI 

Follow this walkthrough to use your MCP on LiteLLM UI

<iframe width="840" height="500" src="https://www.loom.com/embed/57e0763267254bc79dbe6658d0b8758c" frameborder="0" webkitallowfullscreen mozallowfullscreen allowfullscreen></iframe>

### Use with Responses API

Replace `http://localhost:4000` with your LiteLLM Proxy base URL.

Demo Video Using Responses API with LiteLLM Proxy: [Demo video here](https://www.loom.com/share/34587e618c5c47c0b0d67b4e4d02718f?sid=2caf3d45-ead4-4490-bcc1-8d6dd6041c02)


<Tabs>
<TabItem value="curl" label="cURL">

```bash title="cURL Example" showLineNumbers
curl --location 'http://localhost:4000/v1/responses' \
--header 'Content-Type: application/json' \
--header "Authorization: Bearer sk-1234" \
--data '{
    "model": "gpt-5",
    "input": [
    {
      "role": "user",
      "content": "give me TLDR of what BerriAI/litellm repo is about",
      "type": "message"
    }
  ],
    "tools": [
        {
            "type": "mcp",
            "server_label": "litellm",
            "server_url": "litellm_proxy",
            "require_approval": "never"
        }
    ],
    "stream": true,
    "tool_choice": "required"
}'
```

</TabItem>
<TabItem value="python" label="Python SDK">

```python title="Python SDK Example" showLineNumbers
"""
Use LiteLLM Proxy MCP Gateway to call MCP tools.

When using LiteLLM Proxy, you can use the same MCP tools across all your LLM providers.
"""
import openai

client = openai.OpenAI(
    api_key="sk-1234", # paste your litellm proxy api key here
    base_url="http://localhost:4000" # paste your litellm proxy base url here
)
print("Making API request to Responses API with MCP tools")

response = client.responses.create(
    model="gpt-5",
    input=[
        {
            "role": "user",
            "content": "give me TLDR of what BerriAI/litellm repo is about",
            "type": "message"
        }
    ],
    tools=[
        {
            "type": "mcp",
            "server_label": "litellm",
            "server_url": "litellm_proxy",
            "require_approval": "never"
        }
    ],
    stream=True,
    tool_choice="required"
)

for chunk in response:
    print("response chunk: ", chunk)
```

</TabItem>
</Tabs>

#### Specifying MCP Tools

You can specify which MCP tools are available by using the `allowed_tools` parameter. This allows you to restrict access to specific tools within an MCP server.

To get the list of allowed tools when using LiteLLM MCP Gateway, you can naigate to the LiteLLM UI on MCP Servers > MCP Tools > Click the Tool > Copy Tool Name.

<Tabs>
<TabItem value="curl" label="cURL">

```bash title="cURL Example with allowed_tools" showLineNumbers
curl --location 'http://localhost:4000/v1/responses' \
--header 'Content-Type: application/json' \
--header "Authorization: Bearer sk-1234" \
--data '{
    "model": "gpt-5",
    "input": [
    {
      "role": "user",
      "content": "give me TLDR of what BerriAI/litellm repo is about",
      "type": "message"
    }
  ],
    "tools": [
        {
            "type": "mcp",
            "server_label": "litellm",
            "server_url": "litellm_proxy/mcp",
            "require_approval": "never",
            "allowed_tools": ["GitMCP-fetch_litellm_documentation"]
        }
    ],
    "stream": true,
    "tool_choice": "required"
}'
```

</TabItem>
<TabItem value="python" label="Python SDK">

```python title="Python SDK Example with allowed_tools" showLineNumbers
import openai

client = openai.OpenAI(
    api_key="sk-1234",
    base_url="http://localhost:4000"
)

response = client.responses.create(
    model="gpt-5",
    input=[
        {
            "role": "user",
            "content": "give me TLDR of what BerriAI/litellm repo is about",
            "type": "message"
        }
    ],
    tools=[
        {
            "type": "mcp",
            "server_label": "litellm",
            "server_url": "litellm_proxy/mcp",
            "require_approval": "never",
            "allowed_tools": ["GitMCP-fetch_litellm_documentation"]
        }
    ],
    stream=True,
    tool_choice="required"
)

print(response)
```

</TabItem>
</Tabs>

### Use with Cursor IDE

Use tools directly from Cursor IDE with LiteLLM MCP:

**Setup Instructions:**

1. **Open Cursor Settings**: Use `⇧+⌘+J` (Mac) or `Ctrl+Shift+J` (Windows/Linux)
2. **Navigate to MCP Tools**: Go to the "MCP Tools" tab and click "New MCP Server"
3. **Add Configuration**: Copy and paste the JSON configuration below, then save with `Cmd+S` or `Ctrl+S`

```json title="Basic Cursor MCP Configuration" showLineNumbers
{
  "mcpServers": {
    "LiteLLM": {
      "url": "litellm_proxy",
      "headers": {
        "x-litellm-api-key": "Bearer $LITELLM_API_KEY"
      }
    }
  }
}
```

#### How it works when server_url="litellm_proxy"

When server_url="litellm_proxy", LiteLLM bridges non-MCP providers to your MCP tools.

- Tool Discovery: LiteLLM fetches MCP tools and converts them to OpenAI-compatible definitions
- LLM Call: Tools are sent to the LLM with your input; LLM selects which tools to call
- Tool Execution: LiteLLM automatically parses arguments, routes calls to MCP servers, executes tools, and retrieves results
- Response Integration: Tool results are sent back to LLM for final response generation
- Output: Complete response combining LLM reasoning with tool execution results

This enables MCP tool usage with any LiteLLM-supported provider, regardless of native MCP support.

#### Auto-execution for require_approval: "never"

Setting require_approval: "never" triggers automatic tool execution, returning the final response in a single API call without additional user interaction.

### Use with External MCP Servers (Direct)

You can use external MCP servers directly with the Responses API by providing the server URL. OpenAI will connect directly to the MCP server.

**Important Requirements:**
- The MCP server must have a valid SSL/TLS certificate that OpenAI can verify
- The MCP server must be publicly accessible from OpenAI's infrastructure
- Supported models: GPT-4o, GPT-4.1, GPT-5 series, and o-series models

<Tabs>
<TabItem value="python" label="Python SDK">

```python title="External MCP Server Example" showLineNumbers
import litellm

# Configure external MCP server
MCP_TOOLS = [
    {
        "type": "mcp",
        "server_label": "my_mcp_server",
        "server_url": "https://your-mcp-server.com/mcp",
        # Optional: Add headers if authentication is required
        # "headers": {
        #     "Authorization": "Bearer YOUR_TOKEN"
        # }
    }
]

response = litellm.responses(
    model="gpt-4o",
    tools=MCP_TOOLS,
    input="Your query here",
    stream=False
)

print(response)
```

</TabItem>
</Tabs>

**Troubleshooting SSL Errors:**

If you encounter SSL/TLS certificate verification errors like:
```
ServiceUnavailableError: TLS_error:|268435581:SSL routines:OPENSSL_internal:CERTIFICATE_VERIFY_FAILED
```

This means OpenAI cannot verify the MCP server's SSL certificate. Solutions:
1. Ensure the MCP server has a valid SSL certificate from a trusted CA
2. Use the LiteLLM Proxy approach with `server_url="litellm_proxy"` (see above)
3. Use the manual SDK approach (see below)

### Manual SDK Approach for MCP Tools

For cases where the Responses API cannot connect to your MCP server (e.g., SSL issues, non-public servers, or self-hosted servers), you can manually handle tool discovery and execution:

<Tabs>
<TabItem value="python-manual" label="Python Manual Approach">

```python title="Manual MCP Integration" showLineNumbers
import litellm
import asyncio
import json
import re
from litellm.experimental_mcp_client.client import MCPClient
from litellm.types.mcp import MCPTransport
from mcp.types import CallToolRequestParams

def sanitize_tool_name(name):
    """Convert tool name to match OpenAI pattern ^[a-zA-Z0-9_-]+$"""
    sanitized = re.sub(r'[^a-zA-Z0-9_-]', '_', name)
    return sanitized.strip('_')

async def use_mcp_with_litellm(query: str, mcp_server_url: str):
    """
    Manually integrate MCP tools with LiteLLM SDK.
    This approach gives you full control over tool discovery and execution.
    """
    # Initialize MCP client
    mcp_client = MCPClient(
        server_url=mcp_server_url,
        transport_type=MCPTransport.http,
        timeout=60.0
    )

    async with mcp_client:
        # Step 1: Discover available tools from MCP server
        tools_response = await mcp_client.list_tools()

        # Step 2: Convert MCP tools to OpenAI format
        openai_tools = [
            {
                "type": "function",
                "function": {
                    "name": sanitize_tool_name(tool.name),
                    "description": tool.description or "",
                    "parameters": tool.inputSchema
                }
            }
            for tool in tools_response
        ]

        # Create mapping from sanitized to original names
        tool_mapping = {
            sanitize_tool_name(tool.name): tool.name
            for tool in tools_response
        }

        # Step 3: First LLM call with tools
        messages = [{"role": "user", "content": query}]
        response = litellm.completion(
            model="gpt-5",
            messages=messages,
            tools=openai_tools,
            tool_choice="auto"
        )

        # Step 4: If LLM wants to call tools, execute them
        if response['choices'][0]['message'].get('tool_calls'):
            messages.append(response['choices'][0]['message'])

            # Execute all tool calls
            for tool_call in response['choices'][0]['message']['tool_calls']:
                sanitized_name = tool_call['function']['name']
                original_name = tool_mapping[sanitized_name]
                arguments = json.loads(tool_call['function']['arguments'])

                # Call the MCP tool
                result = await mcp_client.call_tool(
                    CallToolRequestParams(
                        name=original_name,
                        arguments=arguments
                    )
                )

                # Add tool result to messages
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call['id'],
                    "content": str(result.content[0].text)
                })

            # Step 5: Final LLM call with tool results
            final_response = litellm.completion(
                model="gpt-5",
                messages=messages
            )

            return final_response['choices'][0]['message']['content']
        else:
            return response['choices'][0]['message']['content']

# Example usage
async def main():
    result = await use_mcp_with_litellm(
        query="Search for latest AI news",
        mcp_server_url="https://your-mcp-server.com/mcp"
    )
    print(result)

# Run the async function
asyncio.run(main())
```

</TabItem>
</Tabs>

**When to use the manual approach:**
- MCP server has SSL certificate issues
- MCP server is self-hosted or behind a firewall
- You need fine-grained control over tool execution
- You want to add custom logic between tool calls
- You're using non-OpenAI providers that don't support MCP natively
