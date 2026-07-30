#!/usr/bin/env python3
import argparse
import socket
import struct
import threading
import time


def checksum(data: bytes) -> int:
    if len(data) % 2:
        data += b"\0"
    total = sum(struct.unpack("!%dH" % (len(data) // 2), data))
    total = (total >> 16) + (total & 0xFFFF)
    total += total >> 16
    return (~total) & 0xFFFF


def read_exact(sock: socket.socket, size: int) -> bytes:
    out = bytearray()
    while len(out) < size:
        chunk = sock.recv(size - len(out))
        if not chunk:
            raise EOFError("connection closed")
        out.extend(chunk)
    return bytes(out)


def read_varint(data: bytes, pos: int):
    value = 0
    shift = 0
    while pos < len(data):
        b = data[pos]
        pos += 1
        value |= (b & 0x7F) << shift
        if not (b & 0x80):
            return value, pos
        shift += 7
        if shift > 63:
            break
    raise ValueError("bad varint")


def parse_len_field(data: bytes, wanted_field: int):
    pos = 0
    while pos < len(data):
        tag, pos = read_varint(data, pos)
        field_no = tag >> 3
        wire_type = tag & 7
        if wire_type == 0:
            _, pos = read_varint(data, pos)
        elif wire_type == 1:
            pos += 8
        elif wire_type == 2:
            size, pos = read_varint(data, pos)
            value = data[pos : pos + size]
            pos += size
            if field_no == wanted_field:
                return value
        elif wire_type == 5:
            pos += 4
        else:
            break
    return b""


def parse_peer_id(payload: bytes) -> str:
    # RendezvousMessage.register_peer = 6, register_pk = 15.
    inner = parse_len_field(payload, 6) or parse_len_field(payload, 15)
    if not inner:
        return ""
    peer_id = parse_len_field(inner, 1)
    return peer_id.decode("ascii", "ignore")


def raw_udp_send(raw_sock, payload: bytes, src_ip: str, src_port: int, dst_ip: str, dst_port: int):
    src = socket.inet_aton(src_ip)
    dst = socket.inet_aton(dst_ip)
    udp_len = 8 + len(payload)
    ip_len = 20 + udp_len
    ip_id = int(time.time() * 1000) & 0xFFFF

    ip_header = struct.pack(
        "!BBHHHBBH4s4s",
        0x45,
        0,
        ip_len,
        ip_id,
        0,
        64,
        socket.IPPROTO_UDP,
        0,
        src,
        dst,
    )
    ip_header = ip_header[:10] + struct.pack("!H", checksum(ip_header)) + ip_header[12:]

    udp_header = struct.pack("!HHHH", src_port, dst_port, udp_len, 0)
    pseudo = src + dst + struct.pack("!BBH", 0, socket.IPPROTO_UDP, udp_len)
    udp_sum = checksum(pseudo + udp_header + payload)
    udp_header = struct.pack("!HHHH", src_port, dst_port, udp_len, udp_sum)

    packet = ip_header + udp_header + payload
    return raw_sock.sendto(packet, (dst_ip, dst_port))


def handle_client(conn: socket.socket, addr, args, raw_sock):
    client_ip, client_port = addr[0], addr[1]
    count = 0
    try:
        conn.settimeout(args.idle_timeout)
        while True:
            header = read_exact(conn, 4)
            size = struct.unpack("!I", header)[0]
            if size <= 0 or size > args.max_payload:
                raise ValueError(f"bad payload size {size}")
            payload = read_exact(conn, size)
            count += 1
            peer_id = parse_peer_id(payload)
            sent = raw_udp_send(
                raw_sock,
                payload,
                client_ip,
                client_port,
                args.udp_host,
                args.udp_port,
            )
            response = (
                f"OK mode=raw-spoof-persistent count={count} payload_len={len(payload)} "
                f"ip_sent={sent} peer_id={peer_id} spoof_src={client_ip}:{client_port} "
                f"target={args.udp_host}:{args.udp_port} utc={time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}\n"
            )
            print(response.strip(), flush=True)
            conn.sendall(response.encode("utf-8"))
    except Exception as exc:
        print(f"client={client_ip}:{client_port} closed count={count} error={exc}", flush=True)
    finally:
        try:
            conn.close()
        except Exception:
            pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--listen-host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=21120)
    parser.add_argument("--udp-host", default="103.205.240.70")
    parser.add_argument("--udp-port", type=int, default=21116)
    parser.add_argument("--idle-timeout", type=int, default=120)
    parser.add_argument("--max-payload", type=int, default=4096)
    args = parser.parse_args()

    raw_sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_RAW)
    raw_sock.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((args.listen_host, args.port))
    srv.listen(128)
    print(
        f"listening tcp {args.listen_host}:{args.port}, persistent raw-spoof udp {args.udp_host}:{args.udp_port}",
        flush=True,
    )
    while True:
        conn, addr = srv.accept()
        print(f"accepted {addr[0]}:{addr[1]}", flush=True)
        threading.Thread(target=handle_client, args=(conn, addr, args, raw_sock), daemon=True).start()


if __name__ == "__main__":
    main()
