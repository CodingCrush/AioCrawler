class JsonDecodeError(Exception):
    pass


class QueueEmpty(Exception):
    """Exception raised when Queue.get_nowait() is called on a Queue object
    which is empty.
    """
    pass


class QueueFull(Exception):
    """Exception raised when the Queue.put_nowait() method is called on a Queue
    object which is full.
    """
    pass
