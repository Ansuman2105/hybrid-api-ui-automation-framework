"""
cms_service.py
--------------
High-level CMS API service for tile management.

This layer owns the *business logic* of tile operations: it knows the
API endpoint paths, required payloads, and how to interpret responses.
Tests and fixtures call this service instead of raw ``APIClient`` calls.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from api.api_client import APIClient
from utils.logger import get_logger
from utils.retry import retry_on_failure

log = get_logger(__name__)


class CMSService:
    """
    CMS Tile Management service.

    All methods return clean Python dicts extracted from the API response,
    never raw ``Response`` objects, to keep callers decoupled from HTTP.

    Args:
        client: Optional pre-built ``APIClient`` (useful for testing with
                a mock client).

    Example::

        cms = CMSService()
        tile = cms.create_tile(title="Breaking News", category="news")
        print(tile["id"])
        cms.delete_tile(tile["id"])
    """

    # CMS endpoint paths
    _ENDPOINT_TILES = "/tiles"
    _ENDPOINT_TILE = "/tiles/{tile_id}"
    _ENDPOINT_CATEGORIES = "/categories"
    _ENDPOINT_PUBLISH = "/tiles/{tile_id}/publish"

    def __init__(self, client: Optional[APIClient] = None) -> None:
        self._client = client or APIClient()

    # ------------------------------------------------------------------
    # Tile CRUD
    # ------------------------------------------------------------------

    @retry_on_failure(attempts=3, delay=1.0)
    def create_tile(
        self,
        title: str,
        category: str = "featured",
        description: str = "",
        image_url: str = "",
        deep_link: str = "",
        position: int = 0,
        is_active: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create a new launcher tile in the CMS.

        Args:
            title:       Tile display name (shown on the STB launcher).
            category:    CMS category slug (e.g. ``featured``, ``sports``).
            description: Optional subtitle / description text.
            image_url:   Tile thumbnail image URL.
            deep_link:   App deep-link URI triggered on tile selection.
            position:    Ordering position within the category row.
            is_active:   Whether the tile is immediately live.
            metadata:    Arbitrary key-value pairs attached to the tile.

        Returns:
            Dict containing the created tile data (including server-assigned
            ``id``, ``created_at``, etc.)

        Raises:
            requests.HTTPError: On API failure after retries.
        """
        correlation_id = str(uuid.uuid4())
        payload = {
            "title": title,
            "category": category,
            "description": description,
            "imageUrl": image_url,
            "deepLink": deep_link,
            "position": position,
            "isActive": is_active,
            "metadata": metadata or {},
            "correlationId": correlation_id,
            "createdBy": "stb-automation-framework",
        }

        log.info(
            "Creating tile: title='%s' category='%s' correlationId=%s",
            title, category, correlation_id,
        )

        response = self._client.post(self._ENDPOINT_TILES, json=payload)
        tile_data = response.json()

        log.info(
            "Tile created: id=%s title='%s'",
            tile_data.get("id", "?"), title,
        )
        return tile_data

    @retry_on_failure(attempts=3, delay=1.0)
    def get_tile(self, tile_id: str) -> Dict[str, Any]:
        """
        Retrieve a single tile by ID.

        Args:
            tile_id: Server-assigned tile identifier.

        Returns:
            Tile dict.
        """
        endpoint = self._ENDPOINT_TILE.format(tile_id=tile_id)
        log.info("Fetching tile: id=%s", tile_id)
        response = self._client.get(endpoint)
        return response.json()

    @retry_on_failure(attempts=3, delay=1.0)
    def list_tiles(
        self,
        category: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        List all tiles, optionally filtered by category.

        Args:
            category:  Filter by category slug.
            page:      Pagination page (1-based).
            page_size: Items per page.

        Returns:
            List of tile dicts.
        """
        params: Dict[str, Any] = {"page": page, "pageSize": page_size}
        if category:
            params["category"] = category

        log.info("Listing tiles: params=%s", params)
        response = self._client.get(self._ENDPOINT_TILES, params=params)
        data = response.json()

        # Handle both ``{"tiles": [...]}`` and bare list responses
        if isinstance(data, list):
            return data
        return data.get("tiles", data.get("items", []))

    @retry_on_failure(attempts=3, delay=1.0)
    def update_tile(
        self, tile_id: str, updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Partially update a tile.

        Args:
            tile_id:  Tile to update.
            updates:  Fields to change (only provided fields are updated).

        Returns:
            Updated tile dict.
        """
        endpoint = self._ENDPOINT_TILE.format(tile_id=tile_id)
        log.info("Updating tile %s: %s", tile_id, updates)
        response = self._client.patch(endpoint, json=updates)
        return response.json()

    @retry_on_failure(attempts=3, delay=1.0)
    def delete_tile(self, tile_id: str) -> bool:
        """
        Delete a tile from the CMS.

        Args:
            tile_id: Server-assigned tile identifier.

        Returns:
            True if deletion succeeded.

        Raises:
            requests.HTTPError: On 4xx/5xx.
        """
        endpoint = self._ENDPOINT_TILE.format(tile_id=tile_id)
        log.info("Deleting tile: id=%s", tile_id)
        response = self._client.delete(endpoint)
        log.info("Tile deleted: id=%s status=%d", tile_id, response.status_code)
        return response.status_code in (200, 204)

    @retry_on_failure(attempts=3, delay=1.0)
    def publish_tile(self, tile_id: str) -> Dict[str, Any]:
        """
        Trigger immediate publish/activation of a tile.

        Args:
            tile_id: Tile to publish.

        Returns:
            Published tile dict.
        """
        endpoint = self._ENDPOINT_PUBLISH.format(tile_id=tile_id)
        log.info("Publishing tile: id=%s", tile_id)
        response = self._client.post(endpoint, json={})
        return response.json()

    def tile_exists_by_title(self, title: str, category: Optional[str] = None) -> bool:
        """
        Check whether a tile with a given *title* exists in the CMS.

        Args:
            title:    Exact tile title to search for.
            category: Optional category filter.

        Returns:
            True if at least one matching tile is found.
        """
        tiles = self.list_tiles(category=category)
        match = any(t.get("title") == title for t in tiles)
        log.debug("Tile '%s' exists in CMS: %s", title, match)
        return match

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Close the underlying HTTP session."""
        self._client.close()

    def __enter__(self) -> "CMSService":
        return self

    def __exit__(self, *_) -> None:
        self.close()
