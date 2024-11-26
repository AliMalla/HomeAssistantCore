"""Define services for the Mealie integration."""

import asyncio
from dataclasses import asdict
from datetime import date
import sqlite3
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
    JsonObjectType,
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
    ATTR_EXCULDED_INGREDIENTS,
    ATTR_INCLUDE_TAGS,
    ATTR_MAX_COOKING_TIME,
    ATTR_MIN_COOKED,
    ATTR_NOTE_TEXT,
    ATTR_NOTE_TITLE,
    ATTR_RECIPE_ID,
    ATTR_RECIPE_NAME,
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
# Define the new service and schema
SERVICE_FILTER_RECIPES = "filter_recipes"
SERVICE_FILTER_RECIPES_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_CONFIG_ENTRY_ID): str,
        vol.Required(ATTR_MAX_COOKING_TIME): int,
    }
)
# Define the new service and schema for filtering recipes by popularity
SERVICE_FILTER_RECIPES_BY_POPULARITY = "filter_recipes_by_popularity"
SERVICE_FILTER_RECIPES_BY_POPULARITY_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_CONFIG_ENTRY_ID): str,
        vol.Required(ATTR_MIN_COOKED): int,
    }
)
# Define the service and schema for marking recipes as cooked
SERVICE_MARK_RECIPE_AS_COOKED = "mark_recipe_as_cooked"
SERVICE_MARK_RECIPE_AS_COOKED_SCHEMA = vol.Schema(
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

SERVICE_GET_SPECIFIC_RECIPE = "get_specific_recipe"
SERVICE_GET_SPECIFIC_RECIPE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_CONFIG_ENTRY_ID): str,
        vol.Required(ATTR_RECIPE_NAME): str,
    }
)

SERVICE_GET_SPECIFIC_RECIPES = "get_specific_recipes"
SERVICE_GET_SPECIFIC_RECIPES_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_CONFIG_ENTRY_ID): str,
        vol.Required(ATTR_RECIPE_NAME): str,
    }
)

SERVICE_GET_RECIPE_CALORIES = "get_recipe_calories"
SERVICE_GET_RECIPE_CALORIES_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_CONFIG_ENTRY_ID): str,
        vol.Required(ATTR_RECIPE_SLUG): str,  # Slug-of-the-recipe
    }
)

SERVICE_GET_FILTERED_RECIPES_BY_INGREDIENTS = "get_filtered_recipes_by_ingredients"
SERVICE_GET_FILTERED_RECIPES_BY_INGREDIENTS_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_CONFIG_ENTRY_ID): str,
        vol.Required(ATTR_EXCULDED_INGREDIENTS): [str],
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


def get_async_get_specific_recipe(hass: HomeAssistant):
    """Get instance of async_get_specific_recipe."""

    async def async_get_specific_recipe(call: ServiceCall) -> ServiceResponse:
        """Get specific recipe."""
        entry = async_get_entry(hass, call.data[ATTR_CONFIG_ENTRY_ID])
        recipe_name = call.data[ATTR_RECIPE_NAME]
        client = entry.runtime_data.client
        try:
            recipes_res = await client.get_recipes()
        except MealieConnectionError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="connection_error",
            ) from err

        # Filter recipes based on recipe name and return only the recipe that matches the recipe name.
        return {
            "recipe": asdict(recipe)
            for recipe in recipes_res.items
            if recipe_name.lower() == recipe.name.lower()
        }

    return async_get_specific_recipe


def get_async_get_specific_recipes(hass: HomeAssistant):
    """Get instance of async_get_specific_recipes."""

    async def async_get_specific_recipes(call: ServiceCall) -> ServiceResponse:
        """Get specific recipes."""
        entry = async_get_entry(hass, call.data[ATTR_CONFIG_ENTRY_ID])
        recipe_name = call.data[ATTR_RECIPE_NAME]
        client = entry.runtime_data.client
        try:
            recipes_res = await client.get_recipes()
        except MealieConnectionError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="connection_error",
            ) from err

        # Filter recipes based on the recipe name
        return {
            "recipes": [
                asdict(recipe)
                for recipe in recipes_res.items
                if recipe_name.lower() in recipe.name.lower()
            ]
        }

    return async_get_specific_recipes


