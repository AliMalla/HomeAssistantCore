import aiohttp
import asyncio
import logging

LOGGER = logging.getLogger(__name__)

class NutritionixClient:
    """Client for handling the communication with the Nutritionix API."""


    def __init__ (self, app_id: str, app_key: str, session: aiohttp.ClientSession):
        self._app_id = app_id
        self._app_key = app_key
        self._session = session

        #URL of the POST endpoint
        self.URL = "https://trackapi.nutritionix.com/v2/natural/nutrients"


    def fetch_nutrition_info(self, query: str) -> dict:
        """Fetch nutrition data of ingredients based on their measures"""

        headers = {
            "x-app-id": self._app_id,
            "x-app-key": self._app_key,
            "Content-Type": "application/json"
        }

        payload = {
            "query" : query
        }

        try:
            response = await self._session.post(self.URL, json=payload, headers=headers)

            #Raise exception if the http status is not OK
            response.raise_for_status()

            #Parse the response into a dict
            data = await response.json()

        except aiohttp.ClientError as err:
            LOGGER.error(f"Error: {err}")
            raise

