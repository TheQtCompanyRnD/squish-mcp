#!/usr/bin/env python3
"""
Parse object_snapshot.xml and generate Python object names for Squish testing.
Improved version that handles duplicates and organizes objects better.
"""

import xml.etree.ElementTree as ET
import re
from collections import defaultdict

def clean_type_name(type_name):
    """Clean and simplify type names for Python variable names."""
    # Remove .ui suffix and QMLTYPE patterns
    cleaned = re.sub(r'\.ui_QMLTYPE_\d+', '', type_name)
    cleaned = re.sub(r'_QMLTYPE_\d+', '', cleaned)
    cleaned = re.sub(r'_QML_\d+', '', cleaned)
    cleaned = re.sub(r'\.ui$', '', cleaned)
    return cleaned

def make_python_var_name(container_prefix, obj_id, obj_type, obj_text=None, occurrence=None):
    """Generate Python variable name following Squish naming conventions."""
    # Base pattern: antares_Cluster_[identifier]_[Type]
    
    # Clean the type name
    clean_type = clean_type_name(obj_type)
    
    # Use ID if available, otherwise use text or type
    if obj_id and obj_id.strip():
        identifier = obj_id
    elif obj_text and obj_text.strip():
        # Clean text for use as identifier
        identifier = re.sub(r'[^\w\s]', '_', str(obj_text))
        identifier = re.sub(r'\s+', '_', identifier)
        identifier = re.sub(r'_+', '_', identifier)
        identifier = identifier.strip('_')
        if len(identifier) > 20:  # Limit length
            identifier = identifier[:20]
    else:
        identifier = clean_type.lower()
    
    # Construct variable name
    var_name = f"{container_prefix}_{identifier}_{clean_type}"
    
    # Add occurrence number if specified
    if occurrence and occurrence > 1:
        var_name += f"_{occurrence}"
    
    # Clean up the variable name
    var_name = re.sub(r'[^\w]', '_', var_name)
    var_name = re.sub(r'_+', '_', var_name)
    var_name = var_name.strip('_')
    
    return var_name

def extract_property_value(element, prop_name):
    """Extract property value from XML element."""
    for prop in element.findall('.//property[@name="{}"]'.format(prop_name)):
        string_elem = prop.find('string')
        if string_elem is not None:
            return string_elem.text
    return None

def parse_object_snapshot(xml_file):
    """Parse the object snapshot XML and extract meaningful objects."""
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
    except Exception as e:
        print(f"Error parsing XML: {e}")
        return []
    
    objects = []
    container_prefix = "antares_Cluster"
    seen_objects = defaultdict(int)  # Track duplicates
    
    def process_element(element, parent_container=None):
        # Extract basic element info
        element_id = element.get('id', '')
        class_name = element.get('class', '')
        simplified_type = element.get('simplifiedType', '')
        
        # Extract properties
        obj_id = extract_property_value(element, 'id')
        obj_text = extract_property_value(element, 'text')
        object_name = extract_property_value(element, 'objectName')
        visible = extract_property_value(element, 'visible')
        
        # Use simplified type if available, otherwise use class
        obj_type = simplified_type if simplified_type else class_name
        
        # Determine container
        if parent_container:
            container = parent_container
        else:
            container = f"{container_prefix}_QQuickWindowQmlImpl"
        
        # Skip objects that are too generic or not useful for testing
        skip_types = {
            'ShaderEffect', 'ShaderEffectSource', 'Item', 'QQuickItem',
            'DesignEffect', 'DesignEffectPrivate', 'DesignLayerBlurPrivate',
            'DesignBackgroundBlurPrivate', 'DesignDropShadowPrivate',
            'DesignInnerShadowPrivate', 'Repeater'
        }
        
        clean_type = clean_type_name(obj_type)
        
        # Only include objects that have meaningful identifiers or are important UI elements
        should_include = (
            (obj_id and obj_id.strip() and len(obj_id.strip()) > 0) or
            (obj_text and obj_text.strip() and len(obj_text.strip()) > 0 and 
             clean_type in {'Text'}) or
            (object_name and object_name.strip() and len(object_name.strip()) > 0) or
            clean_type in {'Rectangle', 'Image', 'Button', 'Slider'} or
            'ui' in obj_type.lower() or
            'comp' in obj_type.lower() or
            'gauge' in obj_type.lower() or
            clean_type.endswith('_ui')
        )
        
        if should_include and clean_type not in skip_types:
            # Create a unique key for deduplication
            if obj_id:
                unique_key = f"{obj_id}_{clean_type}"
            elif obj_text:
                unique_key = f"{obj_text}_{clean_type}"
            else:
                unique_key = f"{clean_type}_{element_id}"
            
            # Track occurrences for duplicate handling
            seen_objects[unique_key] += 1
            occurrence = seen_objects[unique_key]
            
            # Generate Python variable name
            var_name = make_python_var_name(
                container_prefix, obj_id, obj_type, obj_text, 
                occurrence if occurrence > 1 else None
            )
            
            # Create object definition
            obj_def = {
                'var_name': var_name,
                'container': container,
                'id': obj_id,
                'type': clean_type,
                'text': obj_text,
                'object_name': object_name,
                'visible': visible == 'true' if visible else True,
                'element_id': element_id,
                'original_type': obj_type,
                'unique_key': unique_key,
                'occurrence': occurrence
            }
            
            objects.append(obj_def)
            
            # Update container for children if this object has an ID
            if obj_id:
                container = var_name
        
        # Process child elements
        for child in element.findall('element'):
            process_element(child, container if obj_id else parent_container)
    
    # Start processing from root
    for element in root.findall('.//element'):
        process_element(element)
    
    # Remove exact duplicates (same variable name)
    unique_objects = {}
    for obj in objects:
        key = obj['var_name']
        if key not in unique_objects:
            unique_objects[key] = obj
        else:
            # Keep the one with more information
            existing = unique_objects[key]
            if (obj['text'] and not existing['text']) or (obj['id'] and not existing['id']):
                unique_objects[key] = obj
    
    # Final deduplication step: remove objects with identical dictionary representations
    final_objects = _remove_duplicate_definitions(list(unique_objects.values()))
    
    return final_objects

