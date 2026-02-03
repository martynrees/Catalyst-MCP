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


class ComplianceDetail(BaseModel):
    """Compliance detail for a network device."""
    deviceUuid: str = Field(description="Device UUID")
    displayName: str | None = Field(default=None, description="Device display name")
    complianceType: str = Field(description="Type of compliance check (EOX, IMAGE, PSIRT, etc.)")
    status: str = Field(description="Compliance status (COMPLIANT, NON_COMPLIANT, etc.)")
    category: str | None = Field(default=None, description="Compliance category")
    lastSyncTime: int | None = Field(default=None, description="Last sync timestamp (epoch ms)")
    lastUpdateTime: int | None = Field(default=None, description="Last update timestamp (epoch ms)")
    state: str | None = Field(default=None, description="Current state")
    remediationSupported: bool | None = Field(default=None, description="Whether remediation is supported")


class ComplianceDetailResponse(BaseModel):
    """Response containing compliance details."""
    devices: list[ComplianceDetail] = Field(description="List of device compliance details")
    count: int = Field(description="Number of devices returned")


class ComplianceCountResponse(BaseModel):
    """Response containing compliance count."""
    count: int = Field(description="Number of devices matching criteria")
    compliance_type: str | None = Field(default=None, description="Compliance type filter applied")
    compliance_status: str | None = Field(default=None, description="Compliance status filter applied")


class EoXSummaryResponse(BaseModel):
    """Network-wide EoX summary."""
    hardware_count: int = Field(description="Number of devices with hardware EoX alerts")
    software_count: int = Field(description="Number of devices with software EoX alerts")
    module_count: int = Field(description="Number of devices with module EoX alerts")
    total_count: int = Field(description="Total number of devices with any EoX alerts")


class EoXDeviceSummary(BaseModel):
    """EoX summary for a device."""
    device_id: str = Field(description="Device UUID")
    alert_count: int = Field(description="Total number of EoX alerts for this device")
    hardware_count: int | None = Field(default=None, description="Number of hardware EoX alerts")
    software_count: int | None = Field(default=None, description="Number of software EoX alerts")
    module_count: int | None = Field(default=None, description="Number of module EoX alerts")
    scan_status: str | None = Field(default=None, description="Scan status")
    last_scan_time: int | None = Field(default=None, description="Last scan timestamp (epoch ms)")
    comments: list[str] | None = Field(default=None, description="Additional comments")


class EoXDevicesResponse(BaseModel):
    """Response containing EoX device summaries."""
    devices: list[EoXDeviceSummary] = Field(description="List of devices with EoX information")
    count: int = Field(description="Number of devices returned")


class EoXBulletin(BaseModel):
    """EoX bulletin details."""
    bulletinNumber: str | None = Field(default=None, description="Bulletin number")
    bulletinName: str | None = Field(default=None, description="Bulletin name/title")
    eoxType: str | None = Field(default=None, description="EoX type (HARDWARE, SOFTWARE, MODULE)")
    bulletinURL: str | None = Field(default=None, description="URL to bulletin details")
    endOfLifeDate: int | None = Field(default=None, description="End of life date (epoch ms)")
    endOfSaleDate: int | None = Field(default=None, description="End of sale date (epoch ms)")
    endOfSupportDate: int | None = Field(default=None, description="End of support date (epoch ms)")
    endOfSWMaintenanceDate: int | None = Field(default=None, description="End of software maintenance date (epoch ms)")
    endOfSecurityVulnerabilityDate: int | None = Field(default=None, description="End of security/vulnerability support date (epoch ms)")
    lastDateOfSupport: int | None = Field(default=None, description="Last date of support (epoch ms)")


class EoXDeviceDetailsResponse(BaseModel):
    """Response containing detailed EoX information for a device."""
    device_id: str = Field(description="Device UUID")
    alert_count: int = Field(description="Total number of EoX alerts")
    eox_details: list[EoXBulletin] = Field(description="List of EoX bulletins")
    scan_status: str | None = Field(default=None, description="Scan status")
    last_scan_time: int | None = Field(default=None, description="Last scan timestamp (epoch ms)")


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


