import unittest

from soso.state import AttributeAccess, Proxy, _get_proxy_path  # type: ignore


class TestProxy(unittest.TestCase):
    def test_set(self) -> None:
        proxy = Proxy()
        proxy.value = 5
        self.assertEqual(_get_proxy_path(proxy),
                         [AttributeAccess.SETATTR, 'value', 5])

    def test_nested_set(self) -> None:
        proxy = Proxy()
        proxy.nested.value = 12
        self.assertEqual(_get_proxy_path(proxy), [
            AttributeAccess.GETATTR, 'nested', AttributeAccess.SETATTR,
            'value', 12
        ])

    def test_set_multiple(self) -> None:
        proxy = Proxy()
        proxy.value1 = 1
        proxy.value2 = 2
        self.assertEqual(_get_proxy_path(proxy), [
            AttributeAccess.SETATTR, 'value1', 1, AttributeAccess.SETATTR,
            'value2', 2
        ])

    def test_setitem(self) -> None:
        proxy = Proxy()
        proxy.nested.value[1] = 12

        path = _get_proxy_path(proxy)
        self.assertEqual(path, [
            AttributeAccess.GETATTR, "nested", AttributeAccess.GETATTR,
            "value", AttributeAccess.SETITEM, 1, 12
        ])

    def test_access(self) -> None:
        proxy = Proxy()
        proxy.nested.value

        path = _get_proxy_path(proxy)
        self.assertEqual(path, [
            AttributeAccess.GETATTR, "nested", AttributeAccess.GETATTR, "value"
        ])
