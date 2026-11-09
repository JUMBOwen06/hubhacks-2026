"""The launcher behind start.bat and start.sh picks a free port."""
import socket

import launch


def test_pick_port_skips_a_busy_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as busy:
        busy.bind(("127.0.0.1", 0))
        busy.listen()
        taken = busy.getsockname()[1]
        assert not launch.port_is_free(taken)
        chosen = launch.pick_port(taken, tries=5)
        assert chosen != taken
        assert launch.port_is_free(chosen)


def test_pick_port_keeps_a_free_preferred_port():
    free = launch.pick_port(20000)
    assert launch.pick_port(free) == free
