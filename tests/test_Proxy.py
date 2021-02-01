import unittest

from soso.state.state import (GetAttr, GetItem, Proxy, SetAttr, SetItem,
                              _get_ops)


class TestProxy(unittest.TestCase):
    def test_set(self) -> None:
        proxy = Proxy()
        proxy.value = 5
        self.assertEqual(_get_ops(proxy),
                         [SetAttr('value', 5)])

    def test_nested_set(self) -> None:
        proxy = Proxy()
        proxy.nested.value = 12
        self.assertEqual(_get_ops(proxy), [
            GetAttr('nested'),
            SetAttr('value', 12)
        ])

    def test_set_multiple(self) -> None:
        proxy = Proxy()
        proxy.value1 = 1
        proxy.value2 = 2
        self.assertEqual(_get_ops(proxy), [
            SetAttr('value1', 1),
            SetAttr('value2', 2)
        ])

    def test_setitem(self) -> None:
        proxy = Proxy()
        proxy.nested.value[1] = 12

        path = _get_ops(proxy)
        self.assertEqual(path, [
            GetAttr("nested"),
            GetAttr("value"),
            SetItem(1, 12)
        ])

    def test_getitem(self) -> None:
        proxy = Proxy()
        proxy.nested.value[1]

        path = _get_ops(proxy)
        self.assertEqual(path, [
            GetAttr("nested"),
            GetAttr("value"),
            GetItem(1)
        ])

    def test_access(self) -> None:
        proxy = Proxy()
        proxy.nested.value

        path = _get_ops(proxy)
        self.assertEqual(path, [
            GetAttr("nested"),
            GetAttr("value")
        ])
