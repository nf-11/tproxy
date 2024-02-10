import asyncio
import socket
from typing import Literal

import tcp
import tcp_server


class TransparentProxyServer(tcp_server.TCPServer):
    def __init__(self, proxied_host: str, proxied_port: int, proxied_host_ip: str,
                 proxy_host: str, proxy_port: int,
                 upstream_proxy_type: Literal['socks5', 'https'] = 'socks5', timeout: float = 5.0,
                 use_hostname: bool = False):
        super().__init__()
        self.proxied_host = proxied_host
        self.proxied_port = proxied_port
        self.proxied_host_ip = proxied_host_ip
        self.proxy_host = proxy_host
        self.proxy_port = proxy_port
        self.upstream_proxy_type = upstream_proxy_type
        self.timeout = timeout
        self.use_hostname = use_hostname

    def _wait_for(self, fut):
        return asyncio.wait_for(fut, self.timeout)

    @staticmethod
    async def _proxy(s_from: tcp.TCPStream, s_to: tcp.TCPStream):
        while True:
            data = await s_from.read_any()
            if not data:
                s_to.close()
                break
            s_to.write(data)

    async def _http_connect(self, connection: tcp.TCPStream):
        host = self.proxied_host if self.use_hostname else self.proxy_host
        connection.write(f'CONNECT {host}:{self.proxied_port} HTTP/1.0\r\n\r\n'.encode())
        response = (await self._wait_for(connection.read_line())).strip().decode()
        response = response.split(' ')
        http_ver, http_code, *reason_phrase = response
        http_code = int(http_code)
        if http_code < 200 or http_code > 299:
            raise ConnectionError(f"Server returned non-200 code: {http_code}")
        line = (await self._wait_for(connection.read_line())).strip()
        if line:
            raise NotImplementedError(f"Headers are not implemented")

    async def _socks5_handshake(self, connection: tcp.TCPStream):
        connection.write(b'\x05\x01\x00')
        if (await self._wait_for(connection.read(2))) != b'\x05\x00':
            raise ConnectionError("Bad SOCKS5 Server Choice")
        connection.write(b'\x05\x01\x00')
        if self.use_hostname:
            connection.write(b'\x03')
            proxied_host = self.proxied_host.encode()
            connection.write(len(proxied_host).to_bytes(length=1, byteorder='big'))
            connection.write(proxied_host)
        else:
            connection.write(b'\x01')
            connection.write(socket.inet_aton(self.proxied_host_ip))
        connection.write(self.proxied_port.to_bytes(length=2, byteorder='big'))
        _ver, status, _rsv = await self._wait_for(connection.read(3))
        if status:
            raise ConnectionError(f"SOCKS5 connection error ({status})")
        addr_type = int.from_bytes(await self._wait_for(connection.read(1)), byteorder='big')
        if addr_type == 1:
            await self._wait_for(connection.read(4))
        elif addr_type == 3:
            domain_name_length = int.from_bytes(await self._wait_for(connection.read(1)), byteorder='big')
            await self._wait_for(connection.read(domain_name_length))
        elif addr_type == 4:
            await self._wait_for(connection.read(16))
        else:
            raise ConnectionError(f"Unknown address type ({addr_type})")
        await self._wait_for(connection.read(2))

    async def on_connect(self, connection: tcp.TCPStream):
        upstream_conn = tcp.TCPStream()
        try:
            await self._wait_for(upstream_conn.connect(self.proxy_host, self.proxy_port))
            if self.upstream_proxy_type == 'socks5':
                await self._socks5_handshake(upstream_conn)
            elif self.upstream_proxy_type == 'https':
                await self._http_connect(upstream_conn)
            else:
                raise NotImplementedError(f'{self.upstream_proxy_type} upstream proxy is not supported')
            task_1 = asyncio.create_task(self._proxy(connection, upstream_conn))
            task_2 = asyncio.create_task(self._proxy(upstream_conn, connection))
            await task_1
            await task_2
        finally:
            connection.close()
            upstream_conn.close()
