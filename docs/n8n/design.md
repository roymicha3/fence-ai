# N8N Workflow Invoker Module - Design Document

## Architecture Overview

The module follows a layered architecture with clear separation of concerns, inspired by enterprise Python projects like Apache Airflow and Celery.

```
┌─────────────────────────────────────────────────┐
│                 Client Layer                    │
├─────────────────────────────────────────────────┤
│              Workflow Manager                   │
├─────────────────────────────────────────────────┤
│         Invoker Abstraction Layer              │
├─────────────────────────────────────────────────┤
│    HTTP Invoker │ Future: Webhook │ Future: WS  │
├─────────────────────────────────────────────────┤
│            Tracing & Monitoring                 │
├─────────────────────────────────────────────────┤
│         Hooks & Plugin System                   │
├─────────────────────────────────────────────────┤
│            Configuration Layer                  │
└─────────────────────────────────────────────────┘
```

## Core Components

### 1. Base Invoker Interface
Abstract base class defining the contract for all workflow invokers, ensuring extensibility.

### 2. HTTP Invoker Implementation
Concrete implementation for HTTP-based n8n workflow invocation with:
- Retry logic with exponential backoff
- Connection pooling
- Request/response validation
- Authentication handling

### 3. Workflow Manager
High-level orchestrator that:
- Manages workflow lifecycle
- Coordinates invokers and tracers
- Handles error recovery
- Provides unified API

### 4. Tracing System
Comprehensive monitoring with:
- Execution tracking
- Progress reporting
- Performance metrics
- Error classification

### 5. Hook System
Plugin architecture for:
- Pre/post execution hooks
- Custom error handlers
- Metrics collectors
- Notification systems

## Key Design Principles

### Modularity
- Each component has a single responsibility
- Clear interfaces between layers
- Pluggable architecture

### Extensibility
- Abstract base classes for easy extension
- Hook system for custom functionality
- Configuration-driven behavior

### Robustness
- Comprehensive error handling
- Retry mechanisms
- Circuit breaker pattern
- Graceful degradation

### Observability
- Structured logging
- Distributed tracing
- Metrics collection
- Health checks

## Configuration Schema

```yaml
n8n:
  base_url: "https://n8n.example.com"
  api_key: "${N8N_API_KEY}"
  timeout: 30
  
invokers:
  http:
    max_retries: 3
    backoff_factor: 2.0
    pool_connections: 10
    pool_maxsize: 20
    
tracing:
  enabled: true
  backend: "opentelemetry"
  sample_rate: 1.0
  
hooks:
  pre_execution:
    - "logging_hook"
    - "metrics_hook"
  post_execution:
    - "cleanup_hook"
  error:
    - "notification_hook"
```

## API Usage Examples

### Basic Workflow Execution
```python
from n8n_invoker import WorkflowManager

manager = WorkflowManager.from_config("config.yaml")
result = await manager.execute_workflow(
    workflow_id="user-onboarding",
    parameters={"email": "user@example.com", "plan": "premium"}
)
```

### Advanced Usage with Custom Hooks
```python
class CustomMetricsHook(ExecutionHook):
    async def pre_execution(self, context):
        # Custom metrics logic
        pass

manager.register_hook("pre_execution", CustomMetricsHook())
```

### Batch Execution
```python
workflows = [
    {"id": "workflow-1", "params": {"user_id": 1}},
    {"id": "workflow-2", "params": {"user_id": 2}},
]

results = await manager.execute_batch(workflows, max_concurrent=5)
```

## Error Handling Strategy

### Error Classification
- **Transient Errors**: Network timeouts, rate limits (retry)
- **Permanent Errors**: Invalid workflow ID, auth failures (fail fast)
- **Unknown Errors**: Unexpected responses (retry with caution)

### Recovery Mechanisms
- Exponential backoff with jitter
- Circuit breaker for failing endpoints
- Dead letter queue for failed executions
- Manual retry capabilities

## Extension Points

### Custom Invokers
```python
class WebSocketInvoker(BaseInvoker):
    async def invoke(self, workflow_id, parameters):
        # WebSocket implementation
        pass
```

### Custom Tracers
```python
class DatabaseTracer(BaseTracer):
    async def track_execution(self, execution):
        # Database persistence
        pass
```

### Plugin System
```python
class SlackNotificationPlugin(Plugin):
    def on_workflow_failed(self, context):
        # Send Slack notification
        pass
```

## Security Considerations

- API key rotation support
- Request signing for webhooks
- TLS certificate validation
- Secrets management integration
- Rate limiting compliance

## Performance Features

- Connection pooling and reuse
- Async/await throughout
- Batch processing capabilities
- Caching of workflow metadata
- Resource usage monitoring

## Testing Strategy

- Unit tests for each component
- Integration tests with n8n instance
- Performance benchmarks
- Chaos engineering tests
- Contract testing for API compatibility