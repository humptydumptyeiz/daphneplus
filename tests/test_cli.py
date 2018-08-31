# coding: utf8

import logging
from unittest import TestCase

from daphneplus.cli import CommandLineInterface
from daphneplus.endpoints import build_endpoint_description_strings as build


class TestEndpointDescriptions(TestCase):
    """
    Tests that the endpoint parsing/generation works as intended.
    """

    def testBasics(self):
        self.assertEqual(build(), [], msg="Empty list returned when no kwargs given")

    def testTcpPortBindings(self):
        self.assertEqual(
            build(port=1234, host="example.com"),
            ["tcp:port=1234:interface=example.com"],
        )

        self.assertEqual(
            build(port=8000, host="127.0.0.1"), ["tcp:port=8000:interface=127.0.0.1"]
        )

        self.assertEqual(
            build(port=8000, host="[200a::1]"), [r"tcp:port=8000:interface=200a\:\:1"]
        )

        self.assertEqual(
            build(port=8000, host="200a::1"), [r"tcp:port=8000:interface=200a\:\:1"]
        )

        # incomplete port/host kwargs raise errors
        self.assertRaises(ValueError, build, port=123)
        self.assertRaises(ValueError, build, host="example.com")

    def testUnixSocketBinding(self):
        self.assertEqual(
            build(unix_socket="/tmp/daphneplus.sock"), ["unix:/tmp/daphneplus.sock"]
        )

    def testFileDescriptorBinding(self):
        self.assertEqual(build(file_descriptor=5), ["fd:fileno=5"])

    def testMultipleEnpoints(self):
        self.assertEqual(
            sorted(
                build(
                    file_descriptor=123,
                    unix_socket="/tmp/daphneplus.sock",
                    port=8080,
                    host="10.0.0.1",
                )
            ),
            sorted(
                [
                    "tcp:port=8080:interface=10.0.0.1",
                    "unix:/tmp/daphneplus.sock",
                    "fd:fileno=123",
                ]
            ),
        )


class TestCLIInterface(TestCase):
    """
    Tests the overall CLI class.
    """

    class TestedCLI(CommandLineInterface):
        """
        CommandLineInterface subclass that we used for testing (has a fake
        server subclass).
        """

        class TestedServer:
            """
            Mock server object for testing.
            """

            def __init__(self, **kwargs):
                self.init_kwargs = kwargs

            def run(self):
                pass

        server_class = TestedServer

    def setUp(self):
        logging.disable(logging.CRITICAL)

    def tearDown(self):
        logging.disable(logging.NOTSET)

    def assertCLI(self, args, server_kwargs):
        """
        Asserts that the CLI class passes the right args to the server class.
        Passes in a fake application automatically.
        """
        cli = self.TestedCLI()
        cli.run(
            args + ["daphneplus:__version__"]
        )  # We just pass something importable as app
        # Check the server got all arguments as intended
        for key, value in server_kwargs.items():
            # Get the value and sort it if it's a list (for endpoint checking)
            actual_value = cli.server.init_kwargs.get(key)
            if isinstance(actual_value, list):
                actual_value.sort()
            # Check values
            self.assertEqual(
                value,
                actual_value,
                "Wrong value for server kwarg %s: %r != %r"
                % (key, value, actual_value),
            )

    def testCLIBasics(self):
        """
        Tests basic endpoint generation.
        """
        self.assertCLI([], {"endpoints": ["tcp:port=8000:interface=127.0.0.1"]})
        self.assertCLI(
            ["-p", "123"], {"endpoints": ["tcp:port=123:interface=127.0.0.1"]}
        )
        self.assertCLI(
            ["-b", "10.0.0.1"], {"endpoints": ["tcp:port=8000:interface=10.0.0.1"]}
        )
        self.assertCLI(
            ["-b", "200a::1"], {"endpoints": [r"tcp:port=8000:interface=200a\:\:1"]}
        )
        self.assertCLI(
            ["-b", "[200a::1]"], {"endpoints": [r"tcp:port=8000:interface=200a\:\:1"]}
        )
        self.assertCLI(
            ["-p", "8080", "-b", "example.com"],
            {"endpoints": ["tcp:port=8080:interface=example.com"]},
        )

    def testUnixSockets(self):
        self.assertCLI(
            ["-p", "8080", "-u", "/tmp/daphneplus.sock"],
            {
                "endpoints": [
                    "tcp:port=8080:interface=127.0.0.1",
                    "unix:/tmp/daphneplus.sock",
                ]
            },
        )
        self.assertCLI(
            ["-b", "example.com", "-u", "/tmp/daphneplus.sock"],
            {
                "endpoints": [
                    "tcp:port=8000:interface=example.com",
                    "unix:/tmp/daphneplus.sock",
                ]
            },
        )
        self.assertCLI(
            ["-u", "/tmp/daphneplus.sock", "--fd", "5"],
            {"endpoints": ["fd:fileno=5", "unix:/tmp/daphneplus.sock"]},
        )

    def testMixedCLIEndpointCreation(self):
        """
        Tests mixing the shortcut options with the endpoint string options.
        """
        self.assertCLI(
            ["-p", "8080", "-e", "unix:/tmp/daphneplus.sock"],
            {
                "endpoints": [
                    "tcp:port=8080:interface=127.0.0.1",
                    "unix:/tmp/daphneplus.sock",
                ]
            },
        )
        self.assertCLI(
            ["-p", "8080", "-e", "tcp:port=8080:interface=127.0.0.1"],
            {
                "endpoints": [
                    "tcp:port=8080:interface=127.0.0.1",
                    "tcp:port=8080:interface=127.0.0.1",
                ]
            },
        )

    def testCustomEndpoints(self):
        """
        Tests entirely custom endpoints
        """
        self.assertCLI(["-e", "imap:"], {"endpoints": ["imap:"]})
