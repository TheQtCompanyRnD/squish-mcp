#!/usr/bin/env python3
"""
POM Generation Module

This module provides functionality for generating Page Object Model (POM) classes
for Squish test automation by analyzing existing object maps and XML object snapshots.

Key Features:
- Analyzes current object map structure (names.py or global scripts)
- Parses XML object snapshots to extract UI hierarchy
- Generates organized object reference files per page
- Merges new/modified references with existing structure
- Maintains consistency with project patterns

IMPORTANT: This file requires Python 3.10+ due to f-string usage and type hints.
Do not use with Python 2.x - it will cause syntax errors.
"""

import os
import re
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict

# Import our existing object snapshot parser
from .parse_object_snapshot import parse_object_snapshot, generate_python_names


def analyze_current_object_map_structure(context_data: Dict) -> Dict:
    """
    Analyze the current object map structure from cached context data.
    
    Args:
        context_data: Cached context data containing object reference analysis
        
    Returns:
        Dict containing current object map structure analysis
    """
    structure_info = {
        "status": 0,
        "object_files": [],
        "reference_patterns": {},
        "page_organization": {},
        "naming_conventions": {},
        "existing_objects": {},
        "file_locations": {}
    }
    
    try:
        # Extract object reference context if available
        obj_context = context_data.get("object_reference_context", {})
        if obj_context.get("status") == 0:
            analysis = obj_context.get("analysis", {})
            locations = analysis.get("locations", {})
            
            # Process global object files
            global_files = locations.get("global_object_files", [])
            for file_info in global_files:
                structure_info["object_files"].append({
                    "type": "global",
                    "path": file_info.get("file"),
                    "objects": file_info.get("objects", []),
                    "patterns": file_info.get("patterns", [])
                })
                
                # Extract existing objects
                for obj in file_info.get("objects", []):
                    obj_name = obj.get("name", "")
                    if obj_name:
                        structure_info["existing_objects"][obj_name] = {
                            "definition": obj.get("definition", {}),
                            "file": file_info.get("file"),
                            "type": "global"
                        }
            
            # Process suite names.py files
            names_files = locations.get("suite_names_files", [])
            for file_info in names_files:
                structure_info["object_files"].append({
                    "type": "suite_names",
                    "path": file_info.get("file"),
                    "objects": file_info.get("objects", []),
                    "suite": file_info.get("suite")
                })
                
                # Extract existing objects
                for obj in file_info.get("objects", []):
                    obj_name = obj.get("name", "")
                    if obj_name:
                        structure_info["existing_objects"][obj_name] = {
                            "definition": obj.get("definition", {}),
                            "file": file_info.get("file"),
                            "type": "suite_names"
                        }
            
            # Analyze patterns
            patterns = analysis.get("patterns", {})
            structure_info["reference_patterns"] = {
                "common_containers": patterns.get("common_containers", []),
                "naming_patterns": patterns.get("naming_patterns", []),
                "property_patterns": patterns.get("property_patterns", [])
            }
            
            # Determine file organization strategy
            if global_files:
                structure_info["page_organization"]["strategy"] = "global_files"
                structure_info["page_organization"]["base_directory"] = _extract_base_directory(global_files)
            elif names_files:
                structure_info["page_organization"]["strategy"] = "suite_names"
                structure_info["page_organization"]["suites"] = [f.get("suite") for f in names_files]
            
    except Exception as e:
        structure_info["status"] = 1
        structure_info["error"] = f"Error analyzing object map structure: {str(e)}"
    
    return structure_info


def _extract_base_directory(global_files: List[Dict]) -> Optional[str]:
    """Extract common base directory from global object files."""
    if not global_files:
        return None
    
    paths = [f.get("file", "") for f in global_files]
    if not paths:
        return None
    
    # Find common directory
    common_path = os.path.commonpath([os.path.dirname(p) for p in paths if p])
    return common_path if common_path else None


