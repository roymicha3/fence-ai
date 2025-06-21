
from pathlib import Path
from typing import Dict

from creds.csv_credentials_loader import CSVCredentialsLoader
from creds.env_credentials_loader import EnvCredentialsLoader

def load_credentials(source) -> Dict[str, str]:
    """Dispatch to the appropriate loader based on *source* type or suffix."""
    if source == "env":
        return EnvCredentialsLoader().load(source)

    path = Path(source)
    if path.suffix.lower() == ".csv":
        return CSVCredentialsLoader().load(path)
    raise ValueError(f"Unsupported credential source: {source}")
