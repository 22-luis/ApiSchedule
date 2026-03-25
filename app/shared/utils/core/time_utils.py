import pytz
from datetime import datetime, time, date
from typing import Optional

class TimeZoneUtils:
    
    @staticmethod
    def get_el_salvador_timezone():
        return pytz.timezone('America/El_Salvador')
    
    @staticmethod
    def get_now() -> datetime:
        """Retorna la hora actual de El Salvador como datetime naive."""
        el_salvador_tz = TimeZoneUtils.get_el_salvador_timezone()
        return datetime.now(el_salvador_tz).replace(tzinfo=None)
    
    @staticmethod
    def convert_to_el_salvador_time(utc_datetime: datetime) -> datetime:
        if utc_datetime.tzinfo is None:
            utc_datetime = pytz.UTC.localize(utc_datetime)
        return utc_datetime.astimezone(TimeZoneUtils.get_el_salvador_timezone())
    
    @staticmethod
    def format_time_el_salvador(time_str: str) -> str:
        if not time_str:
            return '-'
        
        try:
            # Si es formato HH:mm, devolver directamente
            if ':' in time_str and 'T' not in time_str:
                time_parts = time_str.split(':')
                if len(time_parts) >= 2:
                    hour = int(time_parts[0])
                    minute = time_parts[1]
                    ampm = 'p. m.' if hour >= 12 else 'a. m.'
                    display_hour = 12 if hour == 0 else hour - 12 if hour > 12 else hour
                    return f"{display_hour}:{minute} {ampm}"
            
            # Para formato ISO
            date_obj = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
            el_salvador_time = TimeZoneUtils.convert_to_el_salvador_time(date_obj)
            
            hours = el_salvador_time.hour
            minutes = el_salvador_time.minute
            seconds = el_salvador_time.second
            
            ampm = 'p. m.' if hours >= 12 else 'a. m.'
            display_hour = 12 if hours == 0 else hours - 12 if hours > 12 else hours
            
            return f"{display_hour}:{minutes:02d}:{seconds:02d} {ampm}"
            
        except Exception as e:
            print(f"Error formateando hora El Salvador: {e}")
            return '-'
    
    @staticmethod
    def get_programming_base_time_utc(target_date: date) -> Optional[datetime]:
        try:
            # Determinar hora base según el día
            day_of_week = target_date.weekday()  # 0=Lunes, 6=Domingo
            
            if day_of_week == 6:  # Domingo
                return None
            
            # Configurar hora base
            if day_of_week == 5:  # Sábado
                base_hour = 7
                base_minute = 30
            else:  # Lunes a Viernes
                base_hour = 7
                base_minute = 0
            
            # Crear datetime en zona horaria de El Salvador
            el_salvador_tz = TimeZoneUtils.get_el_salvador_timezone()
            local_datetime = el_salvador_tz.localize(
                datetime.combine(target_date, time(base_hour, base_minute))
            )
            
            # Retornar datetime NAIVE en hora local de El Salvador (sin conversión a UTC)
            return local_datetime.replace(tzinfo=None)
            
        except Exception as e:
            print(f"Error calculando hora base UTC: {e}")
            return None
