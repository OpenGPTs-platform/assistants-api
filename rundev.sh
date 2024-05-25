#!/bin/bash

# Load .env file from current directory
if [ -f .env ]; then
    echo "Loading .env file from current directory"
    export $(cat .env | sed 's/#.*//g' | xargs)
fi

# Load .env file from HEXAMOROUS_RELATIVE_PATH
if [ -f "${HEXAMOROUS_RELATIVE_PATH}/.env" ]; then
    echo "Loading .env file from ${HEXAMOROUS_RELATIVE_PATH}"
    export $(cat "${HEXAMOROUS_RELATIVE_PATH}/.env" | sed 's/#.*//g' | xargs)
fi

docker-compose -f docker-compose.dev.yml down

docker-compose -f docker-compose.dev.yml up

sleep 100

