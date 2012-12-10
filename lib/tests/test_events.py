"""Unit tests for the event handler.
"""

import os
import sys
import threading
import time
import types
import unittest
import xmlrpclib

from mysql.hub import (
    config as _config,
    errors as _errors,
    events as _events,
    persistence as _persistence,
    )

import tests.utils as _test_utils

_TEST1 = None

def test1(job):
    global _TEST1
    _TEST1 = job.args[0]

class Callable(object):
    """A class acting as a callable.
    """
    def __init__(self, n=None):
        self.result = n
        self.__name__ = "Callable(%s)" % (n,)

    def __call__(self, job):
        self.result += job.args[0]


class TestHandler(unittest.TestCase):
    """Test event handler.
    """

    def setUp(self):
        from __main__ import options
        _persistence.init(host=options.host, port=options.port,
                          user=options.user, password=options.password)
        self.handler = _events.Handler()
        self.handler.start()

    def tearDown(self):
        self.handler.shutdown()
        _persistence.deinit()

    def test_events(self):
        "Test creating events."
        self.assertEqual(_events.Event().name, None)
        self.assertEqual(_events.Event("Event").name, "Event")

    def test_register(self):
        "Test event registration functions."
        callables = [Callable(), Callable(), Callable()]

        self.assertFalse(self.handler.is_registered(_events.SERVER_LOST, test1))

        # Check registration of a function
        self.handler.register(_events.SERVER_LOST, test1)
        self.assertTrue(self.handler.is_registered(_events.SERVER_LOST, test1))

        # Check registration of a callable that is not a function
        self.handler.register(_events.SERVER_LOST, callables[0])

        # Check registration of a list of callables
        self.handler.register(_events.SERVER_LOST, callables[1:])

        # Check that all callables are now registered
        for obj in callables:
            self.assertTrue(
                self.handler.is_registered(_events.SERVER_LOST, obj)
                )

        # Check unregistration of a function
        self.handler.unregister(_events.SERVER_LOST, test1)
        self.assertFalse(
            self.handler.is_registered(_events.SERVER_LOST, test1)
            )
        self.assertRaises(
            _errors.UnknownCallableError,
            self.handler.unregister, _events.SERVER_LOST, test1
            )

        # Check unregistration of callables that are not functions
        for obj in callables:
            self.assertRaises(
                _errors.UnknownCallableError,
                self.handler.unregister, _events.SERVER_LOST, obj
                )

        # Check that they are indeed gone
        for obj in callables:
            self.assertFalse(
                self.handler.is_registered(_events.SERVER_LOST, obj)
                )

        # Check that passing a non-event raises an exception
        self.assertRaises(_errors.NotEventError, self.handler.register,
                          list(), test1)
        self.assertRaises(_errors.NotEventError, self.handler.is_registered,
                          list(), test1)
        self.assertRaises(_errors.NotEventError, self.handler.unregister,
                          list(), test1)

        # Check that passing non-callables raise an exception
        self.assertRaises(_errors.NotCallableError, self.handler.register,
                          _events.SERVER_LOST, callables + [5])
        self.assertRaises(_errors.NotCallableError, self.handler.is_registered,
                          _events.SERVER_LOST, callables + [5])
        self.assertRaises(_errors.NotCallableError, self.handler.unregister,
                          _events.SERVER_LOST, callables + [5])

    def test_trigger(self):
        "Test that triggering an event dispatches jobs."

        global _TEST1

        # Register a function that we can check if it was called
        self.handler.register(_events.SERVER_LOST, test1)

        # Register a function and trigger it to see that the executor
        # really executed it.  When triggering the event, a list of
        # the jobs scheduled will be returned, so we iterate over the
        # list and wait until all jobs have been executed.
        _TEST1 = 0
        jobs = self.handler.trigger(_events.SERVER_LOST, 3)
        self.assertEqual(len(jobs), 1)
        for job in jobs:
            job.wait()
        self.assertEqual(_TEST1, 3)

        # Check that triggering an event by name works.
        _TEST1 = 0
        jobs = self.handler.trigger('SERVER_LOST', 4)
        self.assertEqual(len(jobs), 1)
        for job in jobs:
            job.wait()
        self.assertEqual(_TEST1, 4)

        # Check that temporary, unnamed events, also work by
        # registering a bunch of callables with a temporary event
        callables = [ Callable(n) for n in range(0, 2) ]
        my_event = _events.Event("TestEvent")
        self.handler.register(my_event, callables)

        # Trigger the event and wait for all jobs to finish
        jobs = self.handler.trigger(my_event, 3)
        for job in jobs:
            job.wait()

        for idx, obj in enumerate(callables):
            self.assertEqual(obj.result, idx + 3)

#
# Testing the decorator to see that it works
#

_PROMOTED = None
_DEMOTED = None

class TestDecorator(unittest.TestCase):
    "Test the decorators related to events"

    handler = _events.Handler()

    def setUp(self):
        from __main__ import options
        _persistence.init(host=options.host, port=options.port,
                          user=options.user, password=options.password)
        self.handler.start()

    def tearDown(self):
        self.handler.shutdown()
        _persistence.deinit()

    def test_decorator(self):
        global _PROMOTED, _DEMOTED
        _PROMOTED = None

        # Test decorator
        _PROMOTED = None
        jobs = self.handler.trigger(_events.SERVER_PROMOTED, "Testing")
        for job in jobs:
            job.wait()
        self.assertEqual(_PROMOTED, "Testing")

        # Test undo action for decorator
        _DEMOTED = None
        jobs = self.handler.trigger(_events.SERVER_DEMOTED, "Executing")
        for job in jobs:
            job.wait()
        self.assertEqual(_DEMOTED, "Undone")

# Testing that on_event decorator works as expected
@_events.on_event(_events.SERVER_PROMOTED)
def my_event(job):
    global _PROMOTED
    _PROMOTED = job.args[0]

# Testing that undo actions are really executed
_DEMOTED = None

@_events.on_event(_events.SERVER_DEMOTED)
def test2(job):
    global _DEMOTED
    _DEMOTED = job.args[0]
    raise NotImplementedError("Just not here")

@test2.undo
def test2_undo(job):
    global _DEMOTED
    _DEMOTED = "Undone"

class TestService(unittest.TestCase):
    "Test the service interface"

    def setUp(self):
        self.manager, self.proxy = tests.utils.setup_xmlrpc()

    def tearDown(self):
        tests.utils.teardown_xmlrpc(self.manager, self.proxy)

    def test_trigger(self):
        promoted = [None]
        def my_event(job):
            promoted[0] = job.args[0]
        _events.Handler().register(_events.SERVER_PROMOTED, my_event)
        jobs = self.proxy.event.trigger('SERVER_PROMOTED', "my.example.com")
        self.proxy.event.wait_for(jobs)
        self.assertEqual(promoted[0], "my.example.com")

if __name__ == "__main__":
    unittest.main()
