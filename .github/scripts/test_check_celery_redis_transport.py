import os
from pathlib import Path
import subprocess
import sys
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CHECK_SCRIPT = REPOSITORY_ROOT / ".github" / "scripts" / "check_celery_redis_transport.py"


class CeleryRedisTransportSmokeScriptTests(unittest.TestCase):
    def test_dependencies_and_configuration_load_without_connecting(self):
        env = os.environ.copy()
        env.update(
            {
                "DJANGO_ENV": "dev",
                "DJANGO_SECRET_KEY": "local-smoke-test-only",
                "DB_ENGINE": "sqlite",
                "CACHE_BACKEND": "redis",
                "CACHE_REDIS_URL": "redis://127.0.0.1:6379/0",
                "CHAT_ENABLE_WS": "1",
                "CHAT_REDIS_URL": "redis://127.0.0.1:6379/1",
                "CELERY_BROKER_URL": "redis://127.0.0.1:6379/2",
                "CELERY_RESULT_BACKEND": "redis://127.0.0.1:6379/3",
                "CELERY_TASK_ALWAYS_EAGER": "0",
            }
        )

        result = subprocess.run(
            [sys.executable, str(CHECK_SCRIPT)],
            cwd=REPOSITORY_ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(
            "Celery Redis transport smoke check passed (network=skipped)",
            result.stdout,
        )


if __name__ == "__main__":
    unittest.main()
