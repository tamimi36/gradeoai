# Application config
import os
from dotenv import load_dotenv


class Config:
    GEMINI_API_KEY = ""
    GEMINI_MODEL = 'gemini-2.0-flash'
    
    # OpenAI API for image generation (not needed anymore)
    OPENAI_API_KEY = ""
    
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    ALLOWED_PDF_EXTENSIONS = {'pdf'}
    
    # ============ Open-Ended Grading Configuration ============
    
    # Criteria weights (must sum to 1.0)
    OPEN_ENDED_CRITERIA = {
        'core_concept': {
            'weight': 0.40,
            'description': 'Correct understanding of main concept'
        },
        'logical_explanation': {
            'weight': 0.30,
            'description': 'Clear reasoning and logical flow'
        },
        'key_terms': {
            'weight': 0.20,
            'description': 'Use of teacher-specified keywords'
        },
        'clarity_structure': {
            'weight': 0.10,
            'description': 'Well-organized and clear writing'
        }
    }
    
    # Status scores
    OPEN_ENDED_STATUS_SCORES = {
        'full': 1.0,      # Fully present
        'partial': 0.5,   # Partially present
        'absent': 0.0     # Not present
    }
    
    # Number of grading passes for consistency
    OPEN_ENDED_GRADING_PASSES = 3
    
    # ============ Definition Grading Configuration ============
    
    # Meaning units for definition grading (must sum to 1.0)
    DEFINITION_CRITERIA = {
        'core_concept': {
            'weight': 0.50,
            'description': 'The main/essential meaning of the term'
        },
        'required_properties': {
            'weight': 0.30,
            'description': 'Key ideas/words set by the teacher'
        },
        'scope_context': {
            'weight': 0.20,
            'description': 'Correct scope, context, or application'
        }
    }
    
    # Status scores for definition (same as open-ended)
    DEFINITION_STATUS_SCORES = {
        'present': 1.0,    # Fully present
        'partial': 0.5,    # Partially present
        'absent': 0.0      # Not present
    }
    
    @classmethod
    def get_definition_criteria_names(cls):
        return list(cls.DEFINITION_CRITERIA.keys())
    
    @classmethod
    def get_definition_criteria_weight(cls, criterion):
        return cls.DEFINITION_CRITERIA.get(criterion, {}).get('weight', 0)
    
    @classmethod
    def get_allowed_extensions(cls):
        return cls.ALLOWED_IMAGE_EXTENSIONS | cls.ALLOWED_PDF_EXTENSIONS
    
    @classmethod
    def get_criteria_names(cls):
        return list(cls.OPEN_ENDED_CRITERIA.keys())
    
    @classmethod
    def get_criteria_weight(cls, criterion):
        return cls.OPEN_ENDED_CRITERIA.get(criterion, {}).get('weight', 0)