def generate_page_object_references(xml_file_path: str, page_name: str, 
                                   structure_info: Dict) -> Dict:
    """
    Generate object references for a specific page from XML snapshot.
    
    Args:
        xml_file_path: Path to the XML object snapshot file
        page_name: Name of the page/component these objects belong to
        structure_info: Current object map structure information
        
    Returns:
        Dict containing generated object references and organization info
    """
    result = {
        "status": 0,
        "page_name": page_name,
        "new_objects": [],
        "modified_objects": [],
        "unchanged_objects": [],
        "conflicts": [],
        "organization": {}
    }
    
    try:
        # Parse the XML snapshot
        parsed_objects = parse_object_snapshot(xml_file_path)
        
        existing_objects = structure_info.get("existing_objects", {})
        
        # Analyze each parsed object
        for obj in parsed_objects:
            var_name = obj.get("var_name", "")
            
            if var_name in existing_objects:
                # Compare with existing definition
                existing_def = existing_objects[var_name]["definition"]
                new_def = _create_object_definition(obj)
                
                if _objects_are_different(existing_def, new_def):
                    result["modified_objects"].append({
                        "name": var_name,
                        "existing": existing_def,
                        "new": new_def,
                        "source_file": existing_objects[var_name]["file"]
                    })
                else:
                    result["unchanged_objects"].append(var_name)
            else:
                # New object
                result["new_objects"].append({
                    "name": var_name,
                    "definition": _create_object_definition(obj),
                    "metadata": {
                        "page": page_name,
                        "type": obj.get("type", ""),
                        "container": obj.get("container", ""),
                        "has_id": bool(obj.get("id")),
                        "has_text": bool(obj.get("text"))
                    }
                })
        
        # Determine organization strategy
        result["organization"] = _determine_page_organization(
            page_name, structure_info, len(result["new_objects"]), len(result["modified_objects"])
        )
        
    except Exception as e:
        result["status"] = 1
        result["error"] = f"Error generating page object references: {str(e)}"
    
    return result


def _create_object_definition(obj: Dict) -> Dict:
    """Create a standardized object definition dictionary."""
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


def _objects_are_different(existing: Dict, new: Dict) -> bool:
    """Compare two object definitions to see if they're different."""
    # Compare key properties that would affect test execution
    key_props = ["container", "type", "id", "text", "objectName", "visible"]
    
    for prop in key_props:
        if existing.get(prop) != new.get(prop):
            return True
    
    return False


def _determine_page_organization(page_name: str, structure_info: Dict, 
                               new_count: int, modified_count: int) -> Dict:
    """Determine how to organize the page objects based on existing structure."""
    organization = {
        "strategy": "unknown",
        "target_file": None,
        "create_new_file": False,
        "file_name_suggestion": None
    }
    
    page_org = structure_info.get("page_organization", {})
    strategy = page_org.get("strategy", "unknown")
    
    if strategy == "global_files":
        # Use global file organization
        base_dir = page_org.get("base_directory", "")
        organization["strategy"] = "global_file"
        organization["create_new_file"] = True
        organization["target_file"] = os.path.join(base_dir, f"{page_name.lower()}_objects.py")
        organization["file_name_suggestion"] = f"{page_name.lower()}_objects.py"
        
    elif strategy == "suite_names":
        # Use suite names.py approach
        organization["strategy"] = "suite_names"
        organization["create_new_file"] = False
        # Would need to know which suite to add to
        
    else:
        # Default to global file approach
        organization["strategy"] = "global_file"
        organization["create_new_file"] = True
        organization["file_name_suggestion"] = f"{page_name.lower()}_objects.py"
    
    return organization


