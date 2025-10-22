#!/usr/bin/env python3
"""
SquishRunner MCP Server - Main Orchestration Module

This is the main MCP server that orchestrates all Squish functionality.
It imports and exposes tools from the specialized modules:
- squish_test_execution: Test running and suite management
- squish_context_init: Context analysis and caching
- squish_code_analysis: Code analysis and generation
- squishserver_cli: Squish server lifecycle management

IMPORTANT: This file requires Python 3.10+ due to f-string usage and type hints.
Do not use with Python 2.x - it will cause syntax errors.
"""

# from mcp.server.fastmcp import FastMCP
from fastmcp import FastMCP
import os
from typing import Dict, List, Optional

# Import execution modules
from execution.squish_test_execution import (
    run_test
)

# Import CLI modules for global script directory management
from cli.squishrunner_cli import (
    get_global_script_dirs,
    set_global_script_dirs
)

from context import (
    initialize_squish_environment_and_contexts,
    get_global_script_context,
    get_test_format_context,
    get_object_reference_context,
    get_squish_api_context,
    get_squish_rules_context,
    get_bdd_context,
    get_bdd_documentation_context,
    ensure_bdd_documentation_context
)

from scripting import (
    analyze_existing_patterns,
    generate_test_template,
    generate_bdd_template,
    suggest_code_improvements,
    extract_object_references,
    read_suite_conf,
    update_suite_conf,
    create_test_case,
    analyze_current_object_map_structure,
    generate_page_object_references,
    create_page_object_file,
    merge_with_existing_structure,
    generate_page_objects_from_snapshot
)



# Initialize MCP server
mcp = FastMCP("SquishRunner-Server")

# =============================================================================
# TEST EXECUTION TOOLS
# =============================================================================

@mcp.tool()
def run_test_mcp(test_suite_path: str, context: Dict, test_path: str = "", suite_or_test_case: str = 'suite') -> Dict:
    """
    Run a Squish test suite or test case.
    You need to figure out the test suite and test case absolute paths on your own, the user should have to provide it.
    Pay careful attention to if a test suite is being asked for (directory prefixed with 'suite_')
        or if a test case is being asked for (directory prefixed with 'tst_')
    This is a wrapper around the squishrunner command line tool.
    
    IMPORTANT PATH HANDLING AND SQUISH TEST NAMING CONVENTIONS:
    - All paths are are absolute paths, but you should figure out what the paths are if not explicitly provided by the user!!!
    - Test suites are named like `suite_<test_suite_name>` - these are folders under the root path
    - Test cases are named like `tst_<test_name>` - these are folders under the test suite path
    - Test files are under the test case folders and are named like `test.py`

    Args:
        test_suite_path: Absolute path to the test suite which you should figure out on your own
                        Example: "/Users/yourname/projects/addressbook/suite_py"
        context: Dictionary variables of options to pass to Squish
                Format: {"VAR_NAME": "value"}
        test_path: Absolute path to the test case from test_suite_path. If provided also the test suite path needs to be provided.
                  Example: "/Users/yourname/projects/addressbook/suite_py/tst_general"
        suite_or_test_case: 'suite' or 'case' are the only valid options
                If the user requests for a test case or only a single test beginning in "tst_" then use 'case'
                If the user requests for a test suite or a reference directory beginning with "suite_" than use 'suite'
    
    Returns:
        Dict with the following structure:
        {
            "status": int,  # 0 for success, 1 for error
            "message": str   # Contains stdout for success, error message for failure
        }
    """
    return run_test(test_suite_path, context, test_path, suite_or_test_case)

@mcp.tool()
def get_global_script_dirs_mcp() -> Dict:
    """
    Get the global script directories configured in the active Squish test suite.
    This uses the squishrunner --config getGlobalScriptDirs command.
    
    Returns:
        Dict with the following structure:
        {
            "status": int,  # 0 for success, 1 for error
            "message": str,   # Contains stdout for success, error message for failure
            "directories": List[str]  # List of global script directory paths
        }
    """
    return get_global_script_dirs()