def get_async_get_recipe_calories(hass: HomeAssistant):
    """Get instance of async_get_recipe_calories."""

    async def async_get_recipe_calories(call: ServiceCall) -> ServiceResponse:
        """Get calories of a recipe based on its slug"""

        entry = async_get_entry(hass, call.data[ATTR_CONFIG_ENTRY_ID])
        slug = call.data[ATTR_RECIPE_SLUG]
        client = entry.runtime_data.client

        try:
            host = client.api_host
            api_token = client.token

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

        res = {
            "slug": slug,
            "calories": calories
            }
        print(f"Response: {res}")
        return res

    return async_get_recipe_calories


def get_async_get_filtered_recipes_by_ingredients(hass: HomeAssistant):
    """Get instance of async_get_filtered_recipes_by_ingredients."""

    async def async_get_filtered_recipes_by_ingredients(
        call: ServiceCall,
    ) -> ServiceResponse:
        """Get filtered recipes by ingredients."""

        entry = async_get_entry(hass, call.data[ATTR_CONFIG_ENTRY_ID])

        exclude_ingredients = call.data[ATTR_EXCULDED_INGREDIENTS]
        client = entry.runtime_data.client
        try:
            recipes_res = await client.get_recipes()
        except MealieConnectionError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="connection_error",
            ) from err

        # Define an async function to fetch and process each recipe
        async def fetch_and_filter_recipe(recipe):
            try:
                # Fetch detailed recipe info by ID
                detailed_recipe = await client.get_recipe(recipe.recipe_id)
            except MealieConnectionError:
                return None  # Skip this recipe if fetching fails

            # Extract ingredient notes from the detailed recipe
            ingredients_notes = [
                ingredient.get("note", "").lower()
                if isinstance(ingredient, dict)
                else ingredient.note.lower()
                for ingredient in detailed_recipe.ingredients
            ]

            # Check if any unwanted ingredient notes are in the list
            if any(
                excluded.lower() in note
                for excluded in exclude_ingredients
                for note in ingredients_notes
            ):
                return None  # Exclude recipe

            # Return the recipe if it passes the filter
            return asdict(recipe) if not isinstance(recipe, dict) else recipe

        # Launch tasks for all recipes concurrently
        tasks = [fetch_and_filter_recipe(recipe) for recipe in recipes_res.items]
        filtered_recipes = await asyncio.gather(*tasks)

        # Remove None values (excluded recipes)
        filtered_recipes = [recipe for recipe in filtered_recipes if recipe is not None]

        return {"recipes": filtered_recipes}

    return async_get_filtered_recipes_by_ingredients


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


def get_async_filter_recipes(hass: HomeAssistant):
    """Get instance of async_filter_recipes."""

    async def async_filter_recipes(call: ServiceCall) -> JsonObjectType:
        """Filter recipes by cooking time."""
        config_entry_id = call.data[ATTR_CONFIG_ENTRY_ID]
        max_cooking_time = call.data[ATTR_MAX_COOKING_TIME]

        # Access the client directly
        entry = async_get_entry(hass, config_entry_id)
        client = entry.runtime_data.client

        try:
            # Fetch all recipes from the Mealie API
            all_recipes = await client.get_recipes()

            # Filter recipes by cooking time
            filtered_recipes = [
                recipe
                for recipe in all_recipes
                if getattr(recipe, "cooking_time", None)
                and recipe.cooking_time <= max_cooking_time
            ]
        except Exception as err:
            raise HomeAssistantError(f"Error filtering recipes: {err}") from err

        return [recipe.to_dict() for recipe in filtered_recipes]

    return async_filter_recipes


def get_async_mark_recipe_as_cooked(hass: HomeAssistant):
    """Get instance of async_mark_recipe_as_cooked."""

    async def async_mark_recipe_as_cooked(call: ServiceCall) -> None:
        """Mark a recipe as cooked."""
        config_entry_id = call.data[ATTR_CONFIG_ENTRY_ID]
        recipe_id = call.data[ATTR_RECIPE_ID]

        # Retrieve the coordinator for the specified config entry
        coordinator = hass.data[DOMAIN][config_entry_id]

        try:
            # Increment the cooked count for the recipe
            if recipe_id not in coordinator.popularity:
                coordinator.popularity[recipe_id] = 0  # Initialize if not present
            coordinator.popularity[recipe_id] += 1
        except Exception as err:
            raise HomeAssistantError(f"Error marking recipe as cooked: {err}") from err

    return async_mark_recipe_as_cooked


