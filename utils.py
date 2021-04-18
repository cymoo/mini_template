from collections import abc
from keyword import iskeyword
from typing import Any, Mapping, Iterable, Iterator
import re
from pprint import pprint


class DotSon(abc.Mapping):
    """ A :class:`DotSon` is a special dict whose item can be accessed using dot notation.
    There will be a performance penalty when accessing deep-nested element.
    >>> d = DotSon({'name': 'foo', 'hobbits': [{'name': 'bar'}]})
    >>> d.name
    'foo'
    >>> d.hobbits[0].name
    'bar'
    >>> type(d.hobbits[0]) == DotSon
    True
    """

    def __new__(cls, obj: Any) -> Any:
        if isinstance(obj, abc.Mapping):
            return super().__new__(cls)
        elif isinstance(obj, abc.MutableSequence):
            # noinspection PyCallingNonCallable
            return [cls(item) for item in obj]
        else:
            return obj

    def __init__(self, mapping: Mapping):
        # create a shallow copy for security
        self._data = {}
        for key, value in mapping.items():
            if not key.isidentifier():
                raise AttributeError("invalid identifier: {!r}".format(key))
            if iskeyword(key):
                key += '_'
            self._data[key] = value

    def __getattr__(self, name: str) -> Any:
        if hasattr(self._data, name):
            return getattr(self._data, name)
        try:
            return DotSon(self._data[name])
        except KeyError:
            raise AttributeError('{!r} has no attribute {!r}'.format(self, name))

    def __getitem__(self, item: str) -> Any:
        return self._data[item]

    def keys(self) -> Iterable:
        return self._data.keys()

    def values(self) -> Iterable:
        return self._data.values()

    def items(self) -> Iterable:
        return self._data.items()

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def __len__(self) -> int:
        return len(self._data)

    def __iter__(self) -> Iterator:
        return iter(self._data)

    def __str__(self) -> str:
        return str(self._data)

