# Table grading service - same logic as compare/contrast
# Reuses CompareContrastGradingService with output name changed to 'table'
from typing import Dict, Any, List

from app.services.compare_contrast_grading import CompareContrastGradingService


class TableGradingService:
    # Grade table questions using same checklist logic as compare/contrast
    
    def __init__(self):
        # Reuse the compare_contrast service internally
        self.cc_service = CompareContrastGradingService()
    
    def grade_question(self, question: Dict[str, Any], 
                       student_answer: str) -> Dict[str, Any]:
        # Grade using compare_contrast logic, change output name
        result = self.cc_service.grade_question(question, student_answer)
        if 'question_type' in result:
            result['question_type'] = 'table'
        return result
    
    def grade_questions(self, questions: List[Dict[str, Any]], 
                        student_answers: Dict[str, str]) -> Dict[str, Any]:
        # Grade multiple table questions
        result = self.cc_service.grade_questions(questions, student_answers)
        result['question_type'] = 'table'
        return result
