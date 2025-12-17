import re

def clean_string_field(value: str) -> str:
    if value is None:
        return ""
    return str(value).strip()

def clean_order_data(order_data: dict) -> dict:
    cleaned_data = order_data.copy()
    
    # Limpiar campos string
    if 'code' in cleaned_data:
        cleaned_data['code'] = clean_string_field(cleaned_data['code'])
    if 'description' in cleaned_data:
        cleaned_data['description'] = clean_string_field(cleaned_data['description'])
    if 'lote' in cleaned_data and isinstance(cleaned_data['lote'], str):
        cleaned_data['lote'] = clean_string_field(cleaned_data['lote'])
    if 'bin' in cleaned_data and isinstance(cleaned_data['bin'], str):
        cleaned_data['bin'] = clean_string_field(cleaned_data['bin'])
    
    return cleaned_data

def clean_float(value):
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip().replace('\xa0', '').replace(' ', '').replace(',', '.')
        if value == '' or value == '-' or value.lower() == 'null':
            return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None

def clean_str(value):
    if value is None:
        return ""
    if isinstance(value, str):
        cleaned = value.strip().replace('\xa0', ' ')
        cleaned = re.sub(r'\s+', ' ', cleaned)
        return cleaned.upper() if cleaned.lower() != 'null' else ""
    return str(value).strip().upper()

def clean_str_preserve_case(value):
    if value is None:
        return ""
    if isinstance(value, str):
        cleaned = value.strip().replace('\xa0', ' ')
        cleaned = re.sub(r'\s+', ' ', cleaned)
        return cleaned if cleaned.lower() != 'null' else ""
    return str(value).strip()