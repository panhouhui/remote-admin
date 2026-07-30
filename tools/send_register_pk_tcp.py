#!/usr/bin/env python3
import argparse
import os
import socket
import struct
import time
import uuid


def bytes_field(field_no, value):
    if len(value) >= 128:
        raise ValueError("this test encoder only supports short fields")
    return bytes([(field_no << 3) | 2, len(value)]) + value


def build_register_pk(peer_id, machine_uuid=None, pk=None):
    peer_id = peer_id.encode("ascii")
    machine_uuid = (machine_uuid or str(uuid.uuid4())).encode("ascii")
    pk = pk or os.urandom(32)
    inner = bytes_field(1, peer_id) + bytes_field(2, machine_uuid) + bytes_field(3, pk)
    return bytes([(15 << 3) | 2, len(inner)]) + inner, machine_uuid, pk


def main():
    parser = argparse.ArgumentParser(description="Send a RegisterPk payload through TCP proxy")
    parser.add_argument("--host", default="103.205.240.70")
    parser.add_argument("--port", type=int, default=21120)
    parser.add_argument("--id", default="79072974")
    parser.add_argument("--count", type=int, default=1)
    parser.add_argument("--interval", type=float, default=7.0)
    args = parser.parse_args()

    payload, machine_uuid, pk = build_register_pk(args.id)
    print("utc_start=", time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()))
    print("tcp_proxy=", f"{args.host}:{args.port}")
    print("id=", args.id)
    print("uuid=", machine_uuid.decode("ascii"))
    print("pk_len=", len(pk))
    print("wire_len=", len(payload))

    for i in range(args.count):
        with socket.create_connection((args.host, args.port), timeout=5) as conn:
            conn.settimeout(5)
            conn.sendall(struct.pack("!I", len(payload)) + payload)
            raw_len = conn.recv(4)
            if raw_len in (b"OK\n", b"OK\r"):
                response_len = 0
                status = raw_len.decode("utf-8", errors="replace").strip()
                response = b""
            elif raw_len.startswith(b"OK\n") or raw_len.startswith(b"ERR "):
                response_len = 0
                status = (raw_len + conn.recv(4096)).decode("utf-8", errors="replace").strip()
                response = b""
            else:
                if len(raw_len) != 4:
                    raise ConnectionError("proxy closed before response length")
                (response_len,) = struct.unpack("!I", raw_len)
                response = b""
                while len(response) < response_len:
                    chunk = conn.recv(response_len - len(response))
                    if not chunk:
                        break
                    response += chunk
                status = conn.recv(4096).decode("utf-8", errors="replace").strip()
        print(
            "round=", i + 1,
            "utc=", time.strftime("%H:%M:%S", time.gmtime()),
            "response_len=", response_len,
            "status=", status,
        )
        if i + 1 < args.count:
            time.sleep(args.interval)


if __name__ == "__main__":
    main()
