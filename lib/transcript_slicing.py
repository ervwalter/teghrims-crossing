#!/usr/bin/env python
"""
Functions for slicing transcripts into manageable chunks based on timestamps.
"""

import re
from typing import List, Dict


def slice_transcript(transcript_text: str, slice_minutes: int = 30, overlap_minutes: int = 5) -> List[Dict]:
    """
    Slice a transcript into chunks based on timestamps.
    
    Args:
        transcript_text: The full transcript text
        slice_minutes: Size of each slice in minutes
        overlap_minutes: Overlap between slices in minutes
        
    Returns:
        List of dictionaries containing slice info (start_time, end_time, text)
    """
    # Regular expression to find timestamps in the format [HH:MM:SS]
    timestamp_pattern = r'\[(\d{2}):(\d{2}):(\d{2})\]'
    
    # Find all timestamps in the transcript
    matches = list(re.finditer(timestamp_pattern, transcript_text))
    
    if not matches:
        # If no timestamps found, return the entire transcript as one slice
        return [{
            "start_time": "00:00:00",
            "end_time": "Unknown",
            "text": transcript_text
        }]
    
    # Convert slice and overlap times to seconds
    slice_seconds = slice_minutes * 60
    overlap_seconds = overlap_minutes * 60
    step_seconds = slice_seconds - overlap_seconds
    
    # Get the last timestamp to determine the end of the transcript
    last_match = matches[-1]
    last_hours = int(last_match.group(1))
    last_minutes = int(last_match.group(2))
    last_seconds = int(last_match.group(3))
    last_total_seconds = last_hours * 3600 + last_minutes * 60 + last_seconds
    
    # Create slices
    slices = []
    current_start = 0
    
    while current_start <= last_total_seconds:
        current_end = min(current_start + slice_seconds, last_total_seconds + 60)  # Add 60 seconds buffer at the end
        
        # Find the closest timestamp to the start and end times
        start_idx = None
        end_idx = None
        
        for i, match in enumerate(matches):
            hours = int(match.group(1))
            minutes = int(match.group(2))
            seconds = int(match.group(3))
            total_seconds = hours * 3600 + minutes * 60 + seconds
            
            # Find the closest timestamp to the start time
            if total_seconds >= current_start and start_idx is None:
                start_idx = i
            
            # Find the closest timestamp to the end time
            if total_seconds >= current_end and end_idx is None:
                end_idx = i
                break
        
        # If we couldn't find an end index, use the last match
        if end_idx is None:
            end_idx = len(matches) - 1
        
        # If we couldn't find a start index, use the first match
        if start_idx is None:
            start_idx = 0
        
        # Get the text between the start and end timestamps
        if start_idx <= end_idx:
            start_match = matches[start_idx]
            end_match = matches[end_idx]
            
            # Format the start and end times
            start_time = f"{start_match.group(1)}:{start_match.group(2)}:{start_match.group(3)}"
            end_time = f"{end_match.group(1)}:{end_match.group(2)}:{end_match.group(3)}"
            
            # Extract the text for this slice
            if end_idx < len(matches) - 1:
                slice_text = transcript_text[start_match.start():matches[end_idx + 1].start()]
            else:
                slice_text = transcript_text[start_match.start():]
            
            slices.append({
                "start_time": start_time,
                "end_time": end_time,
                "text": slice_text
            })
        
        # Move to the next slice
        current_start += step_seconds
    
    return slices
