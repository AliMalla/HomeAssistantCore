"""Define an object to manage fetching Mealie data."""

from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass
from datetime import timedelta

from aiomealie import (
    MealieAuthenticationError,
    MealieClient,
    MealieConnectionError,
    Mealplan,
    MealplanEntryType,
    RecipesResponse,
    ShoppingItem,
    ShoppingList,
    Statistics,
)

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
import homeassistant.util.dt as dt_util

from .const import LOGGER

WEEK = timedelta(days=7)


@dataclass
class MealieData:
    """Mealie data type."""

    client: MealieClient
    mealplan_coordinator: MealieMealplanCoordinator
    shoppinglist_coordinator: MealieShoppingListCoordinator
    statistics_coordinator: MealieStatisticsCoordinator


type MealieConfigEntry = ConfigEntry[MealieData]


class MealieDataUpdateCoordinator[_DataT](DataUpdateCoordinator[_DataT]):
    """Base coordinator."""

    config_entry: MealieConfigEntry
    _name: str
    _update_interval: timedelta

    def __init__(self, hass: HomeAssistant, client: MealieClient) -> None:
        """Initialize the Mealie data coordinator."""
        super().__init__(
            hass,
            LOGGER,
            name=self._name,
            update_interval=self._update_interval,
        )
        self.client = client
        self.popularity = {}  # Initialize popularity table (recipe_id -> cooked count)

    async def get_all_recipes(self) -> RecipesResponse:
        """Fetch all recipes from Mealie."""
        try:
            return (
                await self.client.get_recipes()
            )  # Uses aiomealie's get_recipes method
        except MealieConnectionError as error:
            LOGGER.error("Failed to fetch recipes: %s", error)
            raise UpdateFailed(error) from error

    async def filter_recipes_by_cooking_time(self, max_cooking_time: int) -> list[dict]:
        """Fetch and filter recipes by cooking time."""
        # Fetch all recipes
        recipes_response = await self.get_all_recipes()
        # Access the 'items' attribute, which contains the list of recipes
        all_recipes = recipes_response.items

        # Filter recipes based on cooking time
        filtered_recipes = [
            recipe
            for recipe in all_recipes
            if isinstance(getattr(recipe, "cooking_time", None), (int, float))
            and getattr(recipe, "cooking_time") <= max_cooking_time
        ]
        return [recipe.to_dict() for recipe in filtered_recipes]

    async def filter_recipes_by_popularity(self, min_cooked: int) -> list[dict]:
        """Fetch and filter recipes by popularity."""
        # Fetch all recipes
        recipes_response = await self.get_all_recipes()
        all_recipes = recipes_response.items

        # Filter recipes
        popular_recipes = [
            recipe
            for recipe in all_recipes
            if self.popularity.get(recipe.id, 0) >= min_cooked
        ]
        return [recipe.to_dict() for recipe in popular_recipes]

    async def _async_update_data(self) -> _DataT:
        """Fetch data from Mealie."""
        try:
            return await self._async_update_internal()
        except MealieAuthenticationError as error:
            raise ConfigEntryAuthFailed from error
        except MealieConnectionError as error:
            raise UpdateFailed(error) from error

    @abstractmethod
    async def _async_update_internal(self) -> _DataT:
        """Fetch data from Mealie."""


class MealieMealplanCoordinator(
    MealieDataUpdateCoordinator[dict[MealplanEntryType, list[Mealplan]]]
):
    """Class to manage fetching Mealie data."""

    _name = "MealieMealplan"
    _update_interval = timedelta(hours=1)

    async def _async_update_internal(self) -> dict[MealplanEntryType, list[Mealplan]]:
        next_week = dt_util.now() + WEEK
        current_date = dt_util.now().date()
        next_week_date = next_week.date()
        response = await self.client.get_mealplans(current_date, next_week_date)
        res: dict[MealplanEntryType, list[Mealplan]] = {
            type_: [] for type_ in MealplanEntryType
        }
        for meal in response.items:
            res[meal.entry_type].append(meal)
        return res


@dataclass
class ShoppingListData:
    """Data class for shopping list data."""

    shopping_list: ShoppingList
    items: list[ShoppingItem]


class MealieShoppingListCoordinator(
    MealieDataUpdateCoordinator[dict[str, ShoppingListData]]
):
    """Class to manage fetching Mealie Shopping list data."""

    _name = "MealieShoppingList"
    _update_interval = timedelta(minutes=5)

    async def _async_update_internal(
        self,
    ) -> dict[str, ShoppingListData]:
        shopping_list_items = {}
        shopping_lists = (await self.client.get_shopping_lists()).items
        for shopping_list in shopping_lists:
            shopping_list_id = shopping_list.list_id

            shopping_items = (
                await self.client.get_shopping_items(shopping_list_id)
            ).items

            shopping_list_items[shopping_list_id] = ShoppingListData(
                shopping_list=shopping_list, items=shopping_items
            )
        return shopping_list_items


class MealieStatisticsCoordinator(MealieDataUpdateCoordinator[Statistics]):
    """Class to manage fetching Mealie Statistics data."""

    _name = "MealieStatistics"
    _update_interval = timedelta(minutes=15)

    async def _async_update_internal(
        self,
    ) -> Statistics:
        return await self.client.get_statistics()
