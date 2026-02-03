"""Cisco Catalyst Center MCP Server.

This server provides MCP tools for interacting with Cisco Catalyst Center.
"""
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any
import httpx
from pydantic import BaseModel, Field
from mcp.server.fastmcp import FastMCP, Context
from mcp.server.session import ServerSession

from .config import Config
from .client import CatalystCenterClient

# Validate configuration on startup
Config.validate()


# Pydantic models for structured output
class ClientCounts(BaseModel):
    """Client count information."""
    wired_count: int = Field(description="Number of wired clients connected to the network")
    wireless_count: int = Field(description="Number of wireless clients connected to the network")
    total_count: int = Field(description="Total number of all clients")
    timestamp: int | str = Field(description="Timestamp of data collection (epoch ms or 'current')")


class NetworkDevice(BaseModel):
    """Network device information."""
    hostname: str | None = Field(description="Device hostname")
    managementIpAddress: str | None = Field(description="Management IP address")
    family: str | None = Field(description="Device family (e.g., 'Switches and Hubs')")
    type: str | None = Field(description="Device type")
    softwareVersion: str | None = Field(description="Software version")
    reachabilityStatus: str | None = Field(description="Reachability status")
    serialNumber: str | None = Field(description="Serial number")
    id: str | None = Field(description="Device UUID")


class NetworkDevicesResponse(BaseModel):
    """Response containing list of network devices."""
    devices: list[NetworkDevice] = Field(description="List of network devices")
    count: int = Field(description="Number of devices returned")


class CategoryHealth(BaseModel):
    """Health information for a device category."""
    healthScore: int = Field(description="Overall health score (-1 means not applicable)")
    totalCount: int = Field(description="Total number of devices in category")
    goodCount: int = Field(description="Number of devices with good health")
    badCount: int = Field(description="Number of devices with bad health")
    fairCount: int = Field(description="Number of devices with fair health")
    unmonitoredCount: int = Field(description="Number of unmonitored devices")


class NetworkHealthResponse(BaseModel):
    """Network health by device category."""
    categories: dict[str, CategoryHealth] = Field(description="Health data by device category")
    timestamp: int | str = Field(description="Timestamp of health data")


class Issue(BaseModel):
    """Network issue information."""
    issueId: str | None = Field(description="Unique issue identifier")
    name: str | None = Field(description="Issue name/title")
    priority: str | None = Field(description="Issue priority (P1, P2, P3, P4)")
    status: str | None = Field(description="Issue status (ACTIVE, IGNORED, RESOLVED)")
    category: str | None = Field(description="Issue category")
    issueOccurenceCount: int | None = Field(description="Number of times issue occurred")
    lastOccurenceTime: int | None = Field(description="Last occurrence timestamp (epoch ms)")


class IssuesResponse(BaseModel):
    """Response containing list of issues."""
    issues: list[Issue] = Field(description="List of network issues")
    count: int = Field(description="Number of issues returned")


class SiteHealth(BaseModel):
    """Site health information."""
    siteName: str | None = Field(description="Site name")
    siteType: str | None = Field(description="Site type (AREA, BUILDING)")
    healthyNetworkDevicePercentage: int | None = Field(description="Percentage of healthy network devices")
    healthyClientsPercentage: int | None = Field(description="Percentage of healthy clients")
    numberOfClients: int | None = Field(description="Number of clients at site")
    numberOfNetworkDevice: int | None = Field(description="Number of network devices at site")
    networkHealthAverage: int | None = Field(description="Average network health score")
    clientHealthAverage: int | None = Field(description="Average client health score")


class SiteHealthResponse(BaseModel):
    """Response containing site health information."""
    sites: list[SiteHealth] = Field(description="List of site health data")
    count: int = Field(description="Number of sites returned")


# Application context for lifespan management
@dataclass
class AppContext:
    """Application context with shared resources."""
    client: CatalystCenterClient


@asynccontextmanager
async def app_lifespan(server: FastMCP):
    """Manage application lifecycle and shared resources.

    Initializes the Catalyst Center API client on startup.
    """
    client = CatalystCenterClient()
    try:
        yield AppContext(client=client)
    finally:
        # Cleanup if needed
        pass


# Initialize FastMCP server with lifespan management
mcp = FastMCP("Catalyst Center", lifespan=app_lifespan)