@mcp.tool()
def set_global_script_dirs_mcp(directories: List[str]) -> Dict:
    """
    Set the global script directories for Squish test execution.
    
    Args:
        directories: List of directory paths to set as global script directories
    
    Returns:
        Dict with operation status
    """
    return set_global_script_dirs(directories)


@mcp.tool()
def create_test_case_mcp(suite_path: str, test_case_name: str, test_content: str = "", update_suite_conf: bool = True, is_bdd: bool = False, test_description: str = "") -> Dict:
    """
    Create a new Squish test case and optionally update the suite.conf file.
    
    Args:
        suite_path: Absolute path to the test suite directory (must start with 'suite_')
        test_case_name: Name of the test case (will be prefixed with 'tst_' if not already)
        test_content: Python code content for the test.py file (optional)
        update_suite_conf: Whether to update suite.conf with the new test case (default: True)
        is_bdd: Whether to create a BDD test with proper QtCare Squish BDD structure (default: False)
        test_description: Description for BDD feature file (optional, recommended for BDD tests)
    
    Returns:
        Dict with creation status, paths, and any issues encountered.
        For BDD tests, creates both test.py and test.feature files with proper structure:
        - test.py: Contains source(findFile()), setupHooks(), collectStepDefinitions(), main() with testSettings.throwOnFailure = True, runFeatureFile()
        - test.feature: Contains Gherkin feature file with Background and Scenario sections
    """
    # Ensure BDD documentation context is available when creating BDD tests
    if is_bdd:
        ensure_bdd_documentation_context()
    
    return create_test_case(suite_path, test_case_name, test_content, update_suite_conf, is_bdd, test_description)

@mcp.tool()
def get_suite_configuration(suite_path: str) -> Dict:
    """
    Read and return the configuration from a suite.conf file.
    
    Args:
        suite_path: Absolute path to the test suite directory
    
    Returns:
        Dict with suite configuration data including test cases, version, language, etc.
    """
    if not os.path.exists(suite_path):
        return {
            "status": 1,
            "message": f"Suite path does not exist: {suite_path}",
            "config": {}
        }
    
    return read_suite_conf(suite_path)

@mcp.tool()
def update_suite_configuration(suite_path: str, test_case_name: str) -> Dict:
    """
    Update the suite.conf file to include a new test case.
    
    Args:
        suite_path: Absolute path to the test suite directory
        test_case_name: Name of the test case to add (will be prefixed with 'tst_' if not already)
    
    Returns:
        Dict with update status and details
    """
    if not os.path.exists(suite_path):
        return {
            "status": 1,
            "message": f"Suite path does not exist: {suite_path}",
            "added": False
        }
    
    # Ensure test case name starts with 'tst_'
    if not test_case_name.startswith('tst_'):
        test_case_name = f"tst_{test_case_name}"
    
    return update_suite_conf(suite_path, test_case_name)

# =============================================================================
# CONTEXT ACCESS TOOLS
# =============================================================================

@mcp.tool()
def get_test_format_context_mcp() -> Dict:
    """
    Get test format analysis and patterns from existing Squish test suites.
    
    This analyzes existing test script formats, patterns, and whether they use 
    native Squish API vs helper functions from global scripts.
    
    Returns:
        Dict with test format analysis including common imports, test patterns,
        and code structure conventions used in the project.
    """
    return get_test_format_context()

@mcp.tool()
def get_object_reference_context_mcp() -> Dict:
    """
    Get object reference locations and usage patterns.
    
    This analyzes where and how object references are stored in the test suite,
    including names.py files, global script object files, and usage patterns.
    
    Returns:
        Dict with object reference analysis including storage locations,
        naming conventions, and access patterns.
    """
    return get_object_reference_context()

@mcp.tool()
def get_global_script_context_mcp() -> Dict:
    """
    Get global script utilities and functions analysis.
    
    This analyzes all files in global script directories to understand available
    functions, classes, and utilities that can be used in Squish tests.
    
    Returns:
        Dict with global script analysis including available utilities,
        functions, and helper classes.
    """
    return get_global_script_context()

