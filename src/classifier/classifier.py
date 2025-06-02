from werkzeug.datastructures import FileStorage
from src.classifier.file_type_handling import classify_file as process_file

def classify_file(file: FileStorage, industry: str = 'finance') -> dict:
    """
    Main document classification function
    
    Args:
        file: FileStorage object containing the document
        industry: Industry context for classification categories
        
    Returns:
        Classification result dictionary
    """
    return process_file(file, industry)