def get_aync_filter_recipes_by_popularity(hass: HomeAssistant):
    """Get instance of async_filter_recipes_by_popularity."""

    async def async_filter_recipes_by_popularity(call: ServiceCall) -> JsonObjectType:
        """Filter recipes by popularity."""
        config_entry_id = call.data[ATTR_CONFIG_ENTRY_ID]
        min_cooked = call.data[ATTR_MIN_COOKED]

        try:
            # Retrieve the client and entry
            entry = async_get_entry(hass, config_entry_id)
            client = entry.runtime_data.client

            # Fetch all recipes
            all_recipes = await client.get_recipes()

            # Filter and include the cooked count
            popular_recipes = [
                {
                    "id": recipe.id,
                    "name": recipe.name,
                    "cooked": getattr(recipe, "cooked", 0),
                }
                for recipe in all_recipes
                if getattr(recipe, "cooked", 0) >= min_cooked
            ]

            return {"popular_recipes": popular_recipes}  # noqa: TRY300

        except Exception as err:
            raise HomeAssistantError(
                f"Error filtering recipes by popularity: {err}"
            ) from err

    return async_filter_recipes_by_popularity


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


def get_async_heart_recipe(hass: HomeAssistant):
    """Add a recipe to favourites."""

    async def async_heart_recipe(call: ServiceCall) -> ServiceResponse:
        """Heart a recipe."""
        entry = async_get_entry(hass, call.data[ATTR_CONFIG_ENTRY_ID])
        recipe_id = call.data[ATTR_RECIPE_ID]
        conn = sqlite3.connect("favourite_recipes.db")
        cursor = conn.cursor()
        cursor.execute(
            """
        INSERT OR IGNORE INTO favourite_recipes (recipe_id)
        VALUES (?)
        """,
            (recipe_id,),
        )
        conn.commit()
        conn.close()

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

    return async_heart_recipe


def get_async_unheart_recipe(hass: HomeAssistant):
    """Remove a recipe to favourites."""

    async def async_unheart_recipe(call: ServiceCall) -> ServiceResponse:
        """Unheart a recipe."""
        entry = async_get_entry(hass, call.data[ATTR_CONFIG_ENTRY_ID])
        recipe_id = call.data[ATTR_RECIPE_ID]
        conn = sqlite3.connect("favourite_recipes.db")
        cursor = conn.cursor()
        cursor.execute(
            """
        DELETE FROM favourite_recipes WHERE recipe_id = ?
        """,
            (recipe_id,),
        )
        conn.commit()
        conn.close()

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

    return async_unheart_recipe


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
        SERVICE_GET_RECIPES,
        get_async_get_recipes(hass),
        schema=SERVICE_GET_RECIPES_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_SPECIFIC_RECIPE,
        get_async_get_specific_recipe(hass),
        schema=SERVICE_GET_SPECIFIC_RECIPE_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_SPECIFIC_RECIPES,
        get_async_get_specific_recipes(hass),
        schema=SERVICE_GET_SPECIFIC_RECIPES_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_FILTERED_RECIPES_BY_INGREDIENTS,
        get_async_get_filtered_recipes_by_ingredients(hass),
        schema=SERVICE_GET_FILTERED_RECIPES_BY_INGREDIENTS_SCHEMA,
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
    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_RECIPE_CALORIES,
        get_async_get_recipe_calories(hass),
        schema=SERVICE_GET_RECIPE_CALORIES_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        "heart_recipe",
        get_async_heart_recipe(hass),
        schema=SERVICE_GET_RECIPE_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_FILTER_RECIPES,
        get_async_filter_recipes(hass),
        schema=SERVICE_FILTER_RECIPES_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        "unheart_recipe",
        get_async_unheart_recipe(hass),
        schema=SERVICE_GET_RECIPE_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_FILTER_RECIPES_BY_POPULARITY,
        get_aync_filter_recipes_by_popularity(hass),
        schema=SERVICE_FILTER_RECIPES_BY_POPULARITY_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_MARK_RECIPE_AS_COOKED,
        get_async_mark_recipe_as_cooked(hass),
        schema=SERVICE_MARK_RECIPE_AS_COOKED_SCHEMA,
        supports_response=False,
    )
