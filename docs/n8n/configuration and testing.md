"""
Configuration and Testing Infrastructure
========================================

Configuration management, testing utilities, and integration examples.
"""

import json
import os
import tempfile
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any, Dict, List, Optional
import yaml
import pytest
import asyncio

from .core_api import (
    WorkflowExecution, ExecutionStatus, InvokerConfig, HTTPInvoker,
    BaseTracer, ExecutionHook, N8NError, TransientError, PermanentError
)
from .workflow_manager import WorkflowManager, WorkflowManagerBuilder


# ============================================================================
# Configuration Management
# ============================================================================

class ConfigurationManager:
    """
    Centralized configuration management with environment variable support,
    validation, and schema enforcement.
    """
    
    DEFAULT_CONFIG = {
        "n8n": {
            "base_url": "http://localhost:5678",
            "api_key": None,
            "timeout": 30,
            "verify_ssl": True
        },
        "invokers": {
            "http": {
                "max_retries": 3,
                "backoff_factor": 2.0,
                "pool_connections": 10,
                "pool_maxsize": 20,
                "max_concurrent": 10
            }
        },
        "tracing": {
            "enabled": True,
            "backend": "structured_logging",
            "sample_rate": 1.0
        },
        "hooks": {
            "pre_execution": ["logging_hook"],
            "post_execution": ["logging_hook"],
            "error": ["logging_hook"],
            "retry": ["logging_hook"]
        },
        "circuit_breaker": {
            "enabled": False,
            "failure_threshold": 5,
            "recovery_timeout": 60
        },
        "metrics": {
            "enabled": False,
            "backend": "prometheus",
            "push_gateway": None
        }
    }
    
    @classmethod
    def load_config(cls, config_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Load configuration from file with environment variable substitution.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            Loaded and processed configuration
        """
        config = cls.DEFAULT_CONFIG.copy()
        
        # Load from file if provided
        if config_path and os.path.exists(config_path):
            with open(config_path, 'r') as f:
                file_config = yaml.safe_load(f)
                config = cls._deep_merge(config, file_config)
        
        # Apply environment variable substitutions
        config = cls._substitute_env_vars(config)
        
        # Validate configuration
        cls._validate_config(config)
        
        return config
    
    @classmethod
    def _deep_merge(cls, base: Dict, override: Dict) -> Dict:
        """Deep merge two dictionaries."""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = cls._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
    
    @classmethod
    def _substitute_env_vars(cls, config: Dict) -> Dict:
        """Substitute environment variables in configuration values."""
        if isinstance(config, dict):
            return {k: cls._substitute_env_vars(v) for k, v in config.items()}
        elif isinstance(config, list):
            return [cls._substitute_env_vars(item) for item in config]
        elif isinstance(config, str) and config.startswith("${") and config.endswith("}"):
            env_var = config[2:-1]
            default_value = None
            
            if ":" in env_var:
                env_var, default_value = env_var.split(":", 1)
            
            return os.getenv(env_var, default_value)
        else:
            return config
    
    @classmethod
    def _validate_config(cls, config: Dict) -> None:
        """Validate configuration structure and required fields."""
        required_fields = [
            ("n8n", "base_url"),
        ]
        
        for section, field in required_fields:
            if section not in config or field not in config[section]:
                raise ValueError(f"Required configuration field missing: {section}.{field}")
            
            if not config[section][field]:
                raise ValueError(f"Required configuration field is empty: {section}.{field}")


# ============================================================================
# Testing Utilities
# ============================================================================

class MockHTTPInvoker(HTTPInvoker):
    """Mock HTTP invoker for testing purposes."""
    
    def __init__(self, config: InvokerConfig):
        super().__init__(config)
        self.executions: Dict[str, WorkflowExecution] = {}
        self.should_fail = False
        self.failure_type = TransientError
        self.delay = 0
    
    async def invoke(self, execution: WorkflowExecution) -> WorkflowExecution:
        """Mock workflow invocation."""
        if self.delay > 0:
            await asyncio.sleep(self.delay)
        
        if self.should_fail:
            raise self.failure_type("Mock failure")
        
        # Simulate successful execution
        execution = execution.with_status(ExecutionStatus.RUNNING)
        execution.started_at = asyncio.get_event_loop().time()
        
        # Simulate some processing time
        await asyncio.sleep(0.1)
        
        execution = execution.with_status(ExecutionStatus.SUCCESS)
        execution.completed_at = asyncio.get_event_loop().time()
        execution.result = {"status": "completed", "output": "mock_result"}
        
        self.executions[execution.id] = execution
        return execution
    
    async def get_status(self, execution_id: str) -> ExecutionStatus:
        """Mock status retrieval."""
        if execution_id in self.executions:
            return self.executions[execution_id].status
        return ExecutionStatus.FAILED
    
    async def cancel(self, execution_id: str) -> bool:
        """Mock cancellation."""
        if execution_id in self.executions:
            execution = self.executions[execution_id]
            if execution.status == ExecutionStatus.RUNNING:
                execution = execution.with_status(ExecutionStatus.CANCELLED)
                self.executions[execution_id] = execution
                return True
        return False


class TestTracer(BaseTracer):
    """Test tracer that captures execution events."""
    
    def __init__(self):
        self.events: List[Dict[str, Any]] = []
    
    async def start_trace(self, execution: WorkflowExecution) -> None:
        """Record trace start event."""
        self.events.append({
            "event": "start_trace",
            "execution_id": execution.id,
            "workflow_id": execution.workflow_id,
            "timestamp": asyncio.get_event_loop().time()
        })
    
    async def update_trace(self, execution: WorkflowExecution) -> None:
        """Record trace update event."""
        self.events.append({
            "event": "update_trace",
            "execution_id": execution.id,
            "status": execution.status.value,
            "timestamp": asyncio.get_event_loop().time()
        })
    
    async def end_trace(self, execution: WorkflowExecution) -> None:
        """Record trace end event."""
        self.events.append({
            "event": "end_trace",
            "execution_id": execution.id,
            "status": execution.status.value,
            "duration": execution.duration,
            "timestamp": asyncio.get_event_loop().time()
        })


class TestHook(ExecutionHook):
    """Test hook that captures execution events."""
    
    def __init__(self):
        self.events: List[Dict[str, Any]] = []
    
    async def pre_execution(self, execution: WorkflowExecution) -> WorkflowExecution:
        """Record pre-execution event."""
        self.events.append({
            "event": "pre_execution",
            "execution_id": execution.id,
            "workflow_id": execution.workflow_id
        })
        return execution
    
    async def post_execution(self, execution: WorkflowExecution) -> WorkflowExecution:
        """Record post-execution event."""
        self.events.append({
            "event": "post_execution",
            "execution_id": execution.id,
            "status": execution.status.value,
            "duration": execution.duration
        })
        return execution
    
    async def on_error(self, execution: WorkflowExecution, error: Exception) -> WorkflowExecution:
        """Record error event."""
        self.events.append({
            "event": "on_error",
            "execution_id": execution.id,
            "error": str(error),
            "error_type": type(error).__name__
        })
        return execution
    
    async def on_retry(self, execution: WorkflowExecution, attempt: int) -> WorkflowExecution:
        """Record retry event."""
        self.events.append({
            "event": "on_retry",
            "execution_id": execution.id,
            "attempt": attempt
        })
        return execution


# ============================================================================
# Test Cases
# ============================================================================

class TestWorkflowManager(unittest.IsolatedAsyncioTestCase):
    """Comprehensive test suite for WorkflowManager."""
    
    async def asyncSetUp(self):
        """Set up test fixtures."""
        self.config = InvokerConfig(
            base_url="http://test.example.com",
            api_key="test-key",
            timeout=10,
            max_retries=2,
            max_concurrent=5
        )
        
        self.mock_invoker = MockHTTPInvoker(self.config)
        self.test_tracer = TestTracer()
        self.test_hook = TestHook()
        
        self.manager = WorkflowManager(
            invoker=self.mock_invoker,
            tracer=self.test_tracer,
            hooks={
                "pre_execution": [self.test_hook],
                "post_execution": [self.test_hook],
                "error": [self.test_hook],
                "retry": [self.test_hook]
            }
        )
    
    async def test_successful_execution(self):
        """Test successful workflow execution."""
        result = await self.manager.execute_workflow(
            workflow_id="test-workflow",
            parameters={"key": "value"}
        )
        
        self.assertEqual(result.status, ExecutionStatus.SUCCESS)
        self.assertEqual(result.workflow_id, "test-workflow")
        self.assertEqual(result.parameters, {"key": "value"})
        self.assertIsNotNone(result.result)
        self.assertIsNone(result.error)
        
        # Check that hooks were called
        hook_events = [event["event"] for event in self.test_hook.events]
        self.assertIn("pre_execution", hook_events)
        self.assertIn("post_execution", hook_events)
        
        # Check that tracing occurred
        trace_events = [event["event"] for event in self.test_tracer.events]
        self.assertIn("start_trace", trace_events)
        self.assertIn("end_trace", trace_events)
    
    async def test_failed_execution(self):
        """Test failed workflow execution."""
        self.mock_invoker.should_fail = True
        self.mock_invoker.failure_type = PermanentError
        
        with self.assertRaises(PermanentError):
            await self.manager.execute_workflow("test-workflow")
        
        # Check that error hook was called
        hook_events = [event["event"] for event in self.test_hook.events]
        self.assertIn("on_error", hook_events)
    
    async def test_batch_execution(self):
        """Test batch workflow execution."""
        workflows = [
            {"id": "workflow-1", "params": {"batch": 1}},
            {"id": "workflow-2", "params": {"batch": 2}},
            {"id": "workflow-3", "params": {"batch": 3}}
        ]
        
        results = await self.manager.execute_batch(workflows, max_concurrent=2)
        
        self.assertEqual(len(results), 3)
        for result in results:
            self.assertEqual(result.status, ExecutionStatus.SUCCESS)
    
    async def test_health_check(self):
        """Test health check functionality."""
        health = await self.manager.health_check()
        
        self.assertTrue(health["healthy"])
        self.assertIn("components", health)
        self.assertTrue(health["components"]["invoker"])
    
    async def test_workflow_manager_builder(self):
        """Test WorkflowManagerBuilder functionality."""
        manager = (WorkflowManagerBuilder()
                   .with_http_invoker(self.config)
                   .with_tracer(self.test_tracer)
                   .with_hook("pre_execution", self.test_hook)
                   .build())
        
        # Replace invoker with mock for testing
        manager.invoker = self.mock_invoker
        
        result = await manager.execute_workflow("test-workflow")
        self.assertEqual(result.status, ExecutionStatus.SUCCESS)


class TestConfigurationManager(unittest.TestCase):
    """Test configuration management functionality."""
    
    def test_default_config_loading(self):
        """Test loading default configuration."""
        config = ConfigurationManager.load_config()
        
        self.assertIn("n8n", config)
        self.assertIn("invokers", config)
        self.assertIn("tracing", config)
    
    def test_config_file_loading(self):
        """Test loading configuration from file."""
        test_config = {
            "n8n": {
                "base_url": "https://custom.example.com",
                "api_key": "custom-key"
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(test_config, f)
            temp_path = f.name
        
        try:
            config = ConfigurationManager.load_config(temp_path)
            self.assertEqual(config["n8n"]["base_url"], "https://custom.example.com")
            self.assertEqual(config["n8n"]["api_key"], "custom-key")
        finally:
            os.unlink(temp_path)
    
    def test_environment_variable_substitution(self):
        """Test environment variable substitution."""
        os.environ["TEST_N8N_URL"] = "https://env.example.com"
        
        test_config = {
            "n8n": {
                "base_url": "${TEST_N8N_URL}",
                "api_key": "${MISSING_VAR:default-key}"
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(test_config, f)
            temp_path = f.name
        
        try:
            config = ConfigurationManager.load_config(temp_path)
            self.assertEqual(config["n8n"]["base_url"], "https://env.example.com")
            self.assertEqual(config["n8n"]["api_key"], "default-key")
        finally:
            os.unlink(temp_path)
            del os.environ["TEST_N8N_URL"]


# ============================================================================
# Integration Test Examples
# ============================================================================

async def integration_test_example():
    """
    Example integration test showing real-world usage patterns.
    
    This would typically run against a real n8n instance in a test environment.
    """
    # Load configuration from environment
    config = ConfigurationManager.load_config("test_config.yaml")
    
    # Create manager with test configuration
    invoker_config = InvokerConfig(
        base_url=config["n8n"]["base_url"],
        api_key=config["n8n"]["api_key"],
        timeout=config["n8n"]["timeout"],
        max_retries=config["invokers"]["http"]["max_retries"]
    )
    
    manager = (WorkflowManagerBuilder()
               .with_http_invoker(invoker_config)
               .with_logging_hooks()
               .build())
    
    try:
        async with manager.session():
            # Test basic workflow execution
            print("Testing basic workflow execution...")
            result = await manager.execute_workflow(
                "test-workflow",
                {"test_param": "integration_test"}
            )
            print(f"Execution result: {result.status}")
            
            # Test batch execution
            print("Testing batch execution...")
            workflows = [
                {"id": "test-workflow", "params": {"batch_id": i}}
                for i in range(5)
            ]
            
            batch_results = await manager.execute_batch(workflows, max_concurrent=3)
            successful = sum(1 for r in batch_results if r.status == ExecutionStatus.SUCCESS)
            print(f"Batch execution: {successful}/{len(batch_results)} succeeded")
            
            # Test error handling
            print("Testing error handling...")
            try:
                await manager.execute_workflow("non-existent-workflow")
            except N8NError as e:
                print(f"Expected error caught: {type(e).__name__}")
            
            # Test health check
            print("Testing health check...")
            health = await manager.health_check()
            print(f"Health status: {health['healthy']}")
            
    except Exception as e:
        print(f"Integration test failed: {e}")
        raise


# ============================================================================
# Performance Testing
# ============================================================================

class PerformanceTestSuite:
    """Performance testing utilities for the workflow manager."""
    
    @staticmethod
    async def benchmark_single_execution(manager: WorkflowManager, iterations: int = 100):
        """Benchmark single workflow execution performance."""
        import time
        
        start_time = time.time()
        
        for i in range(iterations):
            try:
                await manager.execute_workflow(
                    "benchmark-workflow",
                    {"iteration": i}
                )
            except Exception as e:
                print(f"Iteration {i} failed: {e}")
        
        end_time = time.time()
        total_time = end_time - start_time
        avg_time = total_time / iterations
        
        print(f"Single execution benchmark:")
        print(f"  Total time: {total_time:.2f}s")
        print(f"  Average time per execution: {avg_time:.3f}s")
        print(f"  Executions per second: {iterations / total_time:.1f}")
    
    @staticmethod
    async def benchmark_concurrent_execution(
        manager: WorkflowManager, 
        total_executions: int = 100,
        max_concurrent: int = 10
    ):
        """Benchmark concurrent workflow execution performance."""
        import time
        
        workflows = [
            {"id": "benchmark-workflow", "params": {"iteration": i}}
            for i in range(total_executions)
        ]
        
        start_time = time.time()
        
        try:
            results = await manager.execute_batch(workflows, max_concurrent=max_concurrent)
            end_time = time.time()
            
            total_time = end_time - start_time
            successful = sum(1 for r in results if r.status == ExecutionStatus.SUCCESS)
            
            print(f"Concurrent execution benchmark:")
            print(f"  Total executions: {total_executions}")
            print(f"  Max concurrent: {max_concurrent}")
            print(f"  Successful: {successful}")
            print(f"  Total time: {total_time:.2f}s")
            print(f"  Executions per second: {total_executions / total_time:.1f}")
            print(f"  Average time per execution: {total_time / total_executions:.3f}s")
            
        except Exception as e:
            print(f"Concurrent benchmark failed: {e}")
    
    @staticmethod
    async def stress_test(
        manager: WorkflowManager,
        duration_seconds: int = 60,
        target_rps: int = 10
    ):
        """Run stress test for specified duration and target rate."""
        import time
        import asyncio
        
        print(f"Starting stress test:")
        print(f"  Duration: {duration_seconds}s")
        print(f"  Target rate: {target_rps} RPS")
        
        start_time = time.time()
        end_time = start_time + duration_seconds
        
        successful_executions = 0
        failed_executions = 0
        iteration = 0
        
        while time.time() < end_time:
            iteration += 1
            
            try:
                await manager.execute_workflow(
                    "stress-test-workflow",
                    {"iteration": iteration, "timestamp": time.time()}
                )
                successful_executions += 1
                
            except Exception as e:
                failed_executions += 1
                print(f"Execution {iteration} failed: {e}")
            
            # Rate limiting
            await asyncio.sleep(1.0 / target_rps)
        
        actual_duration = time.time() - start_time
        total_executions = successful_executions + failed_executions
        actual_rps = total_executions / actual_duration
        success_rate = successful_executions / total_executions if total_executions > 0 else 0
        
        print(f"Stress test results:")
        print(f"  Actual duration: {actual_duration:.2f}s")
        print(f"  Total executions: {total_executions}")
        print(f"  Successful: {successful_executions}")
        print(f"  Failed: {failed_executions}")
        print(f"  Success rate: {success_rate:.2%}")
        print(f"  Actual RPS: {actual_rps:.1f}")


# ============================================================================
# Example Configuration Files
# ============================================================================

def create_example_configs():
    """Create example configuration files for different environments."""
    
    # Development configuration
    dev_config = {
        "n8n": {
            "base_url": "http://localhost:5678",
            "api_key": "${N8N_API_KEY:}",
            "timeout": 30,
            "verify_ssl": False
        },
        "invokers": {
            "http": {
                "max_retries": 3,
                "backoff_factor": 1.5,
                "max_concurrent": 5
            }
        },
        "tracing": {
            "enabled": True,
            "backend": "structured_logging",
            "sample_rate": 1.0
        },
        "hooks": {
            "pre_execution": ["logging_hook"],
            "post_execution": ["logging_hook"],
            "error": ["logging_hook"]
        }
    }
    
    # Production configuration
    prod_config = {
        "n8n": {
            "base_url": "${N8N_BASE_URL}",
            "api_key": "${N8N_API_KEY}",
            "timeout": 60,
            "verify_ssl": True
        },
        "invokers": {
            "http": {
                "max_retries": 5,
                "backoff_factor": 2.0,
                "max_concurrent": 20,
                "pool_connections": 50,
                "pool_maxsize": 100
            }
        },
        "tracing": {
            "enabled": True,
            "backend": "opentelemetry",
            "sample_rate": 0.1,
            "jaeger_endpoint": "${JAEGER_ENDPOINT:}"
        },
        "hooks": {
            "pre_execution": ["logging_hook", "metrics_hook"],
            "post_execution": ["logging_hook", "metrics_hook"],
            "error": ["logging_hook", "metrics_hook", "alerting_hook"],
            "retry": ["logging_hook"]
        },
        "circuit_breaker": {
            "enabled": True,
            "failure_threshold": 10,
            "recovery_timeout": 300
        },
        "metrics": {
            "enabled": True,
            "backend": "prometheus",
            "push_gateway": "${PROMETHEUS_PUSH_GATEWAY:}",
            "job_name": "n8n_invoker"
        }
    }
    
    # Test configuration
    test_config = {
        "n8n": {
            "base_url": "http://n8n-test:5678",
            "api_key": "test-api-key",
            "timeout": 10
        },
        "invokers": {
            "http": {
                "max_retries": 1,
                "backoff_factor": 1.0,
                "max_concurrent": 2
            }
        },
        "tracing": {
            "enabled": False
        },
        "hooks": {
            "pre_execution": [],
            "post_execution": [],
            "error": [],
            "retry": []
        }
    }
    
    # Write configuration files
    configs = {
        "config_dev.yaml": dev_config,
        "config_prod.yaml": prod_config,
        "config_test.yaml": test_config
    }
    
    for filename, config in configs.items():
        with open(filename, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, indent=2)
        print(f"Created {filename}")


# ============================================================================
# Docker and Deployment Utilities
# ============================================================================

def create_docker_compose():
    """Create docker-compose.yml for testing environment."""
    
    docker_compose = {
        "version": "3.8",
        "services": {
            "n8n": {
                "image": "n8nio/n8n:latest",
                "ports": ["5678:5678"],
                "environment": {
                    "N8N_BASIC_AUTH_ACTIVE": "true",
                    "N8N_BASIC_AUTH_USER": "admin",
                    "N8N_BASIC_AUTH_PASSWORD": "admin",
                    "WEBHOOK_URL": "http://localhost:5678",
                    "GENERIC_TIMEZONE": "UTC"
                },
                "volumes": [
                    "n8n_data:/home/node/.n8n"
                ]
            },
            "workflow-invoker-test": {
                "build": ".",
                "depends_on": ["n8n"],
                "environment": {
                    "N8N_BASE_URL": "http://n8n:5678",
                    "N8N_API_KEY": "test-key"
                },
                "volumes": [
                    "./tests:/app/tests",
                    "./config_test.yaml:/app/config.yaml"
                ],
                "command": "python -m pytest tests/ -v"
            }
        },
        "volumes": {
            "n8n_data": None
        }
    }
    
    with open("docker-compose.yml", 'w') as f:
        yaml.dump(docker_compose, f, default_flow_style=False, indent=2)
    print("Created docker-compose.yml")


def create_dockerfile():
    """Create Dockerfile for the n8n invoker application."""
    
    dockerfile_content = """FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    curl \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Install the package in development mode
RUN pip install -e .

# Create non-root user
RUN useradd --create-home --shell /bin/bash invoker
USER invoker

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
    CMD python -c "import asyncio; from n8n_invoker import create_http_manager; \\
         manager = create_http_manager('http://n8n:5678'); \\
         print('Health check passed' if asyncio.run(manager.health_check())['healthy'] else exit(1))"

CMD ["python", "-m", "n8n_invoker"]
"""
    
    with open("Dockerfile", 'w') as f:
        f.write(dockerfile_content)
    print("Created Dockerfile")


def create_requirements_txt():
    """Create requirements.txt file."""
    
    requirements = [
        "aiohttp>=3.8.0",
        "structlog>=22.0.0",
        "tenacity>=8.0.0",
        "pyyaml>=6.0",
        "pytest>=7.0.0",
        "pytest-asyncio>=0.20.0",
        "prometheus-client>=0.15.0",  # For metrics
        "opentelemetry-api>=1.15.0",  # For tracing
        "opentelemetry-sdk>=1.15.0",
        "opentelemetry-instrumentation-aiohttp-client>=0.36b0"
    ]
    
    with open("requirements.txt", 'w') as f:
        f.write('\n'.join(requirements))
    print("Created requirements.txt")


# ============================================================================
# CLI Interface
# ============================================================================

def create_cli_interface():
    """Create a CLI interface for the n8n invoker."""
    
    cli_content = '''#!/usr/bin/env python3
"""
N8N Workflow Invoker CLI
========================

Command-line interface for executing n8n workflows.
"""

import asyncio
import json
import sys
from argparse import ArgumentParser
from pathlib import Path

from n8n_invoker import WorkflowManager, create_http_manager, execute_workflow_simple


async def main():
    parser = ArgumentParser(description="N8N Workflow Invoker CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Execute command
    execute_parser = subparsers.add_parser("execute", help="Execute a workflow")
    execute_parser.add_argument("workflow_id", help="Workflow ID to execute")
    execute_parser.add_argument("--params", "-p", help="JSON parameters for the workflow")
    execute_parser.add_argument("--config", "-c", help="Configuration file path")
    execute_parser.add_argument("--base-url", help="N8N base URL")
    execute_parser.add_argument("--api-key", help="N8N API key")
    
    # Batch command
    batch_parser = subparsers.add_parser("batch", help="Execute workflows in batch")
    batch_parser.add_argument("workflows_file", help="JSON file with workflow definitions")
    batch_parser.add_argument("--config", "-c", help="Configuration file path")
    batch_parser.add_argument("--concurrent", type=int, default=5, help="Max concurrent executions")
    
    # Health check command
    health_parser = subparsers.add_parser("health", help="Check system health")
    health_parser.add_argument("--config", "-c", help="Configuration file path")
    health_parser.add_argument("--base-url", help="N8N base URL")
    health_parser.add_argument("--api-key", help="N8N API key")
    
    # Test command
    test_parser = subparsers.add_parser("test", help="Run performance tests")
    test_parser.add_argument("--config", "-c", help="Configuration file path")
    test_parser.add_argument("--iterations", type=int, default=10, help="Number of test iterations")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        if args.command == "execute":
            await execute_command(args)
        elif args.command == "batch":
            await batch_command(args)
        elif args.command == "health":
            await health_command(args)
        elif args.command == "test":
            await test_command(args)
            
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


async def execute_command(args):
    """Execute a single workflow."""
    parameters = json.loads(args.params) if args.params else {}
    
    if args.config:
        manager = WorkflowManager.from_config(args.config)
        async with manager.session():
            result = await manager.execute_workflow(args.workflow_id, parameters)
    else:
        result = await execute_workflow_simple(
            args.base_url or "http://localhost:5678",
            args.workflow_id,
            parameters,
            args.api_key
        )
    
    print(json.dumps({
        "execution_id": result.id,
        "workflow_id": result.workflow_id,
        "status": result.status.value,
        "duration": result.duration,
        "result": result.result,
        "error": result.error
    }, indent=2))


async def batch_command(args):
    """Execute workflows in batch."""
    with open(args.workflows_file) as f:
        workflows = json.load(f)
    
    manager = WorkflowManager.from_config(args.config)
    
    async with manager.session():
        results = await manager.execute_batch(workflows, args.concurrent)
    
    summary = {
        "total": len(results),
        "successful": sum(1 for r in results if r.status.value == "success"),
        "failed": sum(1 for r in results if r.status.value == "failed"),
        "results": [
            {
                "execution_id": r.id,
                "workflow_id": r.workflow_id,
                "status": r.status.value,
                "duration": r.duration,
                "error": r.error
            }
            for r in results
        ]
    }
    
    print(json.dumps(summary, indent=2))


async def health_command(args):
    """Check system health."""
    if args.config:
        manager = WorkflowManager.from_config(args.config)
    else:
        manager = create_http_manager(
            args.base_url or "http://localhost:5678",
            args.api_key
        )
    
    async with manager.session():
        health = await manager.health_check()
    
    print(json.dumps(health, indent=2))
    
    if not health["healthy"]:
        sys.exit(1)


async def test_command(args):
    """Run performance tests."""
    from n8n_invoker.testing import PerformanceTestSuite
    
    manager = WorkflowManager.from_config(args.config)
    
    async with manager.session():
        print("Running performance tests...")
        await PerformanceTestSuite.benchmark_single_execution(manager, args.iterations)


if __name__ == "__main__":
    asyncio.run(main())
'''
    
    with open("cli.py", 'w') as f:
        f.write(cli_content)
    print("Created cli.py")


# ============================================================================
# Main Execution
# ============================================================================

if __name__ == "__main__":
    print("Creating example configuration and deployment files...")
    
    create_example_configs()
    create_docker_compose()
    create_dockerfile()
    create_requirements_txt()
    create_cli_interface()
    
    print("\nFiles created successfully!")
    print("\nTo get started:")
    print("1. Install dependencies: pip install -r requirements.txt")
    print("2. Copy and edit config_dev.yaml for your environment")
    print("3. Run tests: python -m pytest")
    print("4. Use CLI: python cli.py --help")
    print("5. Or use in code:")
    print("   from n8n_invoker import create_http_manager")
    print("   manager = create_http_manager('http://localhost:5678')")
    
    # Run the test suite if pytest is available
    try:
        import pytest
        print("\nRunning test suite...")
        pytest.main([__file__, "-v"])
    except ImportError:
        print("\nInstall pytest to run tests: pip install pytest pytest-asyncio")