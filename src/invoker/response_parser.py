from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

@dataclass
class TokenUsageDetails:
    """Detailed token usage breakdown"""
    cached_tokens: int = 0
    audio_tokens: int = 0
    reasoning_tokens: int = 0
    accepted_prediction_tokens: int = 0
    rejected_prediction_tokens: int = 0

@dataclass
class TokenUsage:
    """Token usage statistics"""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    prompt_tokens_details: TokenUsageDetails = field(default_factory=TokenUsageDetails)
    completion_tokens_details: TokenUsageDetails = field(default_factory=TokenUsageDetails)

@dataclass
class Message:
    """Chat message structure"""
    role: str
    content: str
    refusal: Optional[str] = None
    
    def get_content_preview(self, max_length: int = 100) -> str:
        """Get a preview of the message content"""
        if len(self.content) <= max_length:
            return self.content
        return self.content[:max_length] + "..."

@dataclass
class Choice:
    """Individual choice from the response"""
    index: int
    message: Message
    finish_reason: str
    logprobs: Optional[Dict[str, Any]] = None

@dataclass
class ArtifactInfo:
    """Custom artifact information"""
    artifact_content: Optional[str] = None
    artifact_name: Optional[str] = None
    artifact_path: Optional[str] = None
    analysis: Optional[str] = None

