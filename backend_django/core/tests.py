from django.core.cache import cache
from django.test import TestCase, override_settings

from core.cache_utils import bump_namespace_version, get_namespace_version


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "core-cache-tests",
        }
    }
)
class CacheNamespaceVersionTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_namespace_version_remains_readable_after_initialization_and_bump(self):
        self.assertEqual(get_namespace_version("items"), 1)
        self.assertEqual(get_namespace_version("items"), 1)

        self.assertEqual(bump_namespace_version("items"), 2)
        self.assertEqual(get_namespace_version("items"), 2)

