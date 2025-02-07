# app/utils/address_sanitizer.py

from postal.expand import expand_address

def sanitize_with_libpostal(raw_address: str) -> str:
    """
    Use libpostal to expand and normalize a free-form address.
    Returns the first expansion if available.
    """
    try:
        # expand_address returns a list of normalized variants
        expansions = expand_address(raw_address)
        if expansions:
            # Return the first expanded address variant
            return expansions[0]
        else:
            return raw_address
    except Exception as e:
        print("Failed to expand address due to:", e)
        return raw_address
