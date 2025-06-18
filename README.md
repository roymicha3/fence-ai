# fence-ai

## Running Tests on WSL

To run the tests on WSL, ensure the following:

1. **Activate the Python virtual environment** (venv):

    ```sh
    source venv/bin/activate
    ```

2. **Ensure Docker is installed and available** in your WSL environment. You can check this by running:

    ```sh
    docker --version
    ```

   If Docker is not available, see the troubleshooting note below.

3. **Run the tests** using pytest:

    ```sh
    pytest
    ```

### Troubleshooting Docker on WSL

- If you see a message such as `Docker is not available in this environment. Skipping Docker integration tests.`, make sure Docker Desktop is running and that WSL integration is enabled for your distribution.
- You may need to restart Docker Desktop or your WSL terminal after enabling integration.
- For more info, see: [Docker Desktop WSL 2 backend docs](https://docs.docker.com/desktop/wsl/)