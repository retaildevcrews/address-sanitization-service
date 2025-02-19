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
        if expansions:
            # Return an object that contains original address and expanded address
            expanded_address = expansions[0]
        else:
            expanded_address = "unable to expand address"
        return {"original_address": raw_address, "expanded_address": expanded_address}
    except Exception as e:
        print("Failed to expand address due to:", e)
        return raw_address
