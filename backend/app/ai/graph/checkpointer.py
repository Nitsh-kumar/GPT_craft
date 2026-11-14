"""SQLAlchemy ORM-backed LangGraph checkpoint saver (SQLite & PostgreSQL)."""
from __future__ import annotations

import asyncio
import random
from collections.abc import AsyncIterator, Iterator, Sequence
from typing import Any

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import (
    WRITES_IDX_MAP,
    BaseCheckpointSaver,
    ChannelVersions,
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
    SerializerProtocol,
    get_checkpoint_id,
    get_checkpoint_metadata,
    writes_sort_key,
)
from sqlalchemy import delete, select

from app.db.crud_token import insert_once
from app.db.models import AgentCheckpoint, AgentCheckpointBlob, AgentCheckpointWrite
from app.db.session import SessionLocal


class SQLAlchemyCheckpointSaver(BaseCheckpointSaver[str]):
    """Persists LangGraph checkpoints, blobs, and pending writes via SQLAlchemy."""

    def __init__(
        self,
        session_factory=SessionLocal,
        *,
        serde: SerializerProtocol | None = None,
    ) -> None:
        super().__init__(serde=serde)
        self.session_factory = session_factory

    def _load_blobs(
        self,
        db,
        thread_id: str,
        checkpoint_ns: str,
        versions: ChannelVersions,
    ) -> dict[str, Any]:
        if not versions:
            return {}
        version_map = {str(k): str(v) for k, v in versions.items()}
        rows = db.scalars(
            select(AgentCheckpointBlob).where(
                AgentCheckpointBlob.thread_id == thread_id,
                AgentCheckpointBlob.checkpoint_ns == checkpoint_ns,
                AgentCheckpointBlob.channel.in_(list(version_map.keys())),
            )
        ).all()
        result: dict[str, Any] = {}
        for row in rows:
            if version_map.get(row.channel) != row.version:
                continue
            if row.blob_type == "empty" or row.blob_data is None:
                continue
            result[row.channel] = self.serde.loads_typed((row.blob_type, bytes(row.blob_data)))
        return result

    def _load_pending_writes(
        self,
        db,
        thread_id: str,
        checkpoint_ns: str,
        checkpoint_id: str,
    ) -> list[tuple[str, str, Any]]:
        rows = db.scalars(
            select(AgentCheckpointWrite).where(
                AgentCheckpointWrite.thread_id == thread_id,
                AgentCheckpointWrite.checkpoint_ns == checkpoint_ns,
                AgentCheckpointWrite.checkpoint_id == checkpoint_id,
            )
        ).all()
        rows_sorted = sorted(
            rows,
            key=lambda w: writes_sort_key(w.task_path, w.task_id, w.idx),
        )
        return [
            (w.task_id, w.channel, self.serde.loads_typed((w.write_type, bytes(w.write_data))))
            for w in rows_sorted
        ]

    def _build_tuple(
        self,
        db,
        row: AgentCheckpoint,
        *,
        config: RunnableConfig | None = None,
    ) -> CheckpointTuple:
        checkpoint_data: Checkpoint = self.serde.loads_typed(
            (row.checkpoint_type, bytes(row.checkpoint_data))
        )
        metadata: CheckpointMetadata = self.serde.loads_typed(
            (row.metadata_type, bytes(row.metadata_data))
        )
        channel_values = self._load_blobs(
            db,
            row.thread_id,
            row.checkpoint_ns,
            checkpoint_data["channel_versions"],
        )
        pending_writes = self._load_pending_writes(
            db,
            row.thread_id,
            row.checkpoint_ns,
            row.checkpoint_id,
        )
        resolved_config: RunnableConfig = config or {
            "configurable": {
                "thread_id": row.thread_id,
                "checkpoint_ns": row.checkpoint_ns,
                "checkpoint_id": row.checkpoint_id,
            }
        }
        parent_config: RunnableConfig | None = (
            {
                "configurable": {
                    "thread_id": row.thread_id,
                    "checkpoint_ns": row.checkpoint_ns,
                    "checkpoint_id": row.parent_checkpoint_id,
                }
            }
            if row.parent_checkpoint_id
            else None
        )
        return CheckpointTuple(
            config=resolved_config,
            checkpoint={
                **checkpoint_data,
                "channel_values": channel_values,
            },
            metadata=metadata,
            parent_config=parent_config,
            pending_writes=pending_writes,
        )

    def get_tuple(self, config: RunnableConfig) -> CheckpointTuple | None:
        thread_id = str(config["configurable"]["thread_id"])
        checkpoint_ns = str(config["configurable"].get("checkpoint_ns", ""))
        checkpoint_id = get_checkpoint_id(config)

        with self.session_factory() as db:
            stmt = select(AgentCheckpoint).where(
                AgentCheckpoint.thread_id == thread_id,
                AgentCheckpoint.checkpoint_ns == checkpoint_ns,
            )
            if checkpoint_id:
                stmt = stmt.where(AgentCheckpoint.checkpoint_id == checkpoint_id)
                row = db.scalar(stmt)
                if row is None:
                    return None
                return self._build_tuple(db, row, config=config)

            row = db.scalar(
                stmt.order_by(AgentCheckpoint.checkpoint_id.desc()).limit(1)
            )
            if row is None:
                return None
            return self._build_tuple(db, row)

    def list(
        self,
        config: RunnableConfig | None,
        *,
        filter: dict[str, Any] | None = None,
        before: RunnableConfig | None = None,
        limit: int | None = None,
    ) -> Iterator[CheckpointTuple]:
        stmt = select(AgentCheckpoint).order_by(AgentCheckpoint.checkpoint_id.desc())
        if config:
            configurable = config.get("configurable", {})
            if "thread_id" in configurable:
                stmt = stmt.where(AgentCheckpoint.thread_id == str(configurable["thread_id"]))
            if "checkpoint_ns" in configurable and configurable["checkpoint_ns"] is not None:
                stmt = stmt.where(
                    AgentCheckpoint.checkpoint_ns == str(configurable["checkpoint_ns"])
                )
            if cfg_cp_id := get_checkpoint_id(config):
                stmt = stmt.where(AgentCheckpoint.checkpoint_id == cfg_cp_id)

        if before and (before_cp_id := get_checkpoint_id(before)):
            stmt = stmt.where(AgentCheckpoint.checkpoint_id < before_cp_id)

        tuples: list[CheckpointTuple] = []
        remaining = limit
        with self.session_factory() as db:
            for row in db.scalars(stmt):
                metadata = self.serde.loads_typed((row.metadata_type, bytes(row.metadata_data)))
                if filter and not all(
                    query_val == metadata.get(query_key)
                    for query_key, query_val in filter.items()
                ):
                    continue
                if remaining is not None:
                    if remaining <= 0:
                        break
                    remaining -= 1
                tuples.append(self._build_tuple(db, row))

        yield from tuples

    def put(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> RunnableConfig:
        c = checkpoint.copy()
        thread_id = str(config["configurable"]["thread_id"])
        checkpoint_ns = str(config["configurable"].get("checkpoint_ns", ""))
        parent_checkpoint_id = config["configurable"].get("checkpoint_id")
        values: dict[str, Any] = c.pop("channel_values")  # type: ignore[misc]

        ckpt_type, ckpt_bytes = self.serde.dumps_typed(c)
        meta_type, meta_bytes = self.serde.dumps_typed(get_checkpoint_metadata(config, metadata))

        with self.session_factory() as db:
            for channel, version in new_versions.items():
                if channel in values:
                    blob_type, blob_bytes = self.serde.dumps_typed(values[channel])
                else:
                    blob_type, blob_bytes = ("empty", b"")
                db.merge(
                    AgentCheckpointBlob(
                        thread_id=thread_id,
                        checkpoint_ns=checkpoint_ns,
                        channel=str(channel),
                        version=str(version),
                        blob_type=blob_type,
                        blob_data=blob_bytes,
                    )
                )

            db.merge(
                AgentCheckpoint(
                    thread_id=thread_id,
                    checkpoint_ns=checkpoint_ns,
                    checkpoint_id=str(checkpoint["id"]),
                    parent_checkpoint_id=str(parent_checkpoint_id) if parent_checkpoint_id else None,
                    checkpoint_type=ckpt_type,
                    checkpoint_data=ckpt_bytes,
                    metadata_type=meta_type,
                    metadata_data=meta_bytes,
                )
            )
            db.commit()

        return {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_ns": checkpoint_ns,
                "checkpoint_id": str(checkpoint["id"]),
            }
        }

    def put_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        thread_id = str(config["configurable"]["thread_id"])
        checkpoint_ns = str(config["configurable"].get("checkpoint_ns", ""))
        checkpoint_id = str(config["configurable"]["checkpoint_id"])

        with self.session_factory() as db:
            for idx, (channel, value) in enumerate(writes):
                write_idx = WRITES_IDX_MAP.get(channel, idx)
                write_type, write_bytes = self.serde.dumps_typed(value)
                values_dict = {
                    "thread_id": thread_id,
                    "checkpoint_ns": checkpoint_ns,
                    "checkpoint_id": checkpoint_id,
                    "task_id": str(task_id),
                    "idx": int(write_idx),
                    "channel": str(channel),
                    "write_type": write_type,
                    "write_data": write_bytes,
                    "task_path": str(task_path),
                }
                if write_idx >= 0:
                    insert_once(
                        db,
                        AgentCheckpointWrite,
                        values_dict,
                        ["thread_id", "checkpoint_ns", "checkpoint_id", "task_id", "idx"],
                    )
                else:
                    db.merge(AgentCheckpointWrite(**values_dict))
            db.commit()

    def delete_thread(self, thread_id: str) -> None:
        tid = str(thread_id)
        with self.session_factory() as db:
            db.execute(
                delete(AgentCheckpointWrite).where(AgentCheckpointWrite.thread_id == tid)
            )
            db.execute(
                delete(AgentCheckpointBlob).where(AgentCheckpointBlob.thread_id == tid)
            )
            db.execute(
                delete(AgentCheckpoint).where(AgentCheckpoint.thread_id == tid)
            )
            db.commit()

    def get_next_version(self, current: str | None, channel: None) -> str:
        if current is None:
            current_v = 0
        elif isinstance(current, int):
            current_v = current
        else:
            current_v = int(str(current).split(".")[0])
        next_v = current_v + 1
        next_h = random.random()
        return f"{next_v:032}.{next_h:016}"

    async def aget_tuple(self, config: RunnableConfig) -> CheckpointTuple | None:
        return await asyncio.to_thread(self.get_tuple, config)

    async def alist(
        self,
        config: RunnableConfig | None,
        *,
        filter: dict[str, Any] | None = None,
        before: RunnableConfig | None = None,
        limit: int | None = None,
    ) -> AsyncIterator[CheckpointTuple]:
        items = await asyncio.to_thread(
            lambda: list(self.list(config, filter=filter, before=before, limit=limit))
        )
        for item in items:
            yield item

    async def aput(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> RunnableConfig:
        return await asyncio.to_thread(self.put, config, checkpoint, metadata, new_versions)

    async def aput_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        await asyncio.to_thread(self.put_writes, config, writes, task_id, task_path)

    async def adelete_thread(self, thread_id: str) -> None:
        await asyncio.to_thread(self.delete_thread, thread_id)
