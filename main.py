import asyncio
import configparser
import socket

from proxy import TransparentProxyServer


async def main():
    config = configparser.ConfigParser()
    if not config.read('config.ini'):
        raise RuntimeError('config.ini not found')
    proxy_host = config.get('Proxy', 'proxy_host')
    proxy_port = config.getint('Proxy', 'proxy_port')
    addr = config.get('Proxy', 'assign_loopback_from')
    addr = int.from_bytes(socket.inet_aton(addr), byteorder='big')
    tasks = []
    print('# PASTE THIS INTO THE hosts FILE')
    for el in config['Proxied'].values():
        host, port, host_ip = el.split()
        port = int(port)
        server = TransparentProxyServer(host, port, host_ip, proxy_host, proxy_port,
                                        upstream_proxy_type='socks5')
        bind_host = socket.inet_ntoa(int.to_bytes(addr, byteorder='big', length=4))
        tasks.append(asyncio.create_task(server.run_forever(host=bind_host, port=port)))
        addr += 1
        print(f'{bind_host} {host}')
    print('# END HOSTS ENTRIES')
    for task in tasks:
        await task


if __name__ == '__main__':
    asyncio.run(main())
