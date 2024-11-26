"""Define services for the Mealie integration."""

from dataclasses import asdict
from datetime import date
from typing import cast
import aiohttp
import logging

_LOGGER = logging.getLogger(__name__)

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
    ATTR_MAX_CALORIES,
    ATTR_RECIPE_SLUG,
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

SERVICE_GET_RECIPES = "get_recipes"
SERVICE_GET_RECIPES_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_CONFIG_ENTRY_ID): str,
    }
)

SERVICE_GET_RECIPE_CALORIES = "get_recipe_calories"
SERVICE_GET_RECIPE_CALORIES_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_CONFIG_ENTRY_ID): str,
        vol.Required(ATTR_RECIPE_SLUG): str,  # Slug-of-the-recipe
    }
)

SERVICE_GET_FILTERED_RECIPES_BASED_ON_CALORIES = "get_calories_based_filtered_recipes"
SERVICE_GET_FILTERED_RECIPES_BASED_ON_CALORIES_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_CONFIG_ENTRY_ID): str,
        vol.Required(ATTR_MAX_CALORIES): int, # Max calories for filtering
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


def get_async_get_recipes(hass: HomeAssistant):
    """Get instance of async_get_recipes."""

    async def async_get_recipes(call: ServiceCall) -> ServiceResponse:
        """Get recipes."""
        entry = async_get_entry(hass, call.data[ATTR_CONFIG_ENTRY_ID])
        client = entry.runtime_data.client
        try:
            recipes_res = await client.get_recipes()
        except MealieConnectionError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="connection_error",
            ) from err
        # recipes_res.items is by default list[BaseRecipe]
        # Dataclasses are not json serializable
        # Action return values must be json serializable
        return {"recipes": [asdict(x) for x in recipes_res.items]}

    return async_get_recipes


def get_async_get_recipe_calories(hass: HomeAssistant):
    """Get instance of async_get_recipe_calories."""

    async def async_get_recipe_calories(call: ServiceCall) -> ServiceResponse:
        """Get calories of a recipe based on its slug"""

        entry = async_get_entry(hass, call.data[ATTR_CONFIG_ENTRY_ID])
        slug = call.data[ATTR_RECIPE_SLUG]
        client = entry.runtime_data.client

        try:
            # Retrieve the token from the client (adapt this to your client's structure)
            host = client.api_host
            api_token = client.token  # Adjust based on actual implementation


            # Make a direct API call using the token
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {api_token}"}
                url = f"{host}/api/recipes/{slug}"

                async with session.get(url, headers=headers) as response:
                    if response.status != 200:
                        raise HomeAssistantError(f"Error fetching recipe: {response.status}")
                    recipe_data = await response.json()

            # Extract calories from the response
            calories = recipe_data.get("nutrition", {}).get("calories", 0)

        except MealieConnectionError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="connection_error",
            ) from err
        except MealieNotFoundError as err:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="recipe_not_found",
                translation_placeholders={"recipe_slug": slug},
            ) from err

        return {
            "slug": slug,
            "calories": calories
            }

    return async_get_recipe_calories


def get_async_filter_recipes_by_calories(hass: HomeAssistant):
    """Get instance of async_filter_recipes_by_calories."""

    async def async_filter_recipes_by_calories(call: ServiceCall) -> ServiceResponse:
        """Get recipes filtered by calories."""
        entry = async_get_entry(hass, call.data[ATTR_CONFIG_ENTRY_ID])
        client = entry.runtime_data.client

        # Get the max_calories limit from the service call data
        max_calories = call.data.get('max_calories', float('inf'))

        try:
            recipes = await client.get_recipes()
            filtered_recipes = []

            # Loop  to fetch recipes calorie info
            for recipe in recipes.items:
                recipe_slug = recipe.slug
                host = client.api_host
                api_token = client.token

                # Make GET requests to fetch the recipe details for getting the calories
                url = f"{host}/api/recipes/{recipe_slug}"
                headers = {"Authorization": f"Bearer {api_token}"}

                # Fetch the recipe's data including calories
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, headers=headers) as response:
                        if response.status != 200:
                            raise HomeAssistantError(f"Error fetching recipe {recipe_slug}: {response.status}")
                        recipe_data = await response.json()

                # Extract calories from the recipe response safely
                calories_raw = recipe_data.get("nutrition", {}).get("calories", 0)
                try:
                    calories = int(calories_raw) if calories_raw is not None else 0
                except (ValueError, TypeError):
                    # Fallback in case the calories value is invalid
                    calories = 0

                # Add the calories to the recipe data
                recipe_dict = asdict(recipe)
                recipe_dict['calories'] = calories

                # If the recipe's calories are <= max_calories, add it to the filtered list
                if calories <= max_calories:
                    filtered_recipes.append(recipe_dict)
        except MealieConnectionError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="connection_error",
            ) from err
        except MealieNotFoundError as err:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="recipe_not_found",
                translation_placeholders={"recipe_slug": recipe_slug},
            ) from err

        print(f"response: {filtered_recipes}")
        return {"recipes": filtered_recipes}

    return async_filter_recipes_by_calories


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
        SERVICE_GET_FILTERED_RECIPES_BASED_ON_CALORIES,
        get_async_filter_recipes_by_calories(hass),
        schema=SERVICE_GET_FILTERED_RECIPES_BASED_ON_CALORIES_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )

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
        SERVICE_GET_RECIPES,
        get_async_get_recipes(hass),
        schema=SERVICE_GET_RECIPES_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_RECIPE_CALORIES,
        get_async_get_recipe_calories(hass),
        schema=SERVICE_GET_RECIPE_CALORIES_SCHEMA,
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
