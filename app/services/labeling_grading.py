# Labeling grading service using AI multi-pass for consistency
import json
from typing import Dict, Any, List
from collections import Counter
from google import genai

from app.config import Config


class LabelingGradingService:
    # Grade labeling questions (text input) using AI multi-pass grading
    # Returns: present, partial, absent status for each label
    
    GRADING_PASSES = 3  # Number of AI passes for consistency
    
    def __init__(self):
        if not Config.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not set")
        self.client = genai.Client(api_key=Config.GEMINI_API_KEY)
    
    def _build_grading_prompt(self, labeling_items: List[Dict[str, Any]], 
                               student_answers: Dict[str, str]) -> str:
        """Build prompt to grade student labels against correct labels"""
        
        labels_text = []
        for item in labeling_items:
            label_id = item.get('label_id', '')
            correct = item.get('correct_label', '')
            pointer = item.get('pointer_description', '')
            student = student_answers.get(str(label_id), '')
            
            labels_text.append(f"""Label {label_id} ({pointer}):
  - Correct: "{correct}"
  - Student wrote: "{student}" """)
        
        prompt = f"""Grade each label in this diagram labeling question.

LABELS TO GRADE:
{chr(10).join(labels_text)}

For each label, determine the status:
- "present": Student's answer is correct or equivalent (same meaning, minor spelling ok)
- "partial": Student's answer shows partial understanding (partially correct, related term)
- "absent": Student's answer is wrong, missing, or completely unrelated

IMPORTANT:
- Accept synonyms and equivalent terms (e.g., "Left Atrium" = "LA" = "left atrium")
- Minor spelling errors should still be "present" if clearly the right answer
- A partial attempt with some correct elements = "partial"
- Wrong answer or empty = "absent"

Return ONLY valid JSON:
{{
    "labels": [
        {{"label_id": "1", "status": "present", "reason": "brief explanation"}},
        {{"label_id": "2", "status": "partial", "reason": "brief explanation"}},
        {{"label_id": "3", "status": "absent", "reason": "brief explanation"}}
    ]
}}

Include an entry for EVERY label."""
        return prompt
    
    def _call_gemini(self, prompt: str) -> Dict[str, Any]:
        """Call Gemini and parse JSON response"""
        try:
            response = self.client.models.generate_content(
                model=Config.GEMINI_MODEL,
                contents=[prompt],
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
        
        # If there's a clear mode (count > 1), use it
        if most_common[0][1] > 1:
            return most_common[0][0], False
        
        # All 3 different - use median and flag for review
        sorted_statuses = sorted(statuses, key=lambda s: STATUS_ORDER.get(s, 1))
        median_status = sorted_statuses[len(sorted_statuses) // 2]
        return median_status, True
    
    def grade_question(self, question: Dict[str, Any], 
                       student_answers: Dict[str, str]) -> Dict[str, Any]:
        """Grade a single labeling question with multi-pass AI grading"""
        
        labeling_items = question.get('labeling_items', [])
        q_points = question.get('points', len(labeling_items))
        q_num = question.get('question_number', '')
        
        if not labeling_items:
            return {
                'question_number': q_num,
                'error': 'No labeling_items provided',
                'status': 'error'
            }
        
        # Run grading multiple passes
        all_passes = []
        prompt = self._build_grading_prompt(labeling_items, student_answers)
        
        for _ in range(self.GRADING_PASSES):
            result = self._call_gemini(prompt)
            if 'labels' in result:
                all_passes.append(result['labels'])
        
        if not all_passes:
            return {
                'question_number': q_num,
                'error': 'All grading passes failed',
                'status': 'error'
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
            student = student_answers.get(label_id, '')
            
            # Collect statuses from all passes for this label
            statuses = []
            reasons = []
            for pass_labels in all_passes:
                for pl in pass_labels:
                    if str(pl.get('label_id', '')) == label_id:
                        statuses.append(pl.get('status', 'absent'))
                        reasons.append(pl.get('reason', ''))
                        break
            
            if not statuses:
                statuses = ['absent']
                reasons = ['No grading result']
            
            # Get final status
            final_status, flag_for_review = self._calculate_mode_or_median(statuses)
            
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
                'student_label': student,
                'status': final_status,
                'reason': reasons[0] if reasons else '',
                'all_pass_statuses': statuses,
                'flag_for_review': flag_for_review
            })
        
        return {
            'question_number': q_num,
            'question_type': 'labeling',
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
                        student_answers: Dict[str, Any]) -> Dict[str, Any]:
        """Grade multiple labeling questions"""
        
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
            # Student answers can be nested {q_num: {label_id: text}} or flat {label_id: text}
            q_answers = student_answers.get(q_num, {})
            if not isinstance(q_answers, dict):
                q_answers = {}
            
            result = self.grade_question(q, q_answers)
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
            'question_type': 'labeling',
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
