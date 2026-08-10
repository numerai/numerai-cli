import os
import subprocess
import tempfile
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIRECTORY = REPOSITORY_ROOT / "scripts"


class SetupScriptsTest(unittest.TestCase):
    def test_installers_do_not_reference_python_39(self):
        for script_path in SCRIPTS_DIRECTORY.iterdir():
            if not script_path.is_file():
                continue
            with self.subTest(script=script_path.name):
                self.assertNotIn("3.9", script_path.read_text())

    def test_macos_installs_python_312(self):
        script = (SCRIPTS_DIRECTORY / "setup-mac.sh").read_text()

        self.assertIn("Python 3.12.10", script)
        self.assertIn(
            "https://www.python.org/ftp/python/3.12.10/"
            "python-3.12.10-macos11.pkg",
            script,
        )

    def test_macos_runs_the_python_312_installer_when_python_is_missing(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_path = Path(temporary_directory)
            commands_path = temporary_path / "commands"
            commands_path.mkdir()
            command_log = temporary_path / "commands.log"

            commands = {
                "curl": '#!/bin/bash\nprintf "curl %s\\n" "$*" >> "$COMMAND_LOG"\n',
                "sudo": '#!/bin/bash\nprintf "sudo %s\\n" "$*" >> "$COMMAND_LOG"\n',
                "sw_vers": '#!/bin/bash\necho "13.6.0"\n',
                "which": (
                    '#!/bin/bash\nif [[ "$1" == "docker" ]]; then '
                    'echo "/usr/local/bin/docker"; fi\n'
                ),
            }
            for command_name, command in commands.items():
                command_path = commands_path / command_name
                command_path.write_text(command)
                command_path.chmod(0o755)

            environment = os.environ.copy()
            environment.update(
                {
                    "COMMAND_LOG": str(command_log),
                    "HOME": str(temporary_path),
                    "PATH": str(commands_path),
                }
            )
            subprocess.run(
                ["/bin/bash", SCRIPTS_DIRECTORY / "setup-mac.sh"],
                check=True,
                env=environment,
                capture_output=True,
                text=True,
            )

            commands_run = command_log.read_text()
            self.assertIn(
                "curl -fL https://www.python.org/ftp/python/3.12.10/"
                "python-3.12.10-macos11.pkg",
                commands_run,
            )
            self.assertIn(
                "sudo installer -pkg "
                f"{temporary_path}/Downloads/python-3.12.10-installer.pkg -target /",
                commands_run,
            )

    def test_windows_installs_python_312(self):
        script = (SCRIPTS_DIRECTORY / "setup-win10.ps1").read_text()

        self.assertIn('$pythonVersion = "3.12.10"', script)
        self.assertIn(
            "https://www.python.org/ftp/python/$pythonVersion/"
            "python-$pythonVersion-amd64.exe",
            script,
        )

    def test_shell_scripts_have_valid_syntax(self):
        for script_name in ("setup-mac.sh", "setup-ubu.sh"):
            with self.subTest(script=script_name):
                subprocess.run(
                    ["bash", "-n", SCRIPTS_DIRECTORY / script_name], check=True
                )


if __name__ == "__main__":
    unittest.main()