@mcp.tool()
def get_squish_api_context_mcp() -> Dict:
    """
    Get Squish API documentation and function reference.
    
    This provides access to cached Squish API documentation including
    available functions, examples, and usage patterns.
    
    Returns:
        Dict with Squish API documentation and function references.
    """
    return get_squish_api_context()

@mcp.tool()
def get_squish_rules_context_mcp() -> Dict:
    """
    Get project-specific rules and patterns from SQUISH-RULES.yaml.
    
    This provides project-specific conventions, patterns, and rules
    that should be followed when generating or modifying test code.
    
    Returns:
        Dict with project-specific rules and patterns.
    """
    return get_squish_rules_context()

@mcp.tool()
def get_bdd_context_mcp() -> Dict:
    """
    Get BDD test structure and step definitions.
    
    This analyzes BDD test structure including feature files, step definitions,
    and relationships between features and step implementations.
    
    Returns:
        Dict with BDD structure analysis and step definition mappings.
    """
    return get_bdd_context()

@mcp.tool()
def get_bdd_documentation_context_mcp() -> Dict:
    """
    Get official Squish BDD documentation and implementation details.
    
    This provides comprehensive Squish BDD documentation including
    step definition patterns, implementation examples, and best practices.
    
    Returns:
        Dict with Squish BDD documentation and implementation guidance.
    """
    return get_bdd_documentation_context()

