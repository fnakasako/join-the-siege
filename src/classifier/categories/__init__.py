"""
Pre-processing module for document classification

This module contains utilities for preprocessing documents and managing
industry-specific classification categories.
"""

from .category_loader import (
    get_categories_for_industry,
    get_all_industries,
    CategoryLoader
)

__all__ = [
    'get_categories_for_industry',
    'get_all_industries', 
    'CategoryLoader'
]