@mcp.tool()
async def get_compliance_detail(
    compliance_type: str | None = None,
    compliance_status: str | None = None,
    device_uuid: str | None = None,
    limit: int = 100,
    offset: int = 1,
    ctx: Context[ServerSession, AppContext] | None = None
) -> ComplianceDetailResponse:
    """Get detailed compliance status for network devices.

    Retrieves compliance information with flexible filtering by type, status,
    and specific devices. Supports multiple compliance types including EOX,
    IMAGE, PSIRT, RUNNING_CONFIG, and more.

    Args:
        compliance_type: Filter by compliance type(s), comma-separated.
                        Valid types: APPLICATION_VISIBILITY, EOX, FABRIC, IMAGE,
                        NETWORK_PROFILE, NETWORK_SETTINGS, PSIRT, RUNNING_CONFIG, WORKFLOW.
        compliance_status: Filter by compliance status(es), comma-separated.
                          Valid statuses: COMPLIANT, NON_COMPLIANT, IN_PROGRESS,
                          NOT_AVAILABLE, NOT_APPLICABLE, ERROR.
        device_uuid: Filter by device UUID(s), comma-separated.
        limit: Maximum number of devices to return (default: 100, max: 500).
        offset: Offset for pagination, 1-based indexing (default: 1).
        ctx: MCP context for logging and progress reporting (auto-injected).

    Returns:
        ComplianceDetailResponse containing compliance details for matching devices.

    Raises:
        RuntimeError: If the API request fails or data cannot be retrieved.
    """
    try:
        if ctx:
            await ctx.info("Fetching compliance details")
            await ctx.report_progress(0.0, 1.0, "Starting compliance query")
            client = ctx.request_context.lifespan_context.client
        else:
            client = CatalystCenterClient()

        params: dict[str, Any] = {
            "limit": min(limit, 500),
            "offset": offset
        }

        if compliance_type:
            params["complianceType"] = compliance_type
        if compliance_status:
            params["complianceStatus"] = compliance_status
        if device_uuid:
            params["deviceUuid"] = device_uuid

        if ctx:
            await ctx.report_progress(0.3, 1.0, "Querying Catalyst Center API")

        response = await client.get("/dna/intent/api/v1/compliance/detail", params=params)

        if ctx:
            await ctx.report_progress(0.7, 1.0, "Processing compliance data")

        compliance_data = response.get("response", [])

        # Convert to Pydantic models
        devices = [
            ComplianceDetail(
                deviceUuid=item.get("deviceUuid", ""),
                displayName=item.get("displayName"),
                complianceType=item.get("complianceType", ""),
                status=item.get("status", ""),
                category=item.get("category"),
                lastSyncTime=item.get("lastSyncTime"),
                lastUpdateTime=item.get("lastUpdateTime"),
                state=item.get("state"),
                remediationSupported=item.get("remediationSupported")
            )
            for item in compliance_data
        ]

        if ctx:
            await ctx.report_progress(1.0, 1.0, f"Retrieved {len(devices)} compliance records")
            await ctx.info(f"Found {len(devices)} devices with compliance data")

        return ComplianceDetailResponse(
            devices=devices,
            count=len(devices)
        )
    except httpx.HTTPError as e:
        error_msg = f"Failed to fetch compliance details: {str(e)}"
        if ctx:
            await ctx.error(error_msg)
        raise RuntimeError(error_msg) from e
    except Exception as e:
        error_msg = f"Unexpected error fetching compliance details: {str(e)}"
        if ctx:
            await ctx.error(error_msg)
        raise RuntimeError(error_msg) from e


