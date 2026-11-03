"""Version-1 window records. Encoding/dimensions are negotiated out of band.

Little-endian uint64 window ID, uint32 ending round, uint32 payload count,
detector payload, then byte-rounded logical frame (little bit order).
Sparse payload count is index count; dense payload count is byte count.
"""
import struct
import numpy as np


def encode(syndrome, frame, window_id=0, round_id=0, sparse=True):
    syndrome = np.asarray(syndrome,dtype=bool)
    frame = np.asarray(frame,dtype=bool)
    if syndrome.ndim != 1 or frame.ndim != 1:
        raise ValueError('one-dimensional bit arrays required')
    if sparse:
        indices = np.flatnonzero(syndrome).astype('<u4')
        payload, count = indices.tobytes(),len(indices)
    else:
        payload = np.packbits(syndrome,bitorder='little').tobytes()
        count = len(payload)
    return struct.pack('<QII',window_id,round_id,count)+payload+np.packbits(frame,bitorder='little').tobytes()


def decode(record, detectors, observables, sparse=True):
    if detectors < 0 or observables < 0 or len(record) < 16:
        raise ValueError('invalid dimensions or short record')
    window, round_id, count = struct.unpack('<QII',record[:16])
    payload_bytes = 4*count if sparse else count
    if len(record) != 16+payload_bytes+(observables+7)//8:
        raise ValueError('record length disagrees with header')
    payload = record[16:16+payload_bytes]
    if sparse:
        indices = np.frombuffer(payload,dtype='<u4')
        if np.any(indices >= detectors) or len(np.unique(indices)) != count:
            raise ValueError('invalid sparse indices')
        syndrome = np.zeros(detectors,dtype=bool); syndrome[indices] = True
    else:
        if count != (detectors+7)//8:
            raise ValueError('incorrect dense size')
        syndrome = np.unpackbits(np.frombuffer(payload,dtype='u1'),bitorder='little')[:detectors].astype(bool)
    frame = np.unpackbits(np.frombuffer(record[16+payload_bytes:],dtype='u1'),bitorder='little')[:observables].astype(bool)
    return window,round_id,syndrome,frame


def encode_adaptive(syndrome,frame,window_id=0,round_id=0):
    """One byte format tag (0=dense, 1=sparse), followed by a full record."""
    dense = encode(syndrome,frame,window_id,round_id,False)
    sparse = encode(syndrome,frame,window_id,round_id,True)
    return b'\x01'+sparse if len(sparse)<len(dense) else b'\x00'+dense


def decode_adaptive(record,detectors,observables):
    if not record or record[0] not in (0,1):
        raise ValueError('invalid adaptive format tag')
    return decode(record[1:],detectors,observables,bool(record[0]))
