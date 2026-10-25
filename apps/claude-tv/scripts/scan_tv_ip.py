import socket
import concurrent.futures

def check_ip(ip):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(0.3)
    try:
        res = sock.connect_ex((ip, 5555))
        if res == 0:
            return ip
    except Exception:
        pass
    finally:
        sock.close()
    return None

ips = [f"192.168.76.{i}" for i in range(1, 255)]
print("Escaneando sub-rede 192.168.76.0/24 na porta 5555...")

with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
    results = executor.map(check_ip, ips)
    found = [ip for ip in results if ip]

if found:
    for ip in found:
        print(f"TV encontrada em: {ip}")
else:
    print("Nenhum dispositivo com porta 5555 aberta encontrado.")