@mcp.tool()
async def get_compliance_count(
    compliance_type: str | None = None,
    compliance_status: str | None = None,
    ctx: Context[ServerSession, AppContext] | None = None
) -> ComplianceCountResponse:
    """Get aggregate count of devices matching compliance criteria.

    Returns the total number of devices that match the specified compliance
    type and/or status filters. Useful for quick compliance posture assessment.

    Args:
        compliance_type: Filter by compliance type(s), comma-separated.
                        Valid types: APPLICATION_VISIBILITY, EOX, FABRIC, IMAGE,
                        NETWORK_PROFILE, NETWORK_SETTINGS, PSIRT, RUNNING_CONFIG, WORKFLOW.
        compliance_status: Filter by compliance status(es), comma-separated.
                          Valid statuses: COMPLIANT, NON_COMPLIANT, IN_PROGRESS,
                          NOT_AVAILABLE, NOT_APPLICABLE, ERROR.
        ctx: MCP context for logging and progress reporting (auto-injected).

    Returns:
        ComplianceCountResponse containing count and applied filters.

    Raises:
        RuntimeError: If the API request fails or data cannot be retrieved.
    """
    try:
        if ctx:
            await ctx.info("Fetching compliance count")
            client = ctx.request_context.lifespan_context.client
        else:
            client = CatalystCenterClient()

        params: dict[str, Any] = {}

        if compliance_type:
            params["complianceType"] = compliance_type
        if compliance_status:
            params["complianceStatus"] = compliance_status

        response = await client.get("/dna/intent/api/v1/compliance/detail/count", params=params)

        count = response.get("response", 0)

        if ctx:
            await ctx.info(f"Found {count} devices matching compliance criteria")

        return ComplianceCountResponse(
            count=count,
            compliance_type=compliance_type,
            compliance_status=compliance_status
        )
    except httpx.HTTPError as e:
        error_msg = f"Failed to fetch compliance count: {str(e)}"
        if ctx:
            await ctx.error(error_msg)
        raise RuntimeError(error_msg) from e
    except Exception as e:
        error_msg = f"Unexpected error fetching compliance count: {str(e)}"
        if ctx:
            await ctx.error(error_msg)
        raise RuntimeError(error_msg) from e


@mcp.tool()
async def get_eox_summary(
    ctx: Context[ServerSession, AppContext] | None = None
) -> EoXSummaryResponse:
    """Get network-wide End-of-Life/End-of-Support summary.

    Retrieves aggregate counts of devices with EoX alerts by category
    (hardware, software, modules). Provides a high-level view of the
    network's lifecycle management status.

    Args:
        ctx: MCP context for logging and progress reporting (auto-injected).

    Returns:
        EoXSummaryResponse containing counts by EoX category.

    Raises:
        RuntimeError: If the API request fails or data cannot be retrieved.
    """
    try:
        if ctx:
            await ctx.info("Fetching EoX summary")
            client = ctx.request_context.lifespan_context.client
        else:
            client = CatalystCenterClient()

        response = await client.get("/dna/intent/api/v1/eox-status/summary")

        summary = response.get("response", {})

        hardware_count = summary.get("hardwareCount", 0)
        software_count = summary.get("softwareCount", 0)
        module_count = summary.get("moduleCount", 0)
        total_count = summary.get("totalCount", 0)

        if ctx:
            await ctx.info(f"EoX Summary - Total: {total_count} (HW: {hardware_count}, SW: {software_count}, Modules: {module_count})")

        return EoXSummaryResponse(
            hardware_count=hardware_count,
            software_count=software_count,
            module_count=module_count,
            total_count=total_count
        )
    except httpx.HTTPError as e:
        error_msg = f"Failed to fetch EoX summary: {str(e)}"
        if ctx:
            await ctx.error(error_msg)
        raise RuntimeError(error_msg) from e
    except Exception as e:
        error_msg = f"Unexpected error fetching EoX summary: {str(e)}"
        if ctx:
            await ctx.error(error_msg)
        raise RuntimeError(error_msg) from e