@mcp.tool()
def get_squish_contexts_summary() -> Dict:
    """
    Get a summary of all available Squish contexts without the full data.
    
    This provides an overview of what context data is available and loaded,
    along with key statistics, without transferring the full context payloads.
    Use the individual context tools to get specific detailed information.
    
    Returns:
        Dict with context availability summary and key statistics.
    """
    # Get all context data for summary generation only
    test_format_context = get_test_format_context()
    object_reference_context = get_object_reference_context()
    global_script_context = get_global_script_context()
    squish_api_context = get_squish_api_context()
    squish_rules_context = get_squish_rules_context()
    bdd_context = get_bdd_context()
    bdd_documentation_context = get_bdd_documentation_context()
    
    # Generate context availability and statistics
    context_status = {
        "test_format": {
            "status": test_format_context.get("status", 1),
            "available": test_format_context.get("status") == 0
        },
        "object_reference": {
            "status": object_reference_context.get("status", 1),
            "available": object_reference_context.get("status") == 0
        },
        "global_script": {
            "status": global_script_context.get("status", 1),
            "available": global_script_context.get("status") == 0
        },
        "squish_api": {
            "status": squish_api_context.get("status", 1),
            "available": squish_api_context.get("status") == 0
        },
        "squish_rules": {
            "status": squish_rules_context.get("status", 1),
            "available": squish_rules_context.get("status") == 0
        },
        "bdd": {
            "status": bdd_context.get("status", 1),
            "available": bdd_context.get("status") == 0
        },
        "bdd_documentation": {
            "status": bdd_documentation_context.get("status", 1),
            "available": bdd_documentation_context.get("status") == 0
        }
    }
    
    # Generate summary statistics
    summary_parts = []
    
    if test_format_context.get("status") == 0:
        analysis = test_format_context["analysis"]
        test_suites = len(analysis.get("test_suites", []))
        total_cases = sum(len(suite.get("test_cases", [])) for suite in analysis.get("test_suites", []))
        summary_parts.append(f"Found {test_suites} test suites with {total_cases} test cases")
        context_status["test_format"]["statistics"] = {
            "test_suites": test_suites,
            "total_test_cases": total_cases
        }
    
    if object_reference_context.get("status") == 0:
        locations = object_reference_context["analysis"]["locations"]
        obj_files = len(locations.get("global_object_files", []) + locations.get("suite_names_files", []))
        summary_parts.append(f"Analyzed {obj_files} object reference files")
        context_status["object_reference"]["statistics"] = {
            "object_files": obj_files,
            "global_files": len(locations.get("global_object_files", [])),
            "suite_names_files": len(locations.get("suite_names_files", []))
        }
    
    if global_script_context.get("status") == 0:
        analysis = global_script_context["analysis"]
        script_files = len(analysis.get("files", []))
        summary_parts.append(f"Found {script_files} global script utilities")
        context_status["global_script"]["statistics"] = {
            "script_files": script_files,
            "directories": len(analysis.get("directories", []))
        }
    
    if squish_api_context.get("status") == 0:
        api_info = squish_api_context.get("api_info", {})
        functions = len(api_info.get("functions", []))
        summary_parts.append(f"Loaded {functions} API function references")
        context_status["squish_api"]["statistics"] = {
            "api_functions": functions
        }
    
    if squish_rules_context.get("status") == 0:
        patterns = squish_rules_context["rules"].get("memories", {}).get("requested_patterns", [])
        summary_parts.append(f"Loaded {len(patterns)} project-specific patterns")
        context_status["squish_rules"]["statistics"] = {
            "patterns": len(patterns)
        }
    
    if bdd_context.get("status") == 0:
        bdd_summary = bdd_context.get("bdd_summary", {})
        if bdd_summary.get("has_bdd_tests"):
            feature_files = len(bdd_summary.get("feature_files", []))
            summary_parts.append(f"Detected BDD structure with {feature_files} feature files")
            context_status["bdd"]["statistics"] = {
                "has_bdd_tests": True,
                "feature_files": feature_files,
                "bdd_suites": len(bdd_summary.get("bdd_suites", []))
            }
        else:
            summary_parts.append("No BDD test structure found")
            context_status["bdd"]["statistics"] = {"has_bdd_tests": False}
    
    if bdd_documentation_context.get("status") == 0:
        bdd_doc_info = bdd_documentation_context.get("bdd_documentation", {})
        step_patterns = len(bdd_doc_info.get("step_definition_patterns", []))
        examples = len(bdd_doc_info.get("implementation_examples", []))
        summary_parts.append(f"Squish BDD documentation loaded with {step_patterns} step patterns and {examples} examples")
        context_status["bdd_documentation"]["statistics"] = {
            "step_patterns": step_patterns,
            "examples": examples
        }
    else:
        summary_parts.append("Squish BDD documentation not available")
    
    summary = "Squish Context Summary:\n" + "\n".join(f"- {part}" for part in summary_parts)
    
    return {
        "summary": summary,
        "context_status": context_status,
        "available_tools": [
            "get_test_format_context_mcp",
            "get_object_reference_context_mcp", 
            "get_global_script_context_mcp",
            "get_squish_api_context_mcp",
            "get_squish_rules_context_mcp",
            "get_bdd_context_mcp",
            "get_bdd_documentation_context_mcp"
        ],
        "usage_note": "Use individual context tools to get detailed information for specific areas."
    }

