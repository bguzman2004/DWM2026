import pytest

from tests.support.stack import Stack


@pytest.fixture
def stack(tmp_path):
    s = Stack(tmp_path).start()
    yield s
    s.stop()


@pytest.fixture(scope="module")
def shared_stack(tmp_path_factory):
    s = Stack(tmp_path_factory.mktemp("stack")).start()
    yield s
    s.stop()
