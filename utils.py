import re

def validate_somali_phone(phone):
    """Validate Somaliland and Somalia phone numbers"""
    # Remove spaces, dashes, and plus signs for validation
    clean_phone = re.sub(r'[\s\-\+]', '', phone)

    # More flexible patterns for Somalia/Somaliland
    # Accept common prefixes: 252, 0, or direct carrier codes
    patterns = [
        # Full international format: +252XXXXXXXX (9 digits after 252)
        r'^252[0-9]{8,9}$',
        # National format with 0: 0XXXXXXXX (8-9 digits after 0)  
        r'^0[0-9]{8,9}$',
        # Direct carrier format: XXXXXXXX (8-9 digits)
        r'^[0-9]{8,9}$'
    ]

    for pattern in patterns:
        if re.match(pattern, clean_phone):
            return True
    return False

def normalize_phone(phone):
    """Normalize phone number to +252 format"""
    # Remove all spaces, dashes, and plus signs
    clean_phone = re.sub(r'[\s\-\+]', '', phone)

    # If already starts with 252, add +
    if clean_phone.startswith('252'):
        return '+' + clean_phone
    # If starts with 0, replace with +252
    elif clean_phone.startswith('0'):
        return '+252' + clean_phone[1:]
    # Otherwise assume it needs +252 prefix
    else:
        return '+252' + clean_phone