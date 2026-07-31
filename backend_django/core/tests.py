from django.core.cache import cache
from django.test import SimpleTestCase, TestCase, override_settings
from django.conf import settings

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


class ProxyLoggingDocumentationTests(SimpleTestCase):
    def test_ws_migration_logging_has_sanitized_access_and_error_recovery_steps(self):
        document = (
            settings.BASE_DIR.parent / "docs" / "服务器部署文档.md"
        ).read_text(encoding="utf-8")
        self.assertIn("log_format local_flavor_safe", document)
        self.assertIn("$request_method $uri $server_protocol", document)
        self.assertIn("location /ws/", document)
        self.assertIn("error_log /dev/null emerg;", document)
        self.assertIn("AUTH_WS_QUERY_TOKEN_ENABLED=0", document)
        self.assertIn("删除 `error_log /dev/null emerg;`", document)