@mcp.tool()
async def get_eox_devices(
    limit: int = 100,
    offset: int = 1,
    ctx: Context[ServerSession, AppContext] | None = None
) -> EoXDevicesResponse:
    """Get EoX status for all devices in the network.

    Retrieves End-of-Life/End-of-Support status for all network devices,
    showing which devices have EoX alerts and summary counts by category.
    Supports pagination for large networks.

    Args:
        limit: Maximum number of devices to return (default: 100, max: 500).
        offset: Offset for pagination, 1-based indexing (default: 1).
        ctx: MCP context for logging and progress reporting (auto-injected).

    Returns:
        EoXDevicesResponse containing EoX information for devices.

    Raises:
        RuntimeError: If the API request fails or data cannot be retrieved.
    """
    try:
        if ctx:
            await ctx.info("Fetching EoX device status")
            await ctx.report_progress(0.0, 1.0, "Starting EoX device query")
            client = ctx.request_context.lifespan_context.client
        else:
            client = CatalystCenterClient()

        params: dict[str, Any] = {
            "limit": min(limit, 500),
            "offset": offset
        }

        if ctx:
            await ctx.report_progress(0.3, 1.0, "Querying Catalyst Center API")

        response = await client.get("/dna/intent/api/v1/eox-status/device", params=params)

        if ctx:
            await ctx.report_progress(0.7, 1.0, "Processing EoX device data")

        devices_data = response.get("response", [])

        # Convert to Pydantic models
        devices = []
        for item in devices_data:
            # Parse summary array to extract counts by type
            summary_list = item.get("summary", [])
            hardware_count = None
            software_count = None
            module_count = None
            
            if isinstance(summary_list, list):
                for summary_item in summary_list:
                    eox_type = summary_item.get("eoxType", "")
                    count = summary_item.get("count", 0)
                    if eox_type == "HARDWARE":
                        hardware_count = count
                    elif eox_type == "SOFTWARE":
                        software_count = count
                    elif eox_type == "MODULE":
                        module_count = count
            
            devices.append(
                EoXDeviceSummary(
                    device_id=item.get("deviceId", ""),
                    alert_count=item.get("alertCount", 0),
                    hardware_count=hardware_count,
                    software_count=software_count,
                    module_count=module_count,
                    scan_status=item.get("scanStatus"),
                    last_scan_time=item.get("lastScanTime"),
                    comments=item.get("comments")
                )
            )

        if ctx:
            await ctx.report_progress(1.0, 1.0, f"Retrieved {len(devices)} devices with EoX data")
            await ctx.info(f"Found {len(devices)} devices with EoX information")

        return EoXDevicesResponse(
            devices=devices,
            count=len(devices)
        )
    except httpx.HTTPError as e:
        error_msg = f"Failed to fetch EoX devices: {str(e)}"
        if ctx:
            await ctx.error(error_msg)
        raise RuntimeError(error_msg) from e
    except Exception as e:
        error_msg = f"Unexpected error fetching EoX devices: {str(e)}"
        if ctx:
            await ctx.error(error_msg)
        raise RuntimeError(error_msg) from e


@mcp.tool()
async def get_eox_device_details(
    device_id: str,
    ctx: Context[ServerSession, AppContext] | None = None
) -> EoXDeviceDetailsResponse:
    """Get detailed End-of-Life/End-of-Support information for a specific device.

    Retrieves comprehensive EoX bulletin details for a device, including
    end-of-sale dates, end-of-support dates, and URLs to Cisco EoX bulletins.
    Essential for lifecycle planning and remediation.

    Args:
        device_id: Device UUID (required).
        ctx: MCP context for logging and progress reporting (auto-injected).

    Returns:
        EoXDeviceDetailsResponse containing detailed EoX bulletins.

    Raises:
        RuntimeError: If the API request fails or data cannot be retrieved.
    """
    try:
        if ctx:
            await ctx.info(f"Fetching EoX details for device {device_id}")
            client = ctx.request_context.lifespan_context.client
        else:
            client = CatalystCenterClient()

        response = await client.get(f"/dna/intent/api/v1/eox-status/device/{device_id}")

        device_data = response.get("response", {})

        eox_details_data = device_data.get("eoxDetails", [])

        # Convert to Pydantic models
        eox_details = [
            EoXBulletin(
                bulletinNumber=item.get("bulletinNumber"),
                bulletinName=item.get("bulletinName"),
                eoxType=item.get("eoxType"),
                bulletinURL=item.get("bulletinURL"),
                endOfLifeDate=item.get("endOfLifeDate"),
                endOfSaleDate=item.get("endOfSaleDate"),
                endOfSupportDate=item.get("endOfSupportDate"),
                endOfSWMaintenanceDate=item.get("endOfSWMaintenanceDate"),
                endOfSecurityVulnerabilityDate=item.get("endOfSecurityVulnerabilityDate"),
                lastDateOfSupport=item.get("lastDateOfSupport")
            )
            for item in eox_details_data
        ]

        if ctx:
            await ctx.info(f"Retrieved {len(eox_details)} EoX bulletins for device {device_id}")

        return EoXDeviceDetailsResponse(
            device_id=device_data.get("deviceId", device_id),
            alert_count=device_data.get("alertCount", 0),
            eox_details=eox_details,
            scan_status=device_data.get("scanStatus"),
            last_scan_time=device_data.get("lastScanTime")
        )
    except httpx.HTTPError as e:
        error_msg = f"Failed to fetch EoX details for device {device_id}: {str(e)}"
        if ctx:
            await ctx.error(error_msg)
        raise RuntimeError(error_msg) from e
    except Exception as e:
        error_msg = f"Unexpected error fetching EoX details: {str(e)}"
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
