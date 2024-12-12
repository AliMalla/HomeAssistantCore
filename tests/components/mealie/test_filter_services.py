from unittest.mock import AsyncMock  # noqa: D100

import pytest

from homeassistant.components.mealie.services import (
    get_async_filter_recipes,
    get_aync_filter_recipes_by_popularity,
)


@pytest.mark.asyncio
async def test_filter_by_cooking_time():
    """Test the filter by cooking time service."""
    # Mock input parameters
    call = AsyncMock()
    call.data = {
        "config_entry_id": "test_entry",
        "max_cooking_time": 30,
    }

    # Mock objects and methods
    mock_hass = AsyncMock()
    mock_entry = AsyncMock()
    mock_entry.runtime_data.client.get_recipes = AsyncMock(
        return_value={
            "items": [
                {"recipe_id": 1, "name": "Pasta", "cooking_time": 25},
                {"recipe_id": 2, "name": "Salad", "cooking_time": 15},
                {"recipe_id": 3, "name": "Roast Chicken", "cooking_time": 45},
            ]
        }
    )
    mock_hass.data = {"mealie": {"test_entry": mock_entry}}

    # Run the service function
    result = await get_async_filter_recipes(mock_hass, call)

    # Validate the output
    assert result == {
        "filtered_recipes": [
            {"id": 1, "name": "Pasta", "cooking_time": 25},
            {"id": 2, "name": "Salad", "cooking_time": 15},
        ]
    }


@pytest.mark.asyncio
async def test_filter_recipes_by_popularity():  # noqa: D103
    # Mock the Home Assistant object
    mock_hass = AsyncMock()

    # Mock the configuration entry and data
    mock_entry = AsyncMock()
    mock_entry.runtime_data.client.get_recipes = AsyncMock(
        return_value={
            "items": [
                {"id": 1, "name": "Pasta", "cooked": 5},
                {"id": 2, "name": "Salad", "cooked": 3},
                {"id": 3, "name": "Roast Chicken", "cooked": 7},
            ]
        }
    )
    mock_hass.data = {"mealie": {"test_entry": mock_entry}}

    # Prepare the service call with a minimum cooked value
    call = AsyncMock()
    call.data = {"config_entry_id": "test_entry", "min_cooked": 4}

    # Execute the function
    result = await get_aync_filter_recipes_by_popularity(mock_hass, call)

    # Expected result
    expected_result = {
        "popular_recipes": [
            {"id": 1, "name": "Pasta", "cooked": 5},
            {"id": 3, "name": "Roast Chicken", "cooked": 7},
        ]
    }

    # Validate the result
    assert result == expected_result
