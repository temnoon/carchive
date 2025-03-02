"""
Operation functions for results buffers.

This module provides utility functions for manipulating buffer contents
and performing operations like filtering, merging, and transforming.
"""

import uuid
from typing import List, Dict, Any, Optional, Union, Set, Tuple

from carchive.buffer.schemas import (
    BufferFilterCriteria, BufferOperationType
)
from carchive.buffer.buffer_manager import BufferManager


def filter_by_role(
    buffer_id: uuid.UUID,
    role: str,
    target_buffer_id: Optional[uuid.UUID] = None
) -> Union[uuid.UUID, int]:
    """
    Filter buffer contents by message role.
    
    Args:
        buffer_id: The UUID of the buffer to filter
        role: The role to filter by (e.g., 'user', 'assistant')
        target_buffer_id: Optional UUID of a target buffer to store results
        
    Returns:
        If target_buffer_id is None, returns a new buffer's UUID
        If target_buffer_id is provided, returns the count of items added
    """
    filter_criteria = BufferFilterCriteria(role=role)
    return BufferManager.filter_buffer(buffer_id, filter_criteria, target_buffer_id)


def filter_by_content(
    buffer_id: uuid.UUID,
    content: str,
    target_buffer_id: Optional[uuid.UUID] = None
) -> Union[uuid.UUID, int]:
    """
    Filter buffer contents by text content.
    
    Args:
        buffer_id: The UUID of the buffer to filter
        content: The text content to search for
        target_buffer_id: Optional UUID of a target buffer to store results
        
    Returns:
        If target_buffer_id is None, returns a new buffer's UUID
        If target_buffer_id is provided, returns the count of items added
    """
    filter_criteria = BufferFilterCriteria(content=content)
    return BufferManager.filter_buffer(buffer_id, filter_criteria, target_buffer_id)


def filter_by_days(
    buffer_id: uuid.UUID,
    days: int,
    target_buffer_id: Optional[uuid.UUID] = None
) -> Union[uuid.UUID, int]:
    """
    Filter buffer contents by age in days.
    
    Args:
        buffer_id: The UUID of the buffer to filter
        days: The maximum age in days
        target_buffer_id: Optional UUID of a target buffer to store results
        
    Returns:
        If target_buffer_id is None, returns a new buffer's UUID
        If target_buffer_id is provided, returns the count of items added
    """
    filter_criteria = BufferFilterCriteria(days=days)
    return BufferManager.filter_buffer(buffer_id, filter_criteria, target_buffer_id)


def filter_by_has_image(
    buffer_id: uuid.UUID,
    has_image: bool,
    target_buffer_id: Optional[uuid.UUID] = None
) -> Union[uuid.UUID, int]:
    """
    Filter buffer contents by presence of images.
    
    Args:
        buffer_id: The UUID of the buffer to filter
        has_image: Whether items should have images (True) or not have images (False)
        target_buffer_id: Optional UUID of a target buffer to store results
        
    Returns:
        If target_buffer_id is None, returns a new buffer's UUID
        If target_buffer_id is provided, returns the count of items added
    """
    filter_criteria = BufferFilterCriteria(has_image=has_image)
    return BufferManager.filter_buffer(buffer_id, filter_criteria, target_buffer_id)


