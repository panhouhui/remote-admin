#!/usr/bin/env python3
import argparse
import random
import socket
import struct
import threading
import time

HEARTBEATS = {}
HEARTBEATS_LOCK = threading.Lock()


def read_exact(conn, size):
    data = bytearray()
    while len(data) < size:
        chunk = conn.recv(size - len(data))
        if not chunk:
            raise ConnectionError("connection closed while reading")
        data.extend(chunk)
    return bytes(data)


def checksum(data):
    if len(data) % 2:
        data += b"\x00"
    total = 0
    for i in range(0, len(data), 2):
        total += (data[i] << 8) + data[i + 1]
        total = (total & 0xFFFF) + (total >> 16)
    return (~total) & 0xFFFF


def udp_checksum(src_ip, dst_ip, udp_header, payload):
    pseudo = (
        socket.inet_aton(src_ip)
        + socket.inet_aton(dst_ip)
        + struct.pack("!BBH", 0, socket.IPPROTO_UDP, len(udp_header) + len(payload))
    )
    return checksum(pseudo + udp_header + payload)


def raw_spoof_udp_send(payload, src_ip, src_port, dst_ip, dst_port):
    version_ihl = 0x45
    tos = 0
    total_len = 20 + 8 + len(payload)
    packet_id = random.randint(0, 0xFFFF)
    flags_fragment = 0
    ttl = 64
    proto = socket.IPPROTO_UDP
    ip_check = 0
    src_addr = socket.inet_aton(src_ip)
    dst_addr = socket.inet_aton(dst_ip)
    ip_header = struct.pack(
        "!BBHHHBBH4s4s",
        version_ihl,
        tos,
        total_len,
        packet_id,
        flags_fragment,
        ttl,
        proto,
        ip_check,
        src_addr,
        dst_addr,
    )
    ip_header = ip_header[:10] + struct.pack("!H", checksum(ip_header)) + ip_header[12:]

    udp_len = 8 + len(payload)
    udp_header = struct.pack("!HHHH", src_port, dst_port, udp_len, 0)
    udp_check = udp_checksum(src_ip, dst_ip, udp_header, payload)
    udp_header = struct.pack("!HHHH", src_port, dst_port, udp_len, udp_check)

    raw = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_RAW)
    raw.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
    try:
        return raw.sendto(ip_header + udp_header + payload, (dst_ip, dst_port))
    finally:
        raw.close()


def protobuf_read_varint(data, offset):
    shift = 0
    value = 0
    while offset < len(data):
        b = data[offset]
        offset += 1
        value |= (b & 0x7F) << shift
        if not (b & 0x80):
            return value, offset
        shift += 7
        if shift > 63:
            break
    raise ValueError("invalid protobuf varint")


def protobuf_skip_field(data, offset, wire_type):
    if wire_type == 0:
        _, offset = protobuf_read_varint(data, offset)
        return offset
    if wire_type == 1:
        return offset + 8
    if wire_type == 2:
        size, offset = protobuf_read_varint(data, offset)
        return offset + size
    if wire_type == 5:
        return offset + 4
    raise ValueError(f"unsupported protobuf wire type: {wire_type}")


def extract_nested_string_id(payload, outer_field_no):
    offset = 0
    while offset < len(payload):
        tag, offset = protobuf_read_varint(payload, offset)
        field_no = tag >> 3
        wire_type = tag & 0x07
        if field_no != outer_field_no:
            offset = protobuf_skip_field(payload, offset, wire_type)
            continue
        if wire_type != 2:
            raise ValueError(f"unsupported outer wire type: {wire_type}")
        size, offset = protobuf_read_varint(payload, offset)
        value = payload[offset : offset + size]
        offset += size

        inner_offset = 0
        while inner_offset < len(value):
            inner_tag, inner_offset = protobuf_read_varint(value, inner_offset)
            inner_field_no = inner_tag >> 3
            inner_wire_type = inner_tag & 0x07
            if inner_field_no == 1:
                if inner_wire_type != 2:
                    raise ValueError(f"unsupported id wire type: {inner_wire_type}")
                inner_size, inner_offset = protobuf_read_varint(value, inner_offset)
                inner_value = value[inner_offset : inner_offset + inner_size]
                return inner_value.decode("ascii", errors="replace")
            inner_offset = protobuf_skip_field(value, inner_offset, inner_wire_type)
    return ""


def extract_register_peer_id(payload):
    return extract_nested_string_id(payload, 6)


def extract_register_pk_id(payload):
    return extract_nested_string_id(payload, 15)


def remember_heartbeat(peer_id, ip, port):
    now = time.time()
    with HEARTBEATS_LOCK:
        old = HEARTBEATS.get(peer_id)
        HEARTBEATS[peer_id] = (ip, port, now)
    if old is None or old[:2] != (ip, port):
        stamp = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(now))
        print(f"{stamp} heartbeat peer_id={peer_id} udp_src={ip}:{port}", flush=True)


def get_heartbeat(peer_id, ttl):
    if not peer_id:
        return None
    now = time.time()
    with HEARTBEATS_LOCK:
        item = HEARTBEATS.get(peer_id)
    if not item:
        return None
    ip, port, ts = item
    if now - ts > ttl:
        return None
    return ip, port, now - ts


