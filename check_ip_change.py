# Don't forget to remove entries from the hosts file and flush the dns
import configparser
import socket

config = configparser.ConfigParser()
if not config.read('config.ini'):
    raise RuntimeError('config.ini not found')
to_update = []
for k, v in config['Proxied'].items():
    v = v.split()
    host, port, ip = v
    host_ip = socket.gethostbyname(host)
    if host_ip != ip:
        to_update.append(f'{k} = {host} {port} {host_ip}')
if to_update:
    print('Please, update the config ini:')
    for el in to_update:
        print(el)
else:
    print('config.ini is up to date')
