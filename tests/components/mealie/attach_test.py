from unittest.mock import AsyncMock
import pytest
from homeassistant.components.mealie.const import (
    ATTR_CONFIG_ENTRY_ID,
    ATTR_RECIPE_ID,
    ATTR_RECIPE_ID_2,
)
from homeassistant.components.mealie.const import (
    ATTR_CONFIG_ENTRY_ID,
    ATTR_END_DATE,
    ATTR_ENTRY_TYPE,
    ATTR_INCLUDE_TAGS,
    ATTR_NOTE_TEXT,
    ATTR_NOTE_TITLE,
    ATTR_RECIPE_ID,
    ATTR_START_DATE,
    ATTR_URL,
    DOMAIN,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError

from . import setup_integration
from tests.common import MockConfigEntry
from syrupy import SnapshotAssertion


async def test_service_attach_recipe(
    hass: HomeAssistant,
    mock_mealie_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test if attach_recipe service handles self-attaching correctly."""
    await setup_integration(hass, mock_config_entry)

    with pytest.raises(ValueError, match="A recipe can not reference itself."):
        await hass.services.async_call(
            DOMAIN,
            "attach_recipe",
            {
                ATTR_CONFIG_ENTRY_ID: mock_config_entry.entry_id,
                ATTR_RECIPE_ID: "recipe1",
                ATTR_RECIPE_ID_2: "recipe1",
            },
            blocking=True,
            return_response=True,
        )
