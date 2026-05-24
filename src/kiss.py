FEND = 0xC0
FESC = 0xDB
TFEND = 0xDC
TFESC = 0xDD
CMD_DATA = 0x02
FRAME_SIZE = 54  # DATAC4 模式，根据实际模式调整


def kiss_encode(data: bytes, cmd: int = CMD_DATA) -> bytes:
    frame = bytearray()
    frame.append(FEND)
    frame.append(cmd)
    for b in data:
        if b == FEND:
            frame.extend([FESC, TFEND])
        elif b == FESC:
            frame.extend([FESC, TFESC])
        else:
            frame.append(b)
    frame.append(FEND)
    return bytes(frame)


def kiss_decode(buf: bytearray) -> list[bytes]:
    """从缓冲区解码完整 KISS 帧，返回 [(payload, cmd), ...]"""
    frames = []
    in_frame = False
    escape = False
    cmd = 0
    payload = bytearray()
    processed = 0
    for i, b in enumerate(buf):
        if not in_frame:
            if b == FEND:
                in_frame = True
                escape = False
                cmd = 0
                payload = bytearray()
                processed = i + 1
            continue
        if b == FEND:
            if cmd == CMD_DATA and len(payload) > 0:
                frames.append(bytes(payload).rstrip(b"\x00"))
            in_frame = False
            processed = i + 1
            continue
        if len(payload) == 0 and cmd == 0:
            cmd = b & 0x0F
            continue
        if cmd != CMD_DATA:
            continue
        if escape:
            if b == TFEND:
                payload.append(FEND)
            elif b == TFESC:
                payload.append(FESC)
            else:
                payload.append(b)
            escape = False
        elif b == FESC:
            escape = True
        else:
            payload.append(b)
    buf = buf[:processed]
    return frames
