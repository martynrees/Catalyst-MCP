# Cisco Catalyst Center MCP Server

A Model Context Protocol (MCP) server for Cisco Catalyst Center, providing network management capabilities through structured tools.

## Features

This MCP server provides focused, high-value tools for Cisco Catalyst Center:

### Network Monitoring
- **`get_client_counts`** - Get counts of wired and wireless clients connected to the network
- **`get_network_devices`** - Query network device inventory with flexible filtering
- **`get_network_health`** - Get overall network health by device category
- **`get_site_health`** - Get health information for sites (areas and buildings)
- **`get_client_detail`** - Get detailed information about a specific client by MAC address

### Issues & Assurance
- **`get_issues`** - Retrieve network issues with filtering by priority, status, and more

### Compliance & Lifecycle Management
- **`get_compliance_detail`** - Get detailed compliance status for devices (EOX, IMAGE, PSIRT, etc.)
- **`get_compliance_count`** - Get aggregate count of devices by compliance criteria
- **`get_eox_summary`** - Get network-wide End-of-Life/End-of-Support summary
- **`get_eox_devices`** - Get EoX status for all devices in the network
- **`get_eox_device_details`** - Get detailed EoX bulletins for a specific device

## Prerequisites

- Python 3.10 or higher
- Cisco Catalyst Center instance (v2.3.7.9 or compatible)
- Valid Catalyst Center credentials with API access

## Installation

### Using uv (Recommended)

1. Install uv if you haven't already:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. Clone this repository or download the source code

3. Initialize and install dependencies:
```bash
cd catalyst-center-mcp
uv sync
```

4. Create a `.env` file from the example:
```bash
cp .env.example .env
```

5. Edit `.env` with your Catalyst Center credentials:
```env
CATALYST_CENTER_URL=https://your-catalyst-center.example.com
CATALYST_CENTER_USERNAME=your_username
CATALYST_CENTER_PASSWORD=your_password
CATALYST_CENTER_VERIFY_SSL=true
```

## Usage

### Running the MCP Server

Start the server in development mode:

```bash
uv run mcp dev src/server.py
```

Or run directly:

```bash
uv run src/server.py
```

The server will start and be available for MCP clients to connect to via stdio transport.

### Using with Claude Desktop

Add this server to your Claude Desktop configuration file:

**Option 1: Using environment variables directly**

```json
{
  "mcpServers": {
    "catalyst-center": {
      "command": "uv",
      "args": ["run", "src/server.py"],
      "cwd": "/path/to/catalyst-center-mcp",
      "env": {
        "CATALYST_CENTER_URL": "https://your-catalyst-center.example.com",
        "CATALYST_CENTER_USERNAME": "your_username",
        "CATALYST_CENTER_PASSWORD": "your_password",
        "CATALYST_CENTER_VERIFY_SSL": "true"
      }
    }
  }
}
```

**Option 2: Using .env file (recommended)**

Create a `.env` file in the project directory with your credentials, then:

```json
{
  "mcpServers": {
    "catalyst-center": {
      "command": "uv",
      "args": ["run", "src/server.py"],
      "cwd": "/path/to/catalyst-center-mcp"
    }
  }
}
```

## Tool Examples

### Get Client Counts

```python
# Get current wired and wireless client counts
result = await get_client_counts()
# Returns: {"wired_count": 150, "wireless_count": 75, "total_count": 225, "timestamp": "current"}
```

### Get Network Devices

```python
# Get all devices
devices = await get_network_devices()

# Filter by hostname
devices = await get_network_devices(hostname="switch.*")

# Filter by device family
devices = await get_network_devices(device_family="Switches and Hubs", limit=50)
```

### Get Network Health

```python
# Get current network health by device category
health = await get_network_health()
# Returns health scores for Access, Distribution, Core, Router, and Wireless devices
```

### Get Issues

```python
# Get all active P1 issues
issues = await get_issues(priority="P1", issue_status="ACTIVE")

# Get issues for a specific site
issues = await get_issues(site_id="site-uuid-here")

# Get AI-driven issues
issues = await get_issues(ai_driven="YES")
```

