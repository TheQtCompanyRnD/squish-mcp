#!/usr/bin/env python3
"""
POM Generation Helper Functions

This module provides helper functions for the enhanced POM generation workflow
that integrates the parse_object_snapshot.py script with existing pattern analysis
to generate structured object references according to discovered patterns.

Key Functions:
- _determine_output_strategy: Analyzes existing patterns to determine output format
- _generate_pom_class_objects: Creates POM class-based object structure
- _generate_names_file_objects: Creates traditional names.py object structure  
- _create_object_files: Creates the actual files based on generated structure

IMPORTANT: This file requires Python 3.10+ due to f-string usage and type hints.
Do not use with Python 2.x - it will cause syntax errors.
"""

import os
import re
from typing import Dict, List, Optional, Tuple
from collections import defaultdict


def _determine_output_strategy(pattern_analysis: Dict, page_name: str) -> Dict:
    """
    Determine output strategy based on existing object reference patterns.
    
    Args:
        pattern_analysis: Analysis of existing object patterns and file locations
        page_name: Name of the page being processed
        
    Returns:
        Dict containing output strategy and target locations
    """
    strategy = {
        "format": "names_file",  # Default fallback
        "target_directory": None,
        "file_naming": "snake_case",
        "class_naming": "PascalCase",
        "method_naming": "camelCase",
        "structure_type": "flat"
    }
    
    try:
        if pattern_analysis.get("status") == 0:
            object_files = pattern_analysis.get("object_files", [])
            page_org = pattern_analysis.get("page_organization", {})
            
            # Check if we have POM class structure (global files with classes)
            has_pom_classes = any(
                "pom" in f.get("path", "").lower() or 
                "object_references" in f.get("path", "") or
                "base.py" in f.get("path", "")
                for f in object_files if f.get("type") == "global"
            )
            
            # Check for traditional names.py structure  
            has_names_files = any(
                f.get("type") == "suite_names"
                for f in object_files
            )
            
            if has_pom_classes:
                strategy["format"] = "pom_class"
                strategy["structure_type"] = "hierarchical"
                
                # Try to find the base directory from global files
                base_dir = page_org.get("base_directory")
                if base_dir and "pom" in base_dir.lower():
                    strategy["target_directory"] = base_dir
                else:
                    # Look for POM directories in global files
                    for file_info in object_files:
                        if file_info.get("type") == "global":
                            path = file_info.get("path", "")
                            if "pom" in path.lower():
                                strategy["target_directory"] = os.path.dirname(path)
                                break
                
            elif has_names_files:
                strategy["format"] = "names_file"
                strategy["structure_type"] = "flat"
                
                # Use suite names.py approach
                names_files = [f for f in object_files if f.get("type") == "suite_names"]
                if names_files:
                    # Use the directory of the first names.py file found
                    first_names_file = names_files[0].get("path", "")
                    strategy["target_directory"] = os.path.dirname(first_names_file)
        
        # Ensure we have a target directory
        if not strategy["target_directory"]:
            # Default to current working directory + page-based structure
            cwd = os.getcwd()
            strategy["target_directory"] = os.path.join(cwd, "object_references")
            
    except Exception as e:
        print(f"Warning: Error determining output strategy: {e}")
        # Keep default strategy
    
    return strategy


def _generate_pom_class_objects(parsed_objects: List[Dict], page_name: str, 
                               output_strategy: Dict, pattern_analysis: Dict) -> Dict:
    """
    Generate POM class-based object structure.
    
    Args:
        parsed_objects: Filtered objects from parse_object_snapshot.py
        page_name: Name of the page
        output_strategy: Determined output strategy
        pattern_analysis: Analysis of existing patterns
        
    Returns:
        Dict with generated POM class structure
    """
    result = {
        "format": "pom_class",
        "new_object_count": len(parsed_objects),
        "create_files": True,
        "files_to_create": [],
        "class_content": {},
        "base_content": {}
    }
    
    try:
        # Generate class name
        class_name = f"{page_name.replace('-', '_').replace(' ', '_').title()}_Objects"
        
        # Create object_references.py content
        object_refs_content = _generate_object_references_class(
            parsed_objects, class_name, page_name
        )
        result["class_content"]["object_references"] = object_refs_content
        
        # Create actions.py content  
        actions_content = _generate_actions_class(
            parsed_objects, class_name, page_name
        )
        result["class_content"]["actions"] = actions_content
        
        # Create base.py content
        base_content = _generate_base_class(class_name, page_name)
        result["base_content"]["base"] = base_content
        
        # Determine target directory structure
        target_dir = output_strategy["target_directory"]
        page_dir = os.path.join(target_dir, f"{page_name.lower().replace(' ', '-')}-pom")
        
        result["files_to_create"] = [
            {
                "path": os.path.join(page_dir, "object_references.py"),
                "content": object_refs_content,
                "type": "class_objects"
            },
            {
                "path": os.path.join(page_dir, "actions.py"), 
                "content": actions_content,
                "type": "class_actions"
            },
            {
                "path": os.path.join(page_dir, "base.py"),
                "content": base_content,
                "type": "class_base"
            }
        ]
        
    except Exception as e:
        result["error"] = f"Error generating POM class objects: {str(e)}"
    
    return result