def sniff_register_peer_heartbeats(udp_port):
    try:
        packet_socket = socket.socket(
            socket.AF_PACKET, socket.SOCK_RAW, socket.htons(0x0800)
        )
    except Exception as exc:
        print(f"heartbeat sniffer disabled: {exc}", flush=True)
        return

    print(f"heartbeat sniffer enabled for udp/{udp_port}", flush=True)
    while True:
        try:
            packet = packet_socket.recv(65535)
            if len(packet) < 34:
                continue
            eth_type = struct.unpack("!H", packet[12:14])[0]
            ip_offset = 14
            if eth_type == 0x8100 and len(packet) >= 38:
                eth_type = struct.unpack("!H", packet[16:18])[0]
                ip_offset = 18
            if eth_type != 0x0800:
                continue
            first = packet[ip_offset]
            if first >> 4 != 4:
                continue
            ihl = (first & 0x0F) * 4
            proto = packet[ip_offset + 9]
            if proto != socket.IPPROTO_UDP:
                continue
            src_ip = socket.inet_ntoa(packet[ip_offset + 12 : ip_offset + 16])
            udp_offset = ip_offset + ihl
            if len(packet) < udp_offset + 8:
                continue
            src_port, dst_port, udp_len, _ = struct.unpack(
                "!HHHH", packet[udp_offset : udp_offset + 8]
            )
            if dst_port != udp_port:
                continue
            payload = packet[udp_offset + 8 : udp_offset + udp_len]
            peer_id = extract_register_peer_id(payload)
            if peer_id:
                remember_heartbeat(peer_id, src_ip, src_port)
        except Exception as exc:
            print(f"heartbeat sniffer error: {exc}", flush=True)
            time.sleep(1)


def handle_client(
    conn,
    addr,
    udp_target,
    udp_timeout,
    forward_mode,
    spoof_source_port,
    heartbeat_ttl,
):
    start = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
    try:
        raw_len = read_exact(conn, 4)
        (payload_len,) = struct.unpack("!I", raw_len)
        if payload_len <= 0 or payload_len > 4096:
            raise ValueError(f"invalid payload length: {payload_len}")
        payload = read_exact(conn, payload_len)
        peer_id = extract_register_pk_id(payload)

        if forward_mode == "raw-spoof":
            heartbeat = get_heartbeat(peer_id, heartbeat_ttl)
            if heartbeat:
                src_ip, src_port, age = heartbeat
                source = f"heartbeat age={age:.1f}s"
            else:
                src_ip, src_port = addr[0], addr[1]
                source = "tcp-fallback"
            src_port = spoof_source_port or src_port
            sent = raw_spoof_udp_send(payload, src_ip, src_port, udp_target[0], udp_target[1])
            status = (
                f"OK mode=raw-spoof ip_sent={sent} peer_id={peer_id} "
                f"spoof_src={src_ip}:{src_port} source={source} "
                f"target={udp_target[0]}:{udp_target[1]} "
                f"utc={start}\n"
            ).encode("utf-8")
            conn.sendall(struct.pack("!I", 0) + status)
        else:
            udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            udp.settimeout(udp_timeout)
            sent = udp.sendto(payload, udp_target)

            try:
                response, response_addr = udp.recvfrom(4096)
                status = (
                    f"OK mode=udp-loopback udp_sent={sent} peer_id={peer_id} "
                    f"udp_response_len={len(response)} "
                    f"udp_response_from={response_addr[0]}:{response_addr[1]} "
                    f"utc={start}\n"
                ).encode("utf-8")
                conn.sendall(struct.pack("!I", len(response)) + response + status)
            except socket.timeout:
                status = (
                    f"OK mode=udp-loopback udp_sent={sent} peer_id={peer_id} "
                    f"udp_response_timeout utc={start}\n"
                ).encode("utf-8")
                conn.sendall(struct.pack("!I", 0) + status)

        print(
            f"{start} client={addr[0]}:{addr[1]} peer_id={peer_id} "
            f"payload_len={payload_len} mode={forward_mode} sent={sent} "
            f"target={udp_target[0]}:{udp_target[1]}",
            flush=True,
        )
    except Exception as exc:
        msg = f"ERR {exc}\n".encode("utf-8")
        try:
            conn.sendall(struct.pack("!I", 0) + msg)
        except Exception:
            pass
        print(f"{start} client={addr[0]}:{addr[1]} error={exc}", flush=True)
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="TCP to UDP RegisterPk proxy for RustDesk hbbs")
    parser.add_argument("--listen", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=21120)
    parser.add_argument("--udp-host", default="103.205.240.70")
    parser.add_argument("--udp-port", type=int, default=21116)
    parser.add_argument("--udp-timeout", type=float, default=2.0)
    parser.add_argument(
        "--forward-mode",
        choices=("raw-spoof", "udp-loopback"),
        default="raw-spoof",
        help="raw-spoof preserves the client public IP as hbbs sees it",
    )
    parser.add_argument(
        "--spoof-source-port",
        type=int,
        default=0,
        help="0 means use the latest heartbeat UDP port, then TCP port as fallback",
    )
    parser.add_argument(
        "--heartbeat-ttl",
        type=float,
        default=120.0,
        help="seconds to trust a captured RegisterPeer heartbeat source",
    )
    args = parser.parse_args()

    udp_target = (args.udp_host, args.udp_port)
    if args.forward_mode == "raw-spoof":
        threading.Thread(
            target=sniff_register_peer_heartbeats,
            args=(args.udp_port,),
            daemon=True,
        ).start()

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((args.listen, args.port))
    srv.listen(64)
    print(
        f"listening tcp {args.listen}:{args.port}, forwarding udp "
        f"{udp_target[0]}:{udp_target[1]}, mode={args.forward_mode}",
        flush=True,
    )
    while True:
        conn, addr = srv.accept()
        thread = threading.Thread(
            target=handle_client,
            args=(
                conn,
                addr,
                udp_target,
                args.udp_timeout,
                args.forward_mode,
                args.spoof_source_port,
                args.heartbeat_ttl,
            ),
            daemon=True,
        )
        thread.start()


if __name__ == "__main__":
    main()
