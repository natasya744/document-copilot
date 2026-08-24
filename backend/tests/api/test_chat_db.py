import asyncio
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

from app.database import chats


def _builder(data) -> MagicMock:
    execute = AsyncMock(return_value=MagicMock(data=data))
    builder = MagicMock()
    builder.execute = execute
    builder.eq.return_value = builder
    builder.lt.return_value = builder
    return builder


def _client(data) -> MagicMock:
    table = MagicMock()
    table.select.return_value = _builder(data)
    table.delete.return_value = _builder(None)
    table.update.return_value = _builder(None)
    cli = MagicMock()
    cli.table.return_value = table
    return cli


def _run(coro):
    asyncio.run(coro)


def test_purge_stale_empty_threads_deletes_only_empty_ones():
    empty = uuid.uuid4()
    populated = uuid.uuid4()
    cli = _client(
        [
            {"id": str(empty), "chat_messages": []},
            {"id": str(populated), "chat_messages": [{"id": "m-uuid"}]},
        ]
    )
    user_id = uuid.uuid4()

    _run(chats.purge_stale_empty_threads(cli, user_id, days=7))

    delete = cli.table.return_value.delete
    assert delete.call_count == 1
    delete.return_value.eq.assert_called_once_with("id", str(empty))
    cli.table.return_value.select.return_value.execute.assert_awaited_once()


def test_purge_stale_empty_threads_filters_owner_and_cutoff():
    cli = _client([])
    user_id = uuid.uuid4()

    _run(chats.purge_stale_empty_threads(cli, user_id, days=7))

    builder = cli.table.return_value.select.return_value
    builder.eq.assert_called_once_with("user_id", str(user_id))
    builder.lt.assert_called_once()
    args, _kwargs = builder.lt.call_args
    assert args[0] == "updated_at"
    assert datetime.fromisoformat(args[1]) < datetime.now(UTC)


def test_purge_stale_empty_threads_noop_when_none_stale():
    cli = _client([])
    _run(chats.purge_stale_empty_threads(cli, uuid.uuid4(), days=7))
    cli.table.return_value.delete.assert_not_called()


def test_touch_thread_bumps_updated_at():
    cli = _client(None)
    thread_id = uuid.uuid4()

    _run(chats.touch_thread(cli, thread_id))

    table = cli.table.return_value
    assert table.update.call_count == 1
    table.update.return_value.eq.assert_called_once_with("id", str(thread_id))
    table.update.return_value.execute.assert_awaited_once()