def buffer_intersection(
    buffer_ids: List[uuid.UUID],
    target_buffer_id: Optional[uuid.UUID] = None,
    name: Optional[str] = None
) -> Union[uuid.UUID, int]:
    """
    Create a buffer with items that appear in all specified buffers.
    
    Args:
        buffer_ids: The UUIDs of the buffers to intersect
        target_buffer_id: Optional UUID of a target buffer to store results
        name: Optional name for the new buffer
        
    Returns:
        If target_buffer_id is None, returns a new buffer's UUID
        If target_buffer_id is provided, returns the count of items added
    """
    if len(buffer_ids) < 2:
        raise ValueError("At least two buffers are required for intersection")
        
    # Get all buffer contents as sets of (type, id) tuples
    buffer_item_sets = []
    
    for buffer_id in buffer_ids:
        items = BufferManager.get_buffer_contents_as_dbobjects(buffer_id)
        
        # Create a set of (type, id) tuples to represent the items
        item_set = set()
        for item in items:
            if hasattr(item, 'id'):
                item_type = type(item).__name__
                item_set.add((item_type, str(item.id)))
        
        buffer_item_sets.append(item_set)
    
    # Find the intersection of all sets
    intersection = set.intersection(*buffer_item_sets)
    
    # If no items in common, return empty buffer or 0
    if not intersection:
        if target_buffer_id is None:
            # Create an empty buffer
            buffer_data = BufferManager.create_buffer({
                "name": name or "Intersection",
                "buffer_type": "session",
                "description": f"Intersection of {len(buffer_ids)} buffers (empty result)"
            })
            return buffer_data.id
        else:
            return 0
    
    # Get the first buffer to use as a basis
    source_buffer = BufferManager.get_buffer(buffer_ids[0])
    if not source_buffer:
        raise ValueError(f"Source buffer with ID {buffer_ids[0]} not found")
    
    # Create a map of (type, id) -> item from the first buffer
    item_map = {}
    items = BufferManager.get_buffer_contents_as_dbobjects(buffer_ids[0])
    for item in items:
        if hasattr(item, 'id'):
            item_type = type(item).__name__
            item_map[(item_type, str(item.id))] = item
    
    # Extract the intersecting items
    intersecting_items = [item_map[key] for key in intersection if key in item_map]
    
    # If target buffer specified, add items to it
    if target_buffer_id is not None:
        from carchive.buffer.schemas import BufferItemSchema
        
        # Convert DBObjects to BufferItemSchema
        item_schemas = []
        for obj in intersecting_items:
            item = BufferItemSchema()
            
            # Set the appropriate ID based on object type
            if 'MessageRead' in str(type(obj)):
                item.message_id = obj.id
                # Optionally set conversation_id if available
                if hasattr(obj, 'meta_info') and obj.meta_info and 'conversation_id' in obj.meta_info:
                    item.conversation_id = obj.meta_info['conversation_id']
            elif 'ConversationRead' in str(type(obj)):
                item.conversation_id = obj.id
            elif 'ChunkRead' in str(type(obj)):
                item.chunk_id = obj.id
            elif 'AgentOutputRead' in str(type(obj)):
                item.gencom_id = obj.id
            
            item_schemas.append(item)
        
        # Add items to target buffer
        return BufferManager.add_items_to_buffer(target_buffer_id, item_schemas)
    else:
        # Create a new buffer with the intersecting items
        from carchive.buffer.schemas import BufferCreateSchema, BufferItemSchema, BufferType
        
        # Convert DBObjects to BufferItemSchema
        item_schemas = []
        for obj in intersecting_items:
            item = BufferItemSchema()
            
            # Set the appropriate ID based on object type
            if 'MessageRead' in str(type(obj)):
                item.message_id = obj.id
                # Optionally set conversation_id if available
                if hasattr(obj, 'meta_info') and obj.meta_info and 'conversation_id' in obj.meta_info:
                    item.conversation_id = obj.meta_info['conversation_id']
            elif 'ConversationRead' in str(type(obj)):
                item.conversation_id = obj.id
            elif 'ChunkRead' in str(type(obj)):
                item.chunk_id = obj.id
            elif 'AgentOutputRead' in str(type(obj)):
                item.gencom_id = obj.id
            
            item_schemas.append(item)
        
        buffer_data = BufferCreateSchema(
            name=name or "Intersection",
            buffer_type=BufferType.SESSION,
            description=f"Intersection of {len(buffer_ids)} buffers",
            items=item_schemas
        )
        
        # Create buffer
        buffer = BufferManager.create_buffer(buffer_data)
        return buffer.id


def buffer_union(
    buffer_ids: List[uuid.UUID],
    target_buffer_id: Optional[uuid.UUID] = None,
    name: Optional[str] = None,
    deduplicate: bool = True
) -> Union[uuid.UUID, int]:
    """
    Create a buffer with unique items from all specified buffers.
    
    Args:
        buffer_ids: The UUIDs of the buffers to combine
        target_buffer_id: Optional UUID of a target buffer to store results
        name: Optional name for the new buffer
        deduplicate: Whether to remove duplicate items
        
    Returns:
        If target_buffer_id is None, returns a new buffer's UUID
        If target_buffer_id is provided, returns the count of items added
    """
    # This is essentially the same as merge_buffers with deduplicate=True
    return BufferManager.merge_buffers(
        source_buffer_ids=buffer_ids,
        target_buffer_id=target_buffer_id,
        name=name or "Union",
        deduplicate=deduplicate
    )


