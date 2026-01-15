# Labeling Image grading service using Gemini Vision with multi-pass
import json
import base64
from typing import Dict, Any, List
from collections import Counter
from google import genai

from app.config import Config


class LabelingImageGradingService:
    # Grade labeling questions where students write on the image
    # Uses AI Vision OCR + multi-pass grading for consistency
    
    GRADING_PASSES = 3  # Number of AI passes for consistency
    
    def __init__(self):
        if not Config.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not set")
        self.client = genai.Client(api_key=Config.GEMINI_API_KEY)
    
    def _build_ocr_and_grade_prompt(self, labeling_items: List[Dict[str, Any]]) -> str:
        """Build prompt to OCR handwritten labels AND grade them in one call"""
        
        label_descriptions = []
        for item in labeling_items:
            label_id = item.get('label_id', '')
            pointer_desc = item.get('pointer_description', '')
            correct = item.get('correct_label', '')
            label_descriptions.append(f"""- Label {label_id}: points to {pointer_desc}
    Correct answer: "{correct}" """)
        
        labels_text = "\n".join(label_descriptions)
        
        prompt = f"""Analyze this labeled diagram image. The student has written handwritten labels.

LABELS TO FIND AND GRADE:
{labels_text}

For each label:
1. Read the handwritten text the student wrote
2. Compare it to the correct answer
3. Assign a status:
   - "present": Answer is correct or equivalent (synonyms, minor spelling ok)
   - "partial": Partially correct, shows some understanding
   - "absent": Wrong, missing, empty, or unreadable

Return ONLY valid JSON:
{{
    "labels": [
        {{"label_id": "1", "student_text": "what student wrote", "status": "present", "reason": "brief explanation"}},
        {{"label_id": "2", "student_text": "what student wrote", "status": "partial", "reason": "brief explanation"}},
        {{"label_id": "3", "student_text": "", "status": "absent", "reason": "label was empty"}}
    ]
}}

Include an entry for EVERY label number specified above."""
        return prompt
    
    def _call_gemini_vision(self, image_data: str, prompt: str) -> Dict[str, Any]:
        """Call Gemini Vision with image and prompt"""
        try:
            # Handle base64 image data
            if image_data.startswith('data:'):
                parts = image_data.split(',', 1)
                if len(parts) == 2:
                    image_bytes = base64.b64decode(parts[1])
                else:
                    return {"error": "Invalid data URL", "labels": []}
            else:
                image_bytes = base64.b64decode(image_data)
            
            response = self.client.models.generate_content(
                model=Config.GEMINI_MODEL,
                contents=[
                    {
                        "parts": [
                            {"text": prompt},
                            {
                                "inline_data": {
                                    "mime_type": "image/jpeg",
                                    "data": base64.b64encode(image_bytes).decode()
                                }
                            }
                        ]
                    }
                ],
                config={
                    "response_mime_type": "application/json"
                }
            )
            return json.loads(response.text)
        except Exception as e:
            return {"error": str(e), "labels": []}
    
    def _calculate_mode_or_median(self, statuses: List[str]) -> tuple:
        """Calculate mode, or median if all different. Returns (status, flag_for_review)"""
        STATUS_ORDER = {'absent': 0, 'partial': 1, 'present': 2}
        
        counts = Counter(statuses)
        most_common = counts.most_common()
        
        if most_common[0][1] > 1:
            return most_common[0][0], False
        
        sorted_statuses = sorted(statuses, key=lambda s: STATUS_ORDER.get(s, 1))
        median_status = sorted_statuses[len(sorted_statuses) // 2]
        return median_status, True
    
    def grade_question(self, question: Dict[str, Any], 
                       answer_image: str) -> Dict[str, Any]:
        """Grade a single labeling question from image with multi-pass"""
        
        labeling_items = question.get('labeling_items', [])
        q_points = question.get('points', len(labeling_items))
        q_num = question.get('question_number', '')
        
        if not labeling_items:
            return {
                'question_number': q_num,
                'error': 'No labeling_items provided',
                'status': 'error'
            }
        
        if not answer_image:
            # No image = all labels absent
            label_results = []
            for item in labeling_items:
                label_results.append({
                    'label_id': item.get('label_id', ''),
                    'pointer_description': item.get('pointer_description', ''),
                    'student_text': '',
                    'correct_label': item.get('correct_label', ''),
                    'status': 'absent',
                    'reason': 'No image provided',
                    'flag_for_review': False
                })
            return {
                'question_number': q_num,
                'question_type': 'labeling_image',
                'ocr_status': 'no_image',
                'total_labels': len(labeling_items),
                'present': 0,
                'partial': 0,
                'absent': len(labeling_items),
                'flagged_for_review': 0,
                'points_earned': 0,
                'points_possible': q_points,
                'grading_passes': self.GRADING_PASSES,
                'label_details': label_results
            }
        
        # Run grading multiple passes (OCR + grade in one call)
        all_passes = []
        prompt = self._build_ocr_and_grade_prompt(labeling_items)
        
        for _ in range(self.GRADING_PASSES):
            result = self._call_gemini_vision(answer_image, prompt)
            if 'labels' in result:
                all_passes.append(result['labels'])
        
        if not all_passes:
            return {
                'question_number': q_num,
                'error': 'All grading passes failed',
                'status': 'ocr_error'
            }
        
        # Calculate final status for each label using mode/median
        label_results = []
        points_per_label = q_points / len(labeling_items) if labeling_items else 1.0
        earned_points = 0.0
        present_count = 0
        partial_count = 0
        absent_count = 0
        flagged_count = 0
        
        for item in labeling_items:
            label_id = str(item.get('label_id', ''))
            correct = item.get('correct_label', '')
            pointer = item.get('pointer_description', '')
            
            # Collect statuses and texts from all passes
            statuses = []
            student_texts = []
            reasons = []
            
            for pass_labels in all_passes:
                for pl in pass_labels:
                    if str(pl.get('label_id', '')) == label_id:
                        statuses.append(pl.get('status', 'absent'))
                        student_texts.append(pl.get('student_text', ''))
                        reasons.append(pl.get('reason', ''))
                        break
            
            if not statuses:
                statuses = ['absent']
                student_texts = ['']
                reasons = ['No grading result']
            
            # Get final status
            final_status, flag_for_review = self._calculate_mode_or_median(statuses)
            
            # Use most common student text
            text_counts = Counter(student_texts)
            final_student_text = text_counts.most_common(1)[0][0] if text_counts else ''
            
            # Calculate points
            if final_status == 'present':
                earned_points += points_per_label
                present_count += 1
            elif final_status == 'partial':
                earned_points += points_per_label * 0.5
                partial_count += 1
            else:
                absent_count += 1
            
            if flag_for_review:
                flagged_count += 1
            
            label_results.append({
                'label_id': label_id,
                'pointer_description': pointer,
                'correct_label': correct,
                'student_text': final_student_text,
                'status': final_status,
                'reason': reasons[0] if reasons else '',
                'all_pass_statuses': statuses,
                'flag_for_review': flag_for_review
            })
        
        return {
            'question_number': q_num,
            'question_type': 'labeling_image',
            'ocr_status': 'success',
            'diagram_description': question.get('diagram_description', ''),
            'total_labels': len(labeling_items),
            'present': present_count,
            'partial': partial_count,
            'absent': absent_count,
            'flagged_for_review': flagged_count,
            'points_earned': round(earned_points, 2),
            'points_possible': q_points,
            'grading_passes': self.GRADING_PASSES,
            'label_details': label_results
        }
    
    def grade_questions(self, questions: List[Dict[str, Any]], 
                        student_images: Dict[str, str]) -> Dict[str, Any]:
        """Grade multiple labeling questions from images"""
        
        results = []
        total_earned = 0.0
        total_possible = 0.0
        total_labels = 0
        present_count = 0
        partial_count = 0
        absent_count = 0
        flagged_count = 0
        
        for q in questions:
            q_num = str(q.get('question_number', ''))
            answer_image = student_images.get(q_num, '')
            
            result = self.grade_question(q, answer_image)
            results.append(result)
            
            if 'points_earned' in result:
                total_earned += result['points_earned']
                total_possible += result['points_possible']
                total_labels += result.get('total_labels', 0)
                present_count += result.get('present', 0)
                partial_count += result.get('partial', 0)
                absent_count += result.get('absent', 0)
                flagged_count += result.get('flagged_for_review', 0)
        
        return {
            'question_type': 'labeling_image',
            'total_questions': len(questions),
            'total_labels': total_labels,
            'present': present_count,
            'partial': partial_count,
            'absent': absent_count,
            'flagged_for_review': flagged_count,
            'points_earned': round(total_earned, 2),
            'points_possible': round(total_possible, 2),
            'percentage': round((total_earned / total_possible * 100) if total_possible > 0 else 0, 2),
            'grading_passes_per_question': self.GRADING_PASSES,
            'details': results
        }
