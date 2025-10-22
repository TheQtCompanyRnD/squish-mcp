#!/usr/bin/env python3
"""
Squish Code Analysis Module

Handles code analysis and generation functionality including:
- Test script pattern analysis
- Code generation helpers
- Template creation
- Context-aware code suggestions

IMPORTANT: This file requires Python 3.10+ due to f-string usage and type hints.
Do not use with Python 2.x - it will cause syntax errors.
"""

import os
import glob
import re
from typing import Dict, List, Optional, Tuple
from context import (
    get_test_format_context, 
    get_global_script_context, 
    get_object_reference_context,
    get_squish_rules_context
)

def analyze_existing_patterns() -> Dict:
    """
    Analyze existing test patterns to understand how to generate consistent new tests.
    
    Returns:
        Dict with pattern analysis including common imports, object usage, and code structure.
    """
    # Get context from initialization
    test_format_context = get_test_format_context()
    object_ref_context = get_object_reference_context()
    global_script_context = get_global_script_context()
    rules_context = get_squish_rules_context()
    
    analysis = {
        "common_imports": [],
        "object_patterns": {},
        "api_usage": {},
        "global_script_usage": {},
        "template_suggestions": {},
        "coding_conventions": {}
    }
    
    # Analyze test format patterns
    if test_format_context.get("status") == 0:
        patterns = test_format_context["analysis"]["patterns"]
        
        # Extract common imports
        global_imports = patterns.get("global_script_imports", [])
        analysis["common_imports"] = list(set(global_imports))
        
        # Analyze API usage
        api_calls = patterns.get("squish_api_usage", [])
        api_frequency = {}
        for call in api_calls:
            api_frequency[call] = api_frequency.get(call, 0) + 1
        analysis["api_usage"] = dict(sorted(api_frequency.items(), key=lambda x: x[1], reverse=True))
        
        # Object usage patterns
        object_refs = patterns.get("object_usage", [])
        analysis["object_patterns"]["references"] = list(set(object_refs))
    
    # Analyze object reference patterns
    if object_ref_context.get("status") == 0:
        locations = object_ref_context["analysis"]["locations"]
        
        # Determine primary object reference pattern
        if locations["global_object_files"]:
            analysis["object_patterns"]["primary_location"] = "global_scripts"
            analysis["object_patterns"]["files"] = [f["path"] for f in locations["global_object_files"]]
        elif locations["suite_names_files"]:
            analysis["object_patterns"]["primary_location"] = "suite_names"
            analysis["object_patterns"]["files"] = [f["path"] for f in locations["suite_names_files"]]
        else:
            analysis["object_patterns"]["primary_location"] = "other"
            analysis["object_patterns"]["files"] = [f["path"] for f in locations["other_object_files"]]
    
    # Analyze global script usage
    if global_script_context.get("status") == 0:
        files = global_script_context["analysis"]["files"]
        
        # Extract commonly used utilities
        common_functions = []
        for file_info in files:
            if "functions" in file_info:
                common_functions.extend(file_info["functions"])
        
        analysis["global_script_usage"]["available_functions"] = common_functions[:20]  # Top 20
        analysis["global_script_usage"]["directories"] = global_script_context["analysis"]["directories"]
    
    # Apply project-specific rules
    if rules_context.get("status") == 0:
        patterns = rules_context["rules"].get("memories", {}).get("learned_patterns", [])
        
        conventions = {}
        for pattern in patterns:
            if isinstance(pattern, dict):
                pattern_text = pattern.get("pattern", "")
                context_text = pattern.get("context", "")
                
                if "screenshot verification" in pattern_text.lower():
                    conventions["screenshot_verification"] = context_text
                elif "setup function" in pattern_text.lower():
                    conventions["setup_function"] = context_text
        
        analysis["coding_conventions"] = conventions
    
    return {
        "status": 0,
        "message": "Successfully analyzed existing patterns",
        "analysis": analysis
    }

