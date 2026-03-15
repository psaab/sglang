import socket
import unittest

from sglang.srt.utils.common import (
    _get_addrinfos_for_bind,
    bind_port,
    get_free_port,
    get_open_port,
    is_port_available,
    try_bind_socket,
)
from sglang.test.ci.ci_register import register_cpu_ci
from sglang.test.test_utils import CustomTestCase

register_cpu_ci(est_time=1, suite="stage-a-cpu-only")


class TestGetAddrinfosForBind(CustomTestCase):
    def test_returns_nonempty(self):
        """_get_addrinfos_for_bind should return at least one addrinfo tuple."""
        infos = _get_addrinfos_for_bind()
        self.assertGreater(len(infos), 0)

    def test_tuple_structure(self):
        """Each entry should be a 5-tuple (family, socktype, proto, canonname, sockaddr)."""
        for info in _get_addrinfos_for_bind():
            self.assertEqual(len(info), 5)
            family, socktype, proto, canonname, sockaddr = info
            self.assertIn(family, (socket.AF_INET, socket.AF_INET6))
            self.assertEqual(socktype, socket.SOCK_STREAM)

    def test_sockaddr_is_bindable(self):
        """The returned sockaddr should be directly usable with bind()."""
        for family, socktype, proto, _, sockaddr in _get_addrinfos_for_bind():
            with socket.socket(family, socktype, proto) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(sockaddr)
                # port 0 means OS assigns an ephemeral port
                bound_port = s.getsockname()[1]
                self.assertGreater(bound_port, 0)

    def test_with_specific_port(self):
        """_get_addrinfos_for_bind(port=N) should embed that port in sockaddr."""
        port = get_free_port()
        for family, socktype, proto, _, sockaddr in _get_addrinfos_for_bind(port=port):
            # sockaddr[1] is the port for both AF_INET and AF_INET6
            self.assertEqual(sockaddr[1], port)

    def test_with_host(self):
        """_get_addrinfos_for_bind(host, port) should return matching sockaddrs."""
        infos = _get_addrinfos_for_bind("127.0.0.1", 0)
        self.assertGreater(len(infos), 0)
        for family, socktype, proto, _, sockaddr in infos:
            self.assertEqual(family, socket.AF_INET)
            self.assertEqual(sockaddr[0], "127.0.0.1")

    def test_unique_families(self):
        """Results should be deduplicated by address family."""
        infos = _get_addrinfos_for_bind()
        families = [info[0] for info in infos]
        self.assertEqual(len(families), len(set(families)))


class TestTryBindSocket(CustomTestCase):
    def test_returns_bound_socket(self):
        """try_bind_socket should return a bound socket."""
        sock = try_bind_socket()
        try:
            port = sock.getsockname()[1]
            self.assertGreater(port, 0)
        finally:
            sock.close()

    def test_with_specific_port(self):
        """try_bind_socket(port=N) should bind to that port."""
        port = get_free_port()
        sock = try_bind_socket(port=port)
        try:
            self.assertEqual(sock.getsockname()[1], port)
        finally:
            sock.close()

    def test_with_listen(self):
        """try_bind_socket(listen=True) should create a listening socket."""
        sock = try_bind_socket(listen=True)
        try:
            port = sock.getsockname()[1]
            self.assertGreater(port, 0)
        finally:
            sock.close()

    def test_raises_on_occupied_port(self):
        """try_bind_socket should raise OSError if port is occupied."""
        sock1 = try_bind_socket(port=0, listen=True)
        try:
            port = sock1.getsockname()[1]
            with self.assertRaises(OSError):
                try_bind_socket(port=port, listen=True)
        finally:
            sock1.close()


class TestSocketUtilities(CustomTestCase):
    def test_is_port_available(self):
        """is_port_available should return True for a free port."""
        port = get_free_port()
        self.assertTrue(is_port_available(port))

    def test_is_port_available_occupied(self):
        """is_port_available should return False for an occupied port."""
        sock = bind_port(get_free_port())
        try:
            port = sock.getsockname()[1]
            self.assertFalse(is_port_available(port))
        finally:
            sock.close()

    def test_get_free_port(self):
        """get_free_port should return a valid port number."""
        port = get_free_port()
        self.assertGreater(port, 0)
        self.assertLessEqual(port, 65535)

    def test_bind_port(self):
        """bind_port should return a listening socket."""
        port = get_free_port()
        sock = bind_port(port)
        try:
            self.assertEqual(sock.getsockname()[1], port)
        finally:
            sock.close()

    def test_get_open_port(self):
        """get_open_port should return a valid port number."""
        port = get_open_port()
        self.assertGreater(port, 0)
        self.assertLessEqual(port, 65535)


if __name__ == "__main__":
    unittest.main()
