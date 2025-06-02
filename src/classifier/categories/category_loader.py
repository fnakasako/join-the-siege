"""
Utility functions for working w/ {industry: [categories]} dictionary found in the 
pre-processing subdirectory json file.

To extend the classifier to new industries, just add a new industry and its
categories to the 'industry_categories.json' file.
"""

import json
import os
from typing import List, Dict
from pathlib import Path

# Path to the categories JSON file
CATEGORIES_FILE = Path(__file__).parent / "industry_categories.json"

class CategoryLoader:
    """Loads and manages industry-specific document categories"""
    
    def __init__(self):
        self._categories_cache = None
        self._load_categories()
    
    def _load_categories(self) -> None:
        """Load categories from JSON file with error handling"""
        try:
            with open(CATEGORIES_FILE, 'r', encoding='utf-8') as f:
                self._categories_cache = json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Categories file not found: {CATEGORIES_FILE}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in categories file: {e}")
        except Exception as e:
            raise RuntimeError(f"Failed to load categories: {e}")
    
    def get_categories_for_industry(self, industry: str) -> List[str]:
        """
        Get document categories for a specific industry
        
        Args:
            industry: Industry name (e.g., 'finance', 'legal', 'healthcare')
            
        Returns:
            List of document categories for the industry
            
        Example:
            >>> loader = CategoryLoader()
            >>> categories = loader.get_categories_for_industry('finance')
            >>> print(categories)
            ['invoice', 'bank_statement', 'financial_report', ...]
        """
        if not self._categories_cache:
            self._load_categories()
        
        industry_lower = industry.lower()
        
        # Return specific industry categories if available
        if industry_lower in self._categories_cache:
            return self._categories_cache[industry_lower].copy()
        
        # Fallback to default categories
        return self._categories_cache.get('default', ['unknown']).copy()
    
    def get_all_industries(self) -> List[str]:
        """
        Get list of all available industries
        
        Returns:
            List of industry names
        """
        if not self._categories_cache:
            self._load_categories()
        
        return [industry for industry in self._categories_cache.keys() if industry != 'default']
    


# Global instance for easy access
_category_loader = CategoryLoader()

# Convenience functions for direct access
def get_categories_for_industry(industry: str) -> List[str]:
    """
    Get document categories for a specific industry
    
    Args:
        industry: Industry name (e.g., 'finance', 'legal', 'healthcare')
        
    Returns:
        List of document categories for the industry
        
    Example:
        >>> categories = get_categories_for_industry('finance')
        >>> print(categories)
        ['invoice', 'bank_statement', 'financial_report', ...]
    """
    return _category_loader.get_categories_for_industry(industry)

def get_all_industries() -> List[str]:
    """Get list of all available industries"""
    return _category_loader.get_all_industries()