def generate_test_template(test_case_name: str, suite_path: str, test_description: str = "") -> Dict:
    """
    Generate a test template based on existing patterns and project conventions.
    
    Args:
        test_case_name: Name of the test case
        suite_path: Path to the test suite
        test_description:  description of what the test should do
        
    Returns:
        Dict with generated template and metadata
    """
    # Analyze existing patterns
    pattern_analysis = analyze_existing_patterns()
    
    if pattern_analysis["status"] != 0:
        # Fallback to basic template
        return _generate_basic_template(test_case_name, test_description)
    
    analysis = pattern_analysis["analysis"]
    
    # Build imports section
    imports = ["import squish"]
    
    # Add object imports based on discovered patterns
    object_pattern = analysis.get("object_patterns", {})
    if object_pattern.get("primary_location") == "suite_names":
        imports.append("import names")
    elif object_pattern.get("primary_location") == "global_scripts":
        # Extract import names from global script files
        global_files = object_pattern.get("files", [])
        for file_path in global_files[:2]:  # Limit to first 2 files
            basename = os.path.splitext(os.path.basename(file_path))[0]
            if basename not in ["__init__", "test"]:
                imports.append(f"import {basename}")
    
    # Add common global script imports
    common_imports = analysis.get("common_imports", [])
    for imp in common_imports[:3]:  # Limit to top 3
        if imp not in [i.split()[-1] for i in imports]:
            imports.append(f"import {imp}")
    
    # Build main function based on common API usage
    api_usage = analysis.get("api_usage", {})
    common_apis = list(api_usage.keys())[:5]  # Top 5 most used APIs
    
    # Build test steps based on discovered patterns
    test_steps = []
    test_steps.append(f'test.log("Starting test case: {test_case_name}")')
    
    if test_description:
        test_steps.append(f'test.log("Test description: {test_description}")')
    
    # Add common setup if discovered
    conventions = analysis.get("coding_conventions", {})
    if "setup_function" in conventions:
        test_steps.append("# Setup based on project conventions")
        test_steps.append("# " + conventions["setup_function"])
    
    # Add placeholder API calls based on common usage
    if "startApplication" in common_apis:
        test_steps.append("")
        test_steps.append("# Start application")
        test_steps.append('# startApplication("YourApplication")')
    
    if any("waitFor" in api for api in common_apis):
        test_steps.append("")
        test_steps.append("# Wait for objects")
        if object_pattern.get("primary_location") == "suite_names":
            test_steps.append("# waitForObject(names.your_object)")
        else:
            test_steps.append("# waitForObject(your_object_reference)")
    
    if any("click" in api for api in common_apis):
        test_steps.append("")
        test_steps.append("# Interact with UI")
        if object_pattern.get("primary_location") == "suite_names":
            test_steps.append("# clickButton(names.your_button)")
        else:
            test_steps.append("# clickButton(your_button_reference)")
    
    if any("verify" in api for api in common_apis):
        test_steps.append("")
        test_steps.append("# Verify results")
        test_steps.append('# test.verify(condition, "Verification message")')
    
    # Add screenshot verification if it's a pattern
    if "screenshot_verification" in conventions:
        test_steps.append("")
        test_steps.append("# Screenshot verification (project pattern)")
        test_steps.append("# " + conventions["screenshot_verification"])
    
    test_steps.append("")
    test_steps.append(f'test.log("Test case {test_case_name} completed")')
    
    # Build the complete template
    template_parts = []
    template_parts.append("# -*- coding: utf-8 -*-")
    template_parts.append("")
    template_parts.append(f"# Test case: {test_case_name}")
    if test_description:
        template_parts.append(f"# Description: {test_description}")
    template_parts.append("# Auto-generated by Squish MCP Server using project patterns")
    template_parts.append("")
    
    # Add imports
    for imp in imports:
        template_parts.append(imp)
    
    template_parts.append("")
    template_parts.append("def main():")
    template_parts.append('    """')
    template_parts.append(f"    Main test function for {test_case_name}")
    if test_description:
        template_parts.append(f"    {test_description}")
    template_parts.append('    """')
    
    # Add test steps with proper indentation
    for step in test_steps:
        if step.strip():
            template_parts.append(f"    {step}")
        else:
            template_parts.append("")
    
    template_content = "\n".join(template_parts)
    
    return {
        "status": 0,
        "message": f"Generated template for {test_case_name} based on project patterns",
        "template": template_content,
        "metadata": {
            "imports_used": imports,
            "object_pattern": object_pattern.get("primary_location", "unknown"),
            "api_patterns": common_apis,
            "conventions_applied": list(conventions.keys())
        }
    }

