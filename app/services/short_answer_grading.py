# Short answer grading service using AI multi-pass for consistency
import json
from typing import Dict, Any, List
from collections import Counter
from google import genai

from app.config import Config


class ShortAnswerGradingService:
    """
    Grade short answer questions (brief factual responses).
    Uses 3-pass grading with present/partial/absent status for consistency.
    
    Examples of short answer questions:
    - "State 4 characteristics of..."
    - "What is the capital of...?"
    - "Name the process by which..."
    - "List 3 examples of..."
    """
    
    GRADING_PASSES = 3  # Number of AI passes for consistency
    
    # Criteria for short answer grading
    CRITERIA = {
        'factual_accuracy': {
            'weight': 0.60,
            'description': 'Is the answer factually correct?'
        },
        'completeness': {
            'weight': 0.30,
            'description': 'Are all requested items/parts present?'
        },
        'terminology': {
            'weight': 0.10,
            'description': 'Uses correct/appropriate terms?'
        }
    }
    
    STATUS_SCORES = {
        'present': 1.0,
        'partial': 0.5,
        'absent': 0.0
    }
    
    def __init__(self):
        if not Config.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not set")
        self.client = genai.Client(api_key=Config.GEMINI_API_KEY)
    
    def _build_grading_prompt(self, question: Dict[str, Any], student_answer: str) -> str:
        """Build prompt for grading a short answer question"""
        
        question_text = question.get('question_text', '')
        model_answer = question.get('model_answer', '')
        acceptable_answers = question.get('acceptable_answers', [])
        expected_count = question.get('expected_answer_count', None)
        
        acceptable_text = ", ".join(acceptable_answers) if acceptable_answers else "Not specified"
        count_text = f"Expected {expected_count} items" if expected_count else "Number not specified"
        
        prompt = f"""Grade this SHORT ANSWER question (factual response, not analytical).

QUESTION: {question_text}

MODEL ANSWER: {model_answer if model_answer else "Not provided"}

ACCEPTABLE ANSWERS: {acceptable_text}

{count_text}

STUDENT'S ANSWER: "{student_answer}"

Evaluate each criterion:

1. factual_accuracy (60%): Is the student's answer factually correct?
   - "present": Completely correct facts
   - "partial": Some correct, some wrong or vague
   - "absent": Incorrect or no factual content

2. completeness (30%): Are all requested items present?
   - "present": All items/parts provided
   - "partial": Some items missing
   - "absent": Most or all items missing

3. terminology (10%): Uses correct/appropriate terms?
   - "present": Correct terminology used
   - "partial": Some terms correct, some informal/wrong
   - "absent": No appropriate terms

IMPORTANT: 
- Accept synonyms and equivalent phrasing
- Minor spelling errors are OK if meaning is clear
- Focus on FACTUAL correctness, not writing style

Return ONLY valid JSON:
{{
    "factual_accuracy": {{"status": "present|partial|absent", "reason": "brief explanation"}},
    "completeness": {{"status": "present|partial|absent", "reason": "brief explanation"}},
    "terminology": {{"status": "present|partial|absent", "reason": "brief explanation"}}
}}"""
        return prompt
    
    def _call_gemini(self, prompt: str) -> Dict[str, Any]:
        """Call Gemini and parse JSON response"""
        try:
            response = self.client.models.generate_content(
                model=Config.GEMINI_MODEL,
                contents=[prompt],
                config={"response_mime_type": "application/json"}
            )
            return json.loads(response.text)
        except Exception as e:
            return {
                "factual_accuracy": {"status": "partial", "reason": f"Grading error: {e}"},
                "completeness": {"status": "partial", "reason": f"Grading error: {e}"},
                "terminology": {"status": "partial", "reason": f"Grading error: {e}"}
            }
    
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
    
    def _calculate_scores(self, final_statuses: Dict[str, str], max_points: float) -> Dict[str, Any]:
        """Calculate final scores from statuses"""
        criteria_results = {}
        total_percentage = 0.0
        
        for criterion, status in final_statuses.items():
            weight = self.CRITERIA.get(criterion, {}).get('weight', 0.33)
            status_score = self.STATUS_SCORES.get(status, 0.5)
            criterion_score = status_score * weight
            total_percentage += criterion_score
            
            criteria_results[criterion] = {
                'status': status,
                'weight': weight,
                'score': criterion_score
            }
        
        return {
            'criteria_results': criteria_results,
            'total_percentage': round(total_percentage * 100, 2),
            'points_earned': round(total_percentage * max_points, 2),
            'points_possible': max_points
        }
    
    def grade_question(self, question: Dict[str, Any], student_answer: str) -> Dict[str, Any]:
        """Grade a single short answer question with multi-pass grading"""
        
        q_num = question.get('question_number', '')
        max_points = question.get('points', 5)
        
        if not student_answer or not student_answer.strip():
            # Empty answer = all absent
            final_statuses = {name: 'absent' for name in self.CRITERIA.keys()}
            result = self._calculate_scores(final_statuses, max_points)
            result['question_number'] = q_num
            result['student_answer'] = ''
            result['grading_passes'] = 0
            return result
        
        # Run multiple grading passes
        prompt = self._build_grading_prompt(question, student_answer)
        pass_results = []
        
        for _ in range(self.GRADING_PASSES):
            result = self._call_gemini(prompt)
            pass_results.append(result)
        
        # Calculate mode/median for each criterion
        final_statuses = {}
        high_variance_criteria = []
        
        for criterion in self.CRITERIA.keys():
            statuses = []
            for pr in pass_results:
                status = pr.get(criterion, {}).get('status', 'partial')
                if status not in ['present', 'partial', 'absent']:
                    status = 'partial'
                statuses.append(status)
            
            final_status, flag_for_review = self._calculate_mode_or_median(statuses)
            
            if flag_for_review:
                high_variance_criteria.append(criterion)
            
            final_statuses[criterion] = final_status
        
        # Calculate final scores
        result = self._calculate_scores(final_statuses, max_points)
        result['question_number'] = q_num
        result['question_type'] = 'short_answer'
        result['student_answer'] = student_answer[:200] + '...' if len(student_answer) > 200 else student_answer
        result['grading_passes'] = self.GRADING_PASSES
        result['flag_for_review'] = len(high_variance_criteria) > 0
        result['high_variance_criteria'] = high_variance_criteria
        
        # Add reasons from last pass
        for criterion in self.CRITERIA.keys():
            if criterion in result['criteria_results'] and criterion in pass_results[-1]:
                result['criteria_results'][criterion]['reason'] = pass_results[-1][criterion].get('reason', '')
        
        return result
    
    def grade_questions(self, questions: List[Dict[str, Any]], 
                        student_answers: Dict[str, str]) -> Dict[str, Any]:
        """Grade multiple short answer questions"""
        
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
            'question_type': 'short_answer',
            'total_questions': len(questions),
            'grading_passes_per_question': self.GRADING_PASSES,
            'criteria_used': list(self.CRITERIA.keys()),
            'flagged_for_review': flagged_count,
            'points_earned': round(total_earned, 2),
            'points_possible': round(total_possible, 2),
            'percentage': round((total_earned / total_possible * 100) if total_possible > 0 else 0, 2),
            'details': results
        }
