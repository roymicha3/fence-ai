from dataclasses import dataclass
from typing import List, Optional, Union
import json
from datetime import datetime


@dataclass
class ErrorResponse:
    success: bool
    error: str
    timestamp: Optional[str] = None
    status_code: Optional[int] = None
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ErrorResponse':
        # Handle various error response formats gracefully
        current_time = datetime.now().isoformat()
        
        return cls(
            success=data.get('success', False),
            error=data.get('error', data.get('message', 'Unknown error')),
            timestamp=data.get('timestamp', current_time),
            status_code=data.get('status_code')
        )


@dataclass
class Usage:
    input_tokens: int
    output_tokens: int
    total_tokens: int
    text_tokens: Optional[int] = None
    image_tokens: Optional[int] = None
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Usage':
        input_details = data.get('input_tokens_details', {})
        return cls(
            input_tokens=data['input_tokens'],
            output_tokens=data['output_tokens'],
            total_tokens=data['total_tokens'],
            text_tokens=input_details.get('text_tokens'),
            image_tokens=input_details.get('image_tokens')
        )


@dataclass
class GeneratedImage:
    b64_json: str
    
    @classmethod
    def from_dict(cls, data: dict) -> 'GeneratedImage':
        return cls(b64_json=data['b64_json'])


@dataclass
class ImageEditResponse:
    created: int
    data: List[GeneratedImage]
    usage: Usage
    background: str = "opaque"
    output_format: str = "png"
    quality: str = "high"
    size: str = "1536x1024"
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ImageEditResponse':
        return cls(
            created=data['created'],
            data=[GeneratedImage.from_dict(img) for img in data['data']],
            usage=Usage.from_dict(data['usage']),
            background=data.get('background', 'opaque'),
            output_format=data.get('output_format', 'png'),
            quality=data.get('quality', 'high'),
            size=data.get('size', '1536x1024')
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> 'ImageEditResponse':
        return cls.from_dict(json.loads(json_str))
    
    def to_dict(self) -> dict:
        return {
            'created': self.created,
            'background': self.background,
            'output_format': self.output_format,
            'quality': self.quality,
            'size': self.size,
            'images_count': len(self.data),
            'usage': {
                'input_tokens': self.usage.input_tokens,
                'output_tokens': self.usage.output_tokens,
                'total_tokens': self.usage.total_tokens,
                'text_tokens': self.usage.text_tokens,
                'image_tokens': self.usage.image_tokens
            }
        }


@dataclass
class SuccessResponse:
    success: bool
    execution_time: float
    images_count: int
    created: int
    size: str
    format: str
    quality: str
    usage: Usage
    images: List[dict]
    
    @classmethod
    def from_dict(cls, data: dict) -> 'SuccessResponse':
        return cls(
            success=data['success'],
            execution_time=data['execution_time'],
            images_count=data['images_count'],
            created=data['created'],
            size=data['size'],
            format=data['format'],
            quality=data['quality'],
            usage=Usage.from_dict(data['usage']),
            images=data['images']
        )


# Response type union
WorkflowResponse = Union[SuccessResponse, ErrorResponse]


def parse_workflow_response(response: str | dict) -> WorkflowResponse:
    """Parse n8n workflow response into appropriate data class.
    
    Args:
        response: Either a JSON string or an already parsed dictionary
    
    Returns:
        WorkflowResponse: Parsed response as either SuccessResponse or ErrorResponse
    """
    # Handle both string and dictionary inputs
    if isinstance(response, str):
        data = json.loads(response)
    else:
        data = response
    
    if data.get('success', True):  # Default to success if field missing
        return SuccessResponse.from_dict(data)
    else:
        return ErrorResponse.from_dict(data)


# Utility functions
def print_workflow_response(response: WorkflowResponse) -> None:
    """Print formatted information about the workflow response."""
    print("=" * 50)
    print("WORKFLOW RESPONSE SUMMARY")
    print("=" * 50)
    
    if isinstance(response, ErrorResponse):
        print("Status: ERROR")
        print(f"Error message: {response.error}")
        print(f"Timestamp: {response.timestamp}")
    elif isinstance(response, SuccessResponse):
        print("Status: SUCCESS")
        
        # Handle potentially None values with safe formatting
        if response.execution_time is not None:
            print(f"Execution time: {response.execution_time:.2f}s")
        else:
            print("Execution time: Not available")
            
        if response.created is not None:
            created_dt = datetime.fromtimestamp(response.created)
            print(f"Created: {created_dt.strftime('%Y-%m-%d %H:%M:%S %Z')}")
            
        if response.images_count is not None:
            print(f"Images generated: {response.images_count}")
            
        # Handle format, quality, size attributes which might be None
        format_str = getattr(response, 'format', 'unknown')
        quality_str = getattr(response, 'quality', 'unknown')
        size_str = getattr(response, 'size', 'unknown')
        print(f"Output format: {format_str}, {quality_str} quality, {size_str}")
        
        # Handle usage information if available
        if response.usage is not None:
            print(f"\nTOKEN USAGE:")
            print(f"  Input tokens: {response.usage.input_tokens if response.usage.input_tokens is not None else 'N/A'}")
            print(f"  Output tokens: {response.usage.output_tokens if response.usage.output_tokens is not None else 'N/A'}")
            print(f"  Total tokens: {response.usage.total_tokens if response.usage.total_tokens is not None else 'N/A'}")
            
            if response.usage.text_tokens is not None:
                print(f"  Text tokens: {response.usage.text_tokens}")
            if response.usage.image_tokens is not None:
                print(f"  Image tokens: {response.usage.image_tokens}")


# Usage example:
def parse_openai_response(response_json: str) -> ImageEditResponse:
    """Parse OpenAI image edit response into structured data."""
    return ImageEditResponse.from_json(response_json)