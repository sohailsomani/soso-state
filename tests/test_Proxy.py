import unittest

from soso.state import (AttributeAccess, PropertyOp, Proxy,  # type: ignore
                        _get_ops)


class TestProxy(unittest.TestCase):
    def test_set(self) -> None:
        proxy = Proxy()
        proxy.value = 5
        self.assertEqual(_get_ops(proxy),
                         [PropertyOp(AttributeAccess.SETATTR, 'value', 5)])

    def test_nested_set(self) -> None:
        proxy = Proxy()
        proxy.nested.value = 12
        self.assertEqual(_get_ops(proxy), [
            PropertyOp(AttributeAccess.GETATTR, 'nested'),
            PropertyOp(AttributeAccess.SETATTR, 'value', 12)
        ])

    def test_set_multiple(self) -> None:
        proxy = Proxy()
        proxy.value1 = 1
        proxy.value2 = 2
        self.assertEqual(_get_ops(proxy), [
            PropertyOp(AttributeAccess.SETATTR, 'value1', 1),
            PropertyOp(AttributeAccess.SETATTR, 'value2', 2)
        ])

    def test_setitem(self) -> None:
        proxy = Proxy()
        proxy.nested.value[1] = 12

        path = _get_ops(proxy)
        self.assertEqual(path, [
            PropertyOp(AttributeAccess.GETATTR, "nested"),
            PropertyOp(AttributeAccess.GETATTR, "value"),
            PropertyOp(AttributeAccess.SETITEM, 1, 12)
        ])

    def test_access(self) -> None:
        proxy = Proxy()
        proxy.nested.value

        path = _get_ops(proxy)
        self.assertEqual(path, [
            PropertyOp(AttributeAccess.GETATTR, "nested"),
            PropertyOp(AttributeAccess.GETATTR, "value")
        ])
