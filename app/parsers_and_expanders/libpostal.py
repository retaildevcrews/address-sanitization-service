# utils/libpostal.py

from postal.parser import parse_address as libpostal_parse_address
from postal.expand import expand_address as libpostal_expand_address


def parse_address(original_address):
    parsed_address = libpostal_parse_address(original_address)
    parsed_dict = {component[1]: component[0] for component in parsed_address}
    print(parsed_dict)
    return {"original_address": original_address, "parsed_address": parsed_dict}


def expand_address(original_address: str) -> str:
    """
    Use libpostal to expand and normalize a free-form address.
    Returns the first expansion if available.
    """
    try:
        # expand_address returns a list of normalized variants
        expansions = libpostal_expand_address(original_address)
        if expansions:
            # Return an object that contains original address and expanded address
            expanded_address = expansions[0]
        else:
            expanded_address = "unable to expand address"
        return {
            "original_address": original_address,
            "expanded_address": expanded_address,
        }
    except Exception as e:
        print("Failed to expand address due to:", e)
        return original_address
