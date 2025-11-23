# validation.py - Input validation module for HRS
# This module provides validation functions for all user inputs

import re
from datetime import datetime, date

# ============== CONSTANTS ==============
MAX_GUEST_NAME = 35
MAX_ADDRESS = 75
MAX_EMAIL = 40
MAX_PHONE = 11
MAX_DAYS = 14
MIN_DAYS = 1
MAX_COMMENTS = 100
MAX_CC_NUMBER = 16
MIN_CC_NUMBER = 13
MAX_CC_TYPE = 15
USER_NUMBER_LENGTH = 7

# ============== VALIDATION FUNCTIONS ==============

def validate_guest_name(name):
    """
    Validate guest name:
    - Not empty or whitespace only
    - Max 35 characters
    - Contains at least one letter
    Returns: (is_valid: bool, error_message: str or None)
    """
    if not name or not name.strip():
        return False, "Guest name is required."
    
    name = name.strip()
    
    if len(name) > MAX_GUEST_NAME:
        return False, f"Guest name cannot exceed {MAX_GUEST_NAME} characters. You entered {len(name)}."
    
    if not any(c.isalpha() for c in name):
        return False, "Guest name must contain at least one letter."
    
    return True, None


def validate_address(address):
    """
    Validate guest address:
    - Not empty or whitespace only
    - Max 75 characters
    - Should contain street, city, state pattern (basic check)
    Returns: (is_valid: bool, error_message: str or None)
    """
    if not address or not address.strip():
        return False, "Address is required."
    
    address = address.strip()
    
    if len(address) > MAX_ADDRESS:
        return False, f"Address cannot exceed {MAX_ADDRESS} characters. You entered {len(address)}."
    
    # Basic format check - should have at least a comma or multiple parts
    # Relaxed validation: just needs some content
    if len(address) < 5:
        return False, "Please enter a complete address (street, city, state, zip)."
    
    return True, None


def validate_phone(phone):
    """
    Validate phone number:
    - Not empty or whitespace only
    - 10-11 digits (with or without formatting)
    - Only digits after stripping formatting
    Returns: (is_valid: bool, error_message: str or None, cleaned_phone: str)
    """
    if not phone or not phone.strip():
        return False, "Phone number is required.", None
    
    # Remove common formatting characters
    cleaned = re.sub(r'[\s\-\(\)\.]', '', phone.strip())
    
    if not cleaned:
        return False, "Phone number is required.", None
    
    if not cleaned.isdigit():
        return False, "Phone number must contain only digits.", None
    
    if len(cleaned) < 10 or len(cleaned) > MAX_PHONE:
        return False, f"Phone number must be 10-{MAX_PHONE} digits. You entered {len(cleaned)} digits.", None
    
    return True, None, cleaned


def validate_email(email):
    """
    Validate email address:
    - Not empty or whitespace only
    - Max 40 characters
    - Basic email format (contains @ and .)
    Returns: (is_valid: bool, error_message: str or None)
    """
    if not email or not email.strip():
        return False, "Email address is required."
    
    email = email.strip()
    
    if len(email) > MAX_EMAIL:
        return False, f"Email cannot exceed {MAX_EMAIL} characters. You entered {len(email)}."
    
    # Basic email format check
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        return False, "Please enter a valid email address (e.g., name@example.com)."
    
    return True, None


def validate_date(date_str, field_name="Date"):
    """
    Validate date string:
    - Not empty
    - Format: YYYY-MM-DD (10 characters)
    - Valid date values
    Returns: (is_valid: bool, error_message: str or None, date_obj: date or None)
    """
    if not date_str or not date_str.strip():
        return False, f"{field_name} is required.", None
    
    date_str = date_str.strip()
    
    if len(date_str) != 10:
        return False, f"{field_name} must be in YYYY-MM-DD format (10 characters).", None
    
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        return True, None, date_obj
    except ValueError:
        return False, f"{field_name} is invalid. Use YYYY-MM-DD format with valid values.", None


