"""
BP Agent State Definition
"""

from typing import TypedDict, List, Dict, Any, Optional, Annotated
import operator

def merge_list(list1: List[Any], list2: List[Any]) -> List[Any]:
    """Merge two lists."""
    if not list1:
        return list2
    if not list2:
        return list1
    return list1 + list2

class AgentState(TypedDict):
    """
    State for the BP Generation Agent Graph.
    Captures all data flowing through the BP generation process.
    """
    # Input
    business_idea: str
    session_id: Optional[str]  # Primary session identifier (storage-agnostic)
    is_english: bool
    
    # Input Completeness
    input_completeness: Optional[Dict[str, Any]]
    
    # Core Generation Artifacts
    bp_structure: Optional[List[Dict[str, str]]]
    evaluation_result: Optional[Dict[str, Any]]
    
    # Iteration Control
    iteration_count: int
    max_iterations: int
    iteration_history: Annotated[List[Dict[str, Any]], merge_list]
    
    # Production Artifacts
    pitch_result: Optional[Dict[str, Any]]
    ppt_result: Optional[Dict[str, Any]]
    partner_search_result: Optional[Dict[str, Any]]
    html_result: Optional[Dict[str, Any]]  # HTML report generation result
    
    # Intermediate results with markdown summaries
    # Each node can set this field to provide a human-readable markdown summary
    # This field is updated by each node and may be overwritten by subsequent nodes
    markdown_summary: Optional[str]
    
    # File Paths (Output)
    output_file: Optional[str]
    partner_report_file: Optional[str]
    ppt_design_file: Optional[str]
    markdown_content: Optional[str]
    
    # Error handling
    error: Optional[str]

