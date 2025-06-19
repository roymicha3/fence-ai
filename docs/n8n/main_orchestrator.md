"""
Workflow Manager - Main Orchestrator
====================================

High-level workflow management with hook system, tracing, and batch processing.
"""

import asyncio
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional, Sequence, Type, Union
import yaml
from dataclasses import asdict

from .core_api import (
    BaseInvoker, BaseTracer, ExecutionHook, WorkflowExecution,
    ExecutionStatus, InvokerConfig, HTTPInvoker, StructuredTracer,
    LoggingHook, N8NError
)


class WorkflowManager:
    """
    High-level workflow manager that orchestrates invokers, tracers, and hooks.
    
    This is the main entry point for users of the library, providing a clean
    API for workflow execution while handling all the complexity internally.
    """
    
    def __init__(
        self,
        invoker: BaseInvoker,
        tracer: Optional[BaseTracer] = None,
        hooks: Optional[Dict[str, List[ExecutionHook]]] = None
    ):
        """
        Initialize the workflow manager.
        
        Args:
            invoker: The workflow invoker to use
            tracer: Optional tracer for execution monitoring
            hooks: Optional hooks organized by execution phase
        """
        self.invoker = invoker
        self.tracer = tracer or StructuredTracer()
        self.hooks = hooks or {"pre_execution": [], "post_execution": [], "error": [], "retry": []}
        
        # Add default logging hook if no hooks provided
        if not any(self.hooks.values()):
            self.register_hook("pre_execution", LoggingHook())
            self.register_hook("post_execution", LoggingHook())
            self.register_hook("error", LoggingHook())
            self.register_hook("retry", LoggingHook())
    
    @classmethod
    def from_config(cls, config_path: str) -> 'WorkflowManager':
        """
        Create a WorkflowManager from a configuration file.
        
        Args:
            config_path: Path to YAML configuration file
            
        Returns:
            Configured WorkflowManager instance
        """
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Create invoker config
        n8n_config = config.get('n8n', {})
        invoker_config = config.get('invokers', {}).get('http', {})
        
        invoker_cfg = InvokerConfig(
            base_url=n8n_config.get('base_url'),
            api_key=n8n_config.get('api_key'),
            timeout=n8n_config.get('timeout', 30),
            max_retries=invoker_config.get('max_retries', 3),
            backoff_factor=invoker_config.get('backoff_factor', 2.0),
            max_concurrent=invoker_config.get('max_concurrent', 10)
        )
        
        # Create components
        invoker = HTTPInvoker(invoker_cfg)
        tracer = StructuredTracer()
        
        return cls(invoker=invoker, tracer=tracer)
    
    def register_hook(self, phase: str, hook: ExecutionHook) -> None:
        """
        Register a hook for a specific execution phase.
        
        Args:
            phase: Execution phase (pre_execution, post_execution, error, retry)
            hook: Hook instance to register
        """
        if phase not in self.hooks:
            self.hooks[phase] = []
        self.hooks[phase].append(hook)
    
    async def execute_workflow(
        self,
        workflow_id: str,
        parameters: Optional[Dict[str, Any]] = None,
        execution_id: Optional[str] = None
    ) -> WorkflowExecution:
        """
        Execute a single workflow.
        
        Args:
            workflow_id: ID of the workflow to execute
            parameters: Parameters to pass to the workflow
            execution_id: Optional custom execution ID
            
        Returns:
            Completed WorkflowExecution with results or error information
            
        Raises:
            N8NError: For various execution errors
        """
        execution = WorkflowExecution(
            id=execution_id or WorkflowExecution().id,
            workflow_id=workflow_id,
            parameters=parameters or {}
        )
        
        return await self._execute_single(execution)
    
    async def execute_batch(
        self,
        workflows: Sequence[Dict[str, Any]],
        max_concurrent: Optional[int] = None
    ) -> List[WorkflowExecution]:
        """
        Execute multiple workflows concurrently.
        
        Args:
            workflows: List of workflow specs with 'id' and 'params' keys
            max_concurrent: Maximum concurrent executions (defaults to invoker config)
            
        Returns:
            List of completed WorkflowExecutions
        """
        if max_concurrent is None:
            max_concurrent = getattr(self.invoker.config, 'max_concurrent', 10)
        
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def execute_with_semaphore(workflow_spec: Dict[str, Any]) -> WorkflowExecution:
            async with semaphore:
                execution = WorkflowExecution(
                    workflow_id=workflow_spec['id'],
                    parameters=workflow_spec.get('params', {})
                )
                return await self._execute_single(execution)
        
        tasks = [execute_with_semaphore(spec) for spec in workflows]
        return await asyncio.gather(*tasks, return_exceptions=False)
    
    async def get_execution_status(self, execution_id: str) -> ExecutionStatus:
        """
        Get the current status of a workflow execution.
        
        Args:
            execution_id: The execution ID to check
            
        Returns:
            Current execution status
        """
        return await self.invoker.get_status(execution_id)
    
    async def cancel_execution(self, execution_id: str) -> bool:
        """
        Cancel a running workflow execution.
        
        Args:
            execution_id: The execution ID to cancel
            
        Returns:
            True if cancellation was successful
        """
        return await self.invoker.cancel(execution_id)
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform a comprehensive health check.
        
        Returns:
            Health check results including component status
        """
        try:
            invoker_healthy = await self.invoker.health_check()
            return {
                "healthy": invoker_healthy,
                "components": {
                    "invoker": invoker_healthy,
                    "tracer": True,  # Tracer is always healthy
                    "hooks": len(sum(self.hooks.values(), []))
                }
            }
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
                "components": {
                    "invoker": False,
                    "tracer": True,
                    "hooks": len(sum(self.hooks.values(), []))
                }
            }
    
    async def _execute_single(self, execution: WorkflowExecution) -> WorkflowExecution:
        """
        Execute a single workflow with full hook and tracing support.
        
        Args:
            execution: The execution context
            
        Returns:
            Completed execution with results or error information
        """
        # Start tracing
        await self.tracer.start_trace(execution)
        
        try:
            # Pre-execution hooks
            for hook in self.hooks.get("pre_execution", []):
                execution = await hook.pre_execution(execution)
            
            # Execute the workflow
            execution = await self.invoker.invoke(execution)
            
            # Post-execution hooks (only on success)
            if execution.status == ExecutionStatus.SUCCESS:
                for hook in self.hooks.get("post_execution", []):
                    execution = await hook.post_execution(execution)
            
            # Update trace with final state
            await self.tracer.update_trace(execution)
            
            return execution
            
        except Exception as e:
            # Update execution with error
            execution = execution.with_status(ExecutionStatus.FAILED)
            execution.error = str(e)
            execution.completed_at = execution.completed_at or time.time()
            
            # Error hooks
            for hook in self.hooks.get("error", []):
                execution = await hook.on_error(execution, e)
            
            # Update trace with error
            await self.tracer.update_trace(execution)
            
            # Re-raise the exception
            raise
            
        finally:
            # End tracing
            await self.tracer.end_trace(execution)
    
    @asynccontextmanager
    async def session(self):
        """
        Async context manager for managing invoker lifecycle.
        
        Usage:
            async with manager.session():
                result = await manager.execute_workflow("my-workflow")
        """
        if hasattr(self.invoker, '__aenter__'):
            async with self.invoker:
                yield self
        else:
            yield self
    
    async def close(self):
        """Close all resources."""
        if hasattr(self.invoker, 'close'):
            await self.invoker.close()


# ============================================================================
# Workflow Manager Builder
# ============================================================================

class WorkflowManagerBuilder:
    """
    Builder pattern for creating WorkflowManager instances with custom configurations.
    
    Provides a fluent API for building complex workflow managers with custom
    invokers, tracers, and hooks.
    """
    
    def __init__(self):
        self._invoker: Optional[BaseInvoker] = None
        self._tracer: Optional[BaseTracer] = None
        self._hooks: Dict[str, List[ExecutionHook]] = {
            "pre_execution": [], "post_execution": [], "error": [], "retry": []
        }
    
    def with_http_invoker(self, config: InvokerConfig) -> 'WorkflowManagerBuilder':
        """Add HTTP invoker with configuration."""
        self._invoker = HTTPInvoker(config)
        return self
    
    def with_custom_invoker(self, invoker: BaseInvoker) -> 'WorkflowManagerBuilder':
        """Add custom invoker implementation."""
        self._invoker = invoker
        return self
    
    def with_tracer(self, tracer: BaseTracer) -> 'WorkflowManagerBuilder':
        """Add custom tracer."""
        self._tracer = tracer
        return self
    
    def with_hook(self, phase: str, hook: ExecutionHook) -> 'WorkflowManagerBuilder':
        """Add a hook for specific execution phase."""
        if phase not in self._hooks:
            self._hooks[phase] = []
        self._hooks[phase].append(hook)
        return self
    
    def with_logging_hooks(self) -> 'WorkflowManagerBuilder':
        """Add default logging hooks for all phases."""
        logging_hook = LoggingHook()
        return (self
                .with_hook("pre_execution", logging_hook)
                .with_hook("post_execution", logging_hook)
                .with_hook("error", logging_hook)
                .with_hook("retry", logging_hook))
    
    def build(self) -> WorkflowManager:
        """
        Build the WorkflowManager instance.
        
        Returns:
            Configured WorkflowManager
            
        Raises:
            ValueError: If required components are missing
        """
        if not self._invoker:
            raise ValueError("Invoker is required")
        
        return WorkflowManager(
            invoker=self._invoker,
            tracer=self._tracer,
            hooks=self._hooks if any(self._hooks.values()) else None
        )


# ============================================================================
# Utility Functions
# ============================================================================

def create_http_manager(
    base_url: str,
    api_key: Optional[str] = None,
    **kwargs
) -> WorkflowManager:
    """
    Convenience function to create a basic HTTP-based WorkflowManager.
    
    Args:
        base_url: N8N base URL
        api_key: Optional API key for authentication
        **kwargs: Additional configuration options
        
    Returns:
        Configured WorkflowManager
    """
    config = InvokerConfig(
        base_url=base_url,
        api_key=api_key,
        **kwargs
    )
    
    return (WorkflowManagerBuilder()
            .with_http_invoker(config)
            .with_logging_hooks()
            .build())


async def execute_workflow_simple(
    base_url: str,
    workflow_id: str,
    parameters: Optional[Dict[str, Any]] = None,
    api_key: Optional[str] = None
) -> WorkflowExecution:
    """
    Simple function to execute a workflow with minimal setup.
    
    Args:
        base_url: N8N base URL
        workflow_id: Workflow to execute
        parameters: Workflow parameters
        api_key: Optional API key
        
    Returns:
        Completed WorkflowExecution
    """
    manager = create_http_manager(base_url, api_key)
    
    async with manager.session():
        return await manager.execute_workflow(workflow_id, parameters)


# ============================================================================
# Advanced Hook Examples
# ============================================================================

class MetricsHook(ExecutionHook):
    """
    Example hook for collecting execution metrics.
    
    In a real implementation, this would integrate with metrics systems
    like Prometheus, StatsD, or cloud monitoring services.
    """
    
    def __init__(self, metrics_client=None):
        self.metrics_client = metrics_client
        self.executions = {}
    
    async def pre_execution(self, execution: WorkflowExecution) -> WorkflowExecution:
        """Record execution start metrics."""
        self.executions[execution.id] = {
            "start_time": time.time(),
            "workflow_id": execution.workflow_id
        }
        
        if self.metrics_client:
            # Example: increment counter
            self.metrics_client.increment("workflow.executions.started", 
                                        tags={"workflow_id": execution.workflow_id})
        
        return execution
    
    async def post_execution(self, execution: WorkflowExecution) -> WorkflowExecution:
        """Record execution completion metrics."""
        if execution.id in self.executions and self.metrics_client:
            duration = execution.duration or 0
            
            # Example: record timing
            self.metrics_client.timing("workflow.executions.duration", 
                                     duration * 1000,  # Convert to ms
                                     tags={"workflow_id": execution.workflow_id})
            
            # Example: increment success counter
            self.metrics_client.increment("workflow.executions.success",
                                        tags={"workflow_id": execution.workflow_id})
        
        return execution
    
    async def on_error(self, execution: WorkflowExecution, error: Exception) -> WorkflowExecution:
        """Record error metrics."""
        if self.metrics_client:
            self.metrics_client.increment("workflow.executions.error",
                                        tags={
                                            "workflow_id": execution.workflow_id,
                                            "error_type": type(error).__name__
                                        })
        
        return execution


class CircuitBreakerHook(ExecutionHook):
    """
    Example circuit breaker hook to prevent cascading failures.
    
    This implements a simple circuit breaker pattern that can prevent
    executing workflows when they're consistently failing.
    """
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_counts = {}
        self.circuit_states = {}
        self.last_failure_times = {}
    
    async def pre_execution(self, execution: WorkflowExecution) -> WorkflowExecution:
        """Check circuit breaker state before execution."""
        workflow_id = execution.workflow_id
        
        # Check if circuit is open
        if self._is_circuit_open(workflow_id):
            # Check if we should attempt recovery
            if self._should_attempt_recovery(workflow_id):
                self.circuit_states[workflow_id] = "half-open"
            else:
                raise N8NError(f"Circuit breaker is open for workflow {workflow_id}")
        
        return execution
    
    async def post_execution(self, execution: WorkflowExecution) -> WorkflowExecution:
        """Reset circuit breaker on successful execution."""
        workflow_id = execution.workflow_id
        
        # Reset failure count on success
        self.failure_counts[workflow_id] = 0
        self.circuit_states[workflow_id] = "closed"
        
        return execution
    
    async def on_error(self, execution: WorkflowExecution, error: Exception) -> WorkflowExecution:
        """Update circuit breaker state on error."""
        workflow_id = execution.workflow_id
        
        # Increment failure count
        self.failure_counts[workflow_id] = self.failure_counts.get(workflow_id, 0) + 1
        self.last_failure_times[workflow_id] = time.time()
        
        # Open circuit if threshold exceeded
        if self.failure_counts[workflow_id] >= self.failure_threshold:
            self.circuit_states[workflow_id] = "open"
        
        return execution
    
    def _is_circuit_open(self, workflow_id: str) -> bool:
        """Check if circuit is open for a workflow."""
        return self.circuit_states.get(workflow_id, "closed") == "open"
    
    def _should_attempt_recovery(self, workflow_id: str) -> bool:
        """Check if we should attempt recovery from open circuit."""
        last_failure = self.last_failure_times.get(workflow_id, 0)
        return time.time() - last_failure > self.recovery_timeout


# ============================================================================
# Example Usage and Integration
# ============================================================================

async def example_usage():
    """
    Example usage demonstrating various features of the workflow manager.
    """
    import time
    
    # Method 1: Simple usage
    print("=== Simple Usage ===")
    result = await execute_workflow_simple(
        base_url="https://n8n.example.com",
        workflow_id="user-onboarding",
        parameters={"email": "user@example.com", "plan": "premium"},
        api_key="your-api-key"
    )
    print(f"Simple execution result: {result.status}")
    
    # Method 2: Using builder pattern
    print("\n=== Builder Pattern ===")
    config = InvokerConfig(
        base_url="https://n8n.example.com",
        api_key="your-api-key",
        timeout=30,
        max_retries=3
    )
    
    manager = (WorkflowManagerBuilder()
               .with_http_invoker(config)
               .with_logging_hooks()
               .with_hook("pre_execution", MetricsHook())
               .with_hook("error", CircuitBreakerHook())
               .build())
    
    async with manager.session():
        # Single execution
        result = await manager.execute_workflow(
            "data-processing",
            {"input_file": "data.csv", "output_format": "json"}
        )
        print(f"Single execution: {result.status}")
        
        # Batch execution
        workflows = [
            {"id": "email-campaign", "params": {"campaign_id": 1}},
            {"id": "email-campaign", "params": {"campaign_id": 2}},
            {"id": "email-campaign", "params": {"campaign_id": 3}},
        ]
        
        results = await manager.execute_batch(workflows, max_concurrent=2)
        print(f"Batch execution: {len(results)} workflows completed")
        
        # Health check
        health = await manager.health_check()
        print(f"Health check: {health}")
    
    # Method 3: Configuration file
    print("\n=== Configuration File ===")
    # Assuming you have a config.yaml file
    try:
        manager = WorkflowManager.from_config("config.yaml")
        async with manager.session():
            result = await manager.execute_workflow("test-workflow")
            print(f"Config-based execution: {result.status}")
    except FileNotFoundError:
        print("Config file not found, skipping this example")


if __name__ == "__main__":
    asyncio.run(example_usage())