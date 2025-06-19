#!/usr/bin/env python3
"""Example script to convert AWS CSV credentials to config files.

This script demonstrates how to use the csv_to_config function to convert
AWS CSV credential files to JSON or YAML configuration files for use with
the Fence AI S3 access system.
"""

import argparse
import os
import sys
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))  
from fence_ai.csv_config import csv_to_config


def main():
    """Convert AWS CSV credentials to a config file."""
    parser = argparse.ArgumentParser(
        description="Convert AWS CSV credentials to a config file"
    )
    parser.add_argument(
        "csv_path", 
        type=str,
        help="Path to the CSV file containing AWS credentials"
    )
    parser.add_argument(
        "output_path", 
        type=str,
        help="Path where the config file will be written"
    )
    parser.add_argument(
        "--format", 
        type=str, 
        choices=["json", "yaml"], 
        default="json",
        help="Output format (default: json)"
    )
    parser.add_argument(
        "--region", 
        type=str, 
        default="us-east-1",
        help="AWS region to use (default: us-east-1)"
    )
    parser.add_argument(
        "--insecure", 
        action="store_true",
        help="Do not set secure file permissions (0600)"
    )
    parser.add_argument(
        "--no-optional", 
        action="store_true",
        help="Exclude optional fields from the output"
    )
    parser.add_argument(
        "--indent", 
        type=int, 
        default=2,
        help="Indentation level for output (default: 2)"
    )
    parser.add_argument(
        "--endpoint-url", 
        type=str,
        help="Custom S3 endpoint URL (e.g., for LocalStack or MinIO)"
    )
    
    args = parser.parse_args()
    
    # Prepare additional parameters
    kwargs = {}
    if args.endpoint_url:
        kwargs["endpoint_url"] = args.endpoint_url
    
    try:
        output_path = csv_to_config(
            csv_path=args.csv_path,
            output_path=args.output_path,
            format=args.format,
            region=args.region,
            secure=not args.insecure,
            include_optional=not args.no_optional,
            indent=args.indent,
            **kwargs
        )
        print(f"Successfully generated {args.format} config at {output_path}")
        return 0
    except FileNotFoundError as e:
        print(f"Error: File not found: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"Error: Invalid input: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
