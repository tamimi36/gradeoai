import io
import base64
from typing import Dict, Any, List
import requests

from app.services.gemini_ocr import GeminiOCRService
from app.services.annotation_service import AnnotationService
from app.config import Config

class WorkflowService:
    """Orchestrates the full exam processing workflow: 
    OCR (Extract) -> Routing (Grade) -> Annotation (Draw)
    """
    
    def __init__(self):
        self.ocr_service = GeminiOCRService()
        self.annotation_service = AnnotationService()
        # Note: Grading services are typically accessed via internal logic or API calls
        # We will use the service logic directly here for efficiency
        
    def process_full_workflow(self, file_data: bytes, file_name: str, language: str = 'english') -> Dict[str, Any]:
        # Step 1: Run OCR to get structured data and student answers
        file_ext = file_name.rsplit('.', 1)[1].lower() if '.' in file_name else 'png'
        
        if file_ext == 'pdf':
            ocr_result = self.ocr_service.process_pdf(file_data, language)
        else:
            ocr_result = self.ocr_service.process_image(file_data, language)
            
        questions = ocr_result.get('structured_data', {}).get('questions', [])
        
        # Step 2: Route each question to the appropriate grading logic
        # For simplicity in this workflow, we'll collect the questions and 
        # call the grading endpoints internally or use a unified grading mapping
        
        grading_results = []
        total_earned = 0
        total_possible = 0
        
        # Mapping question types to grading logic
        from app.services.math_grading import MathGradingService
        from app.services.labeling_image_grading import LabelingImageGradingService
        
        math_service = MathGradingService()
        labeling_img_service = LabelingImageGradingService()
        
        for q in questions:
            q_type = q.get('question_type')
            q_num = q.get('question_number')
            student_answer = q.get('student_answer')
            correct_answer = q.get('correct_answer')
            points = q.get('points', 1.0)
            
            grade_item = {
                'question_number': q_num,
                'question_type': q_type,
                'points_possible': points,
                'points_earned': 0,
                'correct': False
            }
            
            # Simplified grading logic for workflow (usually this calls other services)
            if q_type == 'multiple_choice' or q_type == 'true_false':
                if str(student_answer).strip().upper() == str(correct_answer).strip().upper():
                    grade_item['points_earned'] = points
                    grade_item['correct'] = True
            
            elif q_type == 'math_equation':
                math_result = math_service.grade_math_equation(
                    q.get('math_content', ''),
                    str(student_answer),
                    str(correct_answer),
                    points
                )
                grade_item['points_earned'] = math_result.get('points_earned', 0)
                grade_item['correct'] = math_result.get('is_correct', False)
                grade_item['feedback'] = math_result.get('feedback')
                
            elif q_type == 'open_ended':
                # For open-ended, we'd normally call AI grading (3-pass)
                # For the workflow demo, we'll do a simple keyword match or basic AI call
                # (Skipping full 3-pass here for speed, but real production would use it)
                if any(kw.lower() in str(student_answer).lower() for kw in q.get('expected_keywords', [])):
                    grade_item['points_earned'] = points
                    grade_item['correct'] = True
            
            else:
                # Default: exact match for others
                if str(student_answer).strip().lower() == str(correct_answer).strip().lower():
                    grade_item['points_earned'] = points
                    grade_item['correct'] = True
            
            grading_results.append(grade_item)
            total_earned += grade_item['points_earned']
            total_possible += grade_item['points_possible']
            
        summary = {
            'questions': grading_results,
            'total_earned': total_earned,
            'total_possible': total_possible,
            'percentage': (total_earned / total_possible * 100) if total_possible > 0 else 0
        }
        
        # Step 3: Run Annotation on the original file
        annotation_result = self.annotation_service.annotate_exam(
            file_data, 
            'pdf' if file_ext == 'pdf' else 'image',
            summary
        )
        
        return {
            'success': True,
            'ocr_data': ocr_result,
            'grading_summary': summary,
            'annotation_output': annotation_result
        }