def create_page_object_file(page_name: str, objects_data: Dict, 
                          target_path: str, structure_info: Dict) -> Dict:
    """
    Create or update a page object file with the generated references.
    
    Args:
        page_name: Name of the page
        objects_data: Generated object references data
        target_path: Path where the file should be created/updated
        structure_info: Current object map structure information
        
    Returns:
        Dict with creation/update status and details
    """
    result = {
        "status": 0,
        "file_path": target_path,
        "objects_added": 0,
        "objects_modified": 0,
        "backup_created": False
    }
    
    try:
        # Create backup if file exists
        if os.path.exists(target_path):
            backup_path = f"{target_path}.backup"
            import shutil
            shutil.copy2(target_path, backup_path)
            result["backup_created"] = True
        
        # Generate file content
        file_content = _generate_page_object_file_content(
            page_name, objects_data, structure_info
        )
        
        # Write the file
        with open(target_path, 'w', encoding='utf-8') as f:
            f.write(file_content)
        
        result["objects_added"] = len(objects_data.get("new_objects", []))
        result["objects_modified"] = len(objects_data.get("modified_objects", []))
        
    except Exception as e:
        result["status"] = 1
        result["error"] = f"Error creating page object file: {str(e)}"
    
    return result


def _generate_page_object_file_content(page_name: str, objects_data: Dict, 
                                     structure_info: Dict) -> str:
    """Generate the content for a page object file."""
    lines = []
    
    # File header
    lines.append(f"# {page_name} Page Object References")
    lines.append("# encoding: UTF-8")
    lines.append("# Generated by Squish MCP POM Generator")
    lines.append("")
    lines.append("from objectmaphelper import *")
    lines.append("")
    
    # Add page-specific container if needed
    page_container = f"{page_name.lower()}_container"
    lines.append(f"# {page_name} page container")
    lines.append(f'{page_container} = {{"type": "QQuickWindowQmlImpl", "unnamed": 1, "visible": True}}')
    lines.append("")
    
    # Add new objects
    new_objects = objects_data.get("new_objects", [])
    if new_objects:
        lines.append(f"# New objects for {page_name}")
        
        # Sort by name for consistency
        new_objects.sort(key=lambda x: x["name"])
        
        for obj_info in new_objects:
            obj_name = obj_info["name"]
            obj_def = obj_info["definition"]
            
            # Format the definition
            props = []
            for key, value in obj_def.items():
                if isinstance(value, str):
                    props.append(f'"{key}": "{value}"')
                elif isinstance(value, bool):
                    props.append(f'"{key}": {str(value).lower()}')
                else:
                    props.append(f'"{key}": {value}')
            
            props_str = ", ".join(props)
            lines.append(f'{obj_name} = {{{props_str}}}')
        
        lines.append("")
    
    # Add modified objects with comments
    modified_objects = objects_data.get("modified_objects", [])
    if modified_objects:
        lines.append(f"# Modified objects for {page_name}")
        lines.append("# Note: These objects have been updated from existing definitions")
        
        for obj_info in modified_objects:
            obj_name = obj_info["name"]
            obj_def = obj_info["new"]
            
            lines.append(f"# Updated from: {obj_info['source_file']}")
            
            # Format the definition
            props = []
            for key, value in obj_def.items():
                if isinstance(value, str):
                    props.append(f'"{key}": "{value}"')
                elif isinstance(value, bool):
                    props.append(f'"{key}": {str(value).lower()}')
                else:
                    props.append(f'"{key}": {value}')
            
            props_str = ", ".join(props)
            lines.append(f'{obj_name} = {{{props_str}}}')
        
        lines.append("")
    
    return "\n".join(lines)


