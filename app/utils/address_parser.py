# app/utils/address_sanitizer.py

from postal.parser import parse_address

def address_parser_score(address: str) -> float:
    """
    Use libpostal to parse an address and return the number of components parsed.
    Score represents the percentage of 5 address components identified
    """
    try:
        parsed = parse_address(address)
        return min((len(parsed) / 5), 1)
    except Exception as e:
        print("Failed to parse address due to:", e)
        return 0.0
