#!/bin/bash

if [ -f .env ]; then
    echo "Loading .env file"
    export $(cat .env | sed 's/#.*//g' | xargs)
fi

docker-compose -f docker-compose.dev.yml down

docker-compose -f docker-compose.dev.yml up

sleep 100

# THEN RUN:
# cd frontend
# npm install # if you haven't already
# npm run dev