def merge_with_existing_structure(objects_data: Dict, structure_info: Dict, 
                                page_name: str) -> Dict:
    """
    Merge generated object references with existing object map structure.
    
    Args:
        objects_data: Generated object references
        structure_info: Current object map structure
        page_name: Name of the page being processed
        
    Returns:
        Dict with merge plan and recommendations
    """
    merge_plan = {
        "status": 0,
        "strategy": "unknown",
        "recommendations": [],
        "files_to_create": [],
        "files_to_update": [],
        "conflicts_to_resolve": []
    }
    
    try:
        organization = objects_data.get("organization", {})
        strategy = organization.get("strategy", "unknown")
        
        if strategy == "global_file":
            # Create new global object file for this page
            target_file = organization.get("target_file")
            if target_file:
                merge_plan["files_to_create"].append({
                    "path": target_file,
                    "type": "page_objects",
                    "page": page_name,
                    "object_count": len(objects_data.get("new_objects", []))
                })
                merge_plan["strategy"] = "create_page_file"
                merge_plan["recommendations"].append(
                    f"Create {target_file} for {page_name} page objects"
                )
        
        elif strategy == "suite_names":
            # Would need to update existing names.py files
            merge_plan["strategy"] = "update_names_files"
            merge_plan["recommendations"].append(
                "Consider creating separate page object files instead of adding to names.py"
            )
        
        # Check for conflicts
        conflicts = objects_data.get("conflicts", [])
        for conflict in conflicts:
            merge_plan["conflicts_to_resolve"].append({
                "object_name": conflict.get("name"),
                "issue": conflict.get("issue"),
                "suggestion": conflict.get("suggestion")
            })
        
        # Add general recommendations
        new_count = len(objects_data.get("new_objects", []))
        modified_count = len(objects_data.get("modified_objects", []))
        
        if new_count > 0:
            merge_plan["recommendations"].append(f"Add {new_count} new object references")
        
        if modified_count > 0:
            merge_plan["recommendations"].append(
                f"Update {modified_count} existing object references"
            )
        
    except Exception as e:
        merge_plan["status"] = 1
        merge_plan["error"] = f"Error creating merge plan: {str(e)}"
    
    return merge_plan