def _remove_duplicate_definitions(objects):
    """
    Remove objects that would generate identical dictionary definitions.
    This ensures no duplicate elements with the exact same dict on the RHS of = operators.
    """
    seen_definitions = set()
    unique_objects = []
    
    for obj in objects:
        # Create the actual dictionary that would be generated
        obj_dict = _create_object_dict(obj)
        
        # Convert to a hashable representation (sorted tuple of items)
        dict_signature = tuple(sorted(obj_dict.items()))
        
        if dict_signature not in seen_definitions:
            seen_definitions.add(dict_signature)
            unique_objects.append(obj)
        else:
            print(f"Removed duplicate definition for: {obj['var_name']}")
    
    return unique_objects

def _create_object_dict(obj):
    """
    Create the actual dictionary representation that would be generated for an object.
    This matches exactly what will appear on the RHS of the = operator.
    """
    obj_dict = {"container": obj["container"]}
    
    if obj['id']:
        obj_dict["id"] = obj["id"]
    
    obj_dict["type"] = obj["type"]
    
    if obj['text']:
        # Use the same escaping as in generate_python_names
        escaped_text = obj['text'].replace('"', '\\"').replace('\n', '\\n')
        obj_dict["text"] = escaped_text
    
    if obj['object_name']:
        obj_dict["objectName"] = obj["object_name"]
    
    # Add occurrence if needed (for text objects without IDs)
    if obj['occurrence'] > 1 and not obj['id']:
        obj_dict["occurrence"] = obj["occurrence"]
    
    obj_dict["unnamed"] = 1
    obj_dict["visible"] = obj["visible"]
    
    return obj_dict

def generate_python_names(objects):
    """Generate Python code for names.py file."""
    lines = []
    
    # Sort objects by variable name for better organization
    objects.sort(key=lambda x: x['var_name'])
    
    # Generate definitions using the same logic as _create_object_dict for consistency
    for obj in objects:
        # Use the same dictionary creation logic to ensure consistency
        obj_dict = _create_object_dict(obj)
        
        # Build properties list from the standardized dictionary
        props = []
        for key, value in obj_dict.items():
            if isinstance(value, str):
                props.append(f'"{key}": "{value}"')
            elif isinstance(value, bool):
                props.append(f'"{key}": {str(value).lower()}')
            else:
                props.append(f'"{key}": {value}')
        
        props_str = ", ".join(props)
        line = f'{obj["var_name"]} = {{{props_str}}}'
        lines.append(line)
    
    return lines

