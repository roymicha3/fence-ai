# CSV to S3 Config Converter

This document describes the CSV to S3 Config Converter feature in the Fence AI project, which allows users to convert AWS CSV credential files to JSON or YAML configuration files for use with the Fence AI S3 access system.

## Overview

The CSV to S3 Config Converter provides a simple way to convert AWS CSV credential files (typically downloaded from the AWS IAM console) into configuration files that can be used with Fence AI's S3 access system. The converter supports:

- Multiple CSV formats with different header names
- Output in JSON or YAML format
- Customizable indentation and field inclusion
- Secure file permissions by default
- Additional AWS parameters like endpoint URLs

## Usage

### Programmatic API

```python
from fence_ai.csv_config import csv_to_config

# Basic usage
output_path = csv_to_config(
    csv_path="path/to/credentials.csv",
    output_path="path/to/output.json",
    format="json",
    region="us-east-1"
)

# With customization options
output_path = csv_to_config(
    csv_path="path/to/credentials.csv",
    output_path="path/to/output.yaml",
    format="yaml",
    region="us-west-2",
    include_optional=False,  # Exclude optional fields like aws_session_token and region_name
    indent=4,                # Use 4 spaces for indentation
    secure=True,             # Set secure file permissions (0600)
    endpoint_url="http://localhost:4566"  # Custom S3 endpoint URL
)
```

### Command-Line Interface

The `setup_s3_config.py` script in the `examples` directory provides a command-line interface for the converter:

```bash
./examples/setup_s3_config.py path/to/credentials.csv path/to/output.json --format json --region us-east-1
```

#### Available Options

- `csv_path`: Path to the CSV file containing AWS credentials (required)
- `output_path`: Path where the config file will be written (required)
- `--format`: Output format, either "json" or "yaml" (default: "json")
- `--region`: AWS region to use (default: "us-east-1")
- `--insecure`: Do not set secure file permissions (0600)
- `--no-optional`: Exclude optional fields from the output
- `--indent`: Indentation level for output (default: 2)
- `--endpoint-url`: Custom S3 endpoint URL (e.g., for LocalStack or MinIO)

## Supported CSV Formats

The converter supports various CSV formats with different header names:

- Standard AWS IAM CSV format: "Access key ID,Secret access key"
- Alternative formats with variations like "Access Key Id", "AccessKeyId", etc.
- CSV files with or without headers

## Integration with S3Access

The generated config files can be used directly with the `S3Access` class:

```python
from fence_ai.storage.s3_access import S3Access

# Initialize S3Access with the generated config
s3_access = S3Access(config_file="path/to/config.json")

# Use the S3Access instance to create clients and resources
s3_client = s3_access.client()
s3_resource = s3_access.resource()
```

## Security Considerations

- By default, the converter sets secure file permissions (0600) on generated config files on Unix-like systems
- Credentials are validated for required fields before file generation
- The converter handles sensitive data carefully and ensures secure file writing

## Dependencies

- Standard Python libraries: `csv`, `json`, `os`, `pathlib`, `typing`, `warnings`
- Optional dependency on `PyYAML` for YAML support (dynamically detected at runtime)
