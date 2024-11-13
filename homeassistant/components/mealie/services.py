"""Define services for the Mealie integration."""

from dataclasses import asdict
from datetime import date
from typing import cast

from aiomealie import (
    MealieConnectionError,
    MealieNotFoundError,
    MealieValidationError,
    MealplanEntryType,
)
import voluptuous as vol

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import ATTR_DATE
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
)
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv

from .const import (
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
from .coordinator import MealieConfigEntry

SERVICE_GET_MEALPLAN = "get_mealplan"
SERVICE_GET_MEALPLAN_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_CONFIG_ENTRY_ID): str,
        vol.Optional(ATTR_START_DATE): cv.date,
        vol.Optional(ATTR_END_DATE): cv.date,
    }
)

SERVICE_GET_RECIPE = "get_recipe"
SERVICE_GET_RECIPE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_CONFIG_ENTRY_ID): str,
        vol.Required(ATTR_RECIPE_ID): str,
    }
)

SERVICE_IMPORT_RECIPE = "import_recipe"
SERVICE_IMPORT_RECIPE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_CONFIG_ENTRY_ID): str,
        vol.Required(ATTR_URL): str,
        vol.Optional(ATTR_INCLUDE_TAGS): bool,
    }
)

SERVICE_SET_RANDOM_MEALPLAN = "set_random_mealplan"
SERVICE_SET_RANDOM_MEALPLAN_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_CONFIG_ENTRY_ID): str,
        vol.Required(ATTR_DATE): cv.date,
        vol.Required(ATTR_ENTRY_TYPE): vol.In([x.lower() for x in MealplanEntryType]),
    }
)

SERVICE_SET_MEALPLAN = "set_mealplan"
SERVICE_SET_MEALPLAN_SCHEMA = vol.Any(
    vol.Schema(
        {
            vol.Required(ATTR_CONFIG_ENTRY_ID): str,
            vol.Required(ATTR_DATE): cv.date,
            vol.Required(ATTR_ENTRY_TYPE): vol.In(
                [x.lower() for x in MealplanEntryType]
            ),
            vol.Required(ATTR_RECIPE_ID): str,
        }
    ),
    vol.Schema(
        {
            vol.Required(ATTR_CONFIG_ENTRY_ID): str,
            vol.Required(ATTR_DATE): cv.date,
            vol.Required(ATTR_ENTRY_TYPE): vol.In(
                [x.lower() for x in MealplanEntryType]
            ),
            vol.Required(ATTR_NOTE_TITLE): str,
            vol.Required(ATTR_NOTE_TEXT): str,
        }
    ),
)


def async_get_entry(hass: HomeAssistant, config_entry_id: str) -> MealieConfigEntry:
    """Get the Mealie config entry."""
    if not (entry := hass.config_entries.async_get_entry(config_entry_id)):
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="integration_not_found",
            translation_placeholders={"target": DOMAIN},
        )
    if entry.state is not ConfigEntryState.LOADED:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="not_loaded",
            translation_placeholders={"target": entry.title},
        )
    return cast(MealieConfigEntry, entry)


# Services
def get_async_get_mealplan(hass: HomeAssistant):
    """Get instance of async_get_meal_plan."""

    async def async_get_mealplan(call: ServiceCall) -> ServiceResponse:
        """Get the mealplan for a specific range."""
        entry = async_get_entry(hass, call.data[ATTR_CONFIG_ENTRY_ID])
        start_date = call.data.get(ATTR_START_DATE, date.today())
        end_date = call.data.get(ATTR_END_DATE, date.today())
        if end_date < start_date:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="end_date_before_start_date",
            )
        client = cast(MealieConfigEntry, entry).runtime_data.client
        try:
            mealplans = await client.get_mealplans(start_date, end_date)
        except MealieConnectionError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="connection_error",
            ) from err
        return {"mealplan": [asdict(x) for x in mealplans.items]}

    return async_get_mealplan


