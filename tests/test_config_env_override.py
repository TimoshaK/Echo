"""Tests for the ECHO_CONFIG_PATH override and the preserved default (CNTR-03).

The override lets a container point the app at a bind-mounted config directory
(`-v <host_dir>:/config` + `ECHO_CONFIG_PATH=/config/app_config.json`), which the
atomic owner-only writer can rewrite — unlike a single-file bind mount, where
`os.replace` fails with EBUSY. With no env var the path must stay the repository
root, byte-identical to the pre-override behavior (REFR-03).

These tests never read, write, or print the repository's real `app_config.json`.
"""

import pathlib
import tempfile
import unittest

from echo import config


def _repository_root_default():
    return pathlib.Path(config.__file__).resolve().parent.parent / "app_config.json"


class ConfigPathOverrideTests(unittest.TestCase):
    def test_default_is_repository_root(self):
        expected = _repository_root_default()
        self.assertEqual(config.resolve_config_path({}), expected)

    def test_env_override_is_used(self):
        self.assertEqual(
            config.resolve_config_path({"ECHO_CONFIG_PATH": "/config/app_config.json"}),
            pathlib.Path("/config/app_config.json"),
        )

    def test_empty_override_falls_back_to_default(self):
        self.assertEqual(
            config.resolve_config_path({"ECHO_CONFIG_PATH": ""}),
            _repository_root_default(),
        )

    def test_whitespace_override_falls_back_to_default(self):
        self.assertEqual(
            config.resolve_config_path({"ECHO_CONFIG_PATH": "   "}),
            _repository_root_default(),
        )

    def test_override_expands_user_home(self):
        self.assertEqual(
            config.resolve_config_path({"ECHO_CONFIG_PATH": "~/cfg/app_config.json"}),
            pathlib.Path("~/cfg/app_config.json").expanduser(),
        )

    def test_module_config_path_is_an_app_config_json(self):
        self.assertEqual(config.CONFIG_PATH.name, "app_config.json")

    def test_relative_override_is_preserved(self):
        self.assertEqual(
            config.resolve_config_path({"ECHO_CONFIG_PATH": "cfg/app_config.json"}),
            pathlib.Path("cfg/app_config.json"),
        )

    def test_load_and_save_use_the_module_attribute(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = pathlib.Path(tmp) / "app_config.json"
            original_path = config.CONFIG_PATH
            config.CONFIG_PATH = target
            try:
                config.save_config({"llm": {"api_key": "sk-override-test"}})
                self.assertTrue(target.exists())
                self.assertEqual(
                    config.load_config()["llm"]["api_key"], "sk-override-test"
                )
            finally:
                config.CONFIG_PATH = original_path


if __name__ == "__main__":
    unittest.main()
