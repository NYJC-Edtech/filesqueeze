from datetime import datetime

from pathlib import Path
from .enums import Format, Status

class State:
    __slots__ = ('__data',)
    def __init__(self, origin: [str, Path]):
        self.__data = {
            'origin': Path(origin),
            'status': Status.PENDING,
            'created': datetime.fromtimestamp(Path(origin).stat().st_ctime),
            'added': datetime.now(),
            'format': None,
            'target': Path(origin),
            'metadata': {},
        }
    
    def __getattr__(self, attr):
        # Read-only access to attributes in __data
        if attr in self.__data:
            return self.__data[attr]
        raise AttributeError

    def set_format(self, format):
        if not type(format) in [f.value for f in Format]:
            raise ValueError("Must be a Format enum member")
        self.__data['format'] = format

    def set_target(self, target):
        self.__data['target'] = Path(target)
    
    def status_analyze(self):
        self.__data['status'] = Status.ANALYZE

    def status_convert(self):
        self.__data['status'] = Status.CONVERT

    def status_compress(self):
        self.__data['status'] = Status.COMPRESS

    def status_complete(self):
        self.__data['status'] = Status.COMPLETE

    def error(self, msg: str):
        self.__data['status'] = Status.ERROR

    def as_dict(self) -> dict:
        return {
            'origin': str(self.origin),
            'status': self.status.value,
            'created': self.created,
            'added': self.added.isoformat(),
            'format': str(self.format),
            'target': str(self.target),
            'metadata': self.metadata.copy(),
        }

    def __repr__(self) -> str:
        return (
            type(self).__name__ + '('
            + ', '.join(
                [f'{key}={value!r}' for key, value in self.__data.items()]
            )
            + ')'
        )
