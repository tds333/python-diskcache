"""Persistent Data Types"""

import operator as op
from collections import OrderedDict
from collections.abc import (
    ItemsView,
    KeysView,
    MutableMapping,
    Sequence,
    ValuesView,
)
from contextlib import contextmanager
from shutil import rmtree

from .core import ENOVAL, Cache


def _make_compare(seq_op, doc):
    """Make compare method with Sequence semantics."""

    def compare(self, that):
        """Compare method for deque and sequence."""
        if not isinstance(that, Sequence):
            return NotImplemented

        len_self = len(self)
        len_that = len(that)

        if len_self != len_that:
            if seq_op is op.eq:
                return False
            if seq_op is op.ne:
                return True

        for alpha, beta in zip(self, that):
            if alpha != beta:
                return seq_op(alpha, beta)

        return seq_op(len_self, len_that)

    compare.__name__ = "__{0}__".format(seq_op.__name__)
    doc_str = "Return True if and only if deque is {0} `that`."
    compare.__doc__ = doc_str.format(doc)

    return compare


class Index(MutableMapping):
    """Persistent mutable mapping with insertion order iteration.

    Items are serialized to disk. Index may be initialized from directory path
    where items are stored.

    Hashing protocol is not used. Keys are looked up by their serialized
    format. See ``diskcache.Disk`` for details.

    >>> index = Index()
    >>> index.update([('a', 1), ('b', 2), ('c', 3)])
    >>> index['a']
    1
    >>> list(index)
    ['a', 'b', 'c']
    >>> len(index)
    3
    >>> del index['b']
    >>> index.popitem()
    ('c', 3)

    """

    def __init__(self, *args, **kwargs):
        """Initialize index in directory and update items.

        Optional first argument may be string specifying directory where items
        are stored. When None or not given, temporary directory is created.

        >>> index = Index({'a': 1, 'b': 2, 'c': 3})
        >>> len(index)
        3
        >>> directory = index.directory
        >>> inventory = Index(directory, d=4)
        >>> inventory['b']
        2
        >>> len(inventory)
        4

        """
        if args and isinstance(args[0], (bytes, str)):
            directory = args[0]
            args = args[1:]
        else:
            if args and args[0] is None:
                args = args[1:]
            directory = None
        self._cache = Cache(directory, eviction_policy="none")
        self._update(*args, **kwargs)

    _update = MutableMapping.update

    @classmethod
    def fromcache(cls, cache, *args, **kwargs):
        """Initialize index using `cache` and update items.

        >>> cache = Cache()
        >>> index = Index.fromcache(cache, {'a': 1, 'b': 2, 'c': 3})
        >>> index.cache is cache
        True
        >>> len(index)
        3
        >>> 'b' in index
        True
        >>> index['c']
        3

        :param Cache cache: cache to use
        :param args: mapping or sequence of items
        :param kwargs: mapping of items
        :return: initialized Index

        """
        # pylint: disable=no-member,protected-access
        self = cls.__new__(cls)
        self._cache = cache
        self._update(*args, **kwargs)
        return self

    @property
    def cache(self):
        """Cache used by index."""
        return self._cache

    @property
    def directory(self):
        """Directory path where items are stored."""
        return self._cache.directory

    def __getitem__(self, key):
        """index.__getitem__(key) <==> index[key]

        Return corresponding value for `key` in index.

        >>> index = Index()
        >>> index.update({'a': 1, 'b': 2})
        >>> index['a']
        1
        >>> index['b']
        2
        >>> index['c']
        Traceback (most recent call last):
            ...
        KeyError: 'c'

        :param key: key for item
        :return: value for item in index with given key
        :raises KeyError: if key is not found

        """
        return self._cache[key]

    def __setitem__(self, key, value):
        """index.__setitem__(key, value) <==> index[key] = value

        Set `key` and `value` item in index.

        >>> index = Index()
        >>> index['a'] = 1
        >>> index[0] = None
        >>> len(index)
        2

        :param key: key for item
        :param value: value for item

        """
        self._cache[key] = value

    def __delitem__(self, key):
        """index.__delitem__(key) <==> del index[key]

        Delete corresponding item for `key` from index.

        >>> index = Index()
        >>> index.update({'a': 1, 'b': 2})
        >>> del index['a']
        >>> del index['b']
        >>> len(index)
        0
        >>> del index['c']
        Traceback (most recent call last):
            ...
        KeyError: 'c'

        :param key: key for item
        :raises KeyError: if key is not found

        """
        del self._cache[key]

    def setdefault(self, key, default=None):
        """Set and get value for `key` in index using `default`.

        If `key` is not in index then set corresponding value to `default`. If
        `key` is in index then ignore `default` and return existing value.

        >>> index = Index()
        >>> index.setdefault('a', 0)
        0
        >>> index.setdefault('a', 1)
        0

        :param key: key for item
        :param default: value if key is missing (default None)
        :return: value for item in index with given key

        """
        _cache = self._cache
        while True:
            try:
                return _cache[key]
            except KeyError:
                _cache.add(key, default, retry=True)

    def peekitem(self, last=True):
        """Peek at key and value item pair in index based on iteration order.

        >>> index = Index()
        >>> for num, letter in enumerate('xyz'):
        ...     index[letter] = num
        >>> index.peekitem()
        ('z', 2)
        >>> index.peekitem(last=False)
        ('x', 0)

        :param bool last: last item in iteration order (default True)
        :return: key and value item pair
        :raises KeyError: if cache is empty

        """
        return self._cache.peekitem(last, retry=True)

    def pop(self, key, default=ENOVAL):
        """Remove corresponding item for `key` from index and return value.

        If `key` is missing then return `default`. If `default` is `ENOVAL`
        then raise KeyError.

        >>> index = Index({'a': 1, 'b': 2})
        >>> index.pop('a')
        1
        >>> index.pop('b')
        2
        >>> index.pop('c', default=3)
        3
        >>> index.pop('d')
        Traceback (most recent call last):
            ...
        KeyError: 'd'

        :param key: key for item
        :param default: return value if key is missing (default ENOVAL)
        :return: value for item if key is found else default
        :raises KeyError: if key is not found and default is ENOVAL

        """
        _cache = self._cache
        value = _cache.pop(key, default=default, retry=True)
        if value is ENOVAL:
            raise KeyError(key)
        return value

    def popitem(self, last=True):
        """Remove and return item pair.

        Item pairs are returned in last-in-first-out (LIFO) order if last is
        True else first-in-first-out (FIFO) order. LIFO order imitates a stack
        and FIFO order imitates a queue.

        >>> index = Index()
        >>> index.update([('a', 1), ('b', 2), ('c', 3)])
        >>> index.popitem()
        ('c', 3)
        >>> index.popitem(last=False)
        ('a', 1)
        >>> index.popitem()
        ('b', 2)
        >>> index.popitem()
        Traceback (most recent call last):
          ...
        KeyError: 'dictionary is empty'

        :param bool last: pop last item pair (default True)
        :return: key and value item pair
        :raises KeyError: if index is empty

        """
        # pylint: disable=arguments-differ,unbalanced-tuple-unpacking
        _cache = self._cache

        with _cache.transact(retry=True):
            key, value = _cache.peekitem(last=last)
            del _cache[key]

        return key, value

    def clear(self):
        """Remove all items from index.

        >>> index = Index({'a': 0, 'b': 1, 'c': 2})
        >>> len(index)
        3
        >>> index.clear()
        >>> dict(index)
        {}

        """
        self._cache.clear(retry=True)

    def __iter__(self):
        """index.__iter__() <==> iter(index)

        Return iterator of index keys in insertion order.

        """
        return iter(self._cache)

    def __reversed__(self):
        """index.__reversed__() <==> reversed(index)

        Return iterator of index keys in reversed insertion order.

        >>> index = Index()
        >>> index.update([('a', 1), ('b', 2), ('c', 3)])
        >>> iterator = reversed(index)
        >>> next(iterator)
        'c'
        >>> list(iterator)
        ['b', 'a']

        """
        return reversed(self._cache)

    def __len__(self):
        """index.__len__() <==> len(index)

        Return length of index.

        """
        return len(self._cache)

    def keys(self):
        """Set-like object providing a view of index keys.

        >>> index = Index()
        >>> index.update({'a': 1, 'b': 2, 'c': 3})
        >>> keys_view = index.keys()
        >>> 'b' in keys_view
        True

        :return: keys view

        """
        return KeysView(self)

    def values(self):
        """Set-like object providing a view of index values.

        >>> index = Index()
        >>> index.update({'a': 1, 'b': 2, 'c': 3})
        >>> values_view = index.values()
        >>> 2 in values_view
        True

        :return: values view

        """
        return ValuesView(self)

    def items(self):
        """Set-like object providing a view of index items.

        >>> index = Index()
        >>> index.update({'a': 1, 'b': 2, 'c': 3})
        >>> items_view = index.items()
        >>> ('b', 2) in items_view
        True

        :return: items view

        """
        return ItemsView(self)

    __hash__ = None  # type: ignore

    def __getstate__(self):
        return self.directory

    def __setstate__(self, state):
        self.__init__(state)

    def __eq__(self, other):
        """index.__eq__(other) <==> index == other

        Compare equality for index and `other`.

        Comparison to another index or ordered dictionary is
        order-sensitive. Comparison to all other mappings is order-insensitive.

        >>> index = Index()
        >>> pairs = [('a', 1), ('b', 2), ('c', 3)]
        >>> index.update(pairs)
        >>> from collections import OrderedDict
        >>> od = OrderedDict(pairs)
        >>> index == od
        True
        >>> index == {'c': 3, 'b': 2, 'a': 1}
        True

        :param other: other mapping in equality comparison
        :return: True if index equals other

        """
        if len(self) != len(other):
            return False

        if isinstance(other, (Index, OrderedDict)):
            alpha = ((key, self[key]) for key in self)
            beta = ((key, other[key]) for key in other)
            pairs = zip(alpha, beta)
            return not any(a != x or b != y for (a, b), (x, y) in pairs)
        else:
            return all(self[key] == other.get(key, ENOVAL) for key in self)

    def __ne__(self, other):
        """index.__ne__(other) <==> index != other

        Compare inequality for index and `other`.

        Comparison to another index or ordered dictionary is
        order-sensitive. Comparison to all other mappings is order-insensitive.

        >>> index = Index()
        >>> index.update([('a', 1), ('b', 2), ('c', 3)])
        >>> from collections import OrderedDict
        >>> od = OrderedDict([('c', 3), ('b', 2), ('a', 1)])
        >>> index != od
        True
        >>> index != {'a': 1, 'b': 2}
        True

        :param other: other mapping in inequality comparison
        :return: True if index does not equal other

        """
        return not self == other

    def memoize(self, name=None, typed=False, ignore=()):
        """Memoizing cache decorator.

        Decorator to wrap callable with memoizing function using cache.
        Repeated calls with the same arguments will lookup result in cache and
        avoid function evaluation.

        If name is set to None (default), the callable name will be determined
        automatically.

        If typed is set to True, function arguments of different types will be
        cached separately. For example, f(3) and f(3.0) will be treated as
        distinct calls with distinct results.

        The original underlying function is accessible through the __wrapped__
        attribute. This is useful for introspection, for bypassing the cache,
        or for rewrapping the function with a different cache.

        >>> from diskcache import Index
        >>> mapping = Index()
        >>> @mapping.memoize()
        ... def fibonacci(number):
        ...     if number == 0:
        ...         return 0
        ...     elif number == 1:
        ...         return 1
        ...     else:
        ...         return fibonacci(number - 1) + fibonacci(number - 2)
        >>> print(fibonacci(100))
        354224848179261915075

        An additional `__cache_key__` attribute can be used to generate the
        cache key used for the given arguments.

        >>> key = fibonacci.__cache_key__(100)
        >>> print(mapping[key])
        354224848179261915075

        Remember to call memoize when decorating a callable. If you forget,
        then a TypeError will occur. Note the lack of parenthenses after
        memoize below:

        >>> @mapping.memoize
        ... def test():
        ...     pass
        Traceback (most recent call last):
            ...
        TypeError: name cannot be callable

        :param str name: name given for callable (default None, automatic)
        :param bool typed: cache different types separately (default False)
        :param set ignore: positional or keyword args to ignore (default ())
        :return: callable decorator

        """
        return self._cache.memoize(name, typed, ignore=ignore)

    @contextmanager
    def transact(self):
        """Context manager to perform a transaction by locking the index.

        While the index is locked, no other write operation is permitted.
        Transactions should therefore be as short as possible. Read and write
        operations performed in a transaction are atomic. Read operations may
        occur concurrent to a transaction.

        Transactions may be nested and may not be shared between threads.

        >>> from diskcache import Index
        >>> mapping = Index()
        >>> with mapping.transact():  # Atomically increment two keys.
        ...     mapping['total'] = mapping.get('total', 0) + 123.4
        ...     mapping['count'] = mapping.get('count', 0) + 1
        >>> with mapping.transact():  # Atomically calculate average.
        ...     average = mapping['total'] / mapping['count']
        >>> average
        123.4

        :return: context manager for use in `with` statement

        """
        with self._cache.transact(retry=True):
            yield

    def __repr__(self):
        """index.__repr__() <==> repr(index)

        Return string with printable representation of index.

        """
        name = type(self).__name__
        return "{0}({1!r})".format(name, self.directory)