@mcp.tool()
def get_squish_contexts() -> Dict:
    """
    Get comprehensive Squish test context summary.
    
    **DEPRECATED**: This function now returns a summary only to reduce response size.
    For detailed context data, use the individual context tools:
    
    - get_test_format_context_mcp() - Test patterns and API usage
    - get_object_reference_context_mcp() - Object locations and patterns  
    - get_global_script_context_mcp() - Global script utilities and functions
    - get_squish_api_context_mcp() - Squish API documentation and examples
    - get_squish_rules_context_mcp() - Project-specific rules and patterns
    - get_bdd_context_mcp() - BDD test structure and step definitions
    - get_bdd_documentation_context_mcp() - Official Squish BDD documentation
    
    IMPORTANT FOR LLM AGENTS - OBJECT REFERENCE BEST PRACTICES:
    
    Object references in Squish tests can be stored in multiple locations (prioritized):
    1. **Global script object files** - Located in global script directories
       - Shared across multiple test suites (PREFERRED)
       - May be named objects.py, locators.py, or similar
       - Imported with specific module names
    
    2. **Other suite resource files** - Other .py files in suite directories
       - Custom object definitions or helper functions
       - Suite-specific utilities
    
    3. **names.py files** - Located in individual test suite directories (suite_*)
       - Contains suite-specific object definitions
       - Imported as 'import names' in test.py files
       - Objects accessed as names.object_name
    
    CRITICAL RULES FOR TEST DEVELOPMENT:
    - Follow existing object reference patterns discovered in the analysis
    - PRIORITIZE using global script objects over names.py when possible
    - Project-specific rules from SQUISH-RULES.yaml take precedence over general patterns
    - Always check all context sections before creating test cases
    - Consistency is key for maintainable test suites
    
    Returns:
        Dict with summary information and available context tools.
        Use individual context tools for detailed data.
    """
    # Delegate to the summary function to maintain backwards compatibility
    # while reducing response size
    summary_result = get_squish_contexts_summary()
    
    # Add the best practices documentation to the summary result
    summary_result["best_practices"] = {
        "object_reference_priority": [
            "Global script object files (PREFERRED)",
            "Other suite resource files", 
            "names.py files in test suite directories"
        ],
        "critical_rules": [
            "Follow existing object reference patterns discovered in the analysis",
            "PRIORITIZE using global script objects over names.py when possible",
            "Project-specific rules from SQUISH-RULES.yaml take precedence over general patterns",
            "Always check all context sections before creating test cases",
            "Consistency is key for maintainable test suites"
        ]
    }
    
    return summary_result

# Maintain backwards compatibility with original tool name
@mcp.tool()
def analyze_global_scripts() -> Dict:
    """
    Analyze all files in the global script directories to understand available
    functions, classes, and utilities that can be used in Squish tests.
    
    NOTE: This function now returns only the global script portion from the comprehensive context.
    For complete context including all analysis, use get_squish_contexts() instead.
    
    Returns:
        Dict with the following structure:
        {
            "status": int,  # 0 for success, 1 for error
            "message": str,
            "analysis": {
                "directories": List[str],  # List of analyzed directories
                "files": List[Dict],  # List of file information with content
                "summary": str  # Summary of available utilities
            }
        }
    """
    # Return only the global script context from the comprehensive context
    return get_global_script_context()

@mcp.tool()
def get_bdd_test_context() -> Dict:
    """
    Get comprehensive BDD (Behavior-Driven Development) test context including:
    - Feature file locations and content
    - Step definition mappings in shared/steps/ directories
    - Relationships between feature files and step implementations
    - BDD-enabled test suites and their structure
    
    This function analyzes the Squish test environment to understand:
    1. Which test cases use BDD with .feature files
    2. Where step definitions are implemented (shared/steps/steps.py)
    3. How feature file steps map to step definition functions
    4. Dependencies between BDD tests and global scripts or test suite resources
    
    Returns:
        Dict with the following structure:
        {
            "status": int,  # 0 for success, 1 for error
            "message": str,
            "bdd_summary": {
                "has_bdd_tests": bool,
                "bdd_suites": List[Dict],  # BDD-enabled test suites
                "feature_files": List[Dict],  # All feature files found
                "step_definitions": List[Tuple],  # Step definitions from steps.py files
                "step_files": List[Dict],  # Step implementation files
                "relationships": List[Dict]  # Feature-to-step mappings
            }
        }
    """
    return get_bdd_context()

# =============================================================================
# CODE ANALYSIS AND GENERATION TOOLS
# =============================================================================

@mcp.tool()
def analyze_existing_patterns_mcp() -> Dict:
    """
    Analyze existing test patterns to understand how to generate consistent new tests.
    
    Returns:
        Dict with pattern analysis including common imports, object usage, and code structure.
    """
    return analyze_existing_patterns()

@mcp.tool()
def generate_test_template_mcp(test_case_name: str, suite_path: str, test_description: str = "") -> Dict:
    """
    Generate a test template based on existing patterns and project conventions.
    
    Args:
        test_case_name: Name of the test case
        suite_path: Path to the test suite
        test_description: Optional description of what the test should do
        
    Returns:
        Dict with generated template and metadata
    """
    return generate_test_template(test_case_name, suite_path, test_description)

