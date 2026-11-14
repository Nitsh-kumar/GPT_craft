import pytest
from langgraph.checkpoint.base import WRITES_IDX_MAP
from sqlalchemy import text
from sqlalchemy.dialects import postgresql

import app.db.models  # noqa: F401 - register all ORM models on Base.metadata
from app.ai.graph.agent import checkpointer as graph_checkpointer
from app.ai.graph.checkpointer import SQLAlchemyCheckpointSaver
from app.db.base import Base
from app.db.migrate import RLS_PROTECTED_MODELS, migrate, rls_enable_statements
from app.db.models import (
    AgentCheckpoint,
    AgentCheckpointBlob,
    AgentCheckpointWrite,
    Conversation,
    DailyQuota,
    Message,
    OAuthAccount,
    Plans,
    User,
)
from app.db.session import SessionLocal, engine


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
    expected_tables = {
        "plans",
        "users",
        "oauth_accounts",
        "user_daily_limit",
        "conversations",
        "messages",
        "daily_quotas",
        "quota_reservations",
        "generation_details",
        "user_preferences",
        "user_memories",
        "agent_approvals",
        "agent_checkpoints",
        "agent_checkpoint_blobs",
        "agent_checkpoint_writes",
    }
    assert expected_tables.issubset(table_names)
    assert set(Base.metadata.tables.keys()).issubset(table_names)
    assert table_names == set(Base.metadata.tables.keys())


def test_rls_enable_statements_cover_all_metadata_tables():
    pg_dialect = postgresql.dialect()
    statements = rls_enable_statements(pg_dialect)
    preparer = pg_dialect.identifier_preparer

    expected_statements = {
        f"ALTER TABLE {preparer.format_table(table)} ENABLE ROW LEVEL SECURITY"
        for table in Base.metadata.tables.values()
    }
    assert len(statements) == len(Base.metadata.tables)
    assert set(statements) == expected_statements


def test_migrate_is_idempotent_preserves_data_and_postgres_rls(registered):
    data, _ = registered()
    user_id = data["user"]["id"]

    with SessionLocal() as db:
        convo = Conversation(user_id=user_id, title="Pre-migration chat")
        db.add(convo)
        db.flush()
        msg = Message(conversation_id=convo.id, role="user", content="hello")
        oauth = OAuthAccount(
            user_id=user_id,
            provider="google",
            provider_user_id="google-sub-123",
            access_token="tok-123",
        )
        db.add_all([msg, oauth])
        db.commit()
        convo_id = convo.id
        msg_id = msg.id
        oauth_id = oauth.id

    saver = SQLAlchemyCheckpointSaver(session_factory=SessionLocal)
    saver.put(
        {"configurable": {"thread_id": "thread_migrate_rls", "checkpoint_ns": ""}},
        {
            "v": 1,
            "id": "00000000-0000-0000-0000-000000000099",
            "ts": "2026-11-14T00:00:00+00:00",
            "channel_values": {"messages": ["persisted"]},
            "channel_versions": {"messages": "1.0"},
            "versions_seen": {},
        },
        {"source": "input", "step": 0},
        {"messages": "1.0"},
    )

    migrate(engine)
    migrate(engine)

    with SessionLocal() as db:
        assert db.query(Plans).count() >= 3
        assert db.get(User, user_id) is not None
        assert db.get(OAuthAccount, oauth_id) is not None
        assert db.get(Conversation, convo_id) is not None
        assert db.get(Message, msg_id) is not None
        assert db.query(DailyQuota).filter_by(user_id=user_id).count() == 1
        assert db.query(AgentCheckpoint).filter_by(thread_id="thread_migrate_rls").count() == 1

        if engine.dialect.name == "postgresql":
            rls_rows = db.execute(
                text(
                    "SELECT tablename, rowsecurity FROM pg_tables "
                    "WHERE schemaname = current_schema()"
                )
            ).all()
            rls_by_table = {row.tablename: row.rowsecurity for row in rls_rows}
            for table_name in Base.metadata.tables:
                assert rls_by_table.get(table_name) is True, (
                    f"Expected RLS enabled on PostgreSQL table {table_name!r}"
                )

            policies = db.execute(
                text(
                    "SELECT tablename, policyname FROM pg_policies "
                    "WHERE schemaname = current_schema()"
                )
            ).all()
            backend_policies = [
                row for row in policies if row.tablename in Base.metadata.tables
            ]
            assert backend_policies == []
