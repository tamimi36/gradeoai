# Compare/Contrast grading service using Gemini AI
import json
from typing import Dict, Any, List
from collections import Counter
from google import genai

from app.config import Config


class CompareContrastGradingService:
    # Grade compare/contrast questions using checklist items and multi-pass grading
    
    def __init__(self):
        if not Config.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not set")
        self.client = genai.Client(api_key=Config.GEMINI_API_KEY)
    
    def _build_grading_prompt(self, student_answer: str, 
                               grading_table: List[Dict[str, Any]]) -> str:
        # Build checklist from grading table
        checklist_items = []
        for i, item in enumerate(grading_table):
            checklist_items.append(f"{i+1}. {item['item']}")
        
        checklist_text = "\n".join(checklist_items)
        
        prompt = f"""You are grading a student's compare/contrast answer.

STUDENT ANSWER:
{student_answer}

For each checklist item below, determine if the student's answer covers it using MEANING-BASED comparison (not exact wording):
- "present": The idea is fully covered in the answer
- "partial": The idea is partially mentioned or implied
- "absent": The idea is not mentioned at all

CHECKLIST ITEMS:
{checklist_text}

Return ONLY valid JSON in this exact format:
{{
    "items": [
        {{"index": 0, "status": "present|partial|absent", "reason": "brief explanation"}},
        {{"index": 1, "status": "present|partial|absent", "reason": "brief explanation"}}
    ]
}}

Include an entry for EVERY checklist item in order."""
        return prompt
    
    def _call_gemini(self, prompt: str) -> Dict[str, Any]:
        # Call Gemini and parse JSON response
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
            return {"error": str(e), "items": []}
    
    def _calculate_mode_or_median(self, statuses: List[str]) -> str:
        # Get mode (most frequent), or median if all different
        counts = Counter(statuses)
        
        # Mode: find status appearing 2+ times
        for status, count in counts.items():
            if count >= 2:
                return status
        
        # Median: order is absent < partial < present
        order = {'absent': 0, 'partial': 1, 'present': 2}
        sorted_statuses = sorted(statuses, key=lambda x: order.get(x, 1))
        return sorted_statuses[len(sorted_statuses) // 2]
    
    def grade_question(self, question: Dict[str, Any], 
                       student_answer: str) -> Dict[str, Any]:
        # Grade a single compare/contrast question
        grading_table = question.get('grading_table', [])
        total_points = question.get('points', 0)
        q_num = question.get('question_number', '')
        
        if not grading_table:
            return {
                'question_number': q_num,
                'error': 'No grading_table provided',
                'status': 'error'
            }
        
        # Calculate points per item if not specified
        for item in grading_table:
            if 'points' not in item:
                item['points'] = total_points / len(grading_table)
        
        if not student_answer or not student_answer.strip():
            # Empty answer = all absent
            item_results = []
            for i, item in enumerate(grading_table):
                item_results.append({
                    'item': item['item'],
                    'status': 'absent',
                    'points_earned': 0,
                    'points_possible': item['points'],
                    'reason': 'No answer provided'
                })
            return {
                'question_number': q_num,
                'student_answer': '',
                'item_results': item_results,
                'grading_passes': 0,
                'flag_for_review': False,
                'high_variance_items': [],
                'points_earned': 0,
                'points_possible': sum(item['points'] for item in grading_table),
                'total_percentage': 0
            }
        
        # Run multiple grading passes
        prompt = self._build_grading_prompt(student_answer, grading_table)
        pass_results = []
        
        for _ in range(Config.OPEN_ENDED_GRADING_PASSES):
            result = self._call_gemini(prompt)
            pass_results.append(result)
        
        # Calculate mode/median for each item and track variance
        final_statuses = []
        high_variance_items = []
        
        for i in range(len(grading_table)):
            statuses = []
            for pr in pass_results:
                items = pr.get('items', [])
                if i < len(items):
                    status = items[i].get('status', 'partial')
                    if status not in ['present', 'partial', 'absent']:
                        status = 'partial'
                    statuses.append(status)
                else:
                    statuses.append('partial')
            
            # Flag if all passes differ (high variance)
            if len(set(statuses)) == len(statuses) and len(statuses) >= 3:
                high_variance_items.append(i)
            
            final_statuses.append(self._calculate_mode_or_median(statuses))
        
        # Calculate scores (CODE, not LLM)
        item_results = []
        total_earned = 0.0
        total_possible = 0.0
        
        for i, item in enumerate(grading_table):
            status = final_statuses[i]
            item_points = item['points']
            
            if status == 'present':
                earned = item_points
            elif status == 'partial':
                earned = item_points * 0.5
            else:
                earned = 0
            
            total_earned += earned
            total_possible += item_points
            
            # Get reason from last pass
            reason = ''
            if pass_results and pass_results[-1].get('items'):
                items = pass_results[-1]['items']
                if i < len(items):
                    reason = items[i].get('reason', '')
            
            item_results.append({
                'item': item['item'],
                'status': status,
                'points_earned': round(earned, 2),
                'points_possible': round(item_points, 2),
                'reason': reason
            })
        
        return {
            'question_number': q_num,
            'student_answer': student_answer[:200] + '...' if len(student_answer) > 200 else student_answer,
            'item_results': item_results,
            'grading_passes': Config.OPEN_ENDED_GRADING_PASSES,
            'flag_for_review': len(high_variance_items) > 0,
            'high_variance_items': high_variance_items,
            'points_earned': round(total_earned, 2),
            'points_possible': round(total_possible, 2),
            'total_percentage': round((total_earned / total_possible * 100) if total_possible > 0 else 0, 2)
        }
    
    def grade_questions(self, questions: List[Dict[str, Any]], 
                        student_answers: Dict[str, str]) -> Dict[str, Any]:
        # Grade multiple compare/contrast questions
        results = []
        total_earned = 0.0
        total_possible = 0.0
        flagged_count = 0
        
        for q in questions:
            q_num = str(q.get('question_number', ''))
            student_answer = student_answers.get(q_num, '')
            
            result = self.grade_question(q, student_answer)
            results.append(result)
            
            if 'points_earned' in result:
                total_earned += result['points_earned']
                total_possible += result['points_possible']
            if result.get('flag_for_review'):
                flagged_count += 1
        
        return {
            'question_type': 'compare_contrast',
            'total_questions': len(questions),
            'grading_passes_per_question': Config.OPEN_ENDED_GRADING_PASSES,
            'flagged_for_review': flagged_count,
            'points_earned': round(total_earned, 2),
            'points_possible': round(total_possible, 2),
            'percentage': round((total_earned / total_possible * 100) if total_possible > 0 else 0, 2),
            'details': results
        }