def _generate_names_file_objects(parsed_objects: List[Dict], page_name: str,
                                output_strategy: Dict, pattern_analysis: Dict) -> Dict:
    """
    Generate traditional names.py file object structure.
    
    Args:
        parsed_objects: Filtered objects from parse_object_snapshot.py
        page_name: Name of the page
        output_strategy: Determined output strategy
        pattern_analysis: Analysis of existing patterns
        
    Returns:
        Dict with generated names.py structure
    """
    result = {
        "format": "names_file", 
        "new_object_count": len(parsed_objects),
        "create_files": True,
        "files_to_create": [],
        "names_content": {}
    }
    
    try:
        # Generate names.py content using existing parse_object_snapshot logic
        from .parse_object_snapshot import generate_python_names
        python_lines = generate_python_names(parsed_objects)
        
        # Create complete names.py file content
        names_content = _generate_names_file_content(python_lines, page_name)
        result["names_content"]["names"] = names_content
        
        # Determine target file
        target_dir = output_strategy["target_directory"] 
        target_file = os.path.join(target_dir, f"{page_name.lower().replace(' ', '_')}_names.py")
        
        result["files_to_create"] = [
            {
                "path": target_file,
                "content": names_content,
                "type": "names_file"
            }
        ]
        
    except Exception as e:
        result["error"] = f"Error generating names file objects: {str(e)}"
    
    return result


def _create_object_files(object_generation: Dict, output_strategy: Dict, page_name: str) -> Dict:
    """
    Create the actual object reference files based on generated structure.
    
    Args:
        object_generation: Generated object structure 
        output_strategy: Output strategy configuration
        page_name: Name of the page
        
    Returns:
        Dict with file creation results
    """
    result = {
        "status": 0,
        "files_created": [],
        "files_failed": [],
        "directories_created": []
    }
    
    try:
        files_to_create = object_generation.get("files_to_create", [])
        
        for file_info in files_to_create:
            file_path = file_info["path"]
            content = file_info["content"]
            file_type = file_info["type"]
            
            try:
                # Ensure directory exists
                dir_path = os.path.dirname(file_path)
                if not os.path.exists(dir_path):
                    os.makedirs(dir_path, exist_ok=True)
                    if dir_path not in result["directories_created"]:
                        result["directories_created"].append(dir_path)
                
                # Create backup if file exists
                if os.path.exists(file_path):
                    backup_path = f"{file_path}.backup"
                    import shutil
                    shutil.copy2(file_path, backup_path)
                
                # Write the file
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                result["files_created"].append({
                    "path": file_path,
                    "type": file_type,
                    "size": len(content)
                })
                
            except Exception as e:
                result["files_failed"].append({
                    "path": file_path,
                    "error": str(e)
                })
        
    except Exception as e:
        result["status"] = 1
        result["error"] = f"Error creating object files: {str(e)}"
    
    return result


def _generate_object_references_class(parsed_objects: List[Dict], class_name: str, page_name: str) -> str:
    """Generate object_references.py class content."""
    lines = [
        f"# {page_name} Page Object References",
        "# encoding: UTF-8", 
        "# Generated by Enhanced Squish MCP POM Generator",
        "",
        "from objectmaphelper import *",
        "",
        f"class {class_name}():",
        "    \"\"\"",
        f"    Object references for {page_name} page.",
        "    Contains static methods that return Squish object references.",
        "    \"\"\"",
        ""
    ]
    
    # Sort objects by name for consistency
    sorted_objects = sorted(parsed_objects, key=lambda x: x.get("var_name", ""))
    
    for obj in sorted_objects:
        var_name = obj.get("var_name", "")
        obj_def = _create_object_definition_dict(obj)
        
        # Create method name from variable name
        method_name = _variable_to_method_name(var_name)
        
        # Format object definition
        props = []
        for key, value in obj_def.items():
            if isinstance(value, str):
                props.append(f'"{key}": "{value}"')
            elif isinstance(value, bool):
                props.append(f'"{key}": {str(value).lower()}')  
            else:
                props.append(f'"{key}": {value}')
        
        props_str = ", ".join(props)
        
        lines.extend([
            "    @staticmethod",
            f"    def {method_name}():",
            f'        """Return {obj.get("type", "object")} object reference."""',
            f"        return waitForObject({{{props_str}}})",
            ""
        ])
    
    return "\n".join(lines)


