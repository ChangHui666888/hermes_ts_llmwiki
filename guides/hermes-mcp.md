---
title: Use MCP with Hermes
created: 2026-06-28
updated: 2026-06-28
type: concept
tags: [guide, mcp, hermes, integration, tools]
sources: [https://hermes-agent.nousresearch.com/docs/guides/use-mcp-with-hermes]
confidence: high
---

# Use MCP with Hermes

**Source:** [Hermes Agent Docs – Use MCP with Hermes](https://hermes-agent.nousresearch.com/docs/guides/use-mcp-with-hermes)

## When to Use MCP

**Use MCP when:**
- A tool already exists in MCP form and you don't want to build a native Hermes tool
- You want Hermes to operate against a local/remote system via a clean RPC layer
- You need fine-grained per-server exposure control (whitelist/blacklist tools)
- You want to connect Hermes to internal APIs, databases, or company systems without modifying core

**Do NOT use MCP when:**
- A built-in Hermes tool already solves the job well
- The server exposes a huge dangerous tool surface and you are not prepared to filter it
- You only need one narrow integration (native tool is simpler and safer)

## Setup

### Step 1: Install MCP Support

```bash
cd ~/.hermes/hermes-agent
uv pip install -e ".[mcp]"
```

Ensure Node.js/npx (for npm servers) and uvx (for Python servers) are available.

### Step 2: Add a Server

```yaml
mcp_servers:
  project_fs:
    command: "npx"
    args: ["-y", "@modelcontextprotocol/server-filesystem", "/home/user/my-project"]
```

### Step 3: Verify

- Check Hermes banner for MCP integration
- Ask: *"Tell me which MCP-backed tools are available right now."*
- Use `/reload-mcp` after config changes

## Tool Filtering

### Whitelist (best default for sensitive systems)

```yaml
mcp_servers:
  github:
    command: "npx"
    args: ["-y", "@modelcontextprotocol/server-github"]
    env:
      GITHUB_PERSONAL_ACCESS_TOKEN: "***"
    tools:
      include: [list_issues, create_issue, search_code]
```

### Blacklist

```yaml
mcp_servers:
  stripe:
    url: "https://mcp.stripe.com"
    headers:
      Authorization: "Bearer ***"
    tools:
      exclude: [delete_customer, refund_payment]
```

### Disable Utility Wrappers

```yaml
mcp_servers:
  docs:
    url: "https://mcp.docs.example.com"
    tools:
      prompts: false
      resources: false
```

## WSL2 → Windows Chrome Bridge

When `/browser connect` fails from WSL, use MCP as bridge:

```bash
hermes mcp add chrome-devtools-win --command cmd.exe --args /c npx -y chrome-devtools-mcp@latest --autoConnect --no-usage-statistics
```

**Pitfalls:** Start Hermes from a Windows-mounted path (`/mnt/c/...`). Avoid `/root` or `/home` paths.

See [[hermes-adding-tools]], [[hermes-build-plugin]], [[hermes-gateway-internals]].
