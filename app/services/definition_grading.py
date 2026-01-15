# Definition grading service using Gemini AI
import json
from typing import Dict, Any, List
from collections import Counter
from google import genai

from app.config import Config


class DefinitionGradingService:
    # Grade definition questions using meaning units and multi-pass grading
    
    def __init__(self):
        if not Config.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not set")
        self.client = genai.Client(api_key=Config.GEMINI_API_KEY)
    
    def _build_grading_prompt(self, term: str, model_definition: str, 
                               student_answer: str, required_keywords: List[str]) -> str:
        # Build prompt dynamically from config
        criteria_desc = []
        json_template_parts = []
        
        for name, info in Config.DEFINITION_CRITERIA.items():
            weight_pct = int(info['weight'] * 100)
            criteria_desc.append(f"- {name} ({weight_pct}%): {info['description']}")
            json_template_parts.append(f'    "{name}": {{"status": "present|partial|absent", "reason": "brief explanation"}}')
        
        criteria_text = "\n".join(criteria_desc)
        json_template = "{\n" + ",\n".join(json_template_parts) + "\n}"
        keywords_text = ", ".join(required_keywords) if required_keywords else "None specified"
        
        prompt = f"""You are grading a student's definition of the term: "{term}"

MODEL DEFINITION (perfect answer):
{model_definition}

STUDENT'S DEFINITION:
{student_answer}

REQUIRED KEYWORDS/PROPERTIES: {keywords_text}

For each meaning unit below, evaluate if it is PRESENT in the student's answer using SEMANTIC MATCHING (not exact wording):
- "present": The meaning unit is fully conveyed
- "partial": Partially mentioned or implied
- "absent": Not mentioned at all

MEANING UNITS:
{criteria_text}

Return ONLY valid JSON in this exact format:
{json_template}"""
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
            return {
                name: {"status": "partial", "reason": f"Grading error: {str(e)}"}
                for name in Config.get_definition_criteria_names()
            }
    
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
    
    def _calculate_final_scores(self, final_statuses: Dict[str, str], 
                                  max_points: float) -> Dict[str, Any]:
        # Calculate scores from config
        criteria_results = {}
        total_percentage = 0.0
        
        for criterion, status in final_statuses.items():
            weight = Config.get_definition_criteria_weight(criterion)
            status_score = Config.DEFINITION_STATUS_SCORES.get(status, 0.5)
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
    
    def grade_question(self, question: Dict[str, Any], 
                       student_answer: str) -> Dict[str, Any]:
        # Grade a single definition question
        term = question.get('term_to_define', question.get('term', ''))
        model_definition = question.get('model_definition', question.get('model_answer', ''))
        required_keywords = question.get('required_keywords', question.get('expected_keywords', []))
        max_points = question.get('points', 10)
        q_num = question.get('question_number', '')
        
        if not model_definition:
            return {
                'question_number': q_num,
                'error': 'No model_definition provided for comparison',
                'status': 'error'
            }
        
        if not student_answer or not student_answer.strip():
            # Empty answer = all absent
            final_statuses = {name: 'absent' for name in Config.get_definition_criteria_names()}
            result = self._calculate_final_scores(final_statuses, max_points)
            result['question_number'] = q_num
            result['term'] = term
            result['student_answer'] = ''
            result['grading_passes'] = 0
            result['flag_for_review'] = False
            result['high_variance_criteria'] = []
            return result
        
        # Run multiple grading passes
        prompt = self._build_grading_prompt(term, model_definition, student_answer, required_keywords)
        pass_results = []
        
        for _ in range(Config.OPEN_ENDED_GRADING_PASSES):
            result = self._call_gemini(prompt)
            pass_results.append(result)
        
        # Calculate mode/median for each criterion and track variance
        final_statuses = {}
        high_variance_criteria = []
        
        for criterion in Config.get_definition_criteria_names():
            statuses = []
            for pr in pass_results:
                status = pr.get(criterion, {}).get('status', 'partial')
                if status not in ['present', 'partial', 'absent']:
                    status = 'partial'
                statuses.append(status)
            
            # Flag if all 3 passes differ (high variance)
            if len(set(statuses)) == len(statuses) and len(statuses) >= 3:
                high_variance_criteria.append(criterion)
            
            final_statuses[criterion] = self._calculate_mode_or_median(statuses)
        
        # Calculate final scores
        result = self._calculate_final_scores(final_statuses, max_points)
        result['question_number'] = q_num
        result['term'] = term
        result['student_answer'] = student_answer[:200] + '...' if len(student_answer) > 200 else student_answer
        result['grading_passes'] = Config.OPEN_ENDED_GRADING_PASSES
        
        # Add high variance flag
        result['flag_for_review'] = len(high_variance_criteria) > 0
        result['high_variance_criteria'] = high_variance_criteria
        
        # Add reasons from last pass
        for criterion in Config.get_definition_criteria_names():
            if criterion in result['criteria_results'] and criterion in pass_results[-1]:
                result['criteria_results'][criterion]['reason'] = pass_results[-1][criterion].get('reason', '')
        
        return result
    
    def grade_questions(self, questions: List[Dict[str, Any]], 
                        student_answers: Dict[str, str]) -> Dict[str, Any]:
        # Grade multiple definition questions
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
            'question_type': 'definition',
            'total_questions': len(questions),
            'grading_passes_per_question': Config.OPEN_ENDED_GRADING_PASSES,
            'criteria_used': list(Config.DEFINITION_CRITERIA.keys()),
            'flagged_for_review': flagged_count,
            'points_earned': round(total_earned, 2),
            'points_possible': round(total_possible, 2),
            'percentage': round((total_earned / total_possible * 100) if total_possible > 0 else 0, 2),
            'details': results
        }
