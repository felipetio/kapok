"""
Kapok MCP Tools

Exposes the Kapok API for indigenous land data through MCP tools.
Uses httpx to call the Django REST API endpoints.
"""

import json
import logging
from typing import Literal

from django.conf import settings

import httpx
from mcp_server import mcp_server

logger = logging.getLogger("kapok.mcp")


async def get_client() -> httpx.AsyncClient:
    """Create an async HTTP client with proper headers and retry logic."""
    headers = {}
    api_token = getattr(settings, "MCP_API_TOKEN", "")
    if api_token:
        headers["Authorization"] = f"Bearer {api_token}"

    transport = httpx.AsyncHTTPTransport(retries=3)
    base_url = getattr(settings, "MCP_API_BASE_URL", "http://localhost:8000")

    return httpx.AsyncClient(
        base_url=base_url,
        headers=headers,
        timeout=30.0,
        transport=transport,
    )


def format_land_results(results: list[dict]) -> list[dict]:
    """Format land results for better readability."""
    formatted = []
    for land in results:
        formatted.append(
            {
                "id": land["id"],
                "name": land["name"],
                "category": land["category_display"],
                "location": land["location"],
                "biome": land["biome"]["name"] if land.get("biome") else None,
                "communities_count": land["communities_count"],
                "communities": [c["name"] for c in land.get("communities", [])],
            }
        )
    return formatted


@mcp_server.tool()
async def search_lands(
    name: str | None = None,
    category: Literal["DI", "PI", "RI", "TI"] | None = None,
    state: str | None = None,
    state_code: str | None = None,
    municipality: str | None = None,
    biome: str | None = None,
    community: str | None = None,
    search: str | None = None,
    page: int | None = None,
    ordering: str | None = None,
) -> str:
    """Search for indigenous lands in Brazil.

    Supports filtering by name, category, state, municipality, biome, and community.
    Returns paginated results with land details.

    Args:
        name: Filter by land name (partial match)
        category: Land category - DI (Dominial Indigena), PI (Parque Indigena), RI (Reserva Indigena), TI (Terra Indigena)
        state: Filter by Brazilian state name
        state_code: Filter by state code (e.g., 'AM', 'PA')
        municipality: Filter by municipality name
        biome: Filter by biome (e.g., 'Amazonia', 'Cerrado', 'Mata Atlantica')
        community: Filter by indigenous community name
        search: General search term across multiple fields
        page: Page number for pagination (default: 1)
        ordering: Field to order by (prefix with '-' for descending)
    """
    logger.info("Tool called: search_lands")

    params = {}
    if name is not None:
        params["name"] = name
    if category is not None:
        params["category"] = category
    if state is not None:
        params["state"] = state
    if state_code is not None:
        params["state_code"] = state_code
    if municipality is not None:
        params["municipality"] = municipality
    if biome is not None:
        params["biome"] = biome
    if community is not None:
        params["community"] = community
    if search is not None:
        params["search"] = search
    if page is not None:
        params["page"] = page
    if ordering is not None:
        params["ordering"] = ordering

    logger.debug(f"Searching lands with params: {params}")

    async with await get_client() as client:
        try:
            response = await client.get("/api/v1/lands/", params=params)
            response.raise_for_status()
            data = response.json()

            result = {
                "total_count": data.get("count", 0),
                "page_results": len(data.get("results", [])),
                "lands": format_land_results(data.get("results", [])),
                "next_page": data.get("next") is not None,
            }

            return json.dumps(result, indent=2, ensure_ascii=False)

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error {e.response.status_code}: {e.response.text}")
            return f"API Error {e.response.status_code}: {e.response.text}"
        except Exception as e:
            logger.error(f"Unexpected error: {type(e).__name__}: {e}")
            return f"Error: {e!s}"


