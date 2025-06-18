import shutil
import subprocess
import pytest

DOCKER_SERVICE = "fence-ai"
TIMEOUT = 60  # seconds for potentially slow CI environments

def is_docker_available() -> bool:
    """Return True if the `docker` CLI exists and the daemon is reachable."""
    docker_path = shutil.which("docker")
    if docker_path is None:
        return False
    try:
        subprocess.run([docker_path, "info"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return True
    except Exception:
        return False

def _container_id() -> str:
    """Return the container ID for the compose service (empty str if none)."""
    result = subprocess.run(
        ["docker-compose", "ps", "-q", DOCKER_SERVICE], capture_output=True, text=True
    )
    return result.stdout.strip()


def test_docker_lifecycle():
    """Full integration-style check: create, verify running, exec cmd, and shutdown."""

    if not is_docker_available():
        pytest.skip("Docker unavailable – skipping Docker lifecycle test.")

    # 1. Start the service in detached mode
    subprocess.run(
        ["docker-compose", "up", "-d", DOCKER_SERVICE], check=True, timeout=TIMEOUT
    )

    # 2. Verify container was created
    cid = _container_id()
    assert cid, "Docker container was not created by docker-compose up."

    # 3. Verify container is running
    inspect = subprocess.check_output(
        ["docker", "inspect", "-f", "{{.State.Running}}", cid]
    ).decode().strip()
    assert inspect == "true", "Docker container is not in a running state."

    # 4. Run a trivial Python command inside the container
    exec_result = subprocess.run(
        [
            "docker-compose",
            "exec",
            "-T",
            DOCKER_SERVICE,
            "python",
            "-c",
            "print('Hello from Docker!')",
        ],
        capture_output=True,
        text=True,
        timeout=TIMEOUT,
    )
    assert exec_result.returncode == 0, f"docker-compose exec failed: {exec_result.stderr}"
    assert "Hello from Docker!" in exec_result.stdout

    # 5. Stop and remove the service
    subprocess.run(["docker-compose", "down"], check=True, timeout=TIMEOUT)

    # 6. Confirm the container is no longer present
    assert _container_id() == "", "Docker container still exists after docker-compose down."
