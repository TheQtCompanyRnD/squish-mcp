"""Custom exceptions for the Squish MCP server."""


class SquishMCPException(Exception):
    """Base exception for all Squish MCP errors."""


class ConfigurationException(SquishMCPException):
    """Missing Squish installation, bad paths, invalid YAML."""


class AnalysisException(SquishMCPException):
    """Failed to parse test suites, object references, or patterns."""


class TestExecutionException(SquishMCPException):
    """Squishrunner failures or subprocess errors."""


class FileOperationException(SquishMCPException):
    """Cannot read or write test files, snapshots, or POM output."""
