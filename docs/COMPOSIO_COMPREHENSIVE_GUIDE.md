# Composio Integration Guide
## Everything You Need to Know About Tools, Toolkits, Tool Router & MCP

---

## Table of Contents

1. [What is Composio?](#what-is-composio)
2. [Core Architecture](#core-architecture)
3. [Tools & Toolkits](#tools--toolkits)
4. [Tool Router](#tool-router)
5. [Model Context Protocol (MCP)](#model-context-protocol-mcp)
6. [Authentication](#authentication)
7. [Sessions](#sessions)
8. [Triggers & Webhooks](#triggers--webhooks)
9. [Integration Patterns](#integration-patterns)
10. [Code Examples](#code-examples)
11. [Best Practices](#best-practices)

---

## What is Composio?

Composio is an integration layer that bridges AI models and the real world, enabling LLMs and agents to reliably interact with 1000+ external tools and services. Think of it as the connective tissue between what AI wants to do and what it can actually execute.

### The Core Value Proposition

- **1000+ Pre-built Integrations**: GitHub, Gmail, Slack, Notion, HubSpot, and hundreds more
- **Managed Authentication**: OAuth, API keys, token refresh handled automatically
- **Dynamic Tool Discovery**: Agents find and use tools at runtime without overwhelming context
- **Execution Infrastructure**: Sandboxed environments for running code and processing large responses
- **Event-Driven Workflows**: Triggers that activate agents based on external events

---

## Core Architecture

Composio operates on a **dual-layer architecture**:

### 1. The Planner Layer
Handles task decomposition and breaks high-level objectives into verifiable sub-tasks. This prevents context window pollution—if you give an agent 100 tools, the documentation consumes thousands of tokens and confuses the model.

### 2. The Executor Layer
Handles actual tool interaction, authentication, and execution with proper error handling.

### The Problem It Solves: Context Window Management

Without Composio, loading documentation for 100 tools would overwhelm your agent's context window. Composio solves this through **managed toolsets** and **dynamic tool discovery**—agents request only what they need, when they need it.

---

## Tools & Toolkits

### Understanding the Hierarchy

**Toolkit** = A collection of related tools for a service  
**Tool** = An individual action your agent can execute

#### Example:
- **Toolkit**: `GITHUB`
- **Tools within it**: 
  - `GITHUB_CREATE_ISSUE`
  - `GITHUB_STAR_REPOSITORY`
  - `GITHUB_CREATE_PULL_REQUEST`
  - ...and 8,000+ more GitHub actions

### Tool Naming Convention

All tools follow the pattern: `{TOOLKIT}_{ACTION}`

Examples:
- `GMAIL_SEND_EMAIL`
- `SLACK_SENDS_A_MESSAGE_TO_A_SLACK_CHANNEL`
- `NOTION_CREATE_PAGE`

### Tool Structure

Every tool has:
1. **Input Schema**: Required and optional parameters
2. **Output Schema**: What it returns
3. **Authentication Requirements**: The credentials needed to execute

### The Meta Tools System

Instead of loading all 1000+ toolkits into context, Composio provides **5 meta tools** that discover, authenticate, and execute tools at runtime:

#### 1. `COMPOSIO_SEARCH_TOOLS`
Discovers relevant tools based on the task description.

**Returns:**
- Matching tools with input schemas
- Connection status (connected/not connected)
- Execution plan and tips

#### 2. `COMPOSIO_MANAGE_CONNECTIONS`
Creates or manages connections to user apps.

**Returns:**
- Active connection details (if connected)
- Authentication link (if not connected)
- Works for OAuth, API keys, and all auth types

#### 3. `COMPOSIO_MULTI_EXECUTE_TOOL`
Executes tools with the user's authenticated credentials.

**Use for:**
- Single tool calls
- Parallel operations on similar data
- Independent tool calls

#### 4. `COMPOSIO_REMOTE_WORKBENCH`
Runs Python code in a persistent sandbox.

**Use for:**
- Bulk operations (e.g., labeling 100 emails)
- Complex data transformations
- When results need further analysis
- Includes helper functions like `invoke_llm`

#### 5. `COMPOSIO_REMOTE_BASH_TOOL`
Executes bash commands for simpler operations.

**Use for:**
- File operations
- Data extraction with tools like jq, awk, sed, grep

### How Meta Tools Work Together

Here's the typical flow when a user says: *"Create a GitHub issue for this bug"*

```
User Request
    ↓
1. Agent calls COMPOSIO_SEARCH_TOOLS
    → Returns: GITHUB_CREATE_ISSUE with schema
    → Returns: Connection status: "not connected"
    → Returns: Execution plan
    ↓
2. Agent calls COMPOSIO_MANAGE_CONNECTIONS
    → Returns: Auth link for GitHub
    → User clicks and authenticates
    ↓
3. Agent calls COMPOSIO_MULTI_EXECUTE_TOOL
    → Executes GITHUB_CREATE_ISSUE with arguments
    → Returns: Created issue details
    ↓
Done ✓
```

### Direct Tool Execution

If you know exactly which tools you need, you can bypass meta tools and execute directly:

```python
from composio import Composio

composio = Composio()
tools = composio.tools.get(
    user_id="user_123",
    toolkits=["GITHUB", "SLACK"]
)

# Tools execute with user's authenticated credentials
# If auth is missing, the agent prompts via COMPOSIO_MANAGE_CONNECTIONS
```

---

## Tool Router

Tool Router is Composio's **experimental** feature that provides a unified interface for searching, planning, authenticating, and executing actions across thousands of tools.

### What is Tool Router?

Think of it as the underlying technology that powers **Rube** (Composio's universal MCP server). It's a gateway that does everything Rube does but with programmatic control.

### Key Capabilities

1. **Dynamic Tool Loading**: Agents load tools from multiple apps based on the task at hand
2. **Single MCP Endpoint**: One endpoint for all integrations
3. **Tool Search Precision**: Programmatically generate MCP URLs with specific apps
4. **Security & Reliability**: Built-in authentication, rate limiting, and error handling

### Architecture

```
User Request
    ↓
Tool Router
    ↓
┌─────────────────┬──────────────────┬──────────────────┐
│   Discovery     │  Authentication  │    Execution     │
├─────────────────┼──────────────────┼──────────────────┤
│ Search for      │ Check for active │ Execute action   │
│ relevant tools  │ connections      │ using            │
│ matching task   │                  │ authenticated    │
│                 │ If missing:      │ connection       │
│ Return toolkit  │ create auth      │                  │
│ details         │ config & URL     │                  │
└─────────────────┴──────────────────┴──────────────────┘
```

### Creating a Tool Router Session

**TypeScript:**
```typescript
import { Composio } from '@composio/core';

const composio = new Composio();
const userId = "user_123";

// Create a tool router session
const session = composio.experimental.toolRouter.createSession(userId);

// Returns a pre-signed MCP URL for the user's session
console.log(session.mcp.url);
```

**Python:**
```python
from composio import Composio

composio = Composio()
session = composio.create(
    user_id="user_123",
    toolkits=["github", "gmail", "slack"]  # optional
)

# Access MCP URL
mcp_url = session.mcp.url
```

### Restricting Available Toolkits

By default, sessions have access to **all** toolkits in the Composio catalog. You can restrict this:

```typescript
const session = await composio.create("user_123", {
    toolkits: ["GITHUB", "SLACK", "NOTION"]
});
```

### Tool Router vs Direct Tool Execution

| Feature | Tool Router | Direct Execution |
|---------|-------------|------------------|
| **Tool Discovery** | ✅ Dynamic at runtime | ❌ Manual specification |
| **Context Management** | ✅ Automatic | ❌ Manual |
| **Multi-app Workflows** | ✅ Seamless | ⚠️ Requires setup |
| **Control** | ⚠️ Experimental | ✅ Full control |
| **Best For** | Exploratory tasks, broad capabilities | Known workflows, production systems |

---

## Model Context Protocol (MCP)

### What is MCP?

MCP is a **protocol** (not a framework) that standardizes how AI applications connect to external data sources and tools. Think of it as the **USB-C port for AI agents**.

Anthropic released MCP in November 2024. By March 2025, it became the hottest topic in AI when major consumer IDEs (Cursor, Cline, Claude Desktop, VS Code) officially adopted it.

### Why MCP Matters

**Before MCP:**
- Every AI tool needed custom integrations for every service
- No standardization between clients (Claude, Cursor) and servers (Gmail, Slack)
- Developers built the same integrations over and over

**After MCP:**
- Universal protocol for tool integration
- Build once, use everywhere
- Client developers focus on UI, server developers focus on integrations

### MCP Architecture

```
┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│     Host     │◄───────►│   Client     │◄───────►│    Server    │
│              │         │              │         │              │
│  Claude      │         │  MCP Client  │         │  GitHub      │
│  Cursor      │         │  (1:1 with   │         │  Slack       │
│  Cline       │         │   server)    │         │  Gmail       │
└──────────────┘         └──────────────┘         └──────────────┘
       ▲                                                  ▲
       │                                                  │
       └──────────────────────────────────────────────────┘
                    Base Protocol Layer
```

#### Components:

1. **Host**: Coordinates the system and manages LLM interactions (e.g., Claude Desktop, Cursor)
2. **Client**: Connects hosts to servers with 1:1 relationships
3. **Server**: Provides specialized capabilities (tools, resources, prompts)
4. **Base Protocol**: Defines communication standards

### MCP Gateway

In production systems with many agents and tools, managing direct connections creates security and observability challenges. An **MCP Gateway** acts as a centralized proxy to:

- Enforce policies
- Monitor traffic
- Simplify integration
- Handle authentication

### Composio's MCP Implementation

Composio implements MCP through **Rube** and **Tool Router**:

#### Rube (Universal MCP Server)
- Access to 850+ SaaS apps
- Just-in-time tool loading
- Remote workbench for large responses
- Keeps LLM context window clean

**Installing Rube in Claude Desktop:**
```bash
# Copy and paste in Claude Code/Desktop
npx @composiohq/cli add-mcp rube
```

#### Tool Router as MCP
Tool Router generates secure MCP URLs that agents can access:

```typescript
const session = await composio.create("user_123", {
    toolkits: ["miro"]
});

const mcpUrl = session.mcp.url;
// Use this URL to connect to the MCP server
```

### MCP Server Creation: Standalone vs Tool Router

**Standalone MCP Server:**
- Fixed set of tools tied to that server
- Less flexible but more controlled
- Good for specific, narrow use cases

**Tool Router MCP:**
- Dynamically loads tools based on task
- Single endpoint for multiple apps
- Better for general-purpose agents

### Working with MCP in Different Frameworks

#### With Vercel AI SDK v6:
```typescript
import { createMCPClient } from "@ai-sdk/mcp";

const session = await composio.create("user_123", {
    toolkits: ["miro"]
});

const mcpClient = createMCPClient({
    url: session.mcp.url,
    headers: session.mcp.headers
});
```

#### With LangChain:
```python
from composio import Composio
from composio_langchain import LangchainProvider

composio = Composio(provider=LangchainProvider())

session = composio.create(
    user_id="user_123",
    toolkits=["smtp2go"]
)

tools = session.tools()
```

#### With OpenAI Agents SDK:
```python
from composio import Composio
from composio_openai_agents import OpenAIAgentsProvider
from agents import Agent, Runner, HostedMCPTool

composio = Composio(provider=OpenAIAgentsProvider())

session = composio.create(
    user_id="user_123",
    toolkits=["clockify"]
)

agent = Agent(
    name="Clockify Agent",
    instructions="You are a time tracking assistant.",
    tools=session.tools()
)
```

---

## Authentication

Composio handles OAuth flows, API keys, token refresh, and credential storage for 500+ apps automatically.

### Authentication Methods Supported

1. **OAuth 2.0** (most common)
2. **API Keys**
3. **Bearer Tokens**
4. **Basic Auth** (username/password)
5. **Custom Schemes**

### Auth Configs

An **Auth Config** defines how users authenticate with a service. You need to create one before users can connect their accounts.

#### Creating Auth Configs

**Via Dashboard:**
1. Navigate to "Auth Configs" tab
2. Click "Create Auth Config"
3. Select toolkit (e.g., Gmail, Slack, GitHub)
4. Configure authentication method

**Via API:**
```python
from composio import Composio

composio = Composio(api_key="YOUR_API_KEY")

# Create OAuth config
auth_config = composio.auth_configs.create(
    toolkit="github",
    auth_config={
        "type": "oauth2",
        "credentials": {
            "client_id": "your_client_id",
            "client_secret": "your_client_secret"
        }
    }
)
```

### Why Multiple Auth Configs?

You might create multiple configs for:
- **Different authentication methods**: One OAuth, one API key
- **Different scopes**: Read-only vs full access
- **Different OAuth apps**: Separate credentials for dev/staging/prod
- **Different permission levels**: Limiting actions for specific use cases

### User Authentication Flow

#### Method 1: Connect Link (Recommended)

Redirect users to a Composio-hosted URL that handles the entire authentication process.

```python
from composio import Composio

composio = Composio(api_key="YOUR_API_KEY")

connection_request = composio.connected_accounts.initiate(
    user_id="user_123",
    auth_config_id="ac_github_config",
    config={"auth_scheme": "OAUTH2"},
    callback_url="https://yourapp.com/callback"
)

print(f"Redirect URL: {connection_request.redirect_url}")

# Wait for user to complete auth
connected_account = connection_request.wait_for_connection()
print(f"Connected: {connected_account.id}")
```

**TypeScript:**
```typescript
const connectionRequest = await composio.connectedAccounts.initiate({
    userId: "user_123",
    authConfigId: "ac_github_config",
    config: { authScheme: "OAUTH2" },
    callbackUrl: "https://yourapp.com/callback"
});

console.log(`Redirect to: ${connectionRequest.redirectUrl}`);
```

#### Method 2: SDK Integration

For programmatic control:

```python
session = composio.create(user_id="user_123")
connection_request = session.authorize("github")
print(f"Auth URL: {connection_request.redirect_url}")
```

### Connection Status

After authentication, connections have these statuses:

- `ACTIVE`: Ready to use
- `INITIATED`: Auth started but not completed
- `EXPIRED`: Refresh attempts failed
- `FAILED`: Authentication or refresh failed

Composio automatically refreshes OAuth tokens before they expire.

### White-Labeling Authentication

Remove Composio branding and use your own OAuth apps:

```python
# Use your own OAuth credentials
auth_config = composio.auth_configs.create(
    toolkit="github",
    auth_config={
        "type": "oauth2",
        "credentials": {
            "client_id": "YOUR_CLIENT_ID",
            "client_secret": "YOUR_CLIENT_SECRET"
        },
        "white_label": True
    }
)
```

### Inspecting Auth Requirements

Before connecting, you can inspect what authentication a toolkit needs:

```python
# Check authentication method and required fields
auth_info = composio.auth_configs.get_requirements(
    toolkit="stripe"
)

print(auth_info.auth_method)  # e.g., "API_KEY"
print(auth_info.required_fields)  # e.g., ["api_key"]
```

---

## Sessions

Sessions are Composio's next-generation abstraction that handles tool fetching, authentication, and execution automatically.

### What is a Session?

A session represents a user's interaction with Composio. It:
- Groups connected accounts
- Manages available toolkits
- Provides meta tools for dynamic discovery
- Handles authentication flows

### Creating Sessions

**Python:**
```python
from composio import Composio

composio = Composio()

# Create session with specific toolkits
session = composio.create(
    user_id="user_123",
    toolkits=["github", "gmail"]  # optional, defaults to all
)

# Get tools
tools = session.tools()
```

**TypeScript:**
```typescript
import { Composio } from '@composio/core';

const composio = new Composio();

const session = await composio.create("user_123", {
    toolkits: ["GITHUB", "GMAIL"]
});

const tools = await session.tools();
```

### Session Configuration Options

```python
session = composio.create(
    user_id="user_123",
    
    # Restrict available toolkits
    toolkits=["github", "slack"],
    
    # Use custom auth configs
    auth_configs={
        "github": "ac_your_github_config",
        "slack": "ac_your_slack_config"
    },
    
    # Select specific connected accounts
    connected_accounts=["ca_account_1", "ca_account_2"]
)
```

### Manual Authentication in Sessions

While sessions handle auth automatically during agent chats, you can also trigger it manually:

```python
session = composio.create(user_id="user_123")

# Manually trigger auth
connection_request = session.authorize("github")
print(f"Authenticate at: {connection_request.redirect_url}")

# Wait for completion
connected_account = connection_request.wait_for_connection()
```

### Session Memory and Context

Meta tool calls within a session are correlated using a `session_id`, allowing them to:
- Share context between calls
- Store useful information (IDs, relationships) for subsequent calls
- Maintain conversation state

---

## Triggers & Webhooks

Triggers enable event-driven workflows where external events automatically activate your AI agents.

### What Are Triggers?

Triggers listen for events in connected apps (new Slack message, GitHub commit, Gmail email) and notify your application when they occur.

**Use Cases:**
- Slack bot that responds to messages
- GitHub bot that analyzes commits
- Email assistant that categorizes incoming mail
- CRM automation on new deals

### Available Triggers

Composio offers triggers for 1000+ apps. Examples:
- `GMAIL_NEW_GMAIL_MESSAGE`
- `SLACK_RECEIVE_MESSAGE`
- `GITHUB_COMMIT_EVENT`
- `NOTION_PAGE_CREATED`
- `HUBSPOT_DEAL_CREATED`

### Creating Triggers

#### Via Dashboard:
1. Navigate to Triggers section
2. Click "Add Trigger"
3. Select the event type
4. Configure any required fields
5. Get your trigger ID from "Active Triggers"

#### Via SDK:

**Python:**
```python
from composio import Composio

composio = Composio()

# Create trigger
trigger = composio.triggers.create(
    user_id="user_123",
    connected_account_id="ca_github_account",
    trigger_name="GITHUB_COMMIT_EVENT",
    config={
        "repo": "composiohq/composio",
        "branch": "main"
    }
)

print(f"Trigger ID: {trigger.id}")
```

**TypeScript:**
```typescript
const trigger = await composio.triggers.create({
    userId: "user_123",
    connectedAccountId: "ca_github_account",
    triggerName: "GITHUB_COMMIT_EVENT",
    config: {
        repo: "composiohq/composio",
        branch: "main"
    }
});
```

### Subscribing to Triggers

You can receive trigger events via two methods:

#### Method 1: Webhooks (Production)

Configure a publicly accessible URL to receive POST requests.

**Setup:**
1. Go to Composio Dashboard → Project Settings → Webhook
2. Add your webhook URL (must be HTTPS in production)
3. Save webhook secret for signature verification

**Local Development:**
Use ngrok or webhook.site to expose your local server:
```bash
ngrok http 3000
# Use the ngrok URL in Composio dashboard
```

**Handling Webhooks:**

```python
from fastapi import FastAPI, Request, HTTPException
import json
from composio import Composio

app = FastAPI()
composio = Composio()

@app.post("/webhook/composio")
async def webhook_handler(request: Request):
    # Get headers for verification
    signature = request.headers.get("webhook-signature")
    timestamp = request.headers.get("webhook-timestamp")
    
    # Get payload
    payload = await request.json()
    
    # Verify webhook signature
    try:
        verified = composio.triggers.verify_webhook(
            signature=signature,
            timestamp=timestamp,
            payload=payload
        )
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    # Process the event
    trigger_slug = payload.get("metadata", {}).get("trigger_slug")
    event_data = payload.get("data")
    
    if trigger_slug == "GITHUB_COMMIT_EVENT":
        commit_data = event_data
        # Invoke your agent with commit_data
        print(f"New commit: {commit_data.get('message')}")
    
    return {"status": "success"}
```

**Webhook Verification:**

Composio signs all webhooks with HMAC-SHA256. Always verify signatures:

```python
from composio import Composio
import os

composio = Composio()

# From webhook headers
signature = "v1,base64_encoded_signature"
timestamp = "1234567890"

# Verify
result = composio.triggers.verify_webhook(
    signature=signature,
    timestamp=timestamp,
    payload=payload,
    tolerance=300  # 5 minutes max age
)

if result.verified:
    # Process safely
    event_data = result.normalized_payload
```

#### Method 2: WebSockets (Development)

For real-time, low-latency connections during development:

```python
from composio import Composio

composio = Composio()

def callback_function(event_data):
    print("Received event:", event_data)
    # Process event

# Subscribe to trigger via WebSocket
composio.triggers.subscribe(
    trigger_id="tg_trigger_123",
    callback=callback_function
)
```

### Webhook Versions

Composio has evolved webhook payloads. The latest is **V3**:

**V3 Format:**
```json
{
  "version": "V3",
  "metadata": {
    "id": "evt_123",
    "trigger_id": "tg_456",
    "trigger_slug": "GMAIL_NEW_GMAIL_MESSAGE",
    "connection_id": "ca_789",
    "user_id": "user_123",
    "timestamp": "2025-03-02T10:30:00Z"
  },
  "data": {
    "from": "sender@example.com",
    "subject": "Important Update",
    "body": "Message content..."
  }
}
```

**Key Improvements:**
- Clear separation between metadata and trigger data
- Follows Standard Webhooks specification
- Same structure for webhooks and WebSockets
- Trigger slug in metadata for easy identification

### Managing Triggers

**Pause/Resume:**
```python
# Pause temporarily
composio.triggers.pause(trigger_id="tg_123")

# Resume
composio.triggers.resume(trigger_id="tg_123")
```

**Delete:**
```python
composio.triggers.delete(trigger_id="tg_123")
```

**List Active Triggers:**
```python
triggers = composio.triggers.list(user_id="user_123")
for trigger in triggers:
    print(f"{trigger.trigger_name}: {trigger.status}")
```

### Webhook Subscriptions API (New)

Composio introduced a flexible webhook subscription model:

```bash
curl -X POST "https://backend.composio.dev/api/v3/webhook_subscriptions" \
  -H "x-api-key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "webhook_url": "https://your-server.com/webhooks/composio",
    "enabled_events": ["composio.trigger.message"],
    "version": "V3"
  }'
```

**Features:**
- Event filtering (subscribe only to what you need)
- HMAC-SHA256 signatures for verification
- Support for platform lifecycle events
- Replaces legacy project-level webhook settings

---

## Integration Patterns

### Pattern 1: Simple Task Automation

**Use Case:** Single-purpose agent that performs specific actions.

```python
from composio import Composio
from composio_openai import OpenAIProvider

composio = Composio(provider=OpenAIProvider())

# Create session
session = composio.create(
    user_id="user_123",
    toolkits=["github"]
)

# Simple task
from openai import OpenAI

client = OpenAI()
response = client.chat.completions.create(
    model="gpt-4",
    messages=[
        {"role": "user", "content": "Star the composiohq/composio repo on GitHub"}
    ],
    tools=session.tools()
)
```

### Pattern 2: Multi-App Workflows

**Use Case:** Complex workflows spanning multiple services.

```python
session = composio.create(
    user_id="user_123",
    toolkits=["github", "slack", "linear"]
)

# Agent can now:
# 1. Detect GitHub issue
# 2. Create Linear task
# 3. Notify team on Slack
```

### Pattern 3: Event-Driven Agent

**Use Case:** Agent that reacts to external events.

```python
from composio import Composio
import asyncio

composio = Composio()

# Create trigger
trigger = composio.triggers.create(
    user_id="user_123",
    connected_account_id="ca_slack",
    trigger_name="SLACK_RECEIVE_MESSAGE",
    config={"channel": "general"}
)

# Define callback
async def handle_slack_message(event_data):
    message = event_data.get("text")
    
    # Invoke agent
    session = composio.create(user_id="user_123")
    # ... agent processes message and responds
    
# Subscribe via webhook (production)
# Configure webhook URL in dashboard to point to your server
```

### Pattern 4: Tool Router for Discovery

**Use Case:** Agent that discovers tools dynamically.

```typescript
import { Composio } from '@composio/core';

const composio = new Composio();

// Create tool router session (all toolkits available)
const session = composio.experimental.toolRouter.createSession("user_123");

// Agent gets meta tools
const tools = await session.tools();

// Agent can now:
// 1. Search for relevant tools with COMPOSIO_SEARCH_TOOLS
// 2. Authenticate with COMPOSIO_MANAGE_CONNECTIONS
// 3. Execute with COMPOSIO_MULTI_EXECUTE_TOOL
```

### Pattern 5: MCP Server Integration

**Use Case:** Building agents that work with Claude Desktop, Cursor, etc.

```python
from composio import Composio

composio = Composio()

# Create session with MCP support
session = composio.create(
    user_id="user_123",
    toolkits=["github", "notion"]
)

# Get MCP URL
mcp_url = session.mcp.url
print(f"Connect your MCP client to: {mcp_url}")

# In Claude Desktop config:
# {
#   "mcpServers": {
#     "composio": {
#       "url": "<mcp_url>",
#       "headers": session.mcp.headers
#     }
#   }
# }
```

---

## Code Examples

### Example 1: GitHub Issue Creator

```python
from composio import Composio
from composio_openai import OpenAIProvider
from openai import OpenAI
import json

# Initialize
composio = Composio(provider=OpenAIProvider())
client = OpenAI()

# Create session
session = composio.create(
    user_id="developer_123",
    toolkits=["github"]
)

# Define the agent
def create_github_issue(user_message: str):
    messages = [
        {
            "role": "system",
            "content": "You are a helpful assistant that creates GitHub issues."
        },
        {
            "role": "user",
            "content": user_message
        }
    ]
    
    response = client.chat.completions.create(
        model="gpt-4",
        messages=messages,
        tools=session.tools(),
        tool_choice="auto"
    )
    
    # Handle tool calls
    while response.choices[0].finish_reason == "tool_calls":
        tool_calls = response.choices[0].message.tool_calls
        
        for tool_call in tool_calls:
            # Execute via Composio
            result = session.execute_tool_call(tool_call)
            
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result)
            })
        
        # Continue conversation
        response = client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            tools=session.tools()
        )
    
    return response.choices[0].message.content

# Use it
result = create_github_issue(
    "Create an issue in composiohq/composio titled 'Add TypeScript support' "
    "with description 'We need better TypeScript types for the SDK'"
)
print(result)
```

### Example 2: Slack Bot with Triggers

```python
from composio import Composio
from fastapi import FastAPI, Request
import json

app = FastAPI()
composio = Composio()

# Create trigger for Slack messages
trigger = composio.triggers.create(
    user_id="bot_user",
    connected_account_id="ca_slack_bot",
    trigger_name="SLACK_RECEIVE_MESSAGE",
    config={"channel": "help-desk"}
)

@app.post("/webhook/slack")
async def handle_slack_event(request: Request):
    # Verify webhook
    signature = request.headers.get("webhook-signature")
    timestamp = request.headers.get("webhook-timestamp")
    payload = await request.json()
    
    composio.triggers.verify_webhook(
        signature=signature,
        timestamp=timestamp,
        payload=payload
    )
    
    # Extract message
    message_data = payload.get("data", {})
    user = message_data.get("user")
    text = message_data.get("text")
    channel = message_data.get("channel")
    
    # Generate response with AI
    response_text = generate_response(text)  # Your AI logic
    
    # Send reply via Composio
    session = composio.create(
        user_id="bot_user",
        toolkits=["slack"]
    )
    
    # Use tool to send message
    session.execute_tool(
        "SLACK_SENDS_A_MESSAGE_TO_A_SLACK_CHANNEL",
        parameters={
            "channel": channel,
            "text": response_text
        }
    )
    
    return {"status": "success"}

def generate_response(message: str) -> str:
    # Your LLM logic here
    return f"I received: {message}"
```

### Example 3: Multi-App Workflow

```python
from composio import Composio
from composio_langchain import LangchainProvider
from langchain_openai import ChatOpenAI
from langchain.agents import create_openai_functions_agent
from langchain.prompts import ChatPromptTemplate

# Initialize
composio = Composio(provider=LangchainProvider())
llm = ChatOpenAI(model="gpt-4")

# Create session with multiple apps
session = composio.create(
    user_id="workflow_user",
    toolkits=["github", "linear", "slack"]
)

# Define the workflow prompt
prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a project management assistant.
    When you receive a GitHub issue, you should:
    1. Create a corresponding Linear task
    2. Post a notification in Slack #dev-updates channel
    3. Provide a summary of what was created"""),
    ("user", "{input}")
])

# Create agent
agent = create_openai_functions_agent(
    llm=llm,
    tools=session.tools(),
    prompt=prompt
)

# Execute workflow
from langchain.agents import AgentExecutor

executor = AgentExecutor(agent=agent, tools=session.tools())

result = executor.invoke({
    "input": "A new critical bug was reported in GitHub issue #342. "
             "Create a Linear task and notify the team."
})

print(result["output"])
```

### Example 4: Custom Tool Creation

```typescript
import { Composio } from '@composio/core';
import { z } from 'zod';

const composio = new Composio();

// Create a standalone custom tool
const customTool = await composio.tools.createCustomTool({
    slug: 'CALCULATE_ROI',
    name: 'Calculate ROI',
    description: 'Calculates return on investment',
    inputParams: z.object({
        investment: z.number().describe('Initial investment amount'),
        returns: z.number().describe('Total returns received'),
    }),
    execute: async (input) => {
        const roi = ((input.returns - input.investment) / input.investment) * 100;
        return {
            data: { roi: roi.toFixed(2) },
            error: null,
            successful: true
        };
    }
});

// Create a toolkit-based custom tool (with auth)
const githubCustomTool = await composio.tools.createCustomTool({
    slug: 'GITHUB_STAR_COMPOSIO_REPOS',
    name: 'Star Composio Repos',
    toolkitSlug: 'github',
    description: 'Stars all Composio repositories',
    inputParams: z.object({
        org: z.string().default('composiohq')
    }),
    execute: async (input, connectionConfig, executeToolRequest) => {
        // Get list of repos
        const repos = await executeToolRequest({
            endpoint: `/orgs/${input.org}/repos`,
            method: 'GET'
        });
        
        // Star each one
        for (const repo of repos.data) {
            await executeToolRequest({
                endpoint: `/user/starred/${input.org}/${repo.name}`,
                method: 'PUT'
            });
        }
        
        return {
            data: { starred: repos.data.length },
            error: null,
            successful: true
        };
    }
});
```

---

## Best Practices

### 1. Authentication Management

**✅ Do:**
- Create separate auth configs for dev/staging/prod
- Use white-labeling for production apps
- Monitor connection status and handle expirations
- Verify webhook signatures

**❌ Don't:**
- Hard-code API keys or OAuth credentials
- Share auth configs between environments
- Ignore connection expiry events

### 2. Tool Selection

**✅ Do:**
- Use meta tools for dynamic discovery when appropriate
- Restrict toolkits in sessions to only what's needed
- Use direct tool execution for known workflows
- Cache tool schemas to reduce API calls

**❌ Don't:**
- Load all 1000+ toolkits into every session
- Bypass authentication checks
- Ignore tool execution errors

### 3. Error Handling

**✅ Do:**
- Implement retry logic for transient failures
- Check connection status before tool execution
- Validate tool parameters before calling
- Log errors for debugging

**❌ Don't:**
- Assume all tool calls will succeed
- Ignore 401/403 authentication errors
- Skip error messages from Composio

### 4. Session Management

**✅ Do:**
- Reuse sessions for the same user
- Set appropriate toolkits per use case
- Monitor session lifecycle
- Clean up unused sessions

**❌ Don't:**
- Create a new session for every tool call
- Mix users in the same session
- Leave sessions running indefinitely

### 5. Triggers & Webhooks

**✅ Do:**
- Always verify webhook signatures
- Use HTTPS endpoints in production
- Implement idempotency for webhook handlers
- Set reasonable timestamp tolerance (5 min)
- Monitor webhook delivery success

**❌ Don't:**
- Expose webhook endpoints without authentication
- Process duplicate events without checking
- Use WebSockets in production (use webhooks)

### 6. Performance Optimization

**✅ Do:**
- Batch similar operations with COMPOSIO_MULTI_EXECUTE_TOOL
- Use COMPOSIO_REMOTE_WORKBENCH for bulk processing
- Cache frequently used tool schemas
- Minimize tool calls through smart planning

**❌ Don't:**
- Make sequential calls when parallel execution works
- Load unnecessary toolkits
- Overuse COMPOSIO_SEARCH_TOOLS

### 7. Security

**✅ Do:**
- Store API keys in environment variables
- Use scoped authentication (request minimum permissions)
- Rotate credentials regularly
- Implement rate limiting
- Validate all user inputs before tool execution

**❌ Don't:**
- Commit credentials to version control
- Grant admin-level access when not needed
- Trust webhook payloads without verification

### 8. MCP Integration

**✅ Do:**
- Use Tool Router for dynamic, exploratory tasks
- Implement proper error handling for MCP calls
- Monitor MCP connection health
- Document which MCP tools are available

**❌ Don't:**
- Assume MCP servers are always available
- Skip connection verification
- Use experimental features in production without testing

### 9. Development Workflow

**✅ Do:**
- Test with ngrok or webhook.site locally
- Use the Composio playground for prototyping
- Check trigger logs in the dashboard
- Read toolkit-specific documentation

**❌ Don't:**
- Deploy to production without testing webhooks
- Skip authentication testing
- Ignore rate limits during development

### 10. Monitoring & Debugging

**✅ Do:**
- Track tool execution success/failure rates
- Monitor webhook delivery
- Log all tool calls for audit trails
- Use Composio dashboard for debugging

**❌ Don't:**
- Deploy without observability
- Ignore failed tool executions
- Skip logging in production

---

## Quick Reference

### Installation

**Python:**
```bash
pip install composio-core
# Framework-specific
pip install composio-openai
pip install composio-langchain
```

**TypeScript:**
```bash
npm install @composio/core
# Framework-specific
npm install @composio/openai-agents
```

### Environment Variables

```bash
COMPOSIO_API_KEY=your_api_key_here
COMPOSIO_WEBHOOK_SECRET=your_webhook_secret
```

### Key URLs

- **Dashboard**: https://platform.composio.dev
- **Documentation**: https://docs.composio.dev
- **API Reference**: https://docs.composio.dev/reference
- **Toolkits**: https://docs.composio.dev/toolkits

### Common Commands

```bash
# Install Composio CLI
curl -fsSL https://composio.dev/install | bash

# Add Rube MCP to Claude Desktop
npx @composiohq/cli add-mcp rube

# List available toolkits
composio list toolkits

# Test a tool
composio test GITHUB_CREATE_ISSUE
```

---

## Troubleshooting

### Tool Execution Failures

**401/403 Errors:**
- Check connection status
- Verify scopes are sufficient
- Ensure account has required permissions
- Check if account requires admin/paid tier

**Missing Tools:**
- Verify toolkit is enabled in session
- Check spelling of tool names (case-sensitive)
- Ensure connected account is active

### Authentication Issues

**OAuth Not Working:**
- Verify callback URL is correct
- Check client_id/client_secret
- Ensure auth config is enabled
- Test with Composio-managed auth first

**Tokens Expiring:**
- Composio auto-refreshes, but check if refresh token is valid
- Some services require manual re-authentication

### Webhook Problems

**Not Receiving Events:**
- Verify webhook URL is publicly accessible
- Check firewall/security groups
- Ensure endpoint accepts POST requests
- Verify trigger is active and enabled

**Signature Verification Failing:**
- Check webhook secret matches
- Verify header names (webhook-signature, webhook-timestamp)
- Ensure payload is raw body, not parsed JSON

---

## Conclusion

Composio provides a comprehensive platform for building production-ready AI agents that interact with the real world. By handling authentication, tool discovery, execution infrastructure, and event-driven workflows, it lets you focus on building agent logic rather than integration plumbing.

**Key Takeaways:**

1. **Tools & Toolkits**: 1000+ pre-built integrations with dynamic discovery
2. **Tool Router**: Unified interface for multi-app workflows
3. **MCP**: Standardized protocol for AI-tool integration
4. **Sessions**: Simplified abstraction for agent building
5. **Authentication**: Managed OAuth, API keys, and credentials
6. **Triggers**: Event-driven agents that react to external events

**Next Steps:**

1. Sign up at https://composio.dev
2. Get your API key
3. Follow the quickstart guide
4. Build your first agent
5. Join the Discord community for support

---

*Last Updated: March 2025*  
*Composio Version: Latest*  
*Documentation: https://docs.composio.dev*