@mcp.tool()
def generate_bdd_template_mcp(test_case_name: str, test_description: str = "") -> Dict:
    """
    Generate a BDD test template with proper QtCare Squish BDD structure.
    
    This creates the proper BDD test structure as used in QtCare:
    - test.py with source(findFile('scripts', 'python/bdd.py')), setupHooks(), collectStepDefinitions(), and runFeatureFile()
    - test.feature with Gherkin format including Background and Scenario sections
    
    Args:
        test_case_name: Name of the test case
        test_description: Description for the BDD feature (recommended)
        
    Returns:
        Dict with generated BDD templates for both test.py and test.feature files
    """
    # Ensure BDD documentation context is available when generating BDD templates
    ensure_bdd_documentation_context()
    
    return generate_bdd_template(test_case_name, test_description)

@mcp.tool()
def suggest_code_improvements_mcp(test_content: str) -> Dict:
    """
    Analyze test content and suggest improvements based on project patterns.
    
    Args:
        test_content: The test code to analyze
        
    Returns:
        Dict with suggestions for improvement
    """
    return suggest_code_improvements(test_content)

@mcp.tool()
def extract_object_references_mcp(test_content: str) -> Dict:
    """
    Extract object references from test content to understand what objects are being used.
    
    Args:
        test_content: The test code to analyze
        
    Returns:
        Dict with extracted object references and their types
    """
    return extract_object_references(test_content)


# =============================================================================
# POM GENERATION TOOLS
# =============================================================================

@mcp.tool()
def generate_page_objects_from_snapshot_mcp(xml_file_path: str, page_name: str) -> Dict:
    """
    Generate page object references from an XML object snapshot file.
    
    This tool:
    1. Calls parse_object_snapshot.py to filter XML elements and generate basic definitions
    2. Analyzes cached object reference patterns to understand existing style and locations
    3. Determines output format (simple dicts vs classes/functions) based on existing patterns
    4. Writes object map to appropriate location (global script dirs vs test suite resources)
    
    Args:
        xml_file_path: Absolute path to the XML object snapshot file
        page_name: Name of the page/component these objects belong to
        
    Returns:
        Dict with parsing results, pattern analysis, and generated file details
    """
    return generate_page_objects_from_snapshot(xml_file_path, page_name)


