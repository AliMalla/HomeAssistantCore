import pytest
from unittest.mock import AsyncMock, MagicMock
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.components.mealie.services import (
    get_async_attach_recipe,
    get_async_remove_attached_recipe,
    get_async_get_attached_recipes,
)


# Mock async_get_entry, ServiceCall and sqlite3
@pytest.mark.asyncio
async def test_attach_recipe():
    """Test attaching a recipe to another."""
    # Mock the service call data
    call = MagicMock()
    call.data = {
        "config_entry_id": "test_entry",
        "recipe_id": "recipe_1",
        "recipe_id_2": "recipe_2",
    }

    # Mock the Home Assistant instance and the async_get_entry function
    mock_hass = AsyncMock(HomeAssistant)
    mock_entry = MagicMock()
    mock_hass.data = {"mealie": {"test_entry": mock_entry}}

    # Mock the async_get_entry function to return a mock entry
    async def mock_async_get_entry(entry_id):
        return mock_entry if entry_id == "test_entry" else None

    mock_hass.config_entries.async_get_entry = mock_async_get_entry

    # Mock the client’s get_recipe method to return mock data
    mock_entry.runtime_data.client.get_recipe = AsyncMock(
        return_value={"recipe_id": "recipe_1", "name": "Pasta"}
    )

    # Mock the sqlite3 database interaction
    mock_db = AsyncMock()
    mock_db.cursor.return_value = MagicMock()
    mock_db.cursor.return_value.fetchall.return_value = [("recipe_2",)]

    # Replace sqlite3.connect with our mock to prevent actual DB calls
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("sqlite3.connect", lambda *args, **kwargs: mock_db)

        # Run the service function
        result = await get_async_attach_recipe(mock_hass)(call)

    # Assert that the result is as expected
    assert result == {"recipe": {"recipe_id": "recipe_1", "name": "Pasta"}}


@pytest.mark.asyncio
async def test_remove_attached_recipe():
    """Test removing an attached recipe."""
    # Mock the service call data
    call = MagicMock()
    call.data = {
        "config_entry_id": "test_entry",
        "recipe_id": "recipe_1",
        "recipe_id_2": "recipe_2",
    }

    # Mock the Home Assistant instance
    mock_hass = AsyncMock(HomeAssistant)
    mock_entry = MagicMock()
    mock_hass.data = {"mealie": {"test_entry": mock_entry}}

    # Mock the async_get_entry function to return the mock entry
    async def mock_async_get_entry(entry_id):
        return mock_entry if entry_id == "test_entry" else None

    mock_hass.config_entries.async_get_entry = mock_async_get_entry

    # Mock the client’s get_recipe method
    mock_entry.runtime_data.client.get_recipe = AsyncMock(
        return_value={"recipe_id": "recipe_1", "name": "Pasta"}
    )

    # Mock the sqlite3 database interaction
    mock_db = AsyncMock()
    mock_db.cursor.return_value = MagicMock()

    # Replace sqlite3.connect with our mock to prevent actual DB calls
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("sqlite3.connect", lambda *args, **kwargs: mock_db)

        # Run the service function
        result = await get_async_remove_attached_recipe(mock_hass)(call)

    # Assert that the result is as expected
    assert result == {"recipe": {"recipe_id": "recipe_1", "name": "Pasta"}}


@pytest.mark.asyncio
async def test_get_attached_recipes():
    """Test retrieving attached recipes."""
    # Mock the service call data
    call = MagicMock()
    call.data = {"config_entry_id": "test_entry", "recipe_id": "recipe_1"}

    # Mock the Home Assistant instance
    mock_hass = AsyncMock(HomeAssistant)
    mock_entry = MagicMock()
    mock_hass.data = {"mealie": {"test_entry": mock_entry}}

    # Mock the async_get_entry function to return the mock entry
    async def mock_async_get_entry(entry_id):
        return mock_entry if entry_id == "test_entry" else None

    mock_hass.config_entries.async_get_entry = mock_async_get_entry

    # Mock the client’s get_recipe method
    mock_entry.runtime_data.client.get_recipe = AsyncMock(
        return_value={"recipe_id": "recipe_1", "name": "Pasta"}
    )

    # Mock the sqlite3 database interaction
    mock_db = AsyncMock()
    mock_db.cursor.return_value = MagicMock()
    mock_db.cursor.return_value.fetchall.return_value = [("recipe_2",)]

    # Replace sqlite3.connect with our mock to prevent actual DB calls
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("sqlite3.connect", lambda *args, **kwargs: mock_db)

        # Run the service function
        result = await get_async_get_attached_recipes(mock_hass)(call)

    # Assert that the result is as expected
    assert result == {"recipes": ["recipe_2"]}
