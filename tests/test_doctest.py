import doctest

import diskcache.core
import diskcache.fanout
import diskcache.persistent
import diskcache.recipes


def test_core():
    failures, _ = doctest.testmod(diskcache.core)
    assert failures == 0


def test_fanout():
    failures, _ = doctest.testmod(diskcache.fanout)
    assert failures == 0


def test_persistent():
    failures, _ = doctest.testmod(diskcache.persistent)
    assert failures == 0


def test_recipes():
    failures, _ = doctest.testmod(diskcache.recipes)
    assert failures == 0


# TODO: Fixme
# def test_tutorial():
#     failures, _ = doctest.testfile("../docs/tutorial.rst")
#     assert failures == 0
