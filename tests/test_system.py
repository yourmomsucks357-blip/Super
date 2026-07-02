import pytest
import asyncio
from src.agents import AgentContext, AgentStatus, executor
from src.agents.examples import EchoAgent, SleepAgent, ComputeAgent
from src.telemetry import collector


@pytest.mark.asyncio
async def test_echo_agent():
    agent = EchoAgent()
    ctx = AgentContext(agent_id=agent.agent_id)
    result = await executor.run(agent, ctx, message="test")
    assert result.status == AgentStatus.COMPLETED
    assert result.output["echo"] == "test"
    assert result.duration_ms is not None


@pytest.mark.asyncio
async def test_compute_agent():
    agent = ComputeAgent()
    result = await executor.run(agent, numbers=[10, 20, 30])
    assert result.status == AgentStatus.COMPLETED
    assert result.output["sum"] == 60
    assert result.output["average"] == 20.0


@pytest.mark.asyncio
async def test_agent_timeout():
    agent = SleepAgent()
    result = await executor.run(agent, timeout=1, seconds=5.0)
    assert result.status == AgentStatus.TIMEOUT
    assert result.error is not None


@pytest.mark.asyncio
async def test_retry_succeeds():
    agent = EchoAgent()
    result = await executor.run_with_retry(agent, message="retry_test", retries=2)
    assert result.status == AgentStatus.COMPLETED


def test_telemetry_collector():
    from src.telemetry.models import TelemetryEvent, EventType
    collector.emit(TelemetryEvent(event_type=EventType.LOG, payload={"msg": "hello"}))
    events = collector.get_events(limit=10)
    assert len(events) >= 1


def test_telemetry_metric():
    from src.telemetry.models import Metric
    collector.record_metric(Metric(name="test.metric", value=42.0, unit="count"))
    metrics = collector.get_metrics(limit=10)
    assert any(m.name == "test.metric" for m in metrics)


def test_agent_registry():
    from src.agents.registry import registry
    types = registry.list_types()
    assert "echo" in types
    assert "sleep" in types
    assert "compute" in types
