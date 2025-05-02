# MarketSage Host Agent

The Host Agent is the core coordinator of the MarketSage platform, responsible for:

- Parsing natural language requests from users
- Routing requests to appropriate remote agents
- Managing communication between remote agents
- Handling task lifecycle and monitoring

## Features

- A2A Protocol implementation for agent communication
- Support for streaming responses
- Push notification capabilities
- Task state management and monitoring

## Installation

```bash
# Install from GitHub Packages
pip install marketsage-host-agent

# Or install from source
poetry install
```

## Usage

### Running the Host Agent

```bash
# Using the CLI
host-agent

# Or with custom port
HOST_AGENT_PORT=10001 host-agent

# Development mode
ENVIRONMENT=development host-agent
```

### Using the Host Agent in Code

```python
from app.agent.host.multiagent.host_agent import HostAgent

# Initialize host agent with remote agent addresses
host_agent = HostAgent(
    remote_agent_addresses=["http://localhost:8001", "http://localhost:8002"],
    task_callback=my_callback_function
)

# Create agent instance
agent = host_agent.create_agent()

# Process a request
response = agent.handle_request("Analyze market data for TSLA")
```

## Configuration

The Host Agent uses environment variables for configuration:

- `HOST_AGENT_PORT`: Port for the API server (default: 10000)
- `ENVIRONMENT`: Set to "development" for debug mode
- `LOG_LEVEL`: Logging level (default: INFO)

## Development

```bash
# Install development dependencies
poetry install --with dev

# Run tests
pytest

# Format code
black app/
isort app/
``` 