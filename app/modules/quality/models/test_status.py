import enum

class TestStatus(str, enum.Enum):
    done = 'done'
    undone = 'undone'