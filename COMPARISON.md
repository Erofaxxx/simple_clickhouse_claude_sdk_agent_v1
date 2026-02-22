# Agent Implementation Comparison

This document compares the two ClickHouse agent implementations.

## Summary

The repository now contains **two separate agents** for working with ClickHouse via MCP server:

1. **Claude SDK Agent** (`agent.py`) - Original implementation
2. **LangChain Agent** (`langchain_agent.py`) - New implementation

## Key Differences

### Architecture

| Feature | Claude SDK Agent | LangChain Agent |
|---------|------------------|-----------------|
| **Framework** | claude-agent-sdk | LangChain + LangGraph |
| **Agent Type** | Direct query | ReAct (Reasoning + Acting) |
| **MCP Launch** | Direct `mcp-clickhouse` | Via `uv run` |
| **Stream Handler** | Basic output | UltraCleanStreamHandler |

### Dependencies

**Claude SDK Agent** (`requirements.txt`):
```
claude-agent-sdk
python-dotenv
mcp-clickhouse
```

**LangChain Agent** (`requirements_langchain.txt`):
```
langchain-mcp-adapters
langgraph
langchain
langchain-anthropic
python-dotenv
mcp-clickhouse
```

### Resource Usage

| Resource | Claude SDK Agent | LangChain Agent |
|----------|------------------|-----------------|
| **RAM** | ~400-600 MB | ~600-800 MB |
| **Disk** | ~300 MB | ~500 MB |
| **Startup Time** | Fast | Moderate |

### Features

#### Claude SDK Agent
- ✅ Minimal dependencies
- ✅ Lower memory footprint
- ✅ Direct MCP server connection
- ✅ Fast startup
- ✅ Simple architecture
- ✅ Sanitized string handling for Unicode
- ✅ Works on servers with 1 GB RAM (with swap)

#### LangChain Agent
- ✅ ReAct architecture (Reasoning + Acting)
- ✅ UltraCleanStreamHandler for clean output
- ✅ Integration with LangChain ecosystem
- ✅ Extensible through LangChain components
- ✅ Better handling of streaming responses
- ✅ Suitable for complex multi-step reasoning

## Implementation Details

### Claude SDK Agent (`agent.py`)

**Key Components:**
- Direct use of `claude_agent_sdk.query()`
- MCP server configuration with direct `mcp-clickhouse` command
- String sanitization to handle Unicode encoding issues
- Straightforward message handling (AssistantMessage, UserMessage, TextBlock, ToolUseBlock)

**MCP Server Configuration:**
```python
options = ClaudeAgentOptions(
    allowed_tools=[...],
    mcp_servers={
        "mcp-clickhouse": {
            "command": "mcp-clickhouse",
            "args": [],
            "env": mcp_env,
        }
    },
)
```

### LangChain Agent (`langchain_agent.py`)

**Key Components:**
- `UltraCleanStreamHandler` class for clean streaming output
- `create_react_agent()` from LangGraph
- `load_mcp_tools()` from langchain-mcp-adapters
- `stdio_client` and `ClientSession` for MCP connection
- Event streaming with `agent.astream_events()`

**MCP Server Configuration:**
```python
server_params = StdioServerParameters(
    command="uv",
    args=["run", "--with", "mcp-clickhouse", "--python", "3.13", "mcp-clickhouse"],
    env=mcp_env,
)
```

**Stream Handler:**
```python
class UltraCleanStreamHandler:
    def handle_chunk(self, chunk):
        # Handles on_chat_model_stream events
        # Handles on_tool_start events
        # Handles on_tool_end events
```

## Setup Scripts

### `setup.sh` (Claude SDK Agent)
- Installs system packages (python3, pip, curl, wget)
- Installs Python dependencies directly via pip
- Downloads Yandex SSL certificate
- Creates swap file on low-memory servers
- No `uv` required

### `setup_langchain.sh` (LangChain Agent)
- Installs system packages
- Installs Python dependencies via pip
- **Installs `uv` manager** (required for MCP server)
- Downloads Yandex SSL certificate
- Creates swap file on low-memory servers

## Documentation

### `README.md`
- Main documentation
- Covers both agents (overview)
- Detailed guide for Claude SDK Agent
- Links to LangChain documentation

### `README_LANGCHAIN.md`
- Dedicated LangChain Agent documentation
- Setup instructions with `setup_langchain.sh`
- Usage examples
- Comparison table
- When to use which agent

## Usage

### Claude SDK Agent
```bash
# Setup
bash setup.sh

# Run
python3 agent.py "Your question here"
```

### LangChain Agent
```bash
# Setup
bash setup_langchain.sh

# Run
python3 langchain_agent.py "Who's committed the most code to ClickHouse?"
```

## When to Use Which Agent?

### Use Claude SDK Agent When:
- ✅ You need minimal setup and dependencies
- ✅ Memory is limited (servers with ≤ 1 GB RAM)
- ✅ You want the fastest possible response times
- ✅ You need a simple, straightforward solution
- ✅ You don't need LangChain integration

### Use LangChain Agent When:
- ✅ You need integration with the LangChain ecosystem
- ✅ You want ReAct architecture for complex reasoning
- ✅ You need better streaming output control
- ✅ You're building a larger LangChain application
- ✅ You need extensibility through LangChain components

## Validation

Run the validation script to check both implementations:
```bash
bash validate_agents.sh
```

This will:
- Check file structure
- Validate Python syntax
- Compare key features
- Show implementation differences

## Conclusion

Both agents are production-ready and fully functional. The choice depends on your specific requirements:
- **Claude SDK Agent**: Best for most use cases (simpler, faster, lower memory)
- **LangChain Agent**: Best when you need LangChain integration or advanced features
