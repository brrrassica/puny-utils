import socket
import struct
import time
import random
import hashlib
import sys
import argparse

# ----------------------------------------------------------------------
# Helper functions
# ----------------------------------------------------------------------
def recv_all(sock: socket.socket, n: int) -> bytes:
    """
    Receive exactly *n* bytes from *sock*.
    Raises IOError if the connection closes before *n* bytes are read.
    """
    data = b""
    while len(data) < n:
        chunk = sock.recv(n - len(data))
        if not chunk:
            raise IOError(f"Unexpected EOF while reading {n} bytes (got {len(data)})")
        data += chunk
    return data


def double_sha256(b: bytes) -> bytes:
    return hashlib.sha256(hashlib.sha256(b).digest()).digest()


# ----------------------------------------------------------------------
# Message construction
# ----------------------------------------------------------------------
MAGIC_MAINNET = 0xD9B4BEF9 

def make_version_payload(
    version: int = 70015,
    services: int = 0,
    timestamp: int = None,
    addr_recv_ip: str = "0.0.0.0",
    addr_recv_port: int = 8333,
    addr_from_ip: str = "0.0.0.0",
    addr_from_port: int = 8333,
    nonce: int = None,
    user_agent: str = "/myclient:0.1/",
    start_height: int = 0,
    relay: bool = False,
) -> bytes:

    """
    Build the payload for the `version` message.
    The layout follows the Bitcoin protocol spec.
    """
    if timestamp is None:
        timestamp = int(time.time())
    if nonce is None:
        nonce = random.getrandbits(64)

    # Helper to pack an IPv6‑mapped IPv4 address
    def pack_ip(ip_str: str) -> bytes:
        ipv4 = socket.inet_aton(ip_str)
        return b"\x00" * 10 + b"\xff\xff" + ipv4

    # User‑agent is a var_str: first a CompactSize uint, then the string bytes
    user_agent_bytes = user_agent.encode("utf-8")
    user_agent_len = len(user_agent_bytes)
    user_agent_varstr = struct.pack("<B", user_agent_len) + user_agent_bytes

    payload = struct.pack(
        "<iQQ26s26sQ",                     # version, services, timestamp, addr_recv, addr_from, nonce
        version,
        services,
        timestamp,
        struct.pack("<Q16sH", services, pack_ip(addr_recv_ip), addr_recv_port),
        struct.pack("<Q16sH", services, pack_ip(addr_from_ip), addr_from_port),
        nonce,
    )
    payload += user_agent_varstr
    payload += struct.pack("<i?", start_height, relay)
    return payload


def make_message(command: str, payload: bytes) -> bytes:
    """
    Wrap *payload* into a Bitcoin P2P message with the given *command*.
    """
    command_padded = command.encode("ascii") + b"\x00" * (12 - len(command))
    checksum = double_sha256(payload)[:4]
    header = struct.pack("<I12sI4s", MAGIC_MAINNET, command_padded, len(payload), checksum)
    return header + payload


# ----------------------------------------------------------------------
# Message parsing
# ----------------------------------------------------------------------
def read_msg(sock: socket.socket) -> tuple[str, bytes]:
    """
    Read a single Bitcoin P2P message from *sock*.
    Returns (command, payload).
    Raises IOError on EOF or malformed data.
    """
    # 1️⃣ Read the 24‑byte header (may require several recv calls)
    header = recv_all(sock, 24)

    # 2️⃣ Unpack the header
    magic, command_raw, length, checksum = struct.unpack("<I12sI4s", header)

    if magic != MAGIC_MAINNET:
        raise IOError(f"Invalid magic {magic:#x}")

    command = command_raw.rstrip(b"\x00").decode("ascii")

    # 3️⃣ Read the payload (exactly *length* bytes)
    payload = recv_all(sock, length)

    # 4️⃣ Verify checksum
    if double_sha256(payload)[:4] != checksum:
        raise IOError(f"Checksum mismatch for command {command}")

    return command, payload


# ----------------------------------------------------------------------
# Addr message decoding
# ----------------------------------------------------------------------
def decode_addr_payload(payload: bytes) -> list[dict]:
    """
    Decode an `addr` message payload.
    Returns a list of dictionaries with the peer information.
    """
    # Parse CompactSize count
    first = payload[0]
    if first < 0xFD:
        count = first
        offset = 1
    elif first == 0xFD:
        count = struct.unpack_from("<H", payload, 1)[0]
        offset = 3
    elif first == 0xFE:
        count = struct.unpack_from("<I", payload, 1)[0]
        offset = 5
    else:  # 0xFF
        count = struct.unpack_from("<Q", payload, 1)[0]
        offset = 9
    #print(f"DEBUG addr payload count={count}")
    peers = []

    for _ in range(count):
        # each entry: timestamp (4), services (8), IPv6 (16), port (2)
        if offset + 30 > len(payload):
            raise IOError("Truncated addr entry")
        ts, services = struct.unpack_from("<I Q", payload, offset)
        offset += 12
        ip_bytes = payload[offset : offset + 16]
        offset += 16
        port = struct.unpack_from(">H", payload, offset)[0]  # network byte order
        offset += 2
        #print(f"DEBUG raw entry: ts={ts}, services={services}, ip_bytes={ip_bytes.hex()}, port={port}")

        # Convert IPv4‑compatible or IPv4‑mapped IPv6 to dotted‑quad if applicable
        if ip_bytes[:12] == b"\x00" * 12:
            ip = socket.inet_ntop(socket.AF_INET, ip_bytes[12:])
        elif ip_bytes[:10] == b"\x00" * 10 + b"\xff\xff":
            ip = socket.inet_ntop(socket.AF_INET, ip_bytes[12:])
        else:
            ip = socket.inet_ntop(socket.AF_INET6, ip_bytes)

        peers.append(
            {
                "timestamp": ts,
                "services": services,
                "ip": ip,
                "port": port,
            }
        )
    return peers


# ----------------------------------------------------------------------
# Main routine
# ----------------------------------------------------------------------
def main(host: str, port: int):
    print(f"Connecting to {host}:{port} …")
    with socket.create_connection((host, port), timeout=10) as s:
        # Send version
        version_payload = make_version_payload()
        s.sendall(make_message("version", version_payload))
        print("→ version sent")

        #  Expect version → verack
        for _ in range(2):
            cmd, payload = read_msg(s)
            print(f"← {cmd} ({len(payload)} bytes)")
            if cmd == "version":
                # Respond with verack
                s.sendall(make_message("verack", b""))
                print("→ verack sent")
            elif cmd == "verack":
                continue
            else:
                pass

        # Send getaddr
        s.sendall(make_message("getaddr", b""))
        print("→ getaddr sent")

        # Wait for addr (may be preceded by ping/pong etc.)
        while True:
            cmd, payload = read_msg(s)
            print(f"← {cmd} ({len(payload)} bytes)")
            if cmd == "addr":
                peers = decode_addr_payload(payload)
                print("\n=== Peer list ===")
                for p in peers:
                    ts = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(p["timestamp"]))
                    print(f"{p['ip']}:{p['port']}  services={p['services']}  time={ts}")
                break
            else:
                continue


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Connect to a Bitcoin node and retrieve peer addresses.")
    parser.add_argument("host", nargs="?", default="corn.alatcerdas.tech", help="Hostname or IP address of the Bitcoin node")
    parser.add_argument("port", nargs="?", type=int, default=8333, help="Port number of the Bitcoin node")
    args = parser.parse_args()
    main(args.host, args.port)