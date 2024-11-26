"""Support for Mealie sensors."""

from collections.abc import Callable
from dataclasses import dataclass
import sqlite3

from aiomealie import Statistics

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from .coordinator import MealieConfigEntry, MealieStatisticsCoordinator
from .entity import MealieEntity


@dataclass(frozen=True, kw_only=True)
class MealieStatisticsSensorEntityDescription(SensorEntityDescription):
    """Describes Mealie Statistics sensor entity."""

    value_fn: Callable[[Statistics], StateType]


SENSOR_TYPES: tuple[MealieStatisticsSensorEntityDescription, ...] = (
    MealieStatisticsSensorEntityDescription(
        key="recipes",
        native_unit_of_measurement="recipes",
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda statistics: statistics.total_recipes,
    ),
    MealieStatisticsSensorEntityDescription(
        key="users",
        native_unit_of_measurement="users",
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda statistics: statistics.total_users,
    ),
    MealieStatisticsSensorEntityDescription(
        key="categories",
        native_unit_of_measurement="categories",
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda statistics: statistics.total_categories,
    ),
    MealieStatisticsSensorEntityDescription(
        key="tags",
        native_unit_of_measurement="tags",
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda statistics: statistics.total_tags,
    ),
    MealieStatisticsSensorEntityDescription(
        key="tools",
        native_unit_of_measurement="tools",
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda statistics: statistics.total_tools,
    ),
)


class HeartedRecipesSensor(Entity):  # pylint: disable=hass-enforce-class-module
    """Entity for hearted recipes."""

    def __init__(self, hass):
        """Set attributes."""
        self.hass = hass
        self._state = None

    @property
    def name(self):
        """Name of the entity."""
        return "Hearted Recipes"

    @property
    def state(self):
        """State of the entity."""
        return len(self.get_hearted_recipes())

    def get_hearted_recipes(self):
        """Return all the hearted recipes."""
        conn = sqlite3.connect("favourite_recipes.db")
        cursor = conn.cursor()
        cursor.execute("SELECT recipe_id FROM favourite_recipes")
        recipes = cursor.fetchall()
        conn.close()
        return [recipe[0] for recipe in recipes]

    @property
    def extra_state_attributes(self):
        """Return the hearted recipes with extra attributes."""
        return {"recipes": self.get_hearted_recipes()}


async def async_setup_entry(
    _: HomeAssistant,
    entry: MealieConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Mealie sensors based on a config entry."""
    coordinator = entry.runtime_data.statistics_coordinator

    async_add_entities(
        MealieStatisticSensors(coordinator, description) for description in SENSOR_TYPES
    )
    async_add_entities([HeartedRecipesSensor(_)])


class MealieStatisticSensors(MealieEntity, SensorEntity):
    """Defines a Mealie sensor."""

    entity_description: MealieStatisticsSensorEntityDescription
    coordinator: MealieStatisticsCoordinator

    def __init__(
        self,
        coordinator: MealieStatisticsCoordinator,
        description: MealieStatisticsSensorEntityDescription,
    ) -> None:
        """Initialize Mealie sensor."""
        super().__init__(coordinator, description.key)
        self.entity_description = description
        self._attr_translation_key = description.key

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        return self.entity_description.value_fn(self.coordinator.data)
