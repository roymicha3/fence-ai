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

---

## Quick-Start API Usage

```python
from pathlib import Path
from fence_ai.s3_access import S3Access
from fence_ai.s3_manager import S3DataManager

access = S3Access()  # credentials resolved automatically (env vars, files, etc.)
manager = S3DataManager(access)

bucket = "my-bucket"
key = "samples/hello.txt"
local_file = Path("hello.txt")

# upload
manager.upload(bucket, key, local_file)

# list
print(manager.list_objects(bucket, prefix="samples/"))

# download
manager.download(bucket, key, Path("downloaded.txt"))

# delete
manager.delete(bucket, key)
```

A runnable script is available in `examples/s3_usage.py`.

### Configuration options

`S3Access` reads credentials and settings with the following precedence:

1. **Defaults** passed to `Config` or `S3Access` constructor
2. **Configuration files** (`.json`, `.yaml`) passed to `Config(files=[...])`
3. **Environment variables** – by default `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, etc.
4. **Runtime overrides** when calling `client()` / `resource()`

See `fence_ai/config_core.py` for full details.

### Logging

The project uses a centralised logger (`fence_ai.logger`).
Set environment variables to control output:

```bash
export FENCE_LOG_LEVEL=DEBUG   # DEBUG|INFO|WARNING|ERROR|CRITICAL
export FENCE_LOG_FORMAT=plain  # plain|color|json (detects optional deps)
```

---