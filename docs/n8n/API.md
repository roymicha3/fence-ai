"""
N8N Workflow Invoker - Core API Implementation
==============================================

Enterprise-grade Python module for invoking n8n workflows with comprehensive
tracing, error handling, and extensibility.
"""

import abc
import asyncio
import logging
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, Union
from uuid import uuid4

import aiohttp
import structlog
from tenacity import (
    retry, stop_after_attempt, wait_exponential,
    retry_if_exception_type, before_sleep_log
)


# ============================================================================
# Core Types and Enums
# ============================================================================

class ExecutionStatus(Enum):
    """Workflow execution status states."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class ErrorType(Enum):
    """Classification of error types for handling strategy."""
    TRANSIENT = "transient"  # Retry-able errors
    PERMANENT = "permanent"  # Non-retry-able errors
    UNKNOWN = "unknown"      # Unclear errors, retry with caution


@dataclass
class WorkflowExecution:
    """Immutable execution context and state."""
    id: str = field(default_factory=lambda: str(uuid4()))
    workflow_id: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    status: ExecutionStatus = ExecutionStatus.PENDING
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def duration(self) -> Optional[float]:
        """Calculate execution duration in seconds."""
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return None
    
    def with_status(self, status: ExecutionStatus) -> 'WorkflowExecution':
        """Return new execution with updated status."""
        return WorkflowExecution(
            id=self.id,
            workflow_id=self.workflow_id,
            parameters=self.parameters,
            status=status,
            started_at=self.started_at,
            completed_at=self.completed_at,
            result=self.result,
            error=self.error,
            metadata=self.metadata
        )


@dataclass
class InvokerConfig:
    """Configuration for workflow invokers."""
    base_url: str
    api_key: Optional[str] = None
    timeout: int = 30
    max_retries: int = 3
    backoff_factor: float = 2.0
    max_concurrent: int = 10


class N8NError(Exception):
    """Base exception for all n8n-related errors."""
    
    def __init__(self, message: str, error_type: ErrorType = ErrorType.UNKNOWN):
        super().__init__(message)
        self.error_type = error_type


class TransientError(N8NError):
    """Transient error that should be retried."""
    
    def __init__(self, message: str):
        super().__init__(message, ErrorType.TRANSIENT)


class PermanentError(N8NError):
    """Permanent error that should not be retried."""
    
    def __init__(self, message: str):
        super().__init__(message, ErrorType.PERMANENT)


# ============================================================================
# Abstract Base Classes
# ============================================================================

class BaseInvoker(abc.ABC):
    """Abstract base class for all workflow invokers."""
    
    def __init__(self, config: InvokerConfig):
        self.config = config
        self.logger = structlog.get_logger(__name__)
    
    @abc.abstractmethod
    async def invoke(self, execution: WorkflowExecution) -> WorkflowExecution:
        """
        Invoke a workflow and return updated execution context.
        
        Args:
            execution: The workflow execution context
            
        Returns:
            Updated execution with results or error information
            
        Raises:
            N8NError: For various error conditions
        """
        pass
    
    @abc.abstractmethod
    async def get_status(self, execution_id: str) -> ExecutionStatus:
        """
        Get the current status of a workflow execution.
        
        Args:
            execution_id: The execution ID to check
            
        Returns:
            Current execution status
        """
        pass
    
    @abc.abstractmethod
    async def cancel(self, execution_id: str) -> bool:
        """
        Cancel a running workflow execution.
        
        Args:
            execution_id: The execution ID to cancel
            
        Returns:
            True if cancellation was successful
        """
        pass
    
    async def health_check(self) -> bool:
        """
        Perform a health check on the invoker.
        
        Returns:
            True if the invoker is healthy
        """
        try:
            # Default implementation - can be overridden
            return True
        except Exception:
            return False


class BaseTracer(abc.ABC):
    """Abstract base class for execution tracers."""
    
    @abc.abstractmethod
    async def start_trace(self, execution: WorkflowExecution) -> None:
        """Start tracing an execution."""
        pass
    
    @abc.abstractmethod
    async def update_trace(self, execution: WorkflowExecution) -> None:
        """Update trace with current execution state."""
        pass
    
    @abc.abstractmethod
    async def end_trace(self, execution: WorkflowExecution) -> None:
        """End tracing for an execution."""
        pass


class ExecutionHook(abc.ABC):
    """Abstract base class for execution hooks."""
    
    async def pre_execution(self, execution: WorkflowExecution) -> WorkflowExecution:
        """Called before workflow execution."""
        return execution
    
    async def post_execution(self, execution: WorkflowExecution) -> WorkflowExecution:
        """Called after successful workflow execution."""
        return execution
    
    async def on_error(self, execution: WorkflowExecution, error: Exception) -> WorkflowExecution:
        """Called when an error occurs during execution."""
        return execution
    
    async def on_retry(self, execution: WorkflowExecution, attempt: int) -> WorkflowExecution:
        """Called before each retry attempt."""
        return execution


# ============================================================================
# HTTP Invoker Implementation
# ============================================================================

class HTTPInvoker(BaseInvoker):
    """HTTP-based n8n workflow invoker with robust error handling."""
    
    def __init__(self, config: InvokerConfig):
        super().__init__(config)
        self._session: Optional[aiohttp.ClientSession] = None
        self._semaphore = asyncio.Semaphore(config.max_concurrent)
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def _ensure_session(self):
        """Ensure HTTP session is initialized."""
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(
                limit=self.config.max_concurrent,
                limit_per_host=self.config.max_concurrent,
                keepalive_timeout=30,
                enable_cleanup_closed=True
            )
            
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            headers = {"Content-Type": "application/json"}
            
            if self.config.api_key:
                headers["Authorization"] = f"Bearer {self.config.api_key}"
            
            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers=headers,
                raise_for_status=False
            )
    
    async def close(self):
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(TransientError),
        before_sleep=before_sleep_log(logging.getLogger(__name__), logging.WARNING)
    )
    async def invoke(self, execution: WorkflowExecution) -> WorkflowExecution:
        """Invoke workflow via HTTP with retry logic."""
        async with self._semaphore:
            await self._ensure_session()
            
            execution = execution.with_status(ExecutionStatus.RUNNING)
            execution.started_at = time.time()
            
            try:
                url = f"{self.config.base_url}/api/v1/workflows/{execution.workflow_id}/execute"
                payload = {
                    "parameters": execution.parameters,
                    "executionId": execution.id
                }
                
                self.logger.info(
                    "Invoking workflow",
                    workflow_id=execution.workflow_id,
                    execution_id=execution.id,
                    url=url
                )
                
                async with self._session.post(url, json=payload) as response:
                    response_data = await response.json() if response.content_type == 'application/json' else {}
                    
                    if response.status == 200:
                        execution.completed_at = time.time()
                        execution = execution.with_status(ExecutionStatus.SUCCESS)
                        execution.result = response_data
                        
                        self.logger.info(
                            "Workflow completed successfully",
                            workflow_id=execution.workflow_id,
                            execution_id=execution.id,
                            duration=execution.duration
                        )
                        
                    elif response.status in (429, 502, 503, 504):
                        # Rate limit or server errors - transient
                        error_msg = f"HTTP {response.status}: {response_data.get('message', 'Server error')}"
                        self.logger.warning("Transient error occurred", error=error_msg)
                        raise TransientError(error_msg)
                        
                    elif response.status in (400, 401, 403, 404):
                        # Client errors - permanent
                        error_msg = f"HTTP {response.status}: {response_data.get('message', 'Client error')}"
                        execution.completed_at = time.time()
                        execution = execution.with_status(ExecutionStatus.FAILED)
                        execution.error = error_msg
                        
                        self.logger.error("Permanent error occurred", error=error_msg)
                        raise PermanentError(error_msg)
                        
                    else:
                        # Unknown error
                        error_msg = f"HTTP {response.status}: {response_data.get('message', 'Unknown error')}"
                        execution.completed_at = time.time()
                        execution = execution.with_status(ExecutionStatus.FAILED)
                        execution.error = error_msg
                        
                        self.logger.error("Unknown error occurred", error=error_msg)
                        raise N8NError(error_msg)
                
                return execution
                
            except aiohttp.ClientError as e:
                execution.completed_at = time.time()
                execution = execution.with_status(ExecutionStatus.FAILED)
                execution.error = str(e)
                
                self.logger.error("HTTP client error", error=str(e))
                raise TransientError(f"HTTP client error: {e}")
            
            except Exception as e:
                execution.completed_at = time.time()
                execution = execution.with_status(ExecutionStatus.FAILED)
                execution.error = str(e)
                
                self.logger.error("Unexpected error", error=str(e))
                raise N8NError(f"Unexpected error: {e}")
    
    async def get_status(self, execution_id: str) -> ExecutionStatus:
        """Get execution status via HTTP API."""
        await self._ensure_session()
        
        try:
            url = f"{self.config.base_url}/api/v1/executions/{execution_id}"
            
            async with self._session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    status_str = data.get("status", "unknown").lower()
                    
                    # Map n8n status to our enum
                    status_mapping = {
                        "new": ExecutionStatus.PENDING,
                        "running": ExecutionStatus.RUNNING,
                        "success": ExecutionStatus.SUCCESS,
                        "failed": ExecutionStatus.FAILED,
                        "canceled": ExecutionStatus.CANCELLED
                    }
                    
                    return status_mapping.get(status_str, ExecutionStatus.FAILED)
                
                elif response.status == 404:
                    return ExecutionStatus.FAILED
                
                else:
                    self.logger.warning(f"Status check failed: HTTP {response.status}")
                    return ExecutionStatus.FAILED
                    
        except Exception as e:
            self.logger.error("Status check error", error=str(e))
            return ExecutionStatus.FAILED
    
    async def cancel(self, execution_id: str) -> bool:
        """Cancel execution via HTTP API."""
        await self._ensure_session()
        
        try:
            url = f"{self.config.base_url}/api/v1/executions/{execution_id}/cancel"
            
            async with self._session.post(url) as response:
                return response.status in (200, 202)
                
        except Exception as e:
            self.logger.error("Cancel request failed", error=str(e))
            return False
    
    async def health_check(self) -> bool:
        """Check if n8n API is accessible."""
        await self._ensure_session()
        
        try:
            url = f"{self.config.base_url}/api/v1/health"
            
            async with self._session.get(url) as response:
                return response.status == 200
                
        except Exception:
            return False


# ============================================================================
# Structured Logging Tracer
# ============================================================================

class StructuredTracer(BaseTracer):
    """Structured logging-based tracer for workflow executions."""
    
    def __init__(self):
        self.logger = structlog.get_logger(__name__)
    
    async def start_trace(self, execution: WorkflowExecution) -> None:
        """Start tracing with structured logging."""
        self.logger.info(
            "Workflow execution started",
            execution_id=execution.id,
            workflow_id=execution.workflow_id,
            parameters=execution.parameters,
            status=execution.status.value
        )
    
    async def update_trace(self, execution: WorkflowExecution) -> None:
        """Update trace with current state."""
        log_data = {
            "execution_id": execution.id,
            "workflow_id": execution.workflow_id,
            "status": execution.status.value
        }
        
        if execution.duration:
            log_data["duration"] = execution.duration
        
        if execution.error:
            log_data["error"] = execution.error
            self.logger.error("Workflow execution updated", **log_data)
        else:
            self.logger.info("Workflow execution updated", **log_data)
    
    async def end_trace(self, execution: WorkflowExecution) -> None:
        """End tracing with final state."""
        log_data = {
            "execution_id": execution.id,
            "workflow_id": execution.workflow_id,
            "status": execution.status.value,
            "duration": execution.duration
        }
        
        if execution.status == ExecutionStatus.SUCCESS:
            self.logger.info("Workflow execution completed successfully", **log_data)
        else:
            log_data["error"] = execution.error
            self.logger.error("Workflow execution failed", **log_data)


# ============================================================================
# Default Hooks
# ============================================================================

class LoggingHook(ExecutionHook):
    """Default logging hook for execution events."""
    
    def __init__(self):
        self.logger = structlog.get_logger(__name__)
    
    async def pre_execution(self, execution: WorkflowExecution) -> WorkflowExecution:
        """Log before execution."""
        self.logger.debug(
            "Pre-execution hook",
            execution_id=execution.id,
            workflow_id=execution.workflow_id
        )
        return execution
    
    async def post_execution(self, execution: WorkflowExecution) -> WorkflowExecution:
        """Log after successful execution."""
        self.logger.debug(
            "Post-execution hook",
            execution_id=execution.id,
            workflow_id=execution.workflow_id,
            duration=execution.duration
        )
        return execution
    
    async def on_error(self, execution: WorkflowExecution, error: Exception) -> WorkflowExecution:
        """Log on error."""
        self.logger.error(
            "Error hook triggered",
            execution_id=execution.id,
            workflow_id=execution.workflow_id,
            error=str(error),
            error_type=type(error).__name__
        )
        return execution
    
    async def on_retry(self, execution: WorkflowExecution, attempt: int) -> WorkflowExecution:
        """Log on retry."""
        self.logger.warning(
            "Retry hook triggered",
            execution_id=execution.id,
            workflow_id=execution.workflow_id,
            attempt=attempt
        )
        return execution