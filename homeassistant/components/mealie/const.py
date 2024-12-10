"""Constants for the Mealie integration."""

import logging

from awesomeversion import AwesomeVersion

DOMAIN = "mealie"

LOGGER = logging.getLogger(__package__)

ATTR_CONFIG_ENTRY_ID = "config_entry_id"
ATTR_START_DATE = "start_date"
ATTR_END_DATE = "end_date"
ATTR_EXCULDED_INGREDIENTS = "excluded_ingredients"
ATTR_RECIPE_ID = "recipe_id"
ATTR_RECIPE_ID_2 = "recipe_id_2"
ATTR_RECIPE_NAME = "recipe_name"
ATTR_URL = "url"
ATTR_INCLUDE_TAGS = "include_tags"
ATTR_ENTRY_TYPE = "entry_type"
ATTR_NOTE_TITLE = "note_title"
ATTR_NOTE_TEXT = "note_text"
ATTR_RECIPE_SLUG = "recipe_slug"
ATTR_MAX_CALORIES = "max_calories"

# New constant for cooking time filter
ATTR_MAX_COOKING_TIME = "max_cooking_time"
ATTR_MIN_COOKED = "min_cooked"

POPULARITY_TABLE = "popularity"

MIN_REQUIRED_MEALIE_VERSION = AwesomeVersion("v1.0.0")
