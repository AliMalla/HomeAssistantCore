from unittest.mock import AsyncMock
import pytest
import sqlite3

from .services import (
    get_async_attach_recipe,
    get_async_remove_attached_recipe,
    get_async_get_attached_recipes,
)


@pytest.mark.asyncio
async def test_attach_recipe():
    """Test attaching a recipe to another."""
    # Mock input parameters
    call = AsyncMock()
    call.data = {
        "config_entry_id": "test_entry",
        "recipe_id": "recipe_1",
        "recipe_id_2": "recipe_2",
    }

    # Mock objects and methods
    mock_hass = AsyncMock()
    mock_entry = AsyncMock()
    mock_entry.runtime_data.client.get_recipe = AsyncMock(
        return_value={"id": "recipe_1", "name": "Recipe 1"}
    )
    mock_hass.data = {"mealie": {"test_entry": mock_entry}}

    # Create a mock database connection
    mock_conn = AsyncMock()
    mock_cursor = AsyncMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.fetchall.return_value = []

    # Replace SQLite connection
    sqlite3.connect = AsyncMock(return_value=mock_conn)

    # Run the service function
    async_attach_recipe = get_async_attach_recipe(mock_hass)
    result = await async_attach_recipe(call)

    # Validate the output
    assert result == {"recipe": {"id": "recipe_1", "name": "Recipe 1"}}
    mock_cursor.execute.assert_called_once_with(
        """
        INSERT OR IGNORE INTO attached_recipes (recipe_id, attached_recipe_id)
        VALUES (?, ?)
        """,
        ("recipe_1", "recipe_2"),
    )


@pytest.mark.asyncio
async def test_detach_recipe():
    """Test detaching a recipe from another."""
    # Mock input parameters
    call = AsyncMock()
    call.data = {
        "config_entry_id": "test_entry",
        "recipe_id": "recipe_1",
        "recipe_id_2": "recipe_2",
    }

    # Mock objects and methods
    mock_hass = AsyncMock()
    mock_entry = AsyncMock()
    mock_entry.runtime_data.client.get_recipe = AsyncMock(
        return_value={"id": "recipe_1", "name": "Recipe 1"}
    )
    mock_hass.data = {"mealie": {"test_entry": mock_entry}}

    # Create a mock database connection
    mock_conn = AsyncMock()
    mock_cursor = AsyncMock()
    mock_conn.cursor.return_value = mock_cursor
    sqlite3.connect = AsyncMock(return_value=mock_conn)

    # Run the service function
    async_remove_attached_recipe = get_async_remove_attached_recipe(mock_hass)
    result = await async_remove_attached_recipe(call)

    # Validate the output
    assert result == {"recipe": {"id": "recipe_1", "name": "Recipe 1"}}
    mock_cursor.execute.assert_called_once_with(
        """
        DELETE FROM attached_recipes WHERE (recipe_id = ? AND attached_recipe_id = ?)
        """,
        ("recipe_1", "recipe_2"),
    )


@pytest.mark.asyncio
async def test_get_attached_recipes():
    """Test getting all recipes attached to a specific recipe."""
    # Mock input parameters
    call = AsyncMock()
    call.data = {
        "config_entry_id": "test_entry",
        "recipe_id": "recipe_1",
    }

    # Mock objects and methods
    mock_hass = AsyncMock()
    mock_entry = AsyncMock()
    mock_entry.runtime_data.client.get_recipe = AsyncMock(
        return_value={"id": "recipe_1", "name": "Recipe 1"}
    )
    mock_hass.data = {"mealie": {"test_entry": mock_entry}}

    # Create a mock database connection
    mock_conn = AsyncMock()
    mock_cursor = AsyncMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.fetchall.return_value = [("recipe_2",), ("recipe_3",)]
    sqlite3.connect = AsyncMock(return_value=mock_conn)

    # Run the service function
    async_get_attached_recipes = get_async_get_attached_recipes(mock_hass)
    result = await async_get_attached_recipes(call)

    # Validate the output
    assert result == {"recipes": ["recipe_2", "recipe_3"]}
    mock_cursor.execute.assert_called_once_with(
        """
            SELECT attached_recipe_id
            FROM attached_recipes
            WHERE recipe_id = ?
            """,
        ("recipe_1",),
    )