def _generate_basic_template(test_case_name: str, test_description: str = "") -> Dict:
    """Generate a basic fallback template when pattern analysis fails."""
    
    template_content = f'''# -*- coding: utf-8 -*-

# Test case: {test_case_name}
{f"# Description: {test_description}" if test_description else ""}
# Auto-generated by Squish MCP Server (basic template)

import names
import squish

def main():
    """
    Main test function for {test_case_name}
    {test_description if test_description else ""}
    """
    # TODO: Implement your test logic here
    test.log("Starting test case: {test_case_name}")
    
    # Example test steps:
    # startApplication("YourApplication")
    # waitForObject(names.your_object)
    # clickButton(names.your_button)
    # test.verify(condition, "Verification message")
    
    test.log("Test case {test_case_name} completed")
'''
    
    return {
        "status": 0,
        "message": f"Generated basic template for {test_case_name}",
        "template": template_content,
        "metadata": {
            "imports_used": ["names", "squish"],
            "object_pattern": "suite_names",
            "api_patterns": [],
            "conventions_applied": []
        }
    }

def _parse_bdd_step_pattern(step_pattern: str) -> Tuple[str, List[str]]:
    """
    Parse a BDD step pattern with |any| placeholders and return the pattern and parameter names.
    
    Args:
        step_pattern: Step pattern like "The title of the application is |any|"
        
    Returns:
        Tuple of (pattern_for_decorator, list_of_parameter_names)
    """
    # Find all |any| placeholders
    any_placeholders = re.findall(r'\|any\|', step_pattern)
    
    # Generate parameter names based on context or position
    parameter_names = []
    # Keep the original pattern with |any| for the decorator
    pattern_for_decorator = step_pattern
    
    # Generate parameter names based on context
    words = step_pattern.lower().split()
    for i, placeholder in enumerate(any_placeholders):
        # Try to infer parameter name from surrounding context
        param_name = f"value_{i+1}"
        
        # Look for context clues in the step text
        if 'title' in words:
            param_name = 'title_name'
        elif 'name' in words:
            param_name = 'name'
        elif 'value' in words:
            param_name = 'value'
        elif 'text' in words:
            param_name = 'text'
        elif 'number' in words or 'count' in words:
            param_name = 'number'
        elif 'status' in words or 'state' in words:
            param_name = 'status'
        else:
            # Use position-based naming if no context clues
            if i == 0:
                param_name = 'first_value'
            elif i == 1:
                param_name = 'second_value'
            else:
                param_name = f'value_{i+1}'
                
        parameter_names.append(param_name)
    
    return pattern_for_decorator, parameter_names

def _generate_bdd_step_function(step_type: str, step_pattern: str) -> str:
    """
    Generate a BDD step function with proper parameter handling for |any| placeholders.
    
    Args:
        step_type: Type of step (given, when, then)
        step_pattern: Step pattern with |any| placeholders
        
    Returns:
        Generated step function code
    """
    pattern_for_decorator, parameter_names = _parse_bdd_step_pattern(step_pattern)
    
    # Create function signature
    params = ['context'] + parameter_names
    function_signature = f"def step({', '.join(params)}):"
    
    # Generate example implementation based on step pattern
    step_lower = step_pattern.lower()
    if 'title' in step_lower and 'application' in step_lower:
        # Example for title verification
        if parameter_names:
            implementation = f'''    test.compare(str(waitForObjectExists(names.o_QQuickWindowQmlImpl).title), {parameter_names[0]})'''
        else:
            implementation = '''    test.compare(str(waitForObjectExists(names.o_QQuickWindowQmlImpl).title), "Expected Title")'''
    elif 'click' in step_lower or 'press' in step_lower:
        # Example for clicking
        implementation = '''    clickButton(waitForObject(names.button_name))'''
    elif 'type' in step_lower or 'enter' in step_lower:
        # Example for text input
        if parameter_names:
            implementation = f'''    type(waitForObject(names.input_field), {parameter_names[0]})'''
        else:
            implementation = '''    type(waitForObject(names.input_field), "sample text")'''
    elif 'verify' in step_lower or 'see' in step_lower or 'should' in step_lower:
        # Example for verification
        if parameter_names:
            implementation = f'''    test.verify(waitForObjectExists(names.expected_object_{parameter_names[0]}))'''
        else:
            implementation = '''    test.verify(waitForObjectExists(names.expected_object))'''
    else:
        # Generic implementation
        implementation = '''    # TODO: Implement this step
    pass'''
    
    return f'''@{step_type}("{pattern_for_decorator}")
{function_signature}
{implementation}
'''

