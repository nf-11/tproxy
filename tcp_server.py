import asyncio
import traceback

import tcp


class TCPServer:
    def __init__(self):
        self.tasks = set()

    async def on_connect(self, connection: tcp.TCPStream):
        pass

    async def _on_connect(self, reader, writer):
        try:
            await self.on_connect(tcp.TCPStream(reader=reader, writer=writer))
        except Exception as ex:
            writer.close()
            traceback.print_exception(ex)

    async def _on_connect_wrapper(self, reader, writer):
        task = asyncio.create_task(self._on_connect(reader, writer))
        self.tasks.add(task)
        task.add_done_callback(self.tasks.remove)

    async def run(self, host: str, port: int) -> None:
        await asyncio.start_server(self._on_connect_wrapper, host, port)

    async def run_forever(self, host: str, port: int) -> None:
        await self.run(host, port)
        await asyncio.Event().wait()
