# fence-ai

## Running and Testing with Docker Compose

All development and test operations now run entirely in Docker. The host no longer needs a local Python virtual environment.

1. **Build the Docker image**

   ```sh
   docker compose build
   ```

2. **Run an interactive shell inside the container** (mounts the project directory):

   ```sh
   docker compose run --rm fence-ai
   ```

3. **Run the test suite** from inside the container (or pass the command directly):

   ```sh
   docker compose run --rm fence-ai pytest
   ```

### Docker requirements

Make sure you have Docker Desktop (or the Docker Engine/CLI) installed and running. For WSL users, enable WSL 2 integration in Docker Desktop and restart your terminal after changing settings.

The container mounts your local project folder, so edits on the host are immediately reflected inside the container.