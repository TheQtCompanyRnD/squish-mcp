from dataclasses import dataclass
from dataclasses import field
from pathlib import Path

from squish_mcp.errors import FileOperationException


@dataclass(frozen=True)
class SuiteConfiguration:
    """Configuration parsed from a suite.conf file."""

    config: dict[str, str] = field(default_factory=dict)

    @staticmethod
    def get_path(suite_path: Path) -> Path:
        """Get the path to the suite.conf file."""
        return suite_path / "suite.conf"

    def __str__(self) -> str:
        return "\n".join(f"{key}={value}" for key, value in self.config.items())

    def update_keyvalue(self, key: str, value: str) -> "SuiteConfiguration":

        new_config = self.config.copy()
        new_config[key] = value
        return SuiteConfiguration(config=new_config)

    def append_value_to_key(self, key: str, value: str) -> "SuiteConfiguration":

        new_config = self.config.copy()
        if key in new_config:
            new_config[key] += f",{value}"
        else:
            new_config[key] = value
        return SuiteConfiguration(config=new_config)

    def get_key_value(self, key: str) -> str | None:
        """Get the value of a configuration key."""
        return self.config.get(key)

    @staticmethod
    def read(suite_path: Path) -> "SuiteConfiguration":
        """Read and parse a suite.conf file from a Squish test suite directory."""
        suite_conf_path = SuiteConfiguration.get_path(suite_path)

        if not suite_conf_path.exists():
            raise FileOperationException(f"suite.conf not found at: {suite_conf_path}. Suite must already exist.")

        try:
            with open(suite_conf_path, "r", encoding="utf-8") as f:
                content = f.read()

            suite_config = {}
            lines = content.strip().split("\n")

            for line in lines:
                line_stripped = line.strip()
                if "=" in line_stripped and not line_stripped.startswith("#"):
                    key, value = line_stripped.split("=", 1)
                    key = key.strip()
                    value = value.strip()
                    suite_config[key] = value

            return SuiteConfiguration(config=suite_config)

        except Exception as e:
            raise FileOperationException(f"Error reading suite.conf: {str(e)}") from e

    def save_in_suite(self, suite_path: Path) -> None:
        """Save the current configuration to the suite.conf file."""
        suite_conf_path = SuiteConfiguration.get_path(suite_path)

        try:
            with open(suite_conf_path, "w", encoding="utf-8") as f:
                for key, value in self.config.items():
                    f.write(f"{key}={value}\n")

        except Exception as e:
            raise FileOperationException(f"Error saving suite.conf: {str(e)}") from e
