#!/usr/bin/env python3
"""
Squish Context Initialization Module

Handles the comprehensive initialization and caching of Squish test context including:
- Global script analysis and caching
- Test format analysis
- Object reference pattern analysis
- Squish API documentation fetching
- Project-specific rules loading from SQUISH-RULES.yaml

IMPORTANT: This file requires Python 3.10+ due to f-string usage and type hints.
Do not use with Python 2.x - it will cause syntax errors.
"""

import subprocess
import os
import glob
import sys
import re
import urllib.request
import urllib.error
import yaml
from typing import Dict, List, Optional

# Import shared configuration
from cli import (
    SQUISH_RUNNER,
    GLOBAL_SCRIPT_DIRS,
    SQUISH_RULES_FILE,
    validate_squish_installation
)

# Global session cache for script analysis
_global_scripts_cache: Optional[Dict] = None
_test_format_cache: Optional[Dict] = None
_object_refs_cache: Optional[Dict] = None
_squish_api_cache: Optional[Dict] = None
_squish_rules_cache: Optional[Dict] = None
_bdd_context_cache: Optional[Dict] = None
_bdd_documentation_cache: Optional[Dict] = None
_cache_initialized = False

def analyze_test_script_formats() -> Dict:
    """
    Analyze existing Squish test suites in the repository to understand test script formats,
    patterns, and whether they use native Squish API vs helper functions from global scripts.
    """
    current_dir = os.getcwd()
    test_suites = []
    analysis = {
        "test_suites": [],
        "patterns": {
            "squish_api_usage": [],
            "global_script_imports": [],
            "common_patterns": [],
            "object_usage": [],
            "bdd_usage": {
                "total_bdd_tests": 0,
                "common_steps": [],
                "step_definitions": [],
                "bdd_suites": []
            }
        },
        "summary": ""
    }
    
    # Find all suite_ directories recursively
    suite_dirs = glob.glob(f"{current_dir}/**/suite_*", recursive=True)
    
    for suite_dir in suite_dirs:
        if not os.path.isdir(suite_dir):
            continue
            
        suite_info = {
            "path": suite_dir,
            "name": os.path.basename(suite_dir),
            "test_cases": [],
            "resources": []
        }
        
        # Find test cases (tst_* directories)
        tst_dirs = glob.glob(os.path.join(suite_dir, "tst_*"))
        
        for tst_dir in tst_dirs:
            if not os.path.isdir(tst_dir):
                continue
                
            test_py_path = os.path.join(tst_dir, "test.py")
            if os.path.exists(test_py_path):
                try:
                    with open(test_py_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Check for BDD feature files and setup
                    feature_file_path = os.path.join(tst_dir, "test.feature")
                    has_feature_file = os.path.exists(feature_file_path)
                    feature_content = ""
                    bdd_steps_used = []
                    
                    if has_feature_file:
                        try:
                            with open(feature_file_path, 'r', encoding='utf-8') as f:
                                feature_content = f.read()
                            # Extract step keywords from feature file
                            bdd_steps_used = re.findall(r'^\s*(Given|When|Then|And|But)\s+(.+)', feature_content, re.MULTILINE)
                        except Exception:
                            feature_content = "Could not read feature file"
                    
                    # Analyze the test.py content
                    test_case_info = {
                        "name": os.path.basename(tst_dir),
                        "path": test_py_path,
                        "squish_api_calls": re.findall(r'\b(test|waitFor|click|type|verify|compare|findObject|startApplication)\s*\(', content),
                        "imports": re.findall(r'^(?:import|from)\s+([^\s]+)', content, re.MULTILINE),
                        "object_references": re.findall(r'names\.[A-Za-z_][A-Za-z0-9_]*', content),
                        "global_script_usage": any(imp for imp in re.findall(r'^(?:import|from)\s+([^\s]+)', content, re.MULTILINE) 
                                                 if not imp.startswith(('squish', '__', 'sys', 'os', 'time', 'datetime'))),
                        "content_preview": content[:1000] + "..." if len(content) > 1000 else content,
                        # BDD-related information
                        "is_bdd": has_feature_file,
                        "feature_file": feature_file_path if has_feature_file else None,
                        "feature_content": feature_content if has_feature_file else None,
                        "bdd_steps_used": bdd_steps_used,
                        "uses_behave": "behave" in content.lower() or "feature" in content.lower()
                    }
                    suite_info["test_cases"].append(test_case_info)
                    
                    # Collect patterns
                    analysis["patterns"]["squish_api_usage"].extend(test_case_info["squish_api_calls"])
                    analysis["patterns"]["global_script_imports"].extend([imp for imp in test_case_info["imports"] 
                                                                        if not imp.startswith(('squish', '__', 'sys', 'os', 'time', 'datetime'))])
                    analysis["patterns"]["object_usage"].extend(test_case_info["object_references"])
                    
                    # Collect BDD patterns
                    if test_case_info["is_bdd"]:
                        analysis["patterns"]["bdd_usage"]["total_bdd_tests"] += 1
                        analysis["patterns"]["bdd_usage"]["common_steps"].extend([step[1] for step in test_case_info["bdd_steps_used"]])
                    
                except Exception as e:
                    suite_info["test_cases"].append({
                        "name": os.path.basename(tst_dir),
                        "path": test_py_path,
                        "error": f"Could not analyze: {str(e)}"
                    })
        
        # Look for resource files (names.py, objects.map, etc.)
        resource_files = []
        for pattern in ["names.py", "objects.map", "*.py"]:
            resource_files.extend(glob.glob(os.path.join(suite_dir, pattern)))
        
        for resource_file in resource_files:
            if os.path.isfile(resource_file):
                suite_info["resources"].append({
                    "name": os.path.basename(resource_file),
                    "path": resource_file
                })
        
        # Check for BDD steps directory and step definitions
        steps_dir = os.path.join(suite_dir, "shared", "steps")
        bdd_info = {
            "has_bdd_structure": False,
            "steps_directory": None,
            "step_files": [],
            "step_definitions": []
        }
        
        if os.path.isdir(steps_dir):
            bdd_info["has_bdd_structure"] = True
            bdd_info["steps_directory"] = steps_dir
            
            # Find all Python files in steps directory
            step_files = glob.glob(os.path.join(steps_dir, "*.py"))
            for step_file in step_files:
                if os.path.isfile(step_file):
                    try:
                        with open(step_file, 'r', encoding='utf-8') as f:
                            step_content = f.read()
                        
                        # Extract step definitions (decorators like @given, @when, @then)
                        step_definitions = re.findall(r'@(given|when|then|step)\s*\(["\'](.+?)["\']\)', step_content, re.IGNORECASE)
                        
                        # Analyze which steps use variable inputs (|any| syntax)
                        variable_steps = []
                        for step_type, step_pattern in step_definitions:
                            if '|any|' in step_pattern:
                                any_count = step_pattern.count('|any|')
                                variable_steps.append({
                                    "type": step_type,
                                    "pattern": step_pattern,
                                    "variable_count": any_count
                                })
                        
                        step_file_info = {
                            "name": os.path.basename(step_file),
                            "path": step_file,
                            "step_definitions": step_definitions,
                            "variable_steps": variable_steps,
                            "imports": re.findall(r'^(?:import|from)\s+([^\s]+)', step_content, re.MULTILINE),
                            "global_script_usage": any(imp for imp in re.findall(r'^(?:import|from)\s+([^\s]+)', step_content, re.MULTILINE) 
                                                     if not imp.startswith(('squish', '__', 'sys', 'os', 'time', 'datetime', 'behave'))),
                            "content_preview": step_content[:500] + "..." if len(step_content) > 500 else step_content
                        }
                        
                        bdd_info["step_files"].append(step_file_info)
                        bdd_info["step_definitions"].extend(step_definitions)
                        
                    except Exception as e:
                        bdd_info["step_files"].append({
                            "name": os.path.basename(step_file),
                            "path": step_file,
                            "error": f"Could not analyze: {str(e)}"
                        })
        
        suite_info["bdd_info"] = bdd_info
        
        # Collect suite-level BDD patterns  
        if bdd_info["has_bdd_structure"]:
            analysis["patterns"]["bdd_usage"]["bdd_suites"].append(suite_info["name"])
            analysis["patterns"]["bdd_usage"]["step_definitions"].extend(bdd_info["step_definitions"])
        
        analysis["test_suites"].append(suite_info)
    
    # Generate summary
    total_test_cases = sum(len(suite["test_cases"]) for suite in analysis["test_suites"])
    unique_api_calls = list(set(analysis["patterns"]["squish_api_usage"]))
    unique_imports = list(set(analysis["patterns"]["global_script_imports"]))
    bdd_usage = analysis["patterns"]["bdd_usage"]
    unique_step_definitions = list(set([step[1] for step in bdd_usage["step_definitions"]]))
    
    analysis["summary"] = f"""Test Script Format Analysis:
- Found {len(analysis['test_suites'])} test suites
- Total test cases: {total_test_cases}
- Common Squish API usage: {', '.join(unique_api_calls[:10])}
- Global script imports: {', '.join(unique_imports[:5])}
- Uses names.py for objects: {any('names.py' in [r['name'] for r in suite.get('resources', [])] for suite in analysis['test_suites'])}
- BDD test cases: {bdd_usage['total_bdd_tests']}
- BDD-enabled suites: {len(bdd_usage['bdd_suites'])} ({', '.join(bdd_usage['bdd_suites']) if bdd_usage['bdd_suites'] else 'none'})
- Common BDD step definitions: {len(unique_step_definitions)} unique steps found
"""
    
    return {
        "status": 0,
        "message": f"Analyzed {len(analysis['test_suites'])} test suites with {total_test_cases} test cases",
        "analysis": analysis
    }

def extract_bdd_context() -> Dict:
    """
    Extract comprehensive BDD context including feature files, step definitions,
    and relationships between tests, features, and step implementations.
    """
    global _bdd_context_cache
    
    if _bdd_context_cache is not None:
        return _bdd_context_cache
    
    # Get test format analysis which now includes BDD information
    test_format_context = get_test_format_context()
    
    if test_format_context.get("status") != 0:
        _bdd_context_cache = {
            "status": 1,
            "message": "Could not analyze BDD context: test format analysis failed",
            "bdd_summary": {}
        }
        return _bdd_context_cache
    
    analysis = test_format_context["analysis"]
    bdd_summary = {
        "has_bdd_tests": False,
        "bdd_suites": [],
        "feature_files": [],
        "step_definitions": [],
        "step_files": [],
        "relationships": []
    }
    
    # Process each test suite for BDD information
    for suite in analysis["test_suites"]:
        suite_bdd_info = suite.get("bdd_info", {})
        
        if suite_bdd_info.get("has_bdd_structure"):
            bdd_summary["has_bdd_tests"] = True
            bdd_summary["bdd_suites"].append({
                "name": suite["name"],
                "path": suite["path"],
                "steps_directory": suite_bdd_info["steps_directory"],
                "step_files": suite_bdd_info["step_files"]
            })
            
            # Collect step files and definitions
            bdd_summary["step_files"].extend(suite_bdd_info["step_files"])
            bdd_summary["step_definitions"].extend(suite_bdd_info["step_definitions"])
        
        # Process individual test cases for feature files
        for test_case in suite["test_cases"]:
            if test_case.get("is_bdd"):
                feature_info = {
                    "test_case": test_case["name"],
                    "suite": suite["name"],
                    "feature_file": test_case["feature_file"],
                    "feature_content": test_case["feature_content"],
                    "steps_used": test_case["bdd_steps_used"]
                }
                bdd_summary["feature_files"].append(feature_info)
                
                # Create relationships between feature files and step definitions
                for step_keyword, step_text in test_case["bdd_steps_used"]:
                    # Try to match step text with step definitions
                    for step_type, step_pattern in suite_bdd_info.get("step_definitions", []):
                        relationship = {
                            "feature_file": test_case["feature_file"],
                            "step_used": f"{step_keyword} {step_text}",
                            "step_definition": f"@{step_type}('{step_pattern}')",
                            "suite": suite["name"]
                        }
                        bdd_summary["relationships"].append(relationship)
    
    _bdd_context_cache = {
        "status": 0,
        "message": f"Found {len(bdd_summary['bdd_suites'])} BDD-enabled suites with {len(bdd_summary['feature_files'])} feature files",
        "bdd_summary": bdd_summary
    }
    
    return _bdd_context_cache

def analyze_object_references() -> Dict:
    """
    Analyze where object references are stored - names.py files in test suites,
    object files in global scripts, or other shared locations.
    """
    current_dir = os.getcwd()
    object_locations = {
        "suite_names_files": [],
        "global_object_files": [],
        "other_object_files": [],
        "patterns": {}
    }
    
    # Look for names.py files in test suites
    names_files = glob.glob(f"{current_dir}/**/suite_*/names.py", recursive=True)
    for names_file in names_files:
        try:
            with open(names_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Count object definitions
            object_defs = re.findall(r'^[A-Za-z_][A-Za-z0-9_]*\s*=', content, re.MULTILINE)
            
            object_locations["suite_names_files"].append({
                "path": names_file,
                "suite": os.path.dirname(names_file),
                "object_count": len(object_defs),
                "sample_objects": object_defs[:5],
                "content_preview": content[:500] + "..." if len(content) > 500 else content
            })
        except Exception as e:
            object_locations["suite_names_files"].append({
                "path": names_file,
                "error": f"Could not analyze: {str(e)}"
            })
    
    # Look for object files in global script directories
    for global_dir in GLOBAL_SCRIPT_DIRS:
        if os.path.exists(global_dir):
            object_files = glob.glob(os.path.join(global_dir, "**", "*object*.py"), recursive=True)
            object_files.extend(glob.glob(os.path.join(global_dir, "**", "*name*.py"), recursive=True))
            object_files.extend(glob.glob(os.path.join(global_dir, "**", "*.map"), recursive=True))
            
            for obj_file in object_files:
                try:
                    with open(obj_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    object_locations["global_object_files"].append({
                        "path": obj_file,
                        "name": os.path.basename(obj_file),
                        "content_preview": content[:500] + "..." if len(content) > 500 else content
                    })
                except Exception as e:
                    object_locations["global_object_files"].append({
                        "path": obj_file,
                        "error": f"Could not analyze: {str(e)}"
                    })
    
    # Look for other potential object reference files
    other_patterns = ["**/objects.py", "**/locators.py", "**/*_objects.py"]
    for pattern in other_patterns:
        files = glob.glob(f"{current_dir}/{pattern}", recursive=True)
        for file_path in files:
            if file_path not in [f["path"] for f in object_locations["suite_names_files"] + object_locations["global_object_files"]]:
                object_locations["other_object_files"].append({
                    "path": file_path,
                    "name": os.path.basename(file_path)
                })
    
    # Generate summary
    summary = f"""Object Reference Analysis:
- Suite names.py files: {len(object_locations['suite_names_files'])}
- Global script object files: {len(object_locations['global_object_files'])}
- Other object files: {len(object_locations['other_object_files'])}
- Primary pattern: {'Suite-based names.py' if object_locations['suite_names_files'] else 'Global object files' if object_locations['global_object_files'] else 'Custom pattern'}
"""
    
    return {
        "status": 0,
        "message": "Object reference analysis complete",
        "analysis": {
            "locations": object_locations,
            "summary": summary
        }
    }

def fetch_squish_api_documentation() -> Dict:
    """
    Load and parse Squish API documentation from local Squish installation.
    """
    # Import shared configuration to get SQUISH_DIR
    from cli import SQUISH_DIR
    
    # Construct path to local API documentation
    squish_api_html_path = os.path.join(SQUISH_DIR, "..", "doc", "html", "squish-api.html")
    squish_api_html_path = os.path.abspath(squish_api_html_path)  # Normalize path
    
    try:
        # Check if the API documentation file exists
        if not os.path.exists(squish_api_html_path):
            return {
                "status": 1,
                "message": f"Local Squish API documentation not found at: {squish_api_html_path}",
                "api_info": {},
                "summary": "Local Squish API documentation not available."
            }
        
        # Read the local HTML file
        with open(squish_api_html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Basic parsing to extract API information
        # Look for function definitions and descriptions
        api_functions = re.findall(r'<h[3-6][^>]*>([^<]*(?:test|wait|click|type|verify|compare|find|start)[^<]*)</h[3-6]>', html_content, re.IGNORECASE)
        code_blocks = re.findall(r'<code[^>]*>([^<]+)</code>', html_content)
        
        # Extract more structured information
        sections = re.split(r'<h[2-3][^>]*>([^<]+)</h[2-3]>', html_content)
        
        api_info = {
            "local_path": squish_api_html_path,
            "functions": list(set(api_functions[:50])),  # Limit to avoid too much data
            "code_examples": list(set(code_blocks[:30])),
            "sections": [sections[i] for i in range(1, len(sections), 2)][:20],  # Section titles
            "content_preview": html_content[:2000] + "..." if len(html_content) > 2000 else html_content,
            "last_loaded": "session_start"
        }
        
        summary = f"""Squish API Documentation:
- Successfully loaded from local installation: {squish_api_html_path}
- Found {len(api_info['functions'])} API function references
- Found {len(api_info['code_examples'])} code examples
- Available sections: {', '.join(api_info['sections'][:5])}

Key API patterns available for test development."""
        
        return {
            "status": 0,
            "message": "Successfully loaded local Squish API documentation",
            "api_info": api_info,
            "summary": summary
        }
        
    except Exception as e:
        return {
            "status": 1,
            "message": f"Failed to load local Squish API documentation: {str(e)}",
            "api_info": {},
            "summary": "Local Squish API documentation not available for this session."
        }

def read_squish_rules() -> Dict:
    """
    Read and parse the SQUISH-RULES.yaml file to get project-specific context and patterns.
    
    Returns:
        Dict with parsed rules, patterns, and context information for LLM guidance.
    """
    if not os.path.exists(SQUISH_RULES_FILE):
        return {
            "status": 1,
            "message": f"SQUISH-RULES.yaml not found at: {SQUISH_RULES_FILE}",
            "rules": {},
            "summary": "No project-specific rules available"
        }
    
    try:
        with open(SQUISH_RULES_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Parse YAML content
        rules_data = yaml.safe_load(content) or {}
        
        # Extract different sections
        parsed_rules = {
            "memories": rules_data.get("memories", {}),
            "context": rules_data.get("context", {}),
            "raw_content": content
        }
        
        # Extract requested patterns for easy access
        requested_patterns = parsed_rules["memories"].get("requested_patterns", [])
        
        # Generate summary
        summary_parts = []
        if requested_patterns:
            summary_parts.append(f"Found {len(requested_patterns)} requested patterns")
            for pattern in requested_patterns[:3]:  # Show first 3 patterns
                if isinstance(pattern, dict) and "pattern" in pattern:
                    summary_parts.append(f"- {pattern['pattern']}")
        
        if parsed_rules["context"]:
            summary_parts.append(f"Context domains: {', '.join(parsed_rules['context'].keys())}")
        
        summary = "\n".join(summary_parts) if summary_parts else "SQUISH-RULES.yaml loaded but contains no specific patterns"
        
        return {
            "status": 0,
            "message": f"Successfully loaded SQUISH-RULES.yaml with {len(requested_patterns)} patterns",
            "rules": parsed_rules,
            "summary": summary
        }
        
    except yaml.YAMLError as e:
        return {
            "status": 1,
            "message": f"Error parsing SQUISH-RULES.yaml: {str(e)}",
            "rules": {},
            "summary": "Failed to parse SQUISH-RULES.yaml - invalid YAML format"
        }
    except Exception as e:
        return {
            "status": 1,
            "message": f"Error reading SQUISH-RULES.yaml: {str(e)}",
            "rules": {},
            "summary": "Failed to read SQUISH-RULES.yaml file"
        }

def fetch_squish_bdd_documentation() -> Dict:
    """
    Fetch and parse Squish BDD documentation from Qt's official documentation.
    This provides comprehensive context about Squish BDD implementation details,
    syntax patterns, and best practices for use when generating or modifying BDD tests.
    """
    url = "https://doc.qt.io/squish/behavior-driven-testing.html"
    
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            html_content = response.read().decode('utf-8')
        
        # Parse BDD-specific information from the documentation
        bdd_info = {
            "url": url,
            "step_definition_patterns": [],
            "placeholder_syntax": [],
            "hook_patterns": [],
            "file_structure": [],
            "context_object_features": [],
            "best_practices": [],
            "implementation_examples": [],
            "content_preview": html_content[:3000] + "..." if len(html_content) > 3000 else html_content,
            "last_fetched": "session_start"
        }
        
        # Extract step definition patterns
        step_patterns = re.findall(r'@(Given|When|Then|Step)\s*\(["\']([^"\']+)["\']\)', html_content, re.IGNORECASE)
        bdd_info["step_definition_patterns"] = list(set(step_patterns))
        
        # Extract placeholder syntax information
        placeholder_patterns = re.findall(r'\|([^|]+)\|', html_content)
        bdd_info["placeholder_syntax"] = list(set(placeholder_patterns))
        
        # Extract hook-related patterns
        hook_patterns = re.findall(r'(OnFeature|OnScenario|OnStep)(?:Start|End)', html_content)
        bdd_info["hook_patterns"] = list(set(hook_patterns))
        
        # Extract context object information
        context_features = re.findall(r'context\.([a-zA-Z_][a-zA-Z0-9_]*)', html_content)
        bdd_info["context_object_features"] = list(set(context_features))
        
        # Extract code examples
        code_blocks = re.findall(r'<code[^>]*>([^<]+)</code>', html_content)
        bdd_info["implementation_examples"] = list(set([code for code in code_blocks if any(keyword in code for keyword in ['@Given', '@When', '@Then', '@Step', 'context'])]))[:20]
        
        # Extract structured sections for best practices
        sections = re.split(r'<h[2-4][^>]*>([^<]+)</h[2-4]>', html_content)
        bdd_info["file_structure"] = [sections[i] for i in range(1, len(sections), 2) if any(keyword in sections[i].lower() for keyword in ['structure', 'organization', 'file'])][:10]
        
        # Create summary of BDD implementation details
        summary = f"""Squish BDD Documentation Context:
- Successfully fetched from {url}
- Step definition patterns: {len(bdd_info['step_definition_patterns'])} found
- Placeholder syntax types: {', '.join(bdd_info['placeholder_syntax'][:5])}
- Hook patterns: {', '.join(bdd_info['hook_patterns'])}
- Context object features: {', '.join(bdd_info['context_object_features'][:5])}
- Implementation examples: {len(bdd_info['implementation_examples'])} code samples

Key BDD implementation details available for test generation:
1. Step definition syntax: @Given, @When, @Then, @Step
2. Parameter placeholders: |word|, |integer|, |any|
3. Context object usage: userData, multiLineText, table
4. Hook system: OnFeatureStart/End, OnScenarioStart/End, OnStepStart/End
5. Gherkin integration with Squish API functions"""
        
        return {
            "status": 0,
            "message": "Successfully fetched Squish BDD documentation",
            "bdd_documentation": bdd_info,
            "summary": summary
        }
        
    except Exception as e:
        return {
            "status": 1,
            "message": f"Failed to fetch Squish BDD documentation: {str(e)}",
            "bdd_documentation": {},
            "summary": "Squish BDD documentation not available for this session."
        }

def perform_global_scripts_analysis() -> Dict:
    """
    Internal function to perform global scripts analysis without MCP tool wrapper.
    """
    # Validate Squish installation
    is_valid, validation_msg = validate_squish_installation()
    if not is_valid:
        return {
            "status": 1,
            "message": validation_msg,
            "analysis": {}
        }
    
    cmd = [SQUISH_RUNNER, "--config", "getGlobalScriptDirs"]
    
    try:
        process = subprocess.run(cmd, capture_output=True, text=True)
        
        if process.returncode != 0:
            return {
                "status": 1,
                "message": f"Command failed with return code {process.returncode}",
                "analysis": {}
            }
        
        directories = []
        if process.stdout.strip():
            raw_dirs = process.stdout.strip().replace(';', '\n').split('\n')
            directories = [dir_path.strip() for dir_path in raw_dirs if dir_path.strip()]
        
        if not directories:
            return {
                "status": 0,
                "message": "No global script directories configured",
                "analysis": {"directories": [], "files": [], "summary": "No global scripts available"}
            }
        
        # Analyze the directories
        analysis = {"directories": directories, "files": [], "summary": ""}
        total_files = 0
        total_functions = 0
        total_classes = 0
        
        for directory in directories:
            if not os.path.exists(directory):
                continue
                
            python_files = glob.glob(os.path.join(directory, "**", "*.py"), recursive=True)
            
            for file_path in python_files:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    lines = content.split('\n')
                    functions = [line.strip() for line in lines if line.strip().startswith('def ')]
                    classes = [line.strip() for line in lines if line.strip().startswith('class ')]
                    imports = [line.strip() for line in lines if line.strip().startswith('import ') or line.strip().startswith('from ')]
                    
                    file_info = {
                        "path": file_path,
                        "relative_path": os.path.relpath(file_path, directory),
                        "size": len(content),
                        "lines": len(lines),
                        "functions": functions,
                        "classes": classes,
                        "imports": imports,
                        "content": content[:2000] + "..." if len(content) > 2000 else content
                    }
                    
                    analysis["files"].append(file_info)
                    total_files += 1
                    total_functions += len(functions)
                    total_classes += len(classes)
                    
                except Exception as e:
                    analysis["files"].append({
                        "path": file_path,
                        "error": f"Could not read file: {str(e)}"
                    })
        
        analysis["summary"] = f"""Global Scripts Analysis:
- Directories: {len(directories)}
- Total Python files: {total_files}
- Total functions: {total_functions}
- Total classes: {total_classes}

Available utilities can be imported and used in Squish test scripts."""
        
        return {
            "status": 0,
            "message": f"Successfully analyzed {total_files} Python files across {len(directories)} directories",
            "analysis": analysis
        }
        
    except Exception as e:
        return {
            "status": 1,
            "message": f"Error analyzing global scripts: {str(e)}",
            "analysis": {}
        }

def initialize_squish_environment_and_contexts():
    """
    Show all below options as TODOs, while thinking.
    Initialize comprehensive Squish test context by analyzing:
    1. Global script directories and available test suite & test case resources/utilities
    2. Existing test script formats and patterns
    3. Object reference locations and conventions
    4. Squish API documentation
    5. Project-specific rules and patterns from SQUISH-RULES.yaml
    This is called once per session to provide complete context for the LLM agent.
    """
    global _global_scripts_cache, _test_format_cache, _object_refs_cache, _squish_api_cache, _squish_rules_cache, _bdd_context_cache, _cache_initialized
    
    if _cache_initialized:
        return
    
    print("=== SQUISH MCP SERVER COMPREHENSIVE INITIALIZATION ===", file=sys.stderr)
    print("Gathering complete Squish test context for LLM agent...", file=sys.stderr)
    print("", file=sys.stderr)
    
    # 1. Analyze global scripts
    print("1. Analyzing global script directories...", file=sys.stderr)
    try:
        analysis_result = perform_global_scripts_analysis()
        _global_scripts_cache = analysis_result
        
        if analysis_result["status"] == 0:
            analysis = analysis_result["analysis"]
            print(f"✓ Found {len(analysis['files'])} Python files across {len(analysis['directories'])} directories", file=sys.stderr)
            print(f"✓ Available: {sum(len(f.get('functions', [])) for f in analysis['files'])} functions, {sum(len(f.get('classes', [])) for f in analysis['files'])} classes", file=sys.stderr)
        else:
            print(f"⚠ Global scripts analysis failed: {analysis_result['message']}", file=sys.stderr)
    except Exception as e:
        print(f"⚠ Error analyzing global scripts: {str(e)}", file=sys.stderr)
        _global_scripts_cache = {"status": 1, "message": f"Error: {str(e)}", "analysis": {}}
    
    # 2. Analyze test script formats
    print("", file=sys.stderr)
    print("2. Analyzing existing test script formats and patterns...", file=sys.stderr)
    try:
        test_format_result = analyze_test_script_formats()
        _test_format_cache = test_format_result
        
        if test_format_result["status"] == 0:
            analysis = test_format_result["analysis"]
            print(f"✓ Found {len(analysis['test_suites'])} test suites", file=sys.stderr)
            total_cases = sum(len(suite['test_cases']) for suite in analysis['test_suites'])
            print(f"✓ Analyzed {total_cases} test cases for patterns and API usage", file=sys.stderr)
            
            # Show key patterns
            unique_apis = list(set(analysis['patterns']['squish_api_usage']))[:5]
            if unique_apis:
                print(f"✓ Common API patterns: {', '.join(unique_apis)}", file=sys.stderr)
            
            # Show BDD information
            bdd_usage = analysis['patterns']['bdd_usage']
            if bdd_usage['total_bdd_tests'] > 0:
                print(f"✓ Found {bdd_usage['total_bdd_tests']} BDD test cases in {len(bdd_usage['bdd_suites'])} suites", file=sys.stderr)
                print(f"✓ BDD-enabled suites: {', '.join(bdd_usage['bdd_suites'])}", file=sys.stderr)
        else:
            print(f"⚠ Test format analysis had issues: {test_format_result['message']}", file=sys.stderr)
    except Exception as e:
        print(f"⚠ Error analyzing test formats: {str(e)}", file=sys.stderr)
        _test_format_cache = {"status": 1, "message": f"Error: {str(e)}", "analysis": {}}
    
    # 3. Analyze object references
    print("", file=sys.stderr)
    print("3. Analyzing object reference patterns and locations...", file=sys.stderr)
    try:
        object_refs_result = analyze_object_references()
        _object_refs_cache = object_refs_result
        
        if object_refs_result["status"] == 0:
            locations = object_refs_result["analysis"]["locations"]
            print(f"✓ Found {len(locations['suite_names_files'])} suite names.py files", file=sys.stderr)
            print(f"✓ Found {len(locations['global_object_files'])} global object files", file=sys.stderr)
            print(f"✓ Found {len(locations['other_object_files'])} other object files", file=sys.stderr)
        else:
            print(f"⚠ Object reference analysis had issues: {object_refs_result['message']}", file=sys.stderr)
    except Exception as e:
        print(f"⚠ Error analyzing object references: {str(e)}", file=sys.stderr)
        _object_refs_cache = {"status": 1, "message": f"Error: {str(e)}", "analysis": {}}
    
    # 4. Fetch Squish API documentation
    print("", file=sys.stderr)
    print("4. Fetching Squish API documentation...", file=sys.stderr)
    try:
        api_result = fetch_squish_api_documentation()
        _squish_api_cache = api_result
        
        if api_result["status"] == 0:
            api_info = api_result["api_info"]
            print(f"✓ Successfully fetched API documentation from {api_info['url']}", file=sys.stderr)
            print(f"✓ Found {len(api_info['functions'])} API functions and {len(api_info['code_examples'])} code examples", file=sys.stderr)
        else:
            print(f"⚠ API documentation fetch failed: {api_result['message']}", file=sys.stderr)
    except Exception as e:
        print(f"⚠ Error fetching API documentation: {str(e)}", file=sys.stderr)
        _squish_api_cache = {"status": 1, "message": f"Error: {str(e)}", "api_info": {}}
    
    # 5. Load project-specific rules
    print("", file=sys.stderr)
    print("5. Loading project-specific rules from SQUISH-RULES.yaml...", file=sys.stderr)
    try:
        rules_result = read_squish_rules()
        _squish_rules_cache = rules_result
        
        if rules_result["status"] == 0:
            patterns = rules_result["rules"].get("memories", {}).get("requested_patterns", [])
            print(f"✓ Successfully loaded SQUISH-RULES.yaml", file=sys.stderr)
            print(f"✓ Found {len(patterns)} project-specific patterns and rules", file=sys.stderr)
            if patterns:
                # Show first pattern as example
                first_pattern = patterns[0]
                if isinstance(first_pattern, dict) and "pattern" in first_pattern:
                    print(f"✓ Example rule: {first_pattern['pattern']}", file=sys.stderr)
        else:
            print(f"⚠ SQUISH-RULES.yaml loading failed: {rules_result['message']}", file=sys.stderr)
    except Exception as e:
        print(f"⚠ Error loading SQUISH-RULES.yaml: {str(e)}", file=sys.stderr)
        _squish_rules_cache = {"status": 1, "message": f"Error: {str(e)}", "rules": {}}
    
    # 6. Extract comprehensive BDD context
    print("", file=sys.stderr)
    print("6. Extracting comprehensive BDD context and relationships...", file=sys.stderr)
    try:
        bdd_result = extract_bdd_context()
        _bdd_context_cache = bdd_result
        
        if bdd_result["status"] == 0:
            bdd_summary = bdd_result["bdd_summary"]
            if bdd_summary["has_bdd_tests"]:
                print(f"✓ Found BDD test structure in {len(bdd_summary['bdd_suites'])} suites", file=sys.stderr)
                print(f"✓ Detected {len(bdd_summary['feature_files'])} feature files with {len(bdd_summary['step_definitions'])} step definitions", file=sys.stderr)
                print(f"✓ Mapped {len(bdd_summary['relationships'])} feature-to-step relationships", file=sys.stderr)
            else:
                print("✓ No BDD test structure detected in current project", file=sys.stderr)
        else:
            print(f"⚠ BDD context extraction failed: {bdd_result['message']}", file=sys.stderr)
    except Exception as e:
        print(f"⚠ Error extracting BDD context: {str(e)}", file=sys.stderr)
        _bdd_context_cache = {"status": 1, "message": f"Error: {str(e)}", "bdd_summary": {}}
    
    # 7. Fetch Squish BDD documentation (cached for BDD operations)
    print("", file=sys.stderr)
    print("7. Fetching Squish BDD documentation for context...", file=sys.stderr)
    try:
        bdd_doc_result = fetch_squish_bdd_documentation()
        _bdd_documentation_cache = bdd_doc_result
        
        if bdd_doc_result["status"] == 0:
            bdd_doc_info = bdd_doc_result["bdd_documentation"]
            print(f"✓ Successfully fetched BDD documentation from {bdd_doc_info['url']}", file=sys.stderr)
            print(f"✓ Found {len(bdd_doc_info['step_definition_patterns'])} step patterns and {len(bdd_doc_info['implementation_examples'])} examples", file=sys.stderr)
            placeholder_types = ', '.join(bdd_doc_info['placeholder_syntax'][:3])
            if placeholder_types:
                print(f"✓ Parameter placeholders: {placeholder_types}", file=sys.stderr)
        else:
            print(f"⚠ BDD documentation fetch failed: {bdd_doc_result['message']}", file=sys.stderr)
    except Exception as e:
        print(f"⚠ Error fetching BDD documentation: {str(e)}", file=sys.stderr)
        _bdd_documentation_cache = {"status": 1, "message": f"Error: {str(e)}", "bdd_documentation": {}}
    
    _cache_initialized = True
    
    print("", file=sys.stderr)
    print("=== INITIALIZATION COMPLETE ===", file=sys.stderr)
    print("", file=sys.stderr)
    
    # Return all context cache elements for MCP tool response
    return {
        "global_scripts_cache": _global_scripts_cache,
        "test_format_cache": _test_format_cache,
        "object_refs_cache": _object_refs_cache,
        "squish_api_cache": _squish_api_cache,
        "squish_rules_cache": _squish_rules_cache,
        "bdd_context_cache": _bdd_context_cache,
        "bdd_documentation_cache": _bdd_documentation_cache,
        "cache_initialized": _cache_initialized
    }

# Context Access Functions
def get_global_script_context() -> Dict:
    """Get the cached global script analysis from the current session."""
    global _global_scripts_cache
        
    if _global_scripts_cache is None:
        return {
            "status": 1,
            "message": "Global scripts cache not initialized",
            "analysis": {}
        }
    
    return _global_scripts_cache

def get_test_format_context() -> Dict:
    """Get analysis of existing test script formats and patterns in the repository."""
    global _test_format_cache
        
    if _test_format_cache is None:
        return {
            "status": 1,
            "message": "Test format cache not initialized",
            "analysis": {}
        }
    
    return _test_format_cache

def get_object_reference_context() -> Dict:
    """Get analysis of where and how object references are stored in the test suite."""
    global _object_refs_cache
        
    if _object_refs_cache is None:
        return {
            "status": 1,
            "message": "Object reference cache not initialized", 
            "analysis": {}
        }
    
    return _object_refs_cache

def get_squish_api_context() -> Dict:
    """Get cached Squish API documentation and function reference."""
    global _squish_api_cache
        
    if _squish_api_cache is None:
        return {
            "status": 1,
            "message": "Squish API cache not initialized",
            "api_info": {}
        }
    
    return _squish_api_cache

def get_squish_rules_context() -> Dict:
    """Get project-specific rules and patterns from SQUISH-RULES.yaml file."""
    global _squish_rules_cache
        
    if _squish_rules_cache is None:
        return {
            "status": 1,
            "message": "Squish rules cache not initialized",
            "rules": {},
            "summary": "No project rules available"
        }
    
    return _squish_rules_cache

def get_bdd_context() -> Dict:
    """Get the cached BDD analysis from the current session."""
    global _bdd_context_cache
        
    if _bdd_context_cache is None:
        return {
            "status": 1,
            "message": "BDD context not initialized",
            "bdd_summary": {}
        }
    
    return _bdd_context_cache

def get_bdd_documentation_context() -> Dict:
    """
    Get the cached Squish BDD documentation from Qt's official docs.
    This provides comprehensive context about Squish BDD implementation for test generation.
    """
    global _bdd_documentation_cache
        
    if _bdd_documentation_cache is None:
        return {
            "status": 1,
            "message": "BDD documentation cache not initialized",
            "bdd_documentation": {},
            "summary": "No BDD documentation available"
        }
    
    return _bdd_documentation_cache

def ensure_bdd_documentation_context() -> Dict:
    """
    Ensure BDD documentation context is loaded and available.
    This function should be called by any BDD-related MCP tool to guarantee
    that the official Squish BDD documentation is available for context.
    
    Returns:
        Dict with BDD documentation context, fetching it if not already cached.
    """
    global _bdd_documentation_cache
    
    # If not cached, fetch it now
    if _bdd_documentation_cache is None:
        _bdd_documentation_cache = fetch_squish_bdd_documentation()
    
    return _bdd_documentation_cache

# initialize_squish_environment_and_contexts() - removed automatic initialization
# Context will be initialized on-demand when first accessed