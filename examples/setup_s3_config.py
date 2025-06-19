"""Example script showing how to convert AWS CSV credentials to config files.

This script demonstrates how to use the fence-ai CSV to S3 config converter
to generate configuration files from AWS CSV credential exports.

Usage:
    python setup_s3_config.py --input=path/to/credentials.csv --output=path/to/config.json

Run with --help for more options.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from fence_ai.csv_config import csv_to_config
from fence_ai.core.logger import get_logger

logger = get_logger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Convert AWS CSV credentials to a config file for fence-ai"
    )
    parser.add_argument(
        "--input", "-i", 
        required=True,
        help="Path to the AWS CSV credentials file"
    )
    parser.add_argument(
        "--output", "-o", 
        required=True,
        help="Path where the config file will be written"
    )
    parser.add_argument(
        "--format", "-f", 
        choices=["json", "yaml"], 
        default="json",
        help="Output format (default: json)"
    )
    parser.add_argument(
        "--region", "-r", 
        default="us-east-1",
        help="AWS region to use (default: us-east-1)"
    )
    parser.add_argument(
        "--secure", "-s", 
        action="store_true",
        help="Set secure file permissions on the output file"
    )
    
    return parser.parse_args()


def main() -> int:
    """Run the CSV to config converter."""
    args = parse_args()
    
    try:
        input_path = Path(args.input)
        output_path = Path(args.output)
        
        logger.info("Converting %s to %s", input_path, output_path)
        
        config_path = csv_to_config(
            input_path,
            output_path,
            format=args.format,
            region=args.region,
            secure=args.secure
        )
        
        logger.info("Successfully created config file at %s", config_path)
        return 0
    except FileNotFoundError as e:
        logger.error("File not found: %s", e)
        return 1
    except ValueError as e:
        logger.error("Invalid input: %s", e)
        return 1
    except Exception as e:
        logger.exception("Unexpected error: %s", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
