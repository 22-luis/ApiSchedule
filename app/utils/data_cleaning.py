"""
Utilidades para limpieza de datos de entrada
"""

def clean_string_field(value: str) -> str:
    """
    Limpia un campo string eliminando espacios en blanco al inicio y final
    
    Args:
        value: El valor string a limpiar
        
    Returns:
        El string limpio sin espacios al inicio y final
    """
    if value is None:
        return ""
    return str(value).strip()

def clean_order_data(order_data: dict) -> dict:
    """
    Limpia todos los campos string de una orden
    
    Args:
        order_data: Diccionario con los datos de la orden
        
    Returns:
        Diccionario con los datos limpios
    """
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