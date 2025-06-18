# Running Fence-AI with Docker Compose

## Build the Docker image
```
docker compose build
```

## Start a container with an interactive shell
```
docker compose run --rm fence-ai
```

## Run tests inside the container
```
docker compose run --rm fence-ai pytest
```

## Notes
- The container mounts your local project directory, so changes on your host are reflected inside the container.
- You can add more services (e.g., databases) to `docker-compose.yml` as needed.
