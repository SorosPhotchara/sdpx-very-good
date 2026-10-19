"""Routes must be reachable under the prefix a platform rewrite forwards."""

import importlib
import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

import app.main


def build_app(prefix: str):
    with patch.dict(os.environ, {"API_ROOT_PATH": prefix}):
        return importlib.reload(app.main).app


class ApiPrefixTests(unittest.TestCase):
    def tearDown(self) -> None:
        importlib.reload(app.main)

    def test_routes_stay_unprefixed_when_no_root_path_is_configured(self) -> None:
        client = TestClient(build_app(""))
        self.assertEqual(client.get("/health").status_code, 200)
        self.assertEqual(client.get("/me").status_code, 401)
        self.assertEqual(client.get("/classrooms/").status_code, 401)
        self.assertEqual(client.get("/api/me").status_code, 404)

    def test_routes_move_under_the_configured_root_path(self) -> None:
        client = TestClient(build_app("/api"))
        self.assertEqual(client.get("/api/health").status_code, 200)
        self.assertEqual(client.get("/api/me").status_code, 401)
        self.assertEqual(client.get("/api/classrooms/").status_code, 401)
        self.assertEqual(client.get("/api/openapi.json").status_code, 200)
        self.assertEqual(client.get("/me").status_code, 404)

    def test_a_trailing_slash_in_the_root_path_does_not_double_up(self) -> None:
        client = TestClient(build_app("/api/"))
        self.assertEqual(client.get("/api/me").status_code, 401)
        self.assertEqual(client.get("/api//me").status_code, 404)


if __name__ == "__main__":
    unittest.main()
