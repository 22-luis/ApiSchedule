import enum

class QuestionType(str, enum.Enum):
    open = 'open'
    close = 'close'
    both = 'both'