def get_async_get_recipe(hass: HomeAssistant):
    """Get instance of async_get_recipe."""

    async def async_get_recipe(call: ServiceCall) -> ServiceResponse:
        """Get a recipe."""
        entry = async_get_entry(hass, call.data[ATTR_CONFIG_ENTRY_ID])
        recipe_id = call.data[ATTR_RECIPE_ID]
        client = entry.runtime_data.client
        try:
            recipe = await client.get_recipe(recipe_id)
        except MealieConnectionError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="connection_error",
            ) from err
        except MealieNotFoundError as err:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="recipe_not_found",
                translation_placeholders={"recipe_id": recipe_id},
            ) from err
        return {"recipe": asdict(recipe)}

    return async_get_recipe


def get_async_import_recipe(hass: HomeAssistant):
    """Get instance of async_import_recipe."""

    async def async_import_recipe(call: ServiceCall) -> ServiceResponse:
        """Import a recipe."""
        entry = async_get_entry(hass, call.data[ATTR_CONFIG_ENTRY_ID])
        url = call.data[ATTR_URL]
        include_tags = call.data.get(ATTR_INCLUDE_TAGS, False)
        client = entry.runtime_data.client
        try:
            recipe = await client.import_recipe(url, include_tags)
        except MealieValidationError as err:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="could_not_import_recipe",
            ) from err
        except MealieConnectionError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="connection_error",
            ) from err
        if call.return_response:
            return {"recipe": asdict(recipe)}
        return None

    return async_import_recipe


def get_async_set_random_mealplan(hass: HomeAssistant):
    """Get instance of async_set_random_mealplan."""

    async def async_set_random_mealplan(call: ServiceCall) -> ServiceResponse:
        """Set a random mealplan."""
        entry = async_get_entry(hass, call.data[ATTR_CONFIG_ENTRY_ID])
        mealplan_date = call.data[ATTR_DATE]
        entry_type = MealplanEntryType(call.data[ATTR_ENTRY_TYPE])
        client = entry.runtime_data.client
        try:
            mealplan = await client.random_mealplan(mealplan_date, entry_type)
        except MealieConnectionError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="connection_error",
            ) from err
        if call.return_response:
            return {"mealplan": asdict(mealplan)}
        return None

    return async_set_random_mealplan


def get_async_set_mealplan(hass: HomeAssistant):
    """Get instance of async_set_mealplan."""

    async def async_set_mealplan(call: ServiceCall) -> ServiceResponse:
        """Set a mealplan."""
        entry = async_get_entry(hass, call.data[ATTR_CONFIG_ENTRY_ID])
        mealplan_date = call.data[ATTR_DATE]
        entry_type = MealplanEntryType(call.data[ATTR_ENTRY_TYPE])
        client = entry.runtime_data.client
        try:
            mealplan = await client.set_mealplan(
                mealplan_date,
                entry_type,
                recipe_id=call.data.get(ATTR_RECIPE_ID),
                note_title=call.data.get(ATTR_NOTE_TITLE),
                note_text=call.data.get(ATTR_NOTE_TEXT),
            )
        except MealieConnectionError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="connection_error",
            ) from err
        if call.return_response:
            return {"mealplan": asdict(mealplan)}
        return None

    return async_set_mealplan


def setup_services(hass: HomeAssistant) -> None:
    """Set up the services for the Mealie integration."""

    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_MEALPLAN,
        get_async_get_mealplan(hass),
        schema=SERVICE_GET_MEALPLAN_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_RECIPE,
        get_async_get_recipe(hass),
        schema=SERVICE_GET_RECIPE_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_IMPORT_RECIPE,
        get_async_import_recipe(hass),
        schema=SERVICE_IMPORT_RECIPE_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_RANDOM_MEALPLAN,
        get_async_set_random_mealplan(hass),
        schema=SERVICE_SET_RANDOM_MEALPLAN_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_MEALPLAN,
        get_async_set_mealplan(hass),
        schema=SERVICE_SET_MEALPLAN_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
