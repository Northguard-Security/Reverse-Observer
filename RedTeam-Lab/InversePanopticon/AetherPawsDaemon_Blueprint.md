# [HYP-API] Aether-PAWS C2 Proxy Interface

## Structure
- Local SOCKS5 listener (Port 1080)
- Asynchronous TCP socket handler
- On outbound connection -> Handshake -> PAWS Desync Injection -> Transparent Bridge in/out.