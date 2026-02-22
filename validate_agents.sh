#!/bin/bash
# Validation script - compares both agent implementations
# Скрипт для проверки обоих агентов

echo "=========================================="
echo "  Agent Implementation Validation"
echo "=========================================="
echo

echo "📋 Checking file structure..."
echo

if [ -f "agent.py" ]; then
    echo "✅ agent.py exists (Claude SDK Agent)"
else
    echo "❌ agent.py not found"
fi

if [ -f "langchain_agent.py" ]; then
    echo "✅ langchain_agent.py exists (LangChain Agent)"
else
    echo "❌ langchain_agent.py not found"
fi

if [ -f "requirements.txt" ]; then
    echo "✅ requirements.txt exists (Claude SDK dependencies)"
else
    echo "❌ requirements.txt not found"
fi

if [ -f "requirements_langchain.txt" ]; then
    echo "✅ requirements_langchain.txt exists (LangChain dependencies)"
else
    echo "❌ requirements_langchain.txt not found"
fi

if [ -f "setup.sh" ]; then
    echo "✅ setup.sh exists"
else
    echo "❌ setup.sh not found"
fi

if [ -f "setup_langchain.sh" ]; then
    echo "✅ setup_langchain.sh exists"
else
    echo "❌ setup_langchain.sh not found"
fi

if [ -f "README.md" ]; then
    echo "✅ README.md exists"
else
    echo "❌ README.md not found"
fi

if [ -f "README_LANGCHAIN.md" ]; then
    echo "✅ README_LANGCHAIN.md exists"
else
    echo "❌ README_LANGCHAIN.md not found"
fi

echo
echo "🐍 Checking Python syntax..."
echo

python3 -m py_compile agent.py 2>&1
if [ $? -eq 0 ]; then
    echo "✅ agent.py syntax is valid"
else
    echo "❌ agent.py has syntax errors"
fi

python3 -m py_compile langchain_agent.py 2>&1
if [ $? -eq 0 ]; then
    echo "✅ langchain_agent.py syntax is valid"
else
    echo "❌ langchain_agent.py has syntax errors"
fi

echo
echo "📊 Key differences:"
echo

echo "Claude SDK Agent (agent.py):"
echo "  - Uses: claude-agent-sdk"
echo "  - Memory: ~400-600 MB"
echo "  - MCP Launch: Direct mcp-clickhouse"
grep -c "from claude_agent_sdk import" agent.py > /dev/null && echo "  - ✅ Imports claude-agent-sdk"

echo
echo "LangChain Agent (langchain_agent.py):"
echo "  - Uses: LangChain + LangGraph"
echo "  - Memory: ~600-800 MB"
echo "  - MCP Launch: Via uv run"
grep -c "from langchain_mcp_adapters import" langchain_agent.py > /dev/null && echo "  - ✅ Imports langchain-mcp-adapters"
grep -c "create_react_agent" langchain_agent.py > /dev/null && echo "  - ✅ Uses ReAct agent"
grep -c "class UltraCleanStreamHandler" langchain_agent.py > /dev/null && echo "  - ✅ Implements UltraCleanStreamHandler"

echo
echo "=========================================="
echo "  Validation Complete"
echo "=========================================="
echo
echo "Next steps:"
echo "1. Review the implementations"
echo "2. Test agent.py with: python3 agent.py"
echo "3. Test langchain_agent.py with: python3 langchain_agent.py"
echo