def generate_bdd_template(test_case_name: str, test_description: str = "") -> Dict:
    """
    Generate a BDD test template based on QtCare Squish BDD structure.
    Supports |any| variable input syntax for parameterized steps.
    
    Args:
        test_case_name: Name of the test case
        test_description: Optional description of what the test should do
        
    Returns:
        Dict with generated BDD template and feature file content
    """
    # Generate test.py content
    test_py_content = f'''source(findFile('scripts', 'python/bdd.py'))

setupHooks('../shared/scripts/bdd_hooks.py')
collectStepDefinitions('./steps', '../shared/steps')

def main():
    testSettings.throwOnFailure = True
    runFeatureFile('test.feature')
'''

    # Generate example step definitions with |any| support
    example_steps = [
        ("given", "The title of the application is |any|"),
        ("when", "I click the |any| button"),
        ("then", "I should see |any| in the result")
    ]
    
    step_definitions_content = '''# Example step definitions with variable input support
# Use |any| in step patterns to capture variable inputs

'''
    
    for step_type, pattern in example_steps:
        step_definitions_content += _generate_bdd_step_function(step_type, pattern) + '\n\n'

    # Generate test.feature content with examples using |any| syntax
    feature_content = f'''# BDD Feature file for {test_case_name}
{f"# {test_description}" if test_description else ""}
Feature: {test_description if test_description else "Brief description of the feature under test"}

    Background:
        Given The application launches successfully

    @test
    Scenario: {test_description if test_description else "Example scenario with variable inputs"}
        Given The title of the application is "My Application"
        When I click the "Submit" button
        Then I should see "Success" in the result
        
    @test
    Scenario: Another example with different values
        Given The title of the application is "Test App"
        When I click the "Cancel" button
        Then I should see "Cancelled" in the result
'''

    return {
        "status": 0,
        "message": f"Generated BDD template for {test_case_name} with |any| variable input support",
        "test_py_template": test_py_content,
        "feature_template": feature_content,
        "step_definitions_template": step_definitions_content,
        "metadata": {
            "test_type": "bdd",
            "requires_bdd_structure": True,
            "files_created": ["test.py", "test.feature", "steps/steps.py"],
            "dependencies": [
                "scripts/python/bdd.py",
                "../shared/scripts/bdd_hooks.py", 
                "../shared/steps"
            ],
            "features": [
                "Variable input support with |any| syntax",
                "Automatic parameter name inference",
                "Context-aware step function generation"
            ]
        }
    }