@mcp.tool()
async def get_client_counts(
    timestamp: int | None = None,
    ctx: Context[ServerSession, AppContext] | None = None
) -> ClientCounts:
    """Get count of wired and wireless clients connected to the network.

    Retrieves the current count of wired and wireless clients from Catalyst Center.
    This provides a high-level view of network client connectivity.

    Args:
        timestamp: Optional epoch time in milliseconds when client health data is required.
                  If not provided, returns current data.
        ctx: MCP context for logging and progress reporting (auto-injected).

    Returns:
        ClientCounts object containing wired, wireless, and total client counts.

    Raises:
        RuntimeError: If the API request fails or data cannot be retrieved.
    """
    try:
        if ctx:
            await ctx.info("Fetching client counts from Catalyst Center")
            client = ctx.request_context.lifespan_context.client
        else:
            # Fallback for testing without context
            client = CatalystCenterClient()

        params: dict[str, Any] = {}
        if timestamp is not None:
            params["timestamp"] = timestamp

        response = await client.get("/dna/intent/api/v1/client-health", params=params)

        # Parse response to extract client counts by type
        wired_count = 0
        wireless_count = 0

        if "response" in response and len(response["response"]) > 0:
            for site_data in response["response"]:
                if "scoreDetail" in site_data:
                    for score in site_data["scoreDetail"]:
                        category = score.get("scoreCategory", {})
                        if category.get("value") == "WIRED":
                            wired_count += score.get("clientCount", 0)
                        elif category.get("value") == "WIRELESS":
                            wireless_count += score.get("clientCount", 0)

        total_count = wired_count + wireless_count

        if ctx:
            await ctx.info(f"Retrieved {wired_count} wired, {wireless_count} wireless ({total_count} total) clients")

        return ClientCounts(
            wired_count=wired_count,
            wireless_count=wireless_count,
            total_count=total_count,
            timestamp=timestamp or "current"
        )
    except httpx.HTTPError as e:
        error_msg = f"Failed to fetch client counts: {str(e)}"
        if ctx:
            await ctx.error(error_msg)
        raise RuntimeError(error_msg) from e
    except Exception as e:
        error_msg = f"Unexpected error fetching client counts: {str(e)}"
        if ctx:
            await ctx.error(error_msg)
        raise RuntimeError(error_msg) from e


@mcp.tool()
async def get_network_devices(
    hostname: str | None = None,
    management_ip: str | None = None,
    device_family: str | None = None,
    device_type: str | None = None,
    limit: int = 25,
    ctx: Context[ServerSession, AppContext] | None = None
) -> NetworkDevicesResponse:
    """Get list of network devices based on filter criteria.

    Query the network device inventory with flexible filtering options.
    Supports wildcard searches using .* pattern.

    Args:
        hostname: Filter by device hostname (supports .* wildcard).
        management_ip: Filter by management IP address (supports .* wildcard).
        device_family: Filter by device family (e.g., "Switches and Hubs", "Routers").
        device_type: Filter by device type.
        limit: Maximum number of devices to return (default: 25, max: 500).
        ctx: MCP context for logging and progress reporting (auto-injected).

    Returns:
        NetworkDevicesResponse containing list of matching devices.

    Raises:
        RuntimeError: If the API request fails or data cannot be retrieved.
    """
    try:
        if ctx:
            await ctx.info("Fetching network devices")
            await ctx.report_progress(0.0, 1.0, "Starting device query")
            client = ctx.request_context.lifespan_context.client
        else:
            client = CatalystCenterClient()

        params: dict[str, Any] = {"limit": min(limit, 500)}

        if hostname:
            params["hostname"] = hostname
        if management_ip:
            params["managementIpAddress"] = management_ip
        if device_family:
            params["family"] = device_family
        if device_type:
            params["type"] = device_type

        if ctx:
            await ctx.report_progress(0.3, 1.0, "Querying Catalyst Center API")

        response = await client.get("/dna/intent/api/v1/network-device", params=params)

        if ctx:
            await ctx.report_progress(0.7, 1.0, "Processing device data")

        devices = response.get("response", [])

        # Convert to Pydantic models
        network_devices = [
            NetworkDevice(
                hostname=device.get("hostname"),
                managementIpAddress=device.get("managementIpAddress"),
                family=device.get("family"),
                type=device.get("type"),
                softwareVersion=device.get("softwareVersion"),
                reachabilityStatus=device.get("reachabilityStatus"),
                serialNumber=device.get("serialNumber"),
                id=device.get("id")
            )
            for device in devices
        ]

        if ctx:
            await ctx.report_progress(1.0, 1.0, f"Retrieved {len(network_devices)} devices")
            await ctx.info(f"Found {len(network_devices)} matching devices")

        return NetworkDevicesResponse(
            devices=network_devices,
            count=len(network_devices)
        )
    except httpx.HTTPError as e:
        error_msg = f"Failed to fetch network devices: {str(e)}"
        if ctx:
            await ctx.error(error_msg)
        raise RuntimeError(error_msg) from e
    except Exception as e:
        error_msg = f"Unexpected error fetching network devices: {str(e)}"
        if ctx:
            await ctx.error(error_msg)
        raise RuntimeError(error_msg) from e


