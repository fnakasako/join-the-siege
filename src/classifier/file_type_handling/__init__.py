"""
File type handling module for document classification

This module contains processors for different file types and utilities
for document conversion and text extraction.
"""

from .file_type_processors import classify_file
from .document_utils import (
    pdf_to_image,
    excel_to_image,
    word_to_image,
    optimize_image_for_llm,
    ocr_extract_text,
    extract_excel_text
)

__all__ = [
    'classify_file',
    'pdf_to_image',
    'excel_to_image', 
    'word_to_image',
    'optimize_image_for_llm',
    'ocr_extract_text',
    'extract_excel_text'
]
