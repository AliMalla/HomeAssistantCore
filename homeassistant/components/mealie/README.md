# Group 6 Mealie Integration
## Features
### Feature 1
Fetch recipes from Mealie and display recipes in Home Assistant "Recipes" panel, in the left menu. Users can filter recipes by name, calories, excluded ingredients, cooking time, and popularity.

### Feature 2
The user can add and remove ingredients they have at home. The user can then view recipes containing those ingredients.

### Feature 3
The user can add and remove recipes as favorites.

### Change request
The user searches for recipes, search results are displayed together with recommended recipes relevant to the previously mentioned recipes.

## Installation
### Home Assistant
Install Home Assistant.
### Mealie
1. Run `docker-compose up` with the docker-compose.yml file.
```
services:
  mealie:
    image: ghcr.io/mealie-recipes/mealie:v2.1.0 # 
    container_name: mealie
    restart: always
    ports:
        - "9925:9000" # 
    deploy:
      resources:
        limits:
          memory: 1000M # 
    volumes:
      - mealie-data-new:/app/data/
    networks:
      - my_homeassistant
    environment:
      # Set Backend ENV Variables Here
      ALLOW_SIGNUP: "false"
      PUID: 1000
      PGID: 1000
      TZ: Europe/Berlin
      MAX_WORKERS: 1
      WEB_CONCURRENCY: 1
      BASE_URL: http://localhost:9925

volumes:
  mealie-data-new:

networks:
  my_homeassistant:
    name: "homeassistant"
    driver: bridge

```
2. This will create a container and a network. The container is running Mealie. The network "homeassistant" is the network that will be used to communicate between Mealie and Home Assistant.
3. Mealie should now be running at http://localhost:9925
4. Create a new account.
5. Create a new API key at http://localhost:9925/user/profile/api-tokens
6. Store the API key somewhere, it will be used when installing the Mealie integration.

### Connect Mealie and Home Assistant
Mealie and Home Assistant cannot by default communicate because they are not part of the same docker-compose.yml.
1. Run `docker network ls`, "homeassistant" should be one of the networks.
2. Run `docker network inspect homeassistant`, under "containers" there should be one container, Mealie. For Mealie and Home Assistant to communicate, both containers need to be on the same network.
3. Run `docker ps`, copy Home Assistant container id.
4. Run `docker network connect homeassistant [container id]`
5. Run `docker network inspect homeassistant` again. Both containers should be on the same network.

### Mealie integration
1. Install Mealie integration.
2. When installing the integration you will be asked for the API key, copy and paste your Mealie API key.
3. Set http://mealie:9000 as the Mealie url.
4. Leave "Verify connection" unchecked.
5. Click "Next".
6. The Mealie integration will test the connection. If a connection could be established the integration will be added.

### Add panels
By default the integration has no frontend components.
1. Clone https://github.com/AndreasWJ/group6-ui
2. Start Home Assistant.
3. Starting Home Assistant will create a config folder, /config.
4. Copy configuration.yaml into config/
5. Copy recipes-panel-99.js into config/www/
6. Copy ingredients-panel-15.js into config/www/
7. Restart Home Assistant.
8. You should now see panels "Recipes" and "Ingredients" in the left menu.
