"""Utilities for saving workflow responses and generated images.

This module provides functions to save parsed workflow responses and 
their associated generated images to disk with proper session organization
and image versioning.
"""
from datetime import datetime
import json
import os
import base64
from pathlib import Path
from typing import Dict, Any, List, Optional

from invoker.response_parser import SuccessResponse, ErrorResponse, WorkflowResponse


def create_session_directory(session_prefix: str) -> Path:
    """Create a session directory under the outputs directory.
    
    Args:
        session_prefix: The session identifier to use for directory naming
        
    Returns:
        Path object pointing to the created session directory
    """
    # Create main outputs directory if it doesn't exist
    outputs_dir = Path("outputs")
    outputs_dir.mkdir(exist_ok=True)
    
    # Create session directory
    session_dir = outputs_dir / session_prefix
    session_dir.mkdir(exist_ok=True)
    
    return session_dir


def save_response(response: WorkflowResponse, session_dir: Path) -> Path:
    """Save the workflow response as JSON in the session directory.
    
    Args:
        response: The parsed workflow response
        session_dir: Path to the session directory
        
    Returns:
        Path to the saved response file
    """
    # Create response data structure with metadata
    response_data = {
        "timestamp": datetime.now().isoformat(),
        "type": "success" if isinstance(response, SuccessResponse) else "error",
    }
    
    # Add response-specific data
    if isinstance(response, SuccessResponse):
        response_data.update({
            "created": response.created,
            "execution_time": response.execution_time,
            "images_count": response.images_count,
            "size": response.size,
            "format": response.format,
            "quality": response.quality,
            "usage": {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.total_tokens,
                "text_tokens": response.usage.text_tokens,
                "image_tokens": response.usage.image_tokens
            }
        })
    else:
        response_data.update({
            "error": response.error,
            "error_timestamp": response.timestamp
        })
    
    # Save to file
    response_file = session_dir / "response.json"
    with open(response_file, 'w') as f:
        json.dump(response_data, f, indent=2)
    
    return response_file


def save_images(response: SuccessResponse, session_dir: Path) -> List[Path]:
    """Extract and save images from a successful response with versioning.
    
    Args:
        response: The successful workflow response containing images
        session_dir: Path to the session directory
        
    Returns:
        List of paths to the saved image files
    """
    saved_paths = []
    
    # Determine image format from response
    img_format = response.format.lower() if hasattr(response, 'format') and response.format else "png"
    
    # Process each image in the response
    if hasattr(response, 'data') and response.data:
        for i, img_data in enumerate(response.data, 1):
            if hasattr(img_data, 'b64_json') and img_data.b64_json:
                # Decode base64 image data
                image_bytes = base64.b64decode(img_data.b64_json)
                
                # Save with versioning
                image_path = session_dir / f"image_v{i}.{img_format}"
                with open(image_path, 'wb') as f:
                    f.write(image_bytes)
                
                saved_paths.append(image_path)
    
    # Also try the images list if data attribute is not available
    elif hasattr(response, 'images') and response.images:
        for i, img in enumerate(response.images, 1):
            if isinstance(img, dict) and 'b64_json' in img:
                # Decode base64 image data
                image_bytes = base64.b64decode(img['b64_json'])
                
                # Save with versioning
                image_path = session_dir / f"image_v{i}.{img_format}"
                with open(image_path, 'wb') as f:
                    f.write(image_bytes)
                
                saved_paths.append(image_path)
    
    return saved_paths


def save_workflow_output(response: WorkflowResponse, session_prefix: str) -> Dict[str, Any]:
    """Main function to save both response and images.
    
    Args:
        response: The parsed workflow response
        session_prefix: The session identifier
        
    Returns:
        Dictionary with paths and metadata about saved files
    """
    # Create session directory
    session_dir = create_session_directory(session_prefix)
    
    # Save response
    response_path = save_response(response, session_dir)
    
    # Save images if it's a success response
    image_paths = []
    if isinstance(response, SuccessResponse):
        image_paths = save_images(response, session_dir)
    
    # Return summary of what was saved
    return {
        "session_dir": str(session_dir),
        "response_file": str(response_path),
        "saved_images": [str(p) for p in image_paths],
        "image_count": len(image_paths),
        "timestamp": datetime.now().isoformat()
    }
