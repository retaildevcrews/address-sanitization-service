# utils/libpostal.py

from postal.parser import parse_address as libpostal_parse_address
from postal.expand import expand_address as libpostal_expand_address


def parse_address(address):
    return libpostal_parse_address(address)


def expand_address(raw_address: str) -> str:
    """
    Use libpostal to expand and normalize a free-form address.
    Returns the first expansion if available.
    """
    try:
        # expand_address returns a list of normalized variants
        expansions = libpostal_expand_address(raw_address)
        print("Expansions: ", str(expansions))
        if expansions:
            # Return the first expanded address variant
            return expansions[0]
        else:
            return raw_address
    except Exception as e:
        print("Failed to expand address due to:", e)
        return raw_address