def buffer_difference(
    buffer_id: uuid.UUID,
    exclude_buffer_ids: List[uuid.UUID],
    target_buffer_id: Optional[uuid.UUID] = None,
    name: Optional[str] = None
) -> Union[uuid.UUID, int]:
    """
    Create a buffer with items that appear in the first buffer but not in any of the exclude buffers.
    
    Args:
        buffer_id: The UUID of the primary buffer
        exclude_buffer_ids: The UUIDs of buffers whose items should be excluded
        target_buffer_id: Optional UUID of a target buffer to store results
        name: Optional name for the new buffer
        
    Returns:
        If target_buffer_id is None, returns a new buffer's UUID
        If target_buffer_id is provided, returns the count of items added
    """
    # Get primary buffer contents
    primary_items = BufferManager.get_buffer_contents_as_dbobjects(buffer_id)
    
    # Create a set of (type, id) tuples for the primary buffer
    primary_set = set()
    for item in primary_items:
        if hasattr(item, 'id'):
            item_type = type(item).__name__
            primary_set.add((item_type, str(item.id)))
    
    # Create sets for all exclude buffers
    exclude_sets = []
    for exclude_id in exclude_buffer_ids:
        exclude_items = BufferManager.get_buffer_contents_as_dbobjects(exclude_id)
        
        # Create a set of (type, id) tuples
        exclude_set = set()
        for item in exclude_items:
            if hasattr(item, 'id'):
                item_type = type(item).__name__
                exclude_set.add((item_type, str(item.id)))
        
        exclude_sets.append(exclude_set)
    
    # Create the union of all exclude sets
    all_excludes = set().union(*exclude_sets) if exclude_sets else set()
    
    # Find items that are in primary_set but not in all_excludes
    difference = primary_set - all_excludes
    
    # Create a map of (type, id) -> item from the primary buffer
    item_map = {}
    for item in primary_items:
        if hasattr(item, 'id'):
            item_type = type(item).__name__
            item_map[(item_type, str(item.id))] = item
    
    # Extract the difference items
    difference_items = [item_map[key] for key in difference if key in item_map]
    
    # If target buffer specified, add items to it
    if target_buffer_id is not None:
        from carchive.buffer.schemas import BufferItemSchema
        
        # Convert DBObjects to BufferItemSchema
        item_schemas = []
        for obj in difference_items:
            item = BufferItemSchema()
            
            # Set the appropriate ID based on object type
            if 'MessageRead' in str(type(obj)):
                item.message_id = obj.id
                # Optionally set conversation_id if available
                if hasattr(obj, 'meta_info') and obj.meta_info and 'conversation_id' in obj.meta_info:
                    item.conversation_id = obj.meta_info['conversation_id']
            elif 'ConversationRead' in str(type(obj)):
                item.conversation_id = obj.id
            elif 'ChunkRead' in str(type(obj)):
                item.chunk_id = obj.id
            elif 'AgentOutputRead' in str(type(obj)):
                item.gencom_id = obj.id
            
            item_schemas.append(item)
        
        # Add items to target buffer
        return BufferManager.add_items_to_buffer(target_buffer_id, item_schemas)
    else:
        # Create a new buffer with the difference items
        from carchive.buffer.schemas import BufferCreateSchema, BufferItemSchema, BufferType
        
        # Convert DBObjects to BufferItemSchema
        item_schemas = []
        for obj in difference_items:
            item = BufferItemSchema()
            
            # Set the appropriate ID based on object type
            if 'MessageRead' in str(type(obj)):
                item.message_id = obj.id
                # Optionally set conversation_id if available
                if hasattr(obj, 'meta_info') and obj.meta_info and 'conversation_id' in obj.meta_info:
                    item.conversation_id = obj.meta_info['conversation_id']
            elif 'ConversationRead' in str(type(obj)):
                item.conversation_id = obj.id
            elif 'ChunkRead' in str(type(obj)):
                item.chunk_id = obj.id
            elif 'AgentOutputRead' in str(type(obj)):
                item.gencom_id = obj.id
            
            item_schemas.append(item)
        
        buffer_data = BufferCreateSchema(
            name=name or "Difference",
            buffer_type=BufferType.SESSION,
            description=f"Difference between primary buffer and {len(exclude_buffer_ids)} exclude buffers",
            items=item_schemas
        )
        
        # Create buffer
        buffer = BufferManager.create_buffer(buffer_data)
        return buffer.id