@mcp.tool()
async def get_network_health(
    timestamp: int | None = None,
    ctx: Context[ServerSession, AppContext] | None = None
) -> NetworkHealthResponse:
    """Get overall network health by device category.

    Retrieves health scores and statistics for each device category
    (Access, Distribution, Core, Router, Wireless).

    Args:
        timestamp: Optional UTC timestamp in milliseconds when health data is required.
                  If not provided, returns current data.
        ctx: MCP context for logging and progress reporting (auto-injected).

    Returns:
        NetworkHealthResponse containing health data by device category.

    Raises:
        RuntimeError: If the API request fails or data cannot be retrieved.
    """
    try:
        if ctx:
            await ctx.info("Fetching network health data")
            client = ctx.request_context.lifespan_context.client
        else:
            client = CatalystCenterClient()

        params: dict[str, Any] = {}
        if timestamp is not None:
            params["timestamp"] = timestamp

        response = await client.get("/dna/intent/api/v1/network-health", params=params)

        categories: dict[str, CategoryHealth] = {}

        if "response" in response and len(response["response"]) > 0:
            for category_data in response["response"]:
                category = category_data.get("category", "Unknown")
                categories[category] = CategoryHealth(
                    healthScore=category_data.get("healthScore", -1),
                    totalCount=category_data.get("totalCount", 0),
                    goodCount=category_data.get("goodCount", 0),
                    badCount=category_data.get("badCount", 0),
                    fairCount=category_data.get("fairCount", 0),
                    unmonitoredCount=category_data.get("unmonitoredCount", 0)
                )

        if ctx:
            await ctx.info(f"Retrieved health data for {len(categories)} device categories")

        return NetworkHealthResponse(
            categories=categories,
            timestamp=timestamp or "current"
        )
    except httpx.HTTPError as e:
        error_msg = f"Failed to fetch network health: {str(e)}"
        if ctx:
            await ctx.error(error_msg)
        raise RuntimeError(error_msg) from e
    except Exception as e:
        error_msg = f"Unexpected error fetching network health: {str(e)}"
        if ctx:
            await ctx.error(error_msg)
        raise RuntimeError(error_msg) from e


@mcp.tool()
async def get_issues(
    priority: str | None = None,
    issue_status: str | None = None,
    site_id: str | None = None,
    device_id: str | None = None,
    mac_address: str | None = None,
    ai_driven: str | None = None,
    ctx: Context[ServerSession, AppContext] | None = None
) -> IssuesResponse:
    """Get list of network issues based on filter criteria.

    Retrieves network issues with flexible filtering by priority, status,
    location, and other criteria.

    Args:
        priority: Filter by priority: P1, P2, P3, or P4 (case insensitive).
        issue_status: Filter by status: ACTIVE, IGNORED, or RESOLVED (case insensitive).
        site_id: Filter by site UUID.
        device_id: Filter by device UUID.
        mac_address: Filter by client MAC address (format: xx:xx:xx:xx:xx:xx).
        ai_driven: Filter by AI-driven issues: YES or NO (case insensitive).
        ctx: MCP context for logging and progress reporting (auto-injected).

    Returns:
        IssuesResponse containing list of matching issues.

    Raises:
        RuntimeError: If the API request fails or data cannot be retrieved.
    """
    try:
        if ctx:
            await ctx.info("Fetching network issues")
            client = ctx.request_context.lifespan_context.client
        else:
            client = CatalystCenterClient()

        params: dict[str, Any] = {}

        if priority:
            params["priority"] = priority
        if issue_status:
            params["issueStatus"] = issue_status
        if site_id:
            params["siteId"] = site_id
        if device_id:
            params["deviceId"] = device_id
        if mac_address:
            params["macAddress"] = mac_address
        if ai_driven:
            params["aiDriven"] = ai_driven

        response = await client.get("/dna/intent/api/v1/issues", params=params)

        issues_data = response.get("response", [])

        # Convert to Pydantic models
        issues = [
            Issue(
                issueId=issue.get("issueId"),
                name=issue.get("name"),
                priority=issue.get("priority"),
                status=issue.get("status"),
                category=issue.get("category"),
                issueOccurenceCount=issue.get("issueOccurenceCount"),
                lastOccurenceTime=issue.get("lastOccurenceTime")
            )
            for issue in issues_data
        ]

        if ctx:
            await ctx.info(f"Found {len(issues)} matching issues")

        return IssuesResponse(
            issues=issues,
            count=len(issues)
        )
    except httpx.HTTPError as e:
        error_msg = f"Failed to fetch issues: {str(e)}"
        if ctx:
            await ctx.error(error_msg)
        raise RuntimeError(error_msg) from e
    except Exception as e:
        error_msg = f"Unexpected error fetching issues: {str(e)}"
        if ctx:
            await ctx.error(error_msg)
        raise RuntimeError(error_msg) from e