def _generate_actions_class(parsed_objects: List[Dict], class_name: str, page_name: str) -> str:
    """Generate actions.py class content."""
    action_class_name = class_name.replace("_Objects", "_Actions")
    
    lines = [
        f"# {page_name} Page Actions",
        "# encoding: UTF-8",
        "# Generated by Enhanced Squish MCP POM Generator",
        "",
        "import test",
        "from objectmaphelper import *",
        f"from .object_references import {class_name}",
        "",
        f"class {action_class_name}():",
        "    \"\"\"",
        f"    Action methods for {page_name} page.",
        "    Contains methods for interacting with page objects.",
        "    \"\"\"",
        "",
        "    @staticmethod",
        "    def verify_page_loaded():",
        f'        """Verify that the {page_name} page is loaded."""',
        "        # TODO: Add specific verification logic",
        "        test.log(f\"Verifying {page_name} page is loaded\")",
        "",
    ]
    
    # Add basic interaction methods for common object types
    button_objects = [obj for obj in parsed_objects if "button" in obj.get("type", "").lower()]
    text_objects = [obj for obj in parsed_objects if obj.get("text") and obj.get("text").strip()]
    
    if button_objects:
        lines.append("    # Button interaction methods")
        for obj in button_objects[:5]:  # Limit to first 5 buttons
            method_name = _variable_to_method_name(obj.get("var_name", ""))
            lines.extend([
                f"    @staticmethod",
                f"    def click_{method_name}():",
                f'        """Click the {obj.get("type", "button")} button."""',
                f"        clickButton({class_name}.{method_name}())",
                ""
            ])
    
    if text_objects:
        lines.append("    # Text verification methods")
        for obj in text_objects[:5]:  # Limit to first 5 text objects
            method_name = _variable_to_method_name(obj.get("var_name", ""))
            expected_text = obj.get("text", "")
            lines.extend([
                f"    @staticmethod", 
                f"    def verify_{method_name}_text():",
                f'        """Verify the text content of {obj.get("type", "text")} object."""',
                f'        actual_text = waitForObject({class_name}.{method_name}()).text',
                f'        test.compare(actual_text, "{expected_text}")',
                ""
            ])
    
    return "\n".join(lines)


def _generate_base_class(class_name: str, page_name: str) -> str:
    """Generate base.py class content."""
    objects_class = class_name
    actions_class = class_name.replace("_Objects", "_Actions")
    page_class = page_name.replace("-", "_").replace(" ", "_").title()
    
    lines = [
        f"# {page_name} Page Base Class",
        "# encoding: UTF-8",
        "# Generated by Enhanced Squish MCP POM Generator",
        "",
        f"from .object_references import {objects_class}",
        f"from .actions import {actions_class}",
        "",
        f"class {page_class}:",
        "    \"\"\"",
        f"    Main class for {page_name} page interactions.",
        "    Combines object references and actions for easy access.",
        "    \"\"\"",
        "",
        "    def __init__(self):",
        f"        self.objects = {objects_class}",
        f"        self.actions = {actions_class}",
        "",
        "    def verify_loaded(self):",
        f'        """Verify that the {page_name} page is loaded."""',
        "        return self.actions.verify_page_loaded()",
        ""
    ]
    
    return "\n".join(lines)


def _generate_names_file_content(python_lines: List[str], page_name: str) -> str:
    """Generate complete names.py file content."""
    lines = [
        f"# {page_name} Object Names",
        "# encoding: UTF-8",
        f"# Generated by Enhanced Squish MCP POM Generator from XML snapshot",
        "",
        "from objectmaphelper import *",
        "",
        "# Main application container",
        "antares_Cluster_QQuickWindowQmlImpl = {\"title\": \"Antares Cluster\", \"type\": \"QQuickWindowQmlImpl\", \"unnamed\": 1, \"visible\": True}",
        "",
        f"# {page_name} page objects",
    ]
    
    lines.extend(python_lines)
    
    return "\n".join(lines)


def _create_object_definition_dict(obj: Dict) -> Dict:
    """Create a standardized object definition dictionary from parsed object."""
    definition = {
        "container": obj.get("container", ""),
        "type": obj.get("type", ""),
        "unnamed": 1,
        "visible": obj.get("visible", True)
    }
    
    if obj.get("id"):
        definition["id"] = obj["id"]
    
    if obj.get("text"):
        definition["text"] = obj["text"]
    
    if obj.get("object_name"):
        definition["objectName"] = obj["object_name"]
    
    if obj.get("occurrence", 1) > 1 and not obj.get("id"):
        definition["occurrence"] = obj["occurrence"]
    
    return definition


def _variable_to_method_name(var_name: str) -> str:
    """Convert variable name to camelCase method name."""
    if not var_name:
        return "unknownObject"
    
    # Remove common prefixes
    clean_name = var_name
    prefixes = ["antares_Cluster_", "antares_", "cluster_"]
    for prefix in prefixes:
        if clean_name.startswith(prefix):
            clean_name = clean_name[len(prefix):]
            break
    
    # Split on underscores and convert to camelCase
    parts = clean_name.split("_")
    if not parts:
        return "unknownObject"
    
    # First part lowercase, rest capitalized
    method_name = parts[0].lower()
    for part in parts[1:]:
        if part:
            method_name += part.capitalize()
    
    # Ensure it's a valid Python identifier
    if not method_name or not method_name[0].isalpha():
        method_name = f"object_{method_name}"
    
    return method_name