def generate_page_objects_from_snapshot(xml_file_path: str, page_name: str) -> Dict:
    """
    Generate page object references from an XML object snapshot file.
    
    This function:
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
    result = {
        "status": 0,
        "page_name": page_name,
        "xml_file": xml_file_path,
        "objects_found": 0,
        "pattern_analysis": {},
        "output_strategy": {},
        "files_created": [],
        "summary": ""
    }
    
    try:
        # Step 1: Validate XML file exists
        if not os.path.exists(xml_file_path):
            result["status"] = 1
            result["error"] = f"XML file not found: {xml_file_path}"
            return result
        
        # Step 2: Call parse_object_snapshot to filter XML elements
        from .parse_object_snapshot import parse_object_snapshot, generate_python_names
        
        parsed_objects = parse_object_snapshot(xml_file_path)
        result["objects_found"] = len(parsed_objects)
        
        if not parsed_objects:
            result["status"] = 1
            result["error"] = "No meaningful objects found in XML snapshot"
            return result
        
        # Step 3: Get cached context to understand existing patterns and locations
        # Import context functions to avoid recursive MCP calls
        from context import (
            get_test_format_context,
            get_object_reference_context,
            get_global_script_context,
            get_squish_api_context,
            get_squish_rules_context,
            get_bdd_context,
            get_bdd_documentation_context
        )
        
        # Build context data directly without MCP recursion
        # print(f"Test Format Context: {get_test_format_context()}")
        # print(f"Obj Ref Context: {get_object_reference_context()}")
        # print(f"Rules Context: {get_squish_rules_context()}")
        
        # Call analyze_object_references directly instead of cached version
        from context.squish_context_init import analyze_object_references
        print("About to call analyze_object_references() directly", flush=True)
        obj_ref_context = analyze_object_references()
        print(f"Got obj_ref_context: status={obj_ref_context.get('status')}", flush=True)
        # test_format_context = get_test_format_context()
        # global_script_context = get_global_script_context()

        context_data = {
            # "test_format_context": test_format_context,
            "object_reference_context": obj_ref_context,
            # "global_script_context": global_script_context,
            # "squish_api_context": get_squish_api_context(),
            "squish_rules_context": get_squish_rules_context(),
        }
        print("Built context_data successfully", flush=True)
        
        # Step 4: Analyze existing object reference patterns and determine strategy
        print("About to call analyze_object_reference_patterns", flush=True)
        print(f"Object context has global_object_files: {len(obj_ref_context.get('analysis', {}).get('locations', {}).get('global_object_files', []))}")
        
        result["pattern_analysis"] = analyze_object_reference_patterns(context_data)
        print("Completed analyze_object_reference_patterns", flush=True)
        print(f"Pattern analysis result: {result['pattern_analysis']}", flush=True)
        
        print("About to call determine_output_strategy_from_patterns", flush=True)
        result["output_strategy"] = determine_output_strategy_from_patterns(
            result["pattern_analysis"], page_name
        )
        print("Completed determine_output_strategy_from_patterns", flush=True)
        
        # Step 5: Generate object definitions in the appropriate format
        if result["output_strategy"]["format"] == "pom_class":
            # Generate POM class-based objects
            file_content = generate_pom_class_content(
                parsed_objects, page_name, result["output_strategy"]
            )
        elif result["output_strategy"]["format"] == "function_based":
            # Generate function-based objects
            file_content = generate_function_based_content(
                parsed_objects, page_name, result["output_strategy"]
            )
        else:
            # Generate simple dictionary definitions (default)
            python_lines = generate_python_names(parsed_objects)
            file_content = generate_simple_dict_content(
                python_lines, page_name, xml_file_path, result["output_strategy"]
            )
        
        # Step 6: Write to appropriate location based on strategy
        output_files = write_object_files(
            file_content, page_name, result["output_strategy"]
        )
        result["files_created"] = output_files
        
        # Generate summary
        files_summary = ", ".join([os.path.basename(f["path"]) for f in output_files])
        location_type = result["output_strategy"]["location_type"]
        format_type = result["output_strategy"]["format"]
        
        result["summary"] = (
            f"Generated {len(parsed_objects)} object definitions for {page_name} "
            f"in {format_type} format, written to {location_type}: {files_summary}"
        )

        result["object_context": obj_ref_context]
        
    except Exception as e:
        result["status"] = 1
        result["error"] = f"Error generating objects from snapshot: {str(e)}"
        import traceback
        result["traceback"] = traceback.format_exc()
    
    return result


def analyze_object_reference_patterns(context_data: Dict) -> Dict:
    """
    Analyze cached context data to understand existing object reference patterns.
    
    Args:
        context_data: Cached Squish context containing object reference analysis
        
    Returns:
        Dict with pattern analysis results
    """
    analysis = {
        "has_pom_classes": False,
        "has_function_based": False,
        "has_simple_dicts": True,  # Default assumption
        "global_script_locations": [],
        "suite_names_locations": [],
        "preferred_location_type": "suite_names",
        "class_patterns": [],
        "function_patterns": []
    }
    
    try:
        obj_context = context_data.get("object_reference_context", {})
        if obj_context.get("status") == 0:
            obj_analysis = obj_context.get("analysis", {})
            locations = obj_analysis.get("locations", {})
            
            # Analyze global object files
            global_files = locations.get("global_object_files", [])
            for file_info in global_files:
                file_path = file_info.get("file", "")
                analysis["global_script_locations"].append(file_path)
                
                # Check for POM class patterns
                if ("pom" in file_path.lower() or 
                    "object_references" in file_path or
                    "object-references" in file_path or  # Added hyphenated version
                    any("class" in str(obj).lower() for obj in file_info.get("objects", []))):
                    analysis["has_pom_classes"] = True
                    analysis["class_patterns"].append(file_path)
                
                # Check for function-based patterns
                patterns = file_info.get("patterns", [])
                if any("def " in str(pattern) for pattern in patterns):
                    analysis["has_function_based"] = True
                    analysis["function_patterns"].append(file_path)
            
            # Analyze suite names files
            names_files = locations.get("suite_names_files", [])
            for file_info in names_files:
                file_path = file_info.get("file", "")
                analysis["suite_names_locations"].append(file_path)
            
            # Determine preferred location type
            if analysis["has_pom_classes"] and analysis["global_script_locations"]:
                analysis["preferred_location_type"] = "global_pom"
            elif analysis["has_function_based"] and analysis["global_script_locations"]:
                analysis["preferred_location_type"] = "global_functions"
            elif analysis["global_script_locations"]:
                analysis["preferred_location_type"] = "global_simple"
            else:
                analysis["preferred_location_type"] = "suite_names"
                
    except Exception as e:
        print(f"Warning: Error analyzing object patterns: {e}")
        # Keep default values
    
    return analysis


def determine_output_strategy_from_patterns(pattern_analysis: Dict, page_name: str) -> Dict:
    """
    Determine output strategy based on analyzed patterns.
    
    Args:
        pattern_analysis: Results from pattern analysis
        page_name: Name of the page being processed
        
    Returns:
        Dict with output strategy configuration
    """
    strategy = {
        "format": "simple_dicts",
        "location_type": "suite_names",
        "target_directory": None,
        "file_structure": "single_file",
        "class_name": None,
        "imports": ["from objectmaphelper import *"]
    }
    
    location_type = pattern_analysis.get("preferred_location_type", "suite_names")
    
    if location_type == "global_pom":
        strategy.update({
            "format": "pom_class",
            "location_type": "global_scripts",
            "file_structure": "multi_file",
            "class_name": f"{page_name.replace('-', '_').replace(' ', '_').title()}_Objects"
        })
        # Use first global script location as base
        global_locations = pattern_analysis.get("global_script_locations", [])
        if global_locations:
            base_dir = os.path.dirname(global_locations[0])
            strategy["target_directory"] = os.path.join(base_dir, f"{page_name.lower().replace(' ', '-')}-pom")
        
    elif location_type == "global_functions":
        strategy.update({
            "format": "function_based",
            "location_type": "global_scripts",
            "file_structure": "single_file"
        })
        global_locations = pattern_analysis.get("global_script_locations", [])
        if global_locations:
            base_dir = os.path.dirname(global_locations[0])
            strategy["target_directory"] = base_dir
        
    elif location_type == "global_simple":
        strategy.update({
            "format": "simple_dicts",
            "location_type": "global_scripts"
        })
        global_locations = pattern_analysis.get("global_script_locations", [])
        if global_locations:
            base_dir = os.path.dirname(global_locations[0])
            strategy["target_directory"] = base_dir
    
    else:  # suite_names
        strategy.update({
            "format": "simple_dicts",
            "location_type": "suite_names"
        })
        suite_locations = pattern_analysis.get("suite_names_locations", [])
        if suite_locations:
            strategy["target_directory"] = os.path.dirname(suite_locations[0])
    
    # Fallback directory if none determined
    if not strategy["target_directory"]:
        strategy["target_directory"] = os.getcwd()
    
    return strategy


def generate_pom_class_content(parsed_objects: List[Dict], page_name: str, strategy: Dict) -> Dict:
    """
    Generate POM class-based content.
    
    Args:
        parsed_objects: Filtered objects from parse_object_snapshot
        page_name: Name of the page
        strategy: Output strategy configuration
        
    Returns:
        Dict with file contents for POM structure
    """
    class_name = strategy["class_name"]
    
    # Generate object_references.py content
    object_refs_lines = [
        f"# {page_name} Page Object References",
        "# encoding: UTF-8",
        "# Generated by Squish MCP POM Generator",
        "",
        "from objectmaphelper import *",
        "",
        f"class {class_name}():",
        '    """',
        f"    Object references for {page_name} page.",
        '    Contains static methods that return Squish object references.',
        '    """',
        ""
    ]
    
    # Generate methods for each object
    for obj in sorted(parsed_objects, key=lambda x: x.get('var_name', '')):
        from .parse_object_snapshot import _create_object_dict
        obj_dict = _create_object_dict(obj)
        
        method_name = variable_to_method_name(obj.get('var_name', ''))
        
        # Format the object definition
        props = []
        for key, value in obj_dict.items():
            if isinstance(value, str):
                props.append(f'"{key}": "{value}"')
            elif isinstance(value, bool):
                props.append(f'"{key}": {str(value).lower()}')
            else:
                props.append(f'"{key}": {value}')
        
        props_str = ", ".join(props)
        
        object_refs_lines.extend([
            "    @staticmethod",
            f"    def {method_name}():",
            f'        """Return {obj.get("type", "object")} object reference."""',
            f"        return waitForObject({{{props_str}}})",
            ""
        ])
    
    return {
        "object_references.py": "\n".join(object_refs_lines)
    }