def suggest_code_improvements(test_content: str) -> Dict:
    """
    Analyze test content and suggest improvements based on project patterns.
    
    Args:
        test_content: The test code to analyze
        
    Returns:
        Dict with suggestions for improvement
    """
    suggestions = []
    
    # Get project patterns
    pattern_analysis = analyze_existing_patterns()
    if pattern_analysis["status"] != 0:
        return {
            "status": 1,
            "message": "Could not analyze patterns for suggestions",
            "suggestions": []
        }
    
    analysis = pattern_analysis["analysis"]
    
    # Check imports
    current_imports = re.findall(r'^(?:import|from)\s+([^\s]+)', test_content, re.MULTILINE)
    common_imports = analysis.get("common_imports", [])
    
    missing_imports = []
    for imp in common_imports[:3]:  # Top 3 common imports
        if imp not in current_imports and imp not in ["sys", "os", "time"]:
            missing_imports.append(imp)
    
    if missing_imports:
        suggestions.append({
            "type": "import",
            "severity": "info",
            "message": f"Consider adding common project imports: {', '.join(missing_imports)}",
            "suggestion": f"Add: {', '.join(f'import {imp}' for imp in missing_imports)}"
        })
    
    # Check object reference patterns
    object_pattern = analysis.get("object_patterns", {})
    if object_pattern.get("primary_location") == "global_scripts":
        if "import names" in test_content and "names." in test_content:
            suggestions.append({
                "type": "object_reference",
                "severity": "warning",
                "message": "Project uses global script objects, but test imports 'names'",
                "suggestion": "Consider using global script object references instead of names.py"
            })
    
    # Check for common API patterns
    api_usage = analysis.get("api_usage", {})
    if api_usage:
        # Look for missing common APIs
        has_verification = bool(re.search(r'\btest\.verify\b', test_content))
        has_logging = bool(re.search(r'\btest\.log\b', test_content))
        
        if "verify" in str(api_usage.keys()) and not has_verification:
            suggestions.append({
                "type": "api_usage",
                "severity": "info",
                "message": "Most tests in this project use verification",
                "suggestion": "Consider adding test.verify() calls to validate results"
            })
        
        if not has_logging:
            suggestions.append({
                "type": "api_usage",
                "severity": "info",
                "message": "Consider adding logging for better test traceability",
                "suggestion": "Add test.log() statements at key points"
            })
    
    # Check for project conventions
    conventions = analysis.get("coding_conventions", {})
    if "screenshot_verification" in conventions:
        if "screenshot" in test_content.lower() or "verify_image" in test_content.lower():
            # Test mentions screenshots but might not follow convention
            if "verify_image" not in test_content:
                suggestions.append({
                    "type": "convention",
                    "severity": "warning",
                    "message": "Project has specific screenshot verification patterns",
                    "suggestion": conventions["screenshot_verification"]
                })
    
    if "setup_function" in conventions:
        if "def main(" in test_content and "setup" not in test_content.lower():
            suggestions.append({
                "type": "convention",
                "severity": "info",
                "message": "Project uses setup functions in tests",
                "suggestion": conventions["setup_function"]
            })
    
    return {
        "status": 0,
        "message": f"Generated {len(suggestions)} suggestions",
        "suggestions": suggestions
    }

def extract_object_references(test_content: str) -> Dict:
    """
    Extract object references from test content to understand what objects are being used.
    
    Args:
        test_content: The test code to analyze
        
    Returns:
        Dict with extracted object references and their types
    """
    references = {
        "names_objects": [],
        "direct_objects": [],
        "global_script_objects": [],
        "unknown_objects": []
    }
    
    # Find names.* references
    names_refs = re.findall(r'names\.([A-Za-z_][A-Za-z0-9_]*)', test_content)
    references["names_objects"] = list(set(names_refs))
    
    # Find direct object references (in function calls)
    function_patterns = [
        r'waitForObject\s*\(\s*([^)]+)\s*\)',
        r'clickButton\s*\(\s*([^)]+)\s*\)',
        r'findObject\s*\(\s*([^)]+)\s*\)',
        r'mouseClick\s*\(\s*([^)]+)\s*\)',
        r'type\s*\(\s*([^)]+)\s*,'
    ]
    
    for pattern in function_patterns:
        matches = re.findall(pattern, test_content)
        for match in matches:
            obj_ref = match.strip().strip('"\'')
            if not obj_ref.startswith('names.') and obj_ref not in references["direct_objects"]:
                if '.' in obj_ref and not obj_ref.startswith(('names.', 'self.')):
                    references["global_script_objects"].append(obj_ref)
                elif obj_ref.isidentifier():
                    references["unknown_objects"].append(obj_ref)
    
    # Count total references
    total_refs = sum(len(refs) for refs in references.values())
    
    return {
        "status": 0,
        "message": f"Extracted {total_refs} object references",
        "references": references,
        "summary": {
            "total_references": total_refs,
            "primary_pattern": "names" if references["names_objects"] else 
                             "global_scripts" if references["global_script_objects"] else 
                             "direct" if references["direct_objects"] else "unknown"
        }
    }