def validate_arrival_date(date_str, reservation_type=None):
    """
    Validate arrival date with business rules:
    - Must be valid date
    - Must be in the future
    - For Prepaid: must be >= 90 days in advance
    - For 60-Day: must be >= 60 days in advance
    Returns: (is_valid: bool, error_message: str or None, date_obj: date or None)
    """
    is_valid, error, date_obj = validate_date(date_str, "Arrival date")
    if not is_valid:
        return is_valid, error, None
    
    today = date.today()
    days_advance = (date_obj - today).days
    
    if date_obj <= today:
        return False, "Arrival date must be in the future.", None
    
    if reservation_type == "Prepaid" and days_advance < 90:
        return False, f"Prepaid reservations must be booked at least 90 days in advance. You selected {days_advance} days.", None
    
    if reservation_type == "60-Day" and days_advance < 60:
        return False, f"60-Day reservations must be booked at least 60 days in advance. You selected {days_advance} days.", None
    
    return True, None, date_obj


def validate_number_of_days(days_str):
    """
    Validate number of days:
    - Not empty
    - Numeric only
    - Between 1 and 14
    Returns: (is_valid: bool, error_message: str or None, days: int or None)
    """
    if not days_str or not str(days_str).strip():
        return False, "Number of days is required.", None
    
    days_str = str(days_str).strip()
    
    if not days_str.isdigit():
        return False, "Number of days must be a numeric value.", None
    
    days = int(days_str)
    
    if days < MIN_DAYS or days > MAX_DAYS:
        return False, f"Number of days must be between {MIN_DAYS} and {MAX_DAYS}. You entered {days}.", None
    
    return True, None, days


def validate_comments(comments):
    """
    Validate comments (optional field):
    - Max 100 characters
    Returns: (is_valid: bool, error_message: str or None)
    """
    if not comments:
        return True, None  # Comments are optional
    
    if len(comments) > MAX_COMMENTS:
        return False, f"Comments cannot exceed {MAX_COMMENTS} characters. You entered {len(comments)}."
    
    return True, None


def validate_credit_card_number(cc_number):
    """
    Validate credit card number:
    - Not empty
    - 13-16 digits
    - Numeric only (after stripping spaces/dashes)
    Returns: (is_valid: bool, error_message: str or None, cleaned_cc: str)
    """
    if not cc_number or not cc_number.strip():
        return False, "Credit card number is required.", None
    
    # Remove spaces and dashes
    cleaned = re.sub(r'[\s\-]', '', cc_number.strip())
    
    if not cleaned.isdigit():
        return False, "Credit card number must contain only digits.", None
    
    if len(cleaned) < MIN_CC_NUMBER or len(cleaned) > MAX_CC_NUMBER:
        return False, f"Credit card number must be {MIN_CC_NUMBER}-{MAX_CC_NUMBER} digits.", None
    
    return True, None, cleaned


def validate_credit_card_expiry(expiry_str):
    """
    Validate credit card expiration date:
    - Format: MM-YYYY or MM/YYYY
    - Month 01-12
    - Not expired (must be current month or future)
    Returns: (is_valid: bool, error_message: str or None)
    """
    if not expiry_str or not expiry_str.strip():
        return False, "Credit card expiration date is required."
    
    expiry_str = expiry_str.strip().replace('/', '-')
    
    # Try to parse MM-YYYY
    try:
        parts = expiry_str.split('-')
        if len(parts) != 2:
            return False, "Expiration date must be in MM-YYYY format."
        
        month = int(parts[0])
        year = int(parts[1])
        
        if month < 1 or month > 12:
            return False, "Month must be between 01 and 12."
        
        if year < 100:  # Handle 2-digit year
            year += 2000
        
        # Check if expired
        today = date.today()
        if year < today.year or (year == today.year and month < today.month):
            return False, "Credit card has expired."
        
        return True, None
        
    except (ValueError, IndexError):
        return False, "Expiration date must be in MM-YYYY format."


