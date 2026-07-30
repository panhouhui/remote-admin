use hbb_common::{
    protobuf::Message as _,
    rendezvous_proto::{RegisterPeer, RegisterPk, RendezvousMessage},
};
use std::{
    env,
    io::{Read, Write},
    net::{TcpStream, UdpSocket},
    time::{Duration, Instant},
};

fn framed_payload(payload: &[u8]) -> Vec<u8> {
    let len = payload.len();
    let mut out = Vec::with_capacity(len + 4);
    if len <= 0x3f {
        out.push((len << 2) as u8);
    } else if len <= 0x3fff {
        out.extend_from_slice(&(((len << 2) as u16 | 0x1).to_le_bytes()));
    } else if len <= 0x3fffff {
        let header = (len << 2) as u32 | 0x2;
        out.extend_from_slice(&(header as u16).to_le_bytes());
        out.push((header >> 16) as u8);
    } else {
        out.extend_from_slice(&(((len << 2) as u32 | 0x3).to_le_bytes()));
    }
    out.extend_from_slice(payload);
    out
}

fn read_frame(stream: &mut TcpStream) -> Result<Vec<u8>, Box<dyn std::error::Error>> {
    let mut first = [0u8; 1];
    stream.read_exact(&mut first)?;
    let head_len = ((first[0] & 0x3) + 1) as usize;
    let mut header = [0u8; 4];
    header[0] = first[0];
    if head_len > 1 {
        stream.read_exact(&mut header[1..head_len])?;
    }
    let mut n = header[0] as usize;
    if head_len > 1 {
        n |= (header[1] as usize) << 8;
    }
    if head_len > 2 {
        n |= (header[2] as usize) << 16;
    }
    if head_len > 3 {
        n |= (header[3] as usize) << 24;
    }
    n >>= 2;
    let mut data = vec![0u8; n];
    stream.read_exact(&mut data)?;
    Ok(data)
}

fn send_proxy_payload(proxy: &str, payload: &[u8]) -> Result<String, Box<dyn std::error::Error>> {
    let mut tcp = TcpStream::connect(proxy)?;
    tcp.set_read_timeout(Some(Duration::from_secs(5)))?;
    tcp.set_write_timeout(Some(Duration::from_secs(5)))?;
    tcp.write_all(&(payload.len() as u32).to_be_bytes())?;
    tcp.write_all(payload)?;
    tcp.flush()?;
    let mut proxy_buf = [0u8; 512];
    let proxy_n = tcp.read(&mut proxy_buf).unwrap_or(0);
    Ok(String::from_utf8_lossy(&proxy_buf[..proxy_n])
        .trim()
        .to_owned())
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args = env::args().collect::<Vec<_>>();
    let host = args
        .get(1)
        .cloned()
        .unwrap_or_else(|| "103.205.240.70:21116".to_owned());
    let id = args
        .get(2)
        .cloned()
        .unwrap_or_else(|| "79072974".to_owned());
    let seconds = args
        .get(3)
        .and_then(|x| x.parse::<u64>().ok())
        .unwrap_or(45);
    let uuid = args.get(4).cloned().unwrap_or_else(|| {
        let suffix = format!("{:0>12}", id)
            .chars()
            .rev()
            .take(12)
            .collect::<String>()
            .chars()
            .rev()
            .collect::<String>();
        format!("00000000-0000-0000-0000-{suffix}")
    });
    let proxy = host
        .rsplit_once(':')
        .map(|(h, _)| format!("{h}:21120"))
        .unwrap_or_else(|| "103.205.240.70:21120".to_owned());

    let mut peer_msg = RendezvousMessage::new();
    peer_msg.set_register_peer(RegisterPeer {
        id: id.clone(),
        serial: 1,
        ..Default::default()
    });
    let peer_bytes = peer_msg.write_to_bytes()?;

    let mut pk_msg = RendezvousMessage::new();
    pk_msg.set_register_pk(RegisterPk {
        id: id.clone(),
        uuid: uuid.clone().into(),
        pk: [7u8; 32].to_vec().into(),
        no_register_device: false,
        ..Default::default()
    });
    let pk_bytes = pk_msg.write_to_bytes()?;

    let udp = UdpSocket::bind("0.0.0.0:0")?;
    udp.set_read_timeout(Some(Duration::from_millis(900)))?;
    println!("host={host}");
    println!("proxy={proxy}");
    println!("id={id}");
    println!("uuid={uuid}");
    println!("udp_local={}", udp.local_addr()?);
    println!("register_peer_wire_len={}", peer_bytes.len());
    println!("register_pk_wire_len={}", pk_bytes.len());

    let first_udp_sent = udp.send_to(&peer_bytes, &host)?;
    println!("first_udp_sent={first_udp_sent}");
    println!(
        "tcp_proxy_register_peer_response={}",
        send_proxy_payload(&proxy, &peer_bytes)?
    );

    let mut hbbs_tcp = TcpStream::connect(&host)?;
    hbbs_tcp.set_read_timeout(Some(Duration::from_millis(900)))?;
    hbbs_tcp.set_write_timeout(Some(Duration::from_secs(5)))?;
    let framed_peer = framed_payload(&peer_bytes);
    hbbs_tcp.write_all(&framed_peer)?;
    hbbs_tcp.flush()?;
    match read_frame(&mut hbbs_tcp) {
        Ok(frame) => println!("hbbs_tcp_first_recv_len={}", frame.len()),
        Err(err) => println!("hbbs_tcp_first_recv_error={err}"),
    }

    println!(
        "tcp_proxy_response={}",
        send_proxy_payload(&proxy, &pk_bytes)?
    );

    let started = Instant::now();
    let mut round = 1usize;
    while started.elapsed() < Duration::from_secs(seconds) {
        round += 1;
        let sent = udp.send_to(&peer_bytes, &host)?;
        print!("udp_round={round} sent={sent} ");
        let mut buf = [0u8; 2048];
        match udp.recv_from(&mut buf) {
            Ok((n, addr)) => println!("recv_len={n} from={addr}"),
            Err(err) => println!("recv_error={err}"),
        }
        match hbbs_tcp
            .write_all(&framed_peer)
            .and_then(|_| hbbs_tcp.flush())
        {
            Ok(()) => match read_frame(&mut hbbs_tcp) {
                Ok(frame) => println!("tcp_round={round} recv_len={}", frame.len()),
                Err(err) => println!("tcp_round={round} recv_error={err}"),
            },
            Err(err) => println!("tcp_round={round} send_error={err}"),
        }
        match send_proxy_payload(&proxy, &peer_bytes) {
            Ok(response) => println!("tcp_proxy_peer_round={round} response={response}"),
            Err(err) => println!("tcp_proxy_peer_round={round} error={err}"),
        }
        std::thread::sleep(Duration::from_secs(3));
    }

    Ok(())
}