@mcp_server.tool()
async def get_land_details(land_id: str) -> str:
    """Retrieve detailed information about a specific indigenous land by its UUID.

    Returns complete land data including biome, communities, location, and metadata.

    Args:
        land_id: UUID of the land to retrieve
    """
    logger.info(f"Tool called: get_land_details({land_id})")

    async with await get_client() as client:
        try:
            response = await client.get(f"/api/v1/lands/{land_id}/")
            response.raise_for_status()
            data = response.json()

            return json.dumps(data, indent=2, ensure_ascii=False)

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error {e.response.status_code}: {e.response.text}")
            return f"API Error {e.response.status_code}: {e.response.text}"
        except Exception as e:
            logger.error(f"Unexpected error: {type(e).__name__}: {e}")
            return f"Error: {e!s}"


@mcp_server.tool()
async def search_communities(
    name: str | None = None,
    lands_count_min: int | None = None,
    lands_count_max: int | None = None,
    search: str | None = None,
    page: int | None = None,
    ordering: str | None = None,
) -> str:
    """Search for indigenous communities in Brazil.

    Supports filtering by name and number of associated lands.
    Returns paginated results.

    Args:
        name: Filter by community name (partial match)
        lands_count_min: Minimum number of lands associated with the community
        lands_count_max: Maximum number of lands associated with the community
        search: General search term
        page: Page number for pagination (default: 1)
        ordering: Field to order by (prefix with '-' for descending)
    """
    logger.info("Tool called: search_communities")

    params = {}
    if name is not None:
        params["name"] = name
    if lands_count_min is not None:
        params["lands_count_min"] = lands_count_min
    if lands_count_max is not None:
        params["lands_count_max"] = lands_count_max
    if search is not None:
        params["search"] = search
    if page is not None:
        params["page"] = page
    if ordering is not None:
        params["ordering"] = ordering

    logger.debug(f"Searching communities with params: {params}")

    async with await get_client() as client:
        try:
            response = await client.get("/api/v1/communities/", params=params)
            response.raise_for_status()
            data = response.json()

            result = {
                "total_count": data.get("count", 0),
                "page_results": len(data.get("results", [])),
                "communities": data.get("results", []),
                "next_page": data.get("next") is not None,
            }

            return json.dumps(result, indent=2, ensure_ascii=False)

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error {e.response.status_code}: {e.response.text}")
            return f"API Error {e.response.status_code}: {e.response.text}"
        except Exception as e:
            logger.error(f"Unexpected error: {type(e).__name__}: {e}")
            return f"Error: {e!s}"


@mcp_server.tool()
async def get_community_details(community_id: str) -> str:
    """Retrieve detailed information about a specific indigenous community by its UUID.

    Returns community data including name and count of associated lands.

    Args:
        community_id: UUID of the community to retrieve
    """
    logger.info(f"Tool called: get_community_details({community_id})")

    async with await get_client() as client:
        try:
            response = await client.get(f"/api/v1/communities/{community_id}/")
            response.raise_for_status()
            data = response.json()

            return json.dumps(data, indent=2, ensure_ascii=False)

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error {e.response.status_code}: {e.response.text}")
            return f"API Error {e.response.status_code}: {e.response.text}"
        except Exception as e:
            logger.error(f"Unexpected error: {type(e).__name__}: {e}")
            return f"Error: {e!s}"


@mcp_server.tool()
async def get_api_stats() -> str:
    """Get summary statistics about the Kapok database.

    Returns counts of lands and communities, useful for understanding the dataset scope.
    """
    logger.info("Tool called: get_api_stats")

    async with await get_client() as client:
        try:
            # Get counts from both endpoints
            lands_response = await client.get("/api/v1/lands/", params={"page": 1})
            communities_response = await client.get("/api/v1/communities/", params={"page": 1})

            lands_response.raise_for_status()
            communities_response.raise_for_status()

            lands_data = lands_response.json()
            communities_data = communities_response.json()

            base_url = getattr(settings, "MCP_API_BASE_URL", "http://localhost:8000")

            stats = {
                "total_lands": lands_data.get("count", 0),
                "total_communities": communities_data.get("count", 0),
                "api_base_url": base_url,
                "api_status": "connected",
            }

            return json.dumps(stats, indent=2, ensure_ascii=False)

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error {e.response.status_code}: {e.response.text}")
            return f"API Error {e.response.status_code}: {e.response.text}"
        except Exception as e:
            logger.error(f"Unexpected error: {type(e).__name__}: {e}")
            return f"Error: {e!s}"
