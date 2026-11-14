import pytest
from langgraph.checkpoint.base import WRITES_IDX_MAP

from app.ai.graph.agent import checkpointer as graph_checkpointer
from app.ai.graph.checkpointer import SQLAlchemyCheckpointSaver
from app.db.migrate import RLS_PROTECTED_MODELS
from app.db.models import AgentCheckpoint, AgentCheckpointBlob, AgentCheckpointWrite
from app.db.session import SessionLocal


def test_agent_uses_sqlalchemy_checkpointer():
    assert isinstance(graph_checkpointer, SQLAlchemyCheckpointSaver)


def test_sqlalchemy_checkpointer_persists_across_saver_instances():
    saver_one = SQLAlchemyCheckpointSaver(session_factory=SessionLocal)
    saver_two = SQLAlchemyCheckpointSaver(session_factory=SessionLocal)

    cfg = {"configurable": {"thread_id": "thread_persist_1", "checkpoint_ns": ""}}
    checkpoint_v1 = {
        "v": 1,
        "id": "00000000-0000-0000-0000-000000000001",
        "ts": "2026-11-13T00:00:00+00:00",
        "channel_values": {"messages": ["hello"], "user_instructions": "Be concise"},
        "channel_versions": {"messages": "1.0", "user_instructions": "1.0"},
        "versions_seen": {},
    }
    saved_cfg = saver_one.put(
        cfg,
        checkpoint_v1,
        {"source": "input", "step": 0},
        {"messages": "1.0", "user_instructions": "1.0"},
    )
    saver_one.put_writes(
        saved_cfg,
        [("messages", "world"), ("__interrupt__", ("confirm",))],
        task_id="task-1",
        task_path="tools",
    )
    # Re-putting positive-index write should be ignored (idempotent), whereas special write overwrites
    saver_one.put_writes(
        saved_cfg,
        [("messages", "should_not_overwrite")],
        task_id="task-1",
        task_path="tools",
    )

    # Read from an independent saver instance (simulating process/worker restart)
    loaded = saver_two.get_tuple({"configurable": {"thread_id": "thread_persist_1"}})
    assert loaded is not None
    assert loaded.checkpoint["id"] == checkpoint_v1["id"]
    assert loaded.checkpoint["channel_values"] == {
        "messages": ["hello"],
        "user_instructions": "Be concise",
    }
    assert loaded.metadata["source"] == "input"
    writes_by_channel = {channel: value for _, channel, value in loaded.pending_writes}
    assert writes_by_channel["messages"] == "world"
    assert writes_by_channel["__interrupt__"] == ["confirm"]
    assert WRITES_IDX_MAP["__interrupt__"] < 0


@pytest.mark.anyio
async def test_sqlalchemy_checkpointer_async_lifecycle_and_delete_thread():
    saver = SQLAlchemyCheckpointSaver(session_factory=SessionLocal)
    cfg_a = {"configurable": {"thread_id": "thread_async_a", "checkpoint_ns": ""}}
    cfg_b = {"configurable": {"thread_id": "thread_async_b", "checkpoint_ns": ""}}

    cp_a = {
        "v": 1,
        "id": "00000000-0000-0000-0000-000000000010",
        "ts": "2026-11-13T00:00:01+00:00",
        "channel_values": {"messages": ["a1"]},
        "channel_versions": {"messages": "1.0"},
        "versions_seen": {},
    }
    cp_b = {
        "v": 1,
        "id": "00000000-0000-0000-0000-000000000020",
        "ts": "2026-11-13T00:00:02+00:00",
        "channel_values": {"messages": ["b1"]},
        "channel_versions": {"messages": "1.0"},
        "versions_seen": {},
    }

    saved_a = await saver.aput(cfg_a, cp_a, {"source": "loop", "step": 1}, {"messages": "1.0"})
    await saver.aput_writes(saved_a, [("messages", "a2")], task_id="task-a")
    await saver.aput(cfg_b, cp_b, {"source": "input", "step": 0}, {"messages": "1.0"})

    got_a = await saver.aget_tuple({"configurable": {"thread_id": "thread_async_a"}})
    assert got_a is not None
    assert got_a.checkpoint["channel_values"] == {"messages": ["a1"]}

    listed_a = [item async for item in saver.alist({"configurable": {"thread_id": "thread_async_a"}}, filter={"source": "loop"})]
    assert len(listed_a) == 1

    await saver.adelete_thread("thread_async_a")
    assert await saver.aget_tuple({"configurable": {"thread_id": "thread_async_a"}}) is None
    assert await saver.aget_tuple({"configurable": {"thread_id": "thread_async_b"}}) is not None

    with SessionLocal() as db:
        assert db.query(AgentCheckpoint).filter_by(thread_id="thread_async_a").count() == 0
        assert db.query(AgentCheckpointBlob).filter_by(thread_id="thread_async_a").count() == 0
        assert db.query(AgentCheckpointWrite).filter_by(thread_id="thread_async_a").count() == 0


def test_migrate_rls_covers_all_internal_tables():
    table_names = {model.__tablename__ for model in RLS_PROTECTED_MODELS}
    assert {
        "daily_quotas",
        "quota_reservations",
        "generation_details",
        "user_preferences",
        "user_memories",
        "agent_approvals",
        "agent_checkpoints",
        "agent_checkpoint_blobs",
        "agent_checkpoint_writes",
    }.issubset(table_names)
