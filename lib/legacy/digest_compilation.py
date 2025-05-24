#!/usr/bin/env python
"""
DEPRECATED: This file has been split into session_digest.py and campaign_knowledge.py
This file remains for backwards compatibility but will be removed in a future version.
"""

# Import all functions from the new modules to maintain backwards compatibility
from ..content.session_digest import (
    get_slice_content,
    get_session_slices,
    combine_slice_contents,
    process_combined_slices,
    combine_session_slices,
    process_all_sessions_to_digests
)

from ..content.campaign_knowledge import update_campaign_knowledge

# Maintain the original interface but print a deprecation warning
import warnings

def _deprecated_function_warning(func_name: str):
    warnings.warn(
        f"digest_compilation.{func_name} is deprecated. "
        f"Use session_digest.{func_name} or campaign_knowledge.{func_name} instead.",
        DeprecationWarning,
        stacklevel=3
    )