def validate_credit_card_type(cc_type):
    """
    Validate credit card type:
    - Not empty
    - Max 15 characters
    Returns: (is_valid: bool, error_message: str or None)
    """
    if not cc_type or not cc_type.strip():
        return False, "Credit card type is required."
    
    cc_type = cc_type.strip()
    
    if len(cc_type) > MAX_CC_TYPE:
        return False, f"Credit card type cannot exceed {MAX_CC_TYPE} characters."
    
    return True, None


def validate_amount(amount_str, field_name="Amount"):
    """
    Validate monetary amount:
    - Not empty
    - Numeric (allows decimal point)
    - Positive value
    Returns: (is_valid: bool, error_message: str or None, amount: float or None)
    """
    if not amount_str or not str(amount_str).strip():
        return False, f"{field_name} is required.", None
    
    amount_str = str(amount_str).strip()
    
    # Remove $ and commas if present
    amount_str = amount_str.replace('$', '').replace(',', '')
    
    try:
        amount = float(amount_str)
        if amount < 0:
            return False, f"{field_name} cannot be negative.", None
        return True, None, amount
    except ValueError:
        return False, f"{field_name} must be a valid number.", None


def validate_user_number(user_num):
    """
    Validate user/staff number:
    - Not empty
    - Exactly 7 digits
    - Numeric only
    Returns: (is_valid: bool, error_message: str or None)
    """
    if not user_num or not user_num.strip():
        return False, "User number is required."
    
    user_num = user_num.strip()
    
    if not user_num.isdigit():
        return False, "User number must contain only digits."
    
    if len(user_num) != USER_NUMBER_LENGTH:
        return False, f"User number must be exactly {USER_NUMBER_LENGTH} digits."
    
    return True, None


def validate_password(password):
    """
    Validate password:
    - Not empty
    Returns: (is_valid: bool, error_message: str or None)
    """
    if not password or not password.strip():
        return False, "Password is required."
    
    return True, None


def validate_reservation_id(res_id):
    """
    Validate reservation ID:
    - Not empty
    - Format: OO followed by digits (e.g., OO4001)
    Returns: (is_valid: bool, error_message: str or None)
    """
    if not res_id or not res_id.strip():
        return False, "Reservation ID is required."
    
    res_id = res_id.strip().upper()
    
    if not res_id.startswith("OO"):
        return False, "Reservation ID must start with 'OO'."
    
    if len(res_id) < 3 or not res_id[2:].isdigit():
        return False, "Reservation ID format is invalid (e.g., OO4001)."
    
    return True, None


def validate_base_rate(rate_str):
    """
    Validate base rate:
    - Not empty
    - Positive numeric value
    Returns: (is_valid: bool, error_message: str or None, rate: float or None)
    """
    if not rate_str or not str(rate_str).strip():
        return False, "Base rate is required.", None
    
    rate_str = str(rate_str).strip().replace('$', '').replace(',', '')
    
    try:
        rate = float(rate_str)
        if rate <= 0:
            return False, "Base rate must be a positive value.", None
        return True, None, rate
    except ValueError:
        return False, "Base rate must be a valid number.", None


# ============== HELPER FUNCTIONS ==============

def trim_and_clean(value):
    """Remove leading/trailing whitespace and normalize internal spaces."""
    if not value:
        return ""
    return ' '.join(str(value).split())


def format_phone_display(phone):
    """Format phone number for display: (XXX) XXX-XXXX"""
    cleaned = re.sub(r'\D', '', phone)
    if len(cleaned) == 10:
        return f"({cleaned[:3]}) {cleaned[3:6]}-{cleaned[6:]}"
    elif len(cleaned) == 11 and cleaned[0] == '1':
        return f"+1 ({cleaned[1:4]}) {cleaned[4:7]}-{cleaned[7:]}"
    return phone


def format_cc_masked(cc_number):
    """Mask credit card number showing only last 4 digits."""
    cleaned = re.sub(r'\D', '', cc_number)
    if len(cleaned) >= 4:
        return "*" * (len(cleaned) - 4) + cleaned[-4:]
    return "*" * len(cleaned)
