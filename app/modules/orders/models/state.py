import enum

class OrderStatus(str, enum.Enum):
    pending = "pending"
    programmed = "programmed"
    unprogrammed = "unprogrammed"
    weighed = "weighed"
    manufactured = "manufactured"
    packaged = "packaged"
    delivered = "delivered"
    completed = "completed"
    not_programmable = "not_programmable"
