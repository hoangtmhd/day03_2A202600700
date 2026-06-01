import re
from typing import Dict, Any

# Mock databases for the E-commerce system
STOCK_DB = {
    "iphone": 10,
    "macbook": 5,
    "ipad": 0,
    "airpods": 50
}

COUPON_DB = {
    "WINNER": 0.10,    # 10% discount
    "WELCOME": 0.05,   # 5% discount
    "SUPER": 0.20      # 20% discount
}

SHIPPING_RATES = {
    "hanoi": 15000,        # 15,000 VND per kg
    "ho chi minh": 30000,  # 30,000 VND per kg
    "da nang": 20000       # 20,000 VND per kg
}

def check_stock(item_name: str) -> str:
    """
    Checks stock levels for a product.
    Input: item_name (str) - e.g., 'iphone', 'macbook'.
    """
    if not item_name:
        return "Error: Product name cannot be empty."
    
    clean_name = item_name.strip().lower()
    # Handle optional quotes that LLM might pass
    clean_name = re.sub(r"['\"]", "", clean_name)
    
    if clean_name in STOCK_DB:
        stock = STOCK_DB[clean_name]
        return f"Stock for {clean_name}: {stock} units."
    else:
        available_items = ", ".join(STOCK_DB.keys())
        return f"Product '{item_name}' not found. Available products: {available_items}."

def get_discount(coupon_code: str) -> str:
    """
    Validates a discount coupon and returns the percentage.
    Input: coupon_code (str) - e.g., 'WINNER', 'WELCOME'.
    """
    if not coupon_code:
        return "Error: Coupon code cannot be empty."
        
    clean_code = coupon_code.strip().upper()
    clean_code = re.sub(r"['\"]", "", clean_code)
    
    if clean_code in COUPON_DB:
        discount = COUPON_DB[clean_code]
        return f"Coupon {clean_code} is valid. Discount: {int(discount*100)}% ({discount})."
    else:
        return f"Coupon code '{coupon_code}' is invalid or expired."

def calc_shipping(weight: float, destination: str) -> str:
    """
    Calculates shipping cost based on package weight and destination city.
    Input: weight (float) in kg, destination (str) e.g., 'hanoi', 'ho chi minh'.
    """
    if not destination:
        return "Error: Destination cannot be empty."
        
    clean_dest = destination.strip().lower()
    clean_dest = re.sub(r"['\"]", "", clean_dest)
    
    # Handle parsing weight from string if LLM passed it as string
    try:
        if isinstance(weight, str):
            # Clean string and extract numbers
            weight_str = re.sub(r"[^\d\.]", "", weight)
            val = float(weight_str)
        else:
            val = float(weight)
    except Exception:
        return f"Error: Invalid weight '{weight}'. Weight must be a positive number."
        
    if val <= 0:
        return "Error: Weight must be greater than 0 kg."
        
    if clean_dest in SHIPPING_RATES:
        rate = SHIPPING_RATES[clean_dest]
        cost = int(rate * val)
        return f"Shipping to {clean_dest}: {cost} VND."
    else:
        # Fallback default shipping rate
        default_rate = 25000
        cost = int(default_rate * val)
        supported_dests = ", ".join(SHIPPING_RATES.keys())
        return f"Shipping to '{destination}' (Standard Rate): {cost} VND. Note: Directly supported cities: {supported_dests}."