@dataclass
class OpenAIResponse:
    """Complete OpenAI API response structure"""
    id: str
    object: str
    created: int
    model: str
    choices: List[Choice]
    usage: TokenUsage
    system_fingerprint: str
    service_tier: str = "default"
    artifact_info: Optional[ArtifactInfo] = None
    
    @property
    def created_datetime(self) -> datetime:
        """Convert timestamp to datetime object"""
        return datetime.fromtimestamp(self.created)
    
    @property
    def created_iso(self) -> str:
        """Get creation time as ISO string"""
        return self.created_datetime.isoformat()
    
    @property
    def main_message(self) -> Optional[Message]:
        """Get the first (main) message from choices"""
        return self.choices[0].message if self.choices else None
    
    @property
    def main_content(self) -> str:
        """Get the content of the main message"""
        main_msg = self.main_message
        return main_msg.content if main_msg else ""
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of key response information"""
        return {
            "id": self.id,
            "model": self.model,
            "created": self.created_iso,
            "service_tier": self.service_tier,
            "total_tokens": self.usage.total_tokens,
            "prompt_tokens": self.usage.prompt_tokens,
            "completion_tokens": self.usage.completion_tokens,
            "message_length": len(self.main_content),
            "finish_reason": self.choices[0].finish_reason if self.choices else None,
            "has_artifact": self.artifact_info is not None
        }

class OpenAIResponseParser:
    """Parser for OpenAI API responses"""
    
    @staticmethod
    def parse_token_usage_details(data: Dict[str, Any]) -> TokenUsageDetails:
        """Parse token usage details"""
        return TokenUsageDetails(
            cached_tokens=data.get('cached_tokens', 0),
            audio_tokens=data.get('audio_tokens', 0),
            reasoning_tokens=data.get('reasoning_tokens', 0),
            accepted_prediction_tokens=data.get('accepted_prediction_tokens', 0),
            rejected_prediction_tokens=data.get('rejected_prediction_tokens', 0)
        )
    
    @staticmethod
    def parse_token_usage(data: Dict[str, Any]) -> TokenUsage:
        """Parse token usage information"""
        prompt_details = data.get('prompt_tokens_details', {})
        completion_details = data.get('completion_tokens_details', {})
        
        return TokenUsage(
            prompt_tokens=data.get('prompt_tokens', 0),
            completion_tokens=data.get('completion_tokens', 0),
            total_tokens=data.get('total_tokens', 0),
            prompt_tokens_details=OpenAIResponseParser.parse_token_usage_details(prompt_details),
            completion_tokens_details=OpenAIResponseParser.parse_token_usage_details(completion_details)
        )
    
    @staticmethod
    def parse_message(data: Dict[str, Any]) -> Message:
        """Parse message data"""
        return Message(
            role=data.get('role', ''),
            content=data.get('content', ''),
            refusal=data.get('refusal')
        )
    
    @staticmethod
    def parse_choice(data: Dict[str, Any]) -> Choice:
        """Parse choice data"""
        message_data = data.get('message', {})
        message = OpenAIResponseParser.parse_message(message_data)
        
        return Choice(
            index=data.get('index', 0),
            message=message,
            finish_reason=data.get('finish_reason', ''),
            logprobs=data.get('logprobs')
        )
    
    @staticmethod
    def parse_artifact_info(data: Dict[str, Any]) -> Optional[ArtifactInfo]:
        """Parse artifact information if present"""
        has_artifact_fields = any(
            field in data for field in ['artifact_content', 'artifact_name', 'artifact_path', 'analysis']
        )
        
        if not has_artifact_fields:
            return None
        
        return ArtifactInfo(
            artifact_content=data.get('artifact_content'),
            artifact_name=data.get('artifact_name'),
            artifact_path=data.get('artifact_path'),
            analysis=data.get('analysis')
        )
    
    @classmethod
    def parse(cls, response_json: Dict[str, Any]) -> OpenAIResponse:
        """
        Parse OpenAI response from JSON string
        
        Args:
            response_text: JSON string containing the response
            
        Returns:
            OpenAIResponse object
            
        Raises:
            ValueError: If parsing fails
        """
        try:
            
            # Parse choices
            choices_data = response_json.get('choices', [])
            choices = [cls.parse_choice(choice) for choice in choices_data]
            
            # Parse usage
            usage_data = response_json.get('usage', {})
            usage = cls.parse_token_usage(usage_data)
            
            # Parse artifact info
            artifact_info = cls.parse_artifact_info(response_json)
            
            # Create response object
            return OpenAIResponse(
                id=response_json.get('id', ''),
                object=response_json.get('object', ''),
                created=response_json.get('created', 0),
                model=response_json.get('model', ''),
                choices=choices,
                usage=usage,
                system_fingerprint=response_json.get('system_fingerprint', ''),
                service_tier=response_json.get('service_tier', 'default'),
                artifact_info=artifact_info
            )
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}")
        except Exception as e:
            raise ValueError(f"Parsing error: {e}")

def print_response_info(response: OpenAIResponse) -> None:
    """Print formatted information about the response"""
    print("=" * 50)
    print("OPENAI RESPONSE SUMMARY")
    print("=" * 50)
    
    # Basic info
    print(f"ID: {response.id}")
    print(f"Model: {response.model}")
    print(f"Created: {response.created_iso}")
    print(f"Service Tier: {response.service_tier}")
    print(f"System Fingerprint: {response.system_fingerprint}")
    
    # Token usage
    print(f"\nTOKEN USAGE:")
    print(f"  Prompt: {response.usage.prompt_tokens}")
    print(f"  Completion: {response.usage.completion_tokens}")
    print(f"  Total: {response.usage.total_tokens}")
    
    # Message info
    if response.main_message:
        msg = response.main_message
        print(f"\nMAIN MESSAGE:")
        print(f"  Role: {msg.role}")
        print(f"  Length: {len(msg.content)} characters")
        print(f"  Preview: {msg.get_content_preview(150)}")
        
        if response.choices:
            print(f"  Finish Reason: {response.choices[0].finish_reason}")
    
    # Artifact info
    if response.artifact_info:
        artifact = response.artifact_info
        print(f"\nARTIFACT INFO:")
        if artifact.artifact_name:
            print(f"  Name: {artifact.artifact_name}")
        if artifact.artifact_path:
            print(f"  Path: {artifact.artifact_path}")
        if artifact.analysis:
            print(f"  Has Analysis: Yes ({len(artifact.analysis)} chars)")
        if artifact.artifact_content:
            print(f"  Has Content: Yes ({len(artifact.artifact_content)} chars)")
