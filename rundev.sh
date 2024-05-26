#!/bin/bash

# Load .env file from current directory
if [ -f .env ]; then
    echo "Loading .env file from current directory"
    export $(cat .env | sed 's/#.*//g' | xargs)
fi

docker-compose -f docker-compose.dev.yml down

docker-compose -f docker-compose.dev.yml up

sleep 100

