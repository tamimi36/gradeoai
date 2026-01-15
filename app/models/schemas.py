# Pydantic models for OCR structured output
from typing import List, Optional, Dict, Union, Literal, Any
from pydantic import BaseModel, Field


# All supported question types (13 types)
QUESTION_TYPES = Literal[
    'multiple_choice',      # MCQ - الاختيار من متعدد
    'true_false',           # T/F - الصواب والخطأ
    'matching',             # Matching - المزاوجة / التوصيل
    'fill_in_blank',        # Fill blanks - ملء الفراغات
    'ordering',             # Ordering - إعادة الترتيب
    'short_answer',         # Brief factual answers - إجابات قصيرة
    'open_ended',           # Open-ended analytical - أسئلة مفتوحة تحليلية
    'compare_contrast',     # Compare - المقارنة والمقابلة
    'definition',           # Definitions - التعريفات
    'labeling',             # Label diagrams (write/draw on shape) - تحديد الأجزاء على الرسم
    'labeling_image',       # Label diagrams (handwriting on image) - الكتابة على الصورة
    'math_equation',        # Math - معادلات رياضية
    'table'                 # Table questions
]

ANSWER_LENGTH = Literal['short', 'long']


class OrderingItem(BaseModel):
    item_id: str
    content: str
    correct_position: Optional[int] = None


class LabelingItem(BaseModel):
    label_id: str
    pointer_description: str
    correct_label: Optional[str] = None


# SubQuestion class removed - no longer needed


class Question(BaseModel):
    order: int = Field(description="Position in document (1-based)")
    question_number: str = Field(description="Number as shown")
    question_type: QUESTION_TYPES
    question_text: str
    
    # MCQ
    options: Optional[Dict[str, str]] = None
    
    # Fill in blank
    blanks: Optional[List[str]] = None
    
    # Matching
    left_column: Optional[List[Dict[str, str]]] = None
    right_column: Optional[List[Dict[str, str]]] = None
    correct_matches: Optional[Dict[str, str]] = None
    
    # Ordering
    ordering_items: Optional[List[OrderingItem]] = None
    correct_order: Optional[List[str]] = None
    
    # Labeling
    labeling_items: Optional[List[LabelingItem]] = None
    diagram_description: Optional[str] = None
    
    # Compare/Contrast
    compare_items: Optional[List[str]] = None
    comparison_aspects: Optional[List[str]] = None
    
    # Definition
    term_to_define: Optional[str] = None
    
    # Math
    math_content: Optional[str] = None
    
    # Table
    table_headers: Optional[List[str]] = None
    table_rows: Optional[List[List[str]]] = None
    
    # Short answer specific
    expected_answer_count: Optional[int] = Field(default=None, description="Number of items expected (e.g., 'State 4...' = 4)")
    acceptable_answers: Optional[List[str]] = Field(default=None, description="List of acceptable answer variants")
    
    # Open-ended specific (analytical questions only)
    answer_length: Optional[ANSWER_LENGTH] = Field(default=None, description="short (1-3 sentences) or long (paragraph+)")
    
    # Answers
    correct_answer: Optional[Union[str, bool, List[str]]] = None
    student_answer: Optional[Union[str, bool, List[str], Dict[str, Any]]] = Field(default=None, description="What the student wrote/marked on the paper")
    student_markings: Optional[str] = Field(default=None, description="Detailed description of visible student marks (ink color, circle vs cross, etc.)")
    answer_markdown: Optional[str] = None
    expected_keywords: Optional[List[str]] = None
    model_answer: Optional[str] = None
    
    # Grading table for compare_contrast and table questions
    grading_table: Optional[List[Dict[str, Any]]] = None
    
    # Metadata
    points: Optional[float] = None
    instructions: Optional[str] = None


class ExamMetadata(BaseModel):
    exam_title: Optional[str] = None
    subject: Optional[str] = None
    grade_level: Optional[str] = None
    total_questions: Optional[int] = None
    total_points: Optional[float] = None
    duration: Optional[str] = None
    instructions: Optional[str] = None
    date: Optional[str] = None
    student_name_field: Optional[bool] = None
    sections: Optional[List[str]] = None


class StructuredData(BaseModel):
    questions: List[Question]
    metadata: ExamMetadata = Field(default_factory=ExamMetadata)


class OCRResponse(BaseModel):
    extracted_text: str
    structured_data: StructuredData
    confidence_score: float = Field(ge=0.0, le=1.0)


# Legacy models
class MultipleChoiceQuestion(BaseModel):
    question_number: int
    question_text: str
    options: Dict[str, str]
    correct_answer: Optional[str] = None


class TrueFalseQuestion(BaseModel):
    question_number: int
    statement: str
    correct_answer: Optional[bool] = None
