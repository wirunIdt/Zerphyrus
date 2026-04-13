def _field(id_: str, value: str) -> str:
    return f"{id_}{len(value):02d}{value}"

def _crc16(data: str) -> str:
    crc = 0xFFFF
    for char in data.encode('ascii'):
        crc ^= char << 8
        for _ in range(8):
            if crc & 0x8000: crc = (crc << 1) ^ 0x1021
            else: crc <<= 1
            crc &= 0xFFFF
    return f"{crc:04X}"

def _normalize_phone(phone: str) -> str:
    digits = ''.join(c for c in phone if c.isdigit())
    if digits.startswith('66') and len(digits) == 11: return '00' + digits
    if digits.startswith('0') and len(digits) == 10: return '0066' + digits[1:]
    if len(digits) == 9: return '0066' + digits
    return '0066' + digits[-9:]

def generate_promptpay_payload(phone: str, amount: float = None) -> str:
    normalized = _normalize_phone(phone)
    mai = _field('00', 'A000000677010111') + _field('01', normalized)
    parts = [_field('00','01'), _field('01','12'), _field('29', mai),
             _field('52','0000'), _field('53','764')]
    if amount is not None: parts.append(_field('54', f"{amount:.2f}"))
    parts += [_field('58','TH'), _field('59','MERCHANT'), _field('60','BANGKOK')]
    payload_without_crc = ''.join(parts) + '6304'
    return payload_without_crc + _crc16(payload_without_crc)
