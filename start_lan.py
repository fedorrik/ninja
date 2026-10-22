#!/usr/bin/env python3
"""Start the game on all local IPv4 interfaces; no router configuration needed."""
import argparse
import ipaddress
import socket
import sys
from http.server import ThreadingHTTPServer

def local_addresses(router):
    addresses = []
    # UDP connect selects a route; no payload is sent to the router.
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.connect((router, 80))
            addresses.append(probe.getsockname()[0])
    except OSError:
        pass
    try:
        addresses.extend(item[4][0] for item in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET))
    except OSError:
        pass
    result = []
    for address in addresses:
        ip = ipaddress.ip_address(address)
        if not ip.is_loopback and not ip.is_unspecified and not ip.is_link_local and address not in result:
            result.append(address)
    return result

def main():
    if sys.version_info < (3, 11):
        print('Нужен Python 3.11 или новее.')
        return 1
    parser = argparse.ArgumentParser(description='Игра для устройств в одной Wi-Fi-сети')
    parser.add_argument('--port', type=int, default=8080, help='Порт сервера (по умолчанию 8080)')
    parser.add_argument('--router', default='192.168.3.1', help='Адрес роутера для определения сетевого интерфейса')
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error('Порт должен быть от 1 до 65535')
    try:
        ipaddress.IPv4Address(args.router)
    except ValueError:
        parser.error('Укажите IPv4-адрес роутера, например 192.168.3.1')
    from server import Handler
    try:
        httpd = ThreadingHTTPServer(('0.0.0.0', args.port), Handler)
    except OSError as error:
        print(f'Не удалось открыть порт {args.port}: {error}')
        print('Остановите уже запущенный сервер или выберите другой порт:')
        print('python start_lan.py --port 8081')
        return 1
    httpd.daemon_threads = True
    with httpd:
        print('\nИгра запущена для локальной сети.\n')
        addresses = local_addresses(args.router)
        if addresses:
            print('Откройте на компьютере и телефонах один из этих адресов:')
            for address in addresses:
                print(f'  http://{address}:{args.port}')
            if len(addresses) > 1:
                print('Выберите адрес Wi-Fi или Ethernet, к которому подключены остальные игроки.')
        else:
            print('Не удалось определить IP. Найдите IPv4 компьютера в настройках сети')
            print(f'и откройте http://IP_КОМПЬЮТЕРА:{args.port} на всех устройствах.')
        print(f'Только на этом компьютере также доступно: http://127.0.0.1:{args.port}')
        print(f'Адрес {args.router} относится к роутеру, а не к игре.')
        print('Все устройства должны быть в одной локальной сети.')
        print('Если Windows спросит, разрешите доступ для частной сети.')
        print('Оставьте это окно открытым. Остановка: Ctrl+C.\n', flush=True)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print('\nСервер остановлен.')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
