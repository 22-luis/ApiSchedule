import enum

class Type(str, enum.Enum):
    open = 'open'
    close = 'close'
    both = 'both'