@mcp.tool()
def initialize_squish_context_mcp(test_suite_context: Optional[Dict] = None) -> Dict:
    """
    Initialize Squish environment and context caches.
    
    This tool initializes all context caches including:
    - Global script analysis
    - Test format analysis  
    - Object reference pattern analysis
    - Squish API documentation
    - Project-specific rules from SQUISH-RULES.yaml
    - BDD context and documentation
    
    Args:
        test_suite_context: Optional dict containing test suite path information for context analysis.
                          Can contain the following keys:
                          - 'base_path': Absolute path to the base directory containing test suites.
                                       This should be the parent directory that contains multiple 'suite_*' directories.
                                       Example: "/Users/yourname/projects/addressbook"
                          - 'test_suite_path': Absolute path to a specific test suite directory or test file.
                                             If provided, the base directory will be derived from this path.
                                             Example: "/Users/yourname/projects/addressbook/suite_py" or
                                                     "/Users/yourname/projects/addressbook/suite_py/tst_general/test.py"
                          
                          If neither is provided, the current working directory will be used.
                          If both are provided, 'base_path' takes precedence.


    Returns:
        Dict with initialization status and summary
    """
    try:
        cache_data = initialize_squish_environment_and_contexts(test_suite_context)
        
        # Generate summary from cache data
        summary_parts = []
        
        # Global scripts summary
        if cache_data["global_scripts_cache"] and cache_data["global_scripts_cache"].get("status") == 0:
            analysis = cache_data["global_scripts_cache"]["analysis"]
            files_count = len(analysis.get("files", []))
            dirs_count = len(analysis.get("directories", []))
            summary_parts.append(f"Global scripts: {files_count} files in {dirs_count} directories")
        
        # Object references summary
        if cache_data["object_refs_cache"] and cache_data["object_refs_cache"].get("status") == 0:
            locations = cache_data["object_refs_cache"]["analysis"]["locations"]
            global_files = len(locations.get("global_object_files", []))
            suite_files = len(locations.get("suite_names_files", []))
            summary_parts.append(f"Object references: {global_files} global files, {suite_files} suite names.py files")
        
        # Test format summary
        if cache_data["test_format_cache"] and cache_data["test_format_cache"].get("status") == 0:
            analysis = cache_data["test_format_cache"]["analysis"]
            suites = len(analysis.get("test_suites", []))
            total_cases = sum(len(suite.get("test_cases", [])) for suite in analysis.get("test_suites", []))
            summary_parts.append(f"Test analysis: {suites} suites with {total_cases} test cases")
        
        # BDD summary
        if cache_data["bdd_context_cache"] and cache_data["bdd_context_cache"].get("status") == 0:
            bdd_summary = cache_data["bdd_context_cache"]["bdd_summary"]
            if bdd_summary.get("has_bdd_tests"):
                bdd_suites = len(bdd_summary.get("bdd_suites", []))
                feature_files = len(bdd_summary.get("feature_files", []))
                summary_parts.append(f"BDD tests: {bdd_suites} BDD suites with {feature_files} feature files")
        
        # API and rules summary
        if cache_data["squish_api_cache"] and cache_data["squish_api_cache"].get("status") == 0:
            summary_parts.append("Squish API documentation loaded")
            
        if cache_data["squish_rules_cache"] and cache_data["squish_rules_cache"].get("status") == 0:
            patterns = cache_data["squish_rules_cache"]["rules"].get("memories", {}).get("requested_patterns", [])
            summary_parts.append(f"Project rules: {len(patterns)} patterns loaded")
        
        return {
            "status": 0,
            "message": "Successfully initialized all Squish context caches",
            "initialized": True,
            # "cache_data": cache_data,  # Commented out to reduce response size
            "summary": "; ".join(summary_parts) if summary_parts else "All caches initialized"
        }
    except Exception as e:
        return {
            "status": 1,
            "message": f"Failed to initialize Squish context: {str(e)}",
            "initialized": False
        }

@mcp.tool()
def analyze_object_map_structure_mcp() -> Dict:
    """
    Analyze the current object map structure to understand existing patterns.
    
    This tool examines your current object reference structure, whether stored in
    names.py files or global script locations, and provides insights into the
    organization patterns for generating consistent new object references.
    
    Returns:
        Dict containing object map structure analysis and organization patterns
    """
    try:
        # Get comprehensive Squish context
        context_data = get_squish_contexts()
        
        # Analyze the object map structure
        structure_analysis = analyze_current_object_map_structure(context_data)
        
        # Add summary information
        if structure_analysis["status"] == 0:
            object_files = structure_analysis.get("object_files", [])
            existing_objects = structure_analysis.get("existing_objects", {})
            
            structure_analysis["summary"] = {
                "total_object_files": len(object_files),
                "global_files": len([f for f in object_files if f["type"] == "global"]),
                "suite_names_files": len([f for f in object_files if f["type"] == "suite_names"]),
                "total_objects": len(existing_objects),
                "organization_strategy": structure_analysis.get("page_organization", {}).get("strategy", "unknown")
            }
        
        return structure_analysis
        
    except Exception as e:
        return {
            "status": 1,
            "error": f"Error analyzing object map structure: {str(e)}"
        }


# =============================================================================
# SERVER INITIALIZATION AND STARTUP
# =============================================================================

if __name__ == "__main__":
    # Uncomment the below line to initialize all Squish context caches before starting the server
    # initialize_squish_environment_and_contexts()
    
    # Initialize and run the server
    mcp.run(transport='stdio')