# =============================================================================
# SUITE CONFIGURATION MANAGEMENT
# =============================================================================

def read_suite_conf(suite_path: str) -> Dict:
    """
    Read and parse a suite.conf file from a Squish test suite directory.
    
    Args:
        suite_path: Path to the test suite directory
        
    Returns:
        Dict with suite configuration data
    """
    suite_conf_path = os.path.join(suite_path, "suite.conf")
    
    if not os.path.exists(suite_conf_path):
        return {
            "status": 1,
            "message": f"suite.conf not found at: {suite_conf_path}. Suite must already exist.",
            "config": {},
            "path": suite_conf_path,
            "exists": False
        }
    
    try:
        # Read the file content
        with open(suite_conf_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse key=value format
        suite_config = {}
        lines = content.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if '=' in line and not line.startswith('#'):
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                suite_config[key] = value
        
        # Parse TEST_CASES line specially - it's space-separated
        test_cases = []
        if 'TEST_CASES' in suite_config:
            test_cases = suite_config['TEST_CASES'].split()
        
        return {
            "status": 0,
            "message": f"Successfully read suite.conf with {len(test_cases)} test cases",
            "config": suite_config,
            "test_cases": test_cases,
            "path": suite_conf_path,
            "exists": True,
            "content": content
        }
        
    except Exception as e:
        return {
            "status": 1,
            "message": f"Error reading suite.conf: {str(e)}",
            "config": {},
            "path": suite_conf_path,
            "exists": True
        }

def update_suite_conf(suite_path: str, test_case_name: str) -> Dict:
    """
    Update suite.conf file to add a new test case to the TEST_CASES line.
    Assumes suite.conf already exists - does not create new suites.
    
    Args:
        suite_path: Path to the test suite directory
        test_case_name: Name of the test case to add (e.g., "tst_new_test")
        
    Returns:
        Dict with operation status and details
    """
    # Read existing configuration
    conf_data = read_suite_conf(suite_path)
    suite_conf_path = conf_data["path"]
    
    if not conf_data["exists"]:
        return {
            "status": 1,
            "message": f"suite.conf must already exist. Cannot create new test suites.",
            "added": False,
            "path": suite_conf_path
        }
    
    try:
        # Get current test cases
        current_cases = conf_data.get("test_cases", [])
        
        # Check if test case already exists
        if test_case_name in current_cases:
            return {
                "status": 0,
                "message": f"Test case '{test_case_name}' already exists in suite.conf",
                "added": False,
                "path": suite_conf_path
            }
        
        # Add new test case
        current_cases.append(test_case_name)
        
        # Update the config
        updated_config = conf_data["config"].copy()
        updated_config["TEST_CASES"] = " ".join(current_cases)
        
        # Reconstruct the suite.conf content preserving the original format
        content_lines = []
        
        # Read original file to preserve order and comments
        original_lines = conf_data["content"].strip().split('\n')
        
        for line in original_lines:
            line = line.strip()
            if line.startswith('TEST_CASES='):
                # Replace the TEST_CASES line
                content_lines.append(f"TEST_CASES={' '.join(current_cases)}")
            else:
                # Keep other lines as-is
                content_lines.append(line)
        
        new_content = "\n".join(content_lines) + "\n"
        
        # Write the updated suite.conf
        with open(suite_conf_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        return {
            "status": 0,
            "message": f"Successfully updated suite.conf with test case '{test_case_name}'",
            "added": True,
            "path": suite_conf_path,
            "content": new_content
        }
        
    except Exception as e:
        return {
            "status": 1,
            "message": f"Error updating suite.conf: {str(e)}",
            "added": False,
            "path": suite_conf_path
        }

def create_test_case(suite_path: str, test_case_name: str, test_content: str = "", update_suite_conf_flag: bool = True, is_bdd: bool = False, test_description: str = "") -> Dict:
    """
    Create a new Squish test case and optionally update the suite.conf file.
    
    Args:
        suite_path: Absolute path to the test suite directory (must start with 'suite_')
        test_case_name: Name of the test case (will be prefixed with 'tst_' if not already)
        test_content: Python code content for the test.py file (optional)
        update_suite_conf_flag: Whether to update suite.conf with the new test case (default: True)
        is_bdd: Whether to create a BDD test with proper structure (default: False)
        test_description: Description for BDD feature (optional)
    
    Returns:
        Dict with creation status, paths, and any issues encountered
    """
    
    # Validate suite path
    if not os.path.exists(suite_path):
        return {
            "status": 1,
            "message": f"Suite path does not exist: {suite_path}",
            "test_case_path": "",
            "suite_conf_updated": False
        }
    
    if not os.path.basename(suite_path).startswith('suite_'):
        return {
            "status": 1,
            "message": f"Suite directory name must start with 'suite_': {os.path.basename(suite_path)}",
            "test_case_path": "",
            "suite_conf_updated": False
        }
    
    # Ensure test case name starts with 'tst_'
    if not test_case_name.startswith('tst_'):
        test_case_name = f"tst_{test_case_name}"
    
    # Create test case directory
    test_case_path = os.path.join(suite_path, test_case_name)
    
    try:
        # Create the test case directory
        os.makedirs(test_case_path, exist_ok=True)
        
        # Create test.py file
        test_py_path = os.path.join(test_case_path, "test.py")
        
        files_created = ["test.py"]
        
        # Determine what content to use
        if is_bdd:
            # Create BDD test structure
            bdd_template = generate_bdd_template(test_case_name, test_description)
            test_content = bdd_template["test_py_template"]
            
            # Also create the test.feature file
            feature_path = os.path.join(test_case_path, "test.feature")
            with open(feature_path, 'w', encoding='utf-8') as f:
                f.write(bdd_template["feature_template"])
            files_created.append("test.feature")
            
        elif not test_content.strip():
            # Create a basic test template
            test_content = f'''# -*- coding: utf-8 -*-

# Test case: {test_case_name}
# Auto-generated by Squish MCP Server

import names
import squish

def main():
    """
    Main test function for {test_case_name}
    """
    # TODO: Implement your test logic here
    test.log("Starting test case: {test_case_name}")
    
    # Example test steps:
    # startApplication("YourApplication")
    # waitForObject(names.your_object)
    # clickButton(names.your_button)
    # test.verify(condition, "Verification message")
    
    test.log("Test case {test_case_name} completed")
'''
        
        # Write the test.py file
        with open(test_py_path, 'w', encoding='utf-8') as f:
            f.write(test_content)
        
        result = {
            "status": 0,
            "message": f"Successfully created {'BDD ' if is_bdd else ''}test case '{test_case_name}'",
            "test_case_path": test_case_path,
            "test_py_path": test_py_path,
            "files_created": files_created,
            "is_bdd": is_bdd,
            "suite_conf_updated": False
        }
        
        if is_bdd:
            result["feature_path"] = os.path.join(test_case_path, "test.feature")
            result["message"] += f" with feature file"
        
        # Update suite.conf if requested
        if update_suite_conf_flag:
            conf_result = update_suite_conf(suite_path, test_case_name)
            result["suite_conf_updated"] = conf_result["added"]
            result["suite_conf_path"] = conf_result["path"]
            
            if conf_result["status"] != 0:
                result["message"] += f". Warning: {conf_result['message']}"
            else:
                result["message"] += f". Updated suite.conf: {conf_result['message']}"
        
        return result
        
    except Exception as e:
        return {
            "status": 1,
            "message": f"Error creating test case: {str(e)}",
            "test_case_path": test_case_path,
            "suite_conf_updated": False
        }