### Get Site Health

```python
# Get health for all sites
sites = await get_site_health()

# Get only building sites
sites = await get_site_health(site_type="BUILDING")
```

### Get Client Detail

```python
# Get detailed info for a specific client
client = await get_client_detail(mac_address="00:11:22:33:44:55")
```

### Get Compliance Detail

```python
# Get all non-compliant devices
compliance = await get_compliance_detail(compliance_status="NON_COMPLIANT")

# Get EOX compliance status for specific devices
compliance = await get_compliance_detail(
    compliance_type="EOX",
    device_uuid="device-uuid-1,device-uuid-2"
)

# Get PSIRT (security advisory) compliance
compliance = await get_compliance_detail(compliance_type="PSIRT", limit=100)
```

### Get Compliance Count

```python
# Count all non-compliant devices
count = await get_compliance_count(compliance_status="NON_COMPLIANT")

# Count devices with image compliance issues
count = await get_compliance_count(
    compliance_type="IMAGE",
    compliance_status="NON_COMPLIANT"
)
```

### Get EoX Summary

```python
# Get network-wide EoX summary
summary = await get_eox_summary()
# Returns: {"hardware_count": 15, "software_count": 8, "module_count": 3, "total_count": 26}
```

### Get EoX Devices

```python
# Get all devices with EoX alerts
devices = await get_eox_devices()

# Get with pagination for large networks
devices = await get_eox_devices(limit=50, offset=1)
```

### Get EoX Device Details

```python
# Get detailed EoX bulletins for a specific device
details = await get_eox_device_details(device_id="device-uuid-here")
# Returns detailed bulletin info with end-of-sale/support dates and URLs
```

## Project Structure

```
catalyst-center-mcp/
├── src/
│   ├── __init__.py
│   ├── server.py       # FastMCP server with tool definitions
│   ├── client.py       # HTTP client for Catalyst Center API
│   ├── auth.py         # Authentication handler
│   └── config.py       # Configuration management
├── requirements.txt    # Python dependencies
├── .env.example       # Environment variable template
├── .gitignore         # Git ignore rules
└── README.md          # This file
```

## Authentication

The server uses Catalyst Center's authentication API:
1. Credentials are sent via Basic Auth to `/dna/system/api/v1/auth/token`
2. A token is returned, valid for 1 hour
3. The token is cached and used in the `X-Auth-Token` header for all API calls
4. On 401 responses, the token is automatically refreshed

## Error Handling

- **Configuration errors**: The server validates required environment variables on startup
- **Authentication failures**: Returns clear error messages for invalid credentials
- **Network errors**: HTTP errors are propagated with meaningful messages
- **Token expiration**: Automatically re-authenticates on 401 responses

## Development

### Adding New Tools

To add a new tool:

1. Define a new function in `src/server.py` decorated with `@mcp.tool()`
2. Add proper type hints and docstring
3. Use the `client` instance to make API calls
4. Return structured data as a dictionary

Example:
```python
@mcp.tool()
async def get_something(param: str) -> dict[str, Any]:
    """
    Description of what this tool does.

    Args:
        param: Description of parameter

    Returns:
        Description of return value
    """
    response = await client.get("/dna/intent/api/v1/endpoint", params={"param": param})
    return response
```

## License

This project is provided as-is for use with Cisco Catalyst Center.

## API Reference

This server uses Cisco Catalyst Center Intent API v2.3.7.9. For full API documentation, refer to the Catalyst Center API documentation.

## Troubleshooting

### SSL Certificate Errors

If you encounter SSL certificate errors, you can disable SSL verification (not recommended for production):
```env
CATALYST_CENTER_VERIFY_SSL=false
```

### Connection Timeouts

The default timeout is 30 seconds. For slower networks, you may need to adjust the timeout in `src/client.py`.

### Authentication Issues

- Verify your credentials are correct
- Ensure the user has API access permissions in Catalyst Center
- Check that the Catalyst Center URL is accessible from your machine