def generate_function_based_content(parsed_objects: List[Dict], page_name: str, strategy: Dict) -> Dict:
    """
    Generate function-based content.
    
    Args:
        parsed_objects: Filtered objects from parse_object_snapshot
        page_name: Name of the page
        strategy: Output strategy configuration
        
    Returns:
        Dict with file content
    """
    safe_page_name = page_name.lower().replace(' ', '_').replace('-', '_')
    
    lines = [
        f"# {page_name} Page Object Functions",
        "# encoding: UTF-8",
        "# Generated by Squish MCP POM Generator",
        "",
        "from objectmaphelper import *",
        ""
    ]
    
    # Generate function for each object
    for obj in sorted(parsed_objects, key=lambda x: x.get('var_name', '')):
        from .parse_object_snapshot import _create_object_dict
        obj_dict = _create_object_dict(obj)
        
        func_name = variable_to_method_name(obj.get('var_name', ''))
        
        # Format the object definition
        props = []
        for key, value in obj_dict.items():
            if isinstance(value, str):
                props.append(f'"{key}": "{value}"')
            elif isinstance(value, bool):
                props.append(f'"{key}": {str(value).lower()}')
            else:
                props.append(f'"{key}": {value}')
        
        props_str = ", ".join(props)
        
        lines.extend([
            f"def {func_name}():",
            f'    """Return {obj.get("type", "object")} object reference."""',
            f"    return waitForObject({{{props_str}}})",
            ""
        ])
    
    return {
        f"{safe_page_name}_objects.py": "\n".join(lines)
    }


