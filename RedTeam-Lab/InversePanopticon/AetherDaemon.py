# [HYP-API] AetherDaemon: Asynchronous SOCKS5 Listener & Proxy
# METAMODEL_ADVERSARIAL_ONTOLOGY_V9 -> TOPOLOGY: INGRESS
import asyncio
import struct
import socket
from PAWS_Desync import inject_ghost_fin, apply_paws_desync

async def handle_client(reader, writer):
    """
    State 0: Deconstruction
    Raw SOCKS5 ingestion and protocol peeling.
    """
    try:
        # Initial Handshake
        version, nmethods = struct.unpack("!BB", await reader.readexactly(2))
        methods = await reader.readexactly(nmethods)
        writer.write(b"\x05\x00")
        await writer.drain()

        # Connect Request
        version, cmd, _, address_type = struct.unpack("!BBBB", await reader.readexactly(4))
        if address_type == 1:  # IPv4
            address = socket.inet_ntoa(await reader.readexactly(4))
        elif address_type == 3:  # Domain
            domain_length = ord(await reader.readexactly(1))
            address = (await reader.readexactly(domain_length)).decode()
        elif address_type == 4:  # IPv6
            address = socket.inet_ntop(socket.AF_INET6, await reader.readexactly(16))
        else:
            return
            
        port = struct.unpack("!H", await reader.readexactly(2))[0]

        # State 2: Contradiction & Falsification
        # Neutralize carrier observe points prior to target handshake.
        remote_reader, remote_writer = await asyncio.open_connection(address, port)
        
        # Subvert Middleboxes
        inject_ghost_fin(address, port, ttl=13)
        apply_paws_desync(address, port, seq_offset=4200000000)

        # Confirm SOCKS connect
        writer.write(b"\x05\x00\x00\x01" + socket.inet_aton("0.0.0.0") + struct.pack("!H", 0))
        await writer.drain()

        # State 3: Constructive Synthesis (Bridging)
        async def forward(src, dst):
            try:
                while True:
                    data = await src.read(4096)
                    if not data: break
                    dst.write(data)
                    await dst.drain()
            except Exception:
                pass
        
        await asyncio.gather(
            forward(reader, remote_writer),
            forward(remote_reader, writer)
        )
            
    except Exception as e:
        # Failure mode: Refusal or crash telemetry localized
        try:
            writer.write(b"\x05\x05\x00\x01\x00\x00\x00\x00\x00\x00")
            await writer.drain()
        except:
            pass
    finally:
        writer.close()

async def main():
    server = await asyncio.start_server(handle_client, '127.0.0.1', 1080)
    async with server:
        await server.serve_forever()

if __name__ == '__main__':
    asyncio.run(main())
