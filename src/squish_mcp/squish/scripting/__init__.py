"""
Squish Code Generation and Scripting Module

This module handles code generation and file operations including:
- Test template generation
- POM (Page Object Model) generation
- BDD test template generation
- Test case file creation
- Suite configuration management
- XML object snapshot parsing

This module consumes analysis data from squish/analysis/ and generates actual code/files.
"""

from .code_generation import BDDTemplateResult
from .code_generation import TestCaseCreationResult
from .code_generation import TestSuiteCreationResult
from .code_generation import TestTemplateResult
from .code_generation import create_test_case
from .code_generation import create_test_suite
from .code_generation import generate_bdd_template
from .code_generation import generate_test_template
from .parse_object_snapshot import parse_object_snapshot
from .pom_generation import OutputStrategy
from .pom_generation import POMFormat
from .pom_generation import SnapshotParseResult
from .pom_generation import page_objects_from_snapshot
from .pom_generation import pom_class_generator
from .pom_generation import pom_dict_generator
from .pom_generation import pom_function_generator
from .pom_generation import variable_to_method_name
from .suite_conf_management import SuiteConfiguration


__all__ = [
    # Models
    "BDDTemplateResult",
    "SuiteConfiguration",
    "SuiteUpdateResult",
    "TestCaseCreationResult",
    "TestSuiteCreationResult",
    "TestTemplateResult",
    # Functions
    "create_test_case",
    "create_test_suite",
    "generate_bdd_template",
    "pom_function_generator",
    "page_objects_from_snapshot",
    "pom_class_generator",
    "pom_dict_generator",
    "generate_test_template",
    "OutputStrategy",
    "parse_object_snapshot",
    "POMFormat",
    "SnapshotParseResult",
    "variable_to_method_name",
]
