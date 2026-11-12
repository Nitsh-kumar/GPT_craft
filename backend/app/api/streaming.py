"""Listen for disconnects even on ASGI 2.4+, while a provider is waiting."""
import anyio
from fastapi.responses import StreamingResponse


class CancellableStreamingResponse(StreamingResponse):
    def __init__(self, *args, on_disconnect, **kwargs):
        super().__init__(*args, **kwargs)
        self.on_disconnect = on_disconnect

    async def __call__(self, scope, receive, send):
        async with anyio.create_task_group() as group:
            async def deliver():
                try:
                    await self.stream_response(send)
                finally:
                    # A disconnect during send can leave an async generator
                    # suspended at yield. Close it explicitly to settle usage.
                    with anyio.CancelScope(shield=True):
                        await self.body_iterator.aclose()
                    group.cancel_scope.cancel()
            group.start_soon(deliver)
            try:
                await self.listen_for_disconnect(receive)
                self.on_disconnect()
            finally:
                group.cancel_scope.cancel()
        if self.background is not None:
            await self.background()
