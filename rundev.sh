#!/bin/bash

# Load .env file from current directory
if [ -f .env ]; then
    echo "Loading .env file from current directory"
    export $(cat .env | sed 's/#.*//g' | xargs)
fi

# Set Docker Compose HTTP timeout
export COMPOSE_HTTP_TIMEOUT=200

# Function to bring up Docker Compose with retries
function start_docker_compose {
    local retries=3
    local count=0

    while [ $count -lt $retries ]; do
        docker-compose -f docker-compose.dev.yml down
        docker-compose -f docker-compose.dev.yml up
        if [ $? -eq 0 ]; then
            echo "Docker Compose started successfully"
            return 0
        else
            echo "Error starting Docker Compose, retrying... ($((count+1))/$retries)"
            count=$((count+1))
            sleep 10
        fi
    done

    echo "Failed to start Docker Compose after $retries attempts"
    return 1
}

# Start Docker Compose with retries
if start_docker_compose; then
    # Sleep for a specified duration to allow services to initialize
    sleep 100
    # Show the logs and follow them
    docker-compose -f docker-compose.dev.yml logs -f
else
    echo "Exiting script due to failure in starting Docker Compose."
    exit 1
fi