@mcp.tool()
async def get_site_health(
    site_type: str | None = None,
    limit: int = 25,
    offset: int = 1,
    ctx: Context[ServerSession, AppContext] | None = None
) -> SiteHealthResponse:
    """Get health information for all sites.

    Retrieves health metrics for sites in the network hierarchy,
    with optional filtering by site type.

    Args:
        site_type: Filter by site type: AREA or BUILDING (case insensitive).
        limit: Maximum number of sites to return (default: 25, max: 50).
        offset: Offset for pagination, 1-based indexing (default: 1).
        ctx: MCP context for logging and progress reporting (auto-injected).

    Returns:
        SiteHealthResponse containing health data for matching sites.

    Raises:
        RuntimeError: If the API request fails or data cannot be retrieved.
    """
    try:
        if ctx:
            await ctx.info("Fetching site health data")
            client = ctx.request_context.lifespan_context.client
        else:
            client = CatalystCenterClient()

        params: dict[str, Any] = {
            "limit": min(limit, 50),
            "offset": offset
        }

        if site_type:
            params["siteType"] = site_type

        response = await client.get("/dna/intent/api/v1/site-health", params=params)

        sites_data = response.get("response", [])

        # Convert to Pydantic models
        sites = [
            SiteHealth(
                siteName=site.get("siteName"),
                siteType=site.get("siteType"),
                healthyNetworkDevicePercentage=site.get("healthyNetworkDevicePercentage"),
                healthyClientsPercentage=site.get("healthyClientsPercentage"),
                numberOfClients=site.get("numberOfClients"),
                numberOfNetworkDevice=site.get("numberOfNetworkDevice"),
                networkHealthAverage=site.get("networkHealthAverage"),
                clientHealthAverage=site.get("clientHealthAverage")
            )
            for site in sites_data
        ]

        if ctx:
            await ctx.info(f"Retrieved health data for {len(sites)} sites")

        return SiteHealthResponse(
            sites=sites,
            count=len(sites)
        )
    except httpx.HTTPError as e:
        error_msg = f"Failed to fetch site health: {str(e)}"
        if ctx:
            await ctx.error(error_msg)
        raise RuntimeError(error_msg) from e
    except Exception as e:
        error_msg = f"Unexpected error fetching site health: {str(e)}"
        if ctx:
            await ctx.error(error_msg)
        raise RuntimeError(error_msg) from e


@mcp.tool()
async def get_client_detail(
    mac_address: str,
    timestamp: int | None = None,
    ctx: Context[ServerSession, AppContext] | None = None
) -> dict[str, Any]:
    """Get detailed information about a specific client by MAC address.

    Retrieves comprehensive details about a client including connection status,
    health scores, device information, and connectivity details.

    Args:
        mac_address: Client MAC address (required, format: xx:xx:xx:xx:xx:xx).
        timestamp: Optional epoch time in milliseconds when client data is required.
                  If not provided, returns current data.
        ctx: MCP context for logging and progress reporting (auto-injected).

    Returns:
        Dictionary containing detailed client information from Catalyst Center API.

    Raises:
        RuntimeError: If the API request fails or data cannot be retrieved.
    """
    try:
        if ctx:
            await ctx.info(f"Fetching details for client {mac_address}")
            client = ctx.request_context.lifespan_context.client
        else:
            client = CatalystCenterClient()

        params: dict[str, Any] = {"macAddress": mac_address}

        if timestamp is not None:
            params["timestamp"] = timestamp

        response = await client.get("/dna/intent/api/v1/client-detail", params=params)

        if ctx:
            await ctx.info(f"Retrieved detailed information for client {mac_address}")

        return response
    except httpx.HTTPError as e:
        error_msg = f"Failed to fetch client detail for {mac_address}: {str(e)}"
        if ctx:
            await ctx.error(error_msg)
        raise RuntimeError(error_msg) from e
    except Exception as e:
        error_msg = f"Unexpected error fetching client detail: {str(e)}"
        if ctx:
            await ctx.error(error_msg)
        raise RuntimeError(error_msg) from e


if __name__ == "__main__":
    import sys

    # Support both stdio (default) and HTTP transports
    if "--http" in sys.argv:
        mcp.run(transport="sse")
    else:
        mcp.run()  # stdio by default