def generate_simple_dict_content(python_lines: List[str], page_name: str, xml_file_path: str, strategy: Dict) -> Dict:
    """
    Generate simple dictionary definitions content.
    
    Args:
        python_lines: Generated Python object definition lines
        page_name: Name of the page
        xml_file_path: Path to source XML file
        strategy: Output strategy configuration
        
    Returns:
        Dict with file content
    """
    safe_page_name = page_name.lower().replace(' ', '_').replace('-', '_')
    
    lines = [
        f"# {page_name} Page Object Definitions",
        "# encoding: UTF-8",
        f"# Generated from: {os.path.basename(xml_file_path)}",
        "# Generated by: Squish MCP POM Generator",
        "",
        "from objectmaphelper import *",
        "",
        "# Main application container",
        'antares_Cluster_QQuickWindowQmlImpl = {"title": "Antares Cluster", "type": "QQuickWindowQmlImpl", "unnamed": 1, "visible": True}',
        "",
        f"# {page_name} page objects",
    ]
    
    lines.extend(python_lines)
    
    return {
        f"{safe_page_name}_objects.py": "\n".join(lines)
    }


def write_object_files(file_content: Dict, page_name: str, strategy: Dict) -> List[Dict]:
    """
    Write object files to appropriate locations.
    
    Args:
        file_content: Dict of filename -> content
        page_name: Name of the page
        strategy: Output strategy configuration
        
    Returns:
        List of created file information
    """
    created_files = []
    target_dir = strategy["target_directory"]
    
    # Ensure target directory exists
    if not os.path.exists(target_dir):
        os.makedirs(target_dir, exist_ok=True)
    
    for filename, content in file_content.items():
        file_path = os.path.join(target_dir, filename)
        
        # Create backup if file exists
        if os.path.exists(file_path):
            backup_path = f"{file_path}.backup"
            import shutil
            shutil.copy2(file_path, backup_path)
        
        # Write the file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        created_files.append({
            "path": file_path,
            "filename": filename,
            "size": len(content),
            "location_type": strategy["location_type"]
        })
    
    return created_files


def variable_to_method_name(var_name: str) -> str:
    """
    Convert variable name to camelCase method name.
    
    Args:
        var_name: Variable name to convert
        
    Returns:
        camelCase method name
    """
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