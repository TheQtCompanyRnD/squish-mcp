#!/usr/bin/env python3
"""
Squish Code Analysis and Scripting Module

This module handles code analysis and generation functionality including:
- Test script pattern analysis
- Code generation helpers
- Template creation
- Context-aware code suggestions
- Suite configuration management

IMPORTANT: This file requires Python 3.10+ due to f-string usage and type hints.
Do not use with Python 2.x - it will cause syntax errors.
"""

# Auto-import all public functions from the modules
from .squish_code_analysis import *
from .pom_generation import (
    analyze_current_object_map_structure,
    generate_page_object_references,
    create_page_object_file,
    merge_with_existing_structure,
    generate_page_objects_from_snapshot,
    analyze_object_reference_patterns,
    determine_output_strategy_from_patterns,
    generate_pom_class_content,
    generate_function_based_content,
    generate_simple_dict_content,
    write_object_files,
    variable_to_method_name
)
from .pom_generation_helpers import (
    _determine_output_strategy,
    _generate_pom_class_objects,
    _generate_names_file_objects,
    _create_object_files
)