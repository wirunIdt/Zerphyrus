"""
PromptPay QR Code - EMVCo format generator
Returns the PromptPay payload string that can be encoded as a QR code.
"""


def _field(id_: str, value: str) -> str:
    """Format a single EMV field: ID + length (2 digits) + value."""
    return f"{id_}{len(value):02d}{value}"


def _crc16(data: str) -> str:
    """CRC-16/CCITT-FALSE checksum."""
    crc = 0xFFFF
    for char in data.encode('ascii'):
        crc ^= char << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ 0x1021
            else:
                crc <<= 1
            crc &= 0xFFFF
    return f"{crc:04X}"


def _normalize_phone(phone: str) -> str:
    """Normalize Thai phone number to 13-char PromptPay format (0066XXXXXXXXX)."""
    # Strip non-digits
    digits = ''.join(c for c in phone if c.isdigit())
    # Handle formats: 0XXXXXXXXX (10 digits) → 66XXXXXXXXX (11)
    if digits.startswith('66') and len(digits) == 11:
        return '00' + digits
    if digits.startswith('0') and len(digits) == 10:
        return '0066' + digits[1:]
    if len(digits) == 9:
        return '0066' + digits
    return '0066' + digits[-9:]


def generate_promptpay_payload(phone: str, amount: float = None) -> str:
    """
    Generate a PromptPay QR payload string.

    Args:
        phone: Thai phone number (any common format)
        amount: Amount in THB (optional). If None, amount is not specified.

    Returns:
        EMVCo payload string ready to be encoded as QR code.
    """
    normalized = _normalize_phone(phone)

    # Merchant Account Info (tag 29)
    mai = (
        _field('00', 'A000000677010111') +   # Globally Unique ID
        _field('01', normalized)              # Phone / Proxy
    )

    parts = [
        _field('00', '01'),                  # Payload Format Indicator
        _field('01', '12'),                  # Point of Initiation: dynamic
        _field('29', mai),                   # Merchant Account Info
        _field('52', '0000'),                # Merchant Category Code
        _field('53', '764'),                 # Currency: THB
    ]

    if amount is not None:
        parts.append(_field('54', f"{amount:.2f}"))

    parts += [
        _field('58', 'TH'),                  # Country Code
        _field('59', 'MERCHANT'),            # Merchant Name (ASCII only)
        _field('60', 'BANGKOK'),             # Merchant City
    ]

    payload_without_crc = ''.join(parts) + '6304'
    crc = _crc16(payload_without_crc)

    return payload_without_crc + crc


if __name__ == '__main__':
    # Quick test
    payload = generate_promptpay_payload('0812345678', 100.00)
    print('Payload length:', len(payload))
    print('Payload:', payload)
    print('Ends with CRC:', payload[-4:])
