# Math equation grading service using PEMDAS step breakdown
import json
from typing import Dict, Any, List
from collections import Counter
from google import genai

from app.config import Config


class MathGradingService:
    # Grade math equations using PEMDAS step breakdown and multi-pass grading
    
    def __init__(self):
        if not Config.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not set")
        self.client = genai.Client(api_key=Config.GEMINI_API_KEY)
    
    def _to_latex(self, expression: str) -> str:
        # Convert plain math expression to LaTeX format
        if not expression:
            return ''
        latex = expression
        # Replace common math symbols with LaTeX equivalents
        replacements = [
            ('×', r' \times '),
            ('÷', r' \div '),
            ('√', r'\sqrt'),
            ('²', '^{2}'),
            ('³', '^{3}'),
            ('±', r'\pm'),
            ('≠', r'\neq'),
            ('≤', r'\leq'),
            ('≥', r'\geq'),
            ('π', r'\pi'),
        ]
        for plain, tex in replacements:
            latex = latex.replace(plain, tex)
        return f'${latex}$'
    
    def _build_steps_prompt(self, problem: str, correct_answer: str) -> str:
        # Build prompt to generate PEMDAS steps for the problem
        prompt = f"""Analyze this math problem and break it into PEMDAS steps.

PROBLEM: {problem}
FINAL ANSWER: {correct_answer}

PEMDAS ORDER:
1. Parentheses (innermost first, including brackets)
2. Exponents (powers, square roots)
3. Multiplication and Division (left to right)
4. Addition and Subtraction (left to right)

IMPORTANT:
- List ONLY the computational steps, NOT a separate "final answer" step
- The last computational step should naturally produce the final answer
- Example: For "(2+3) × 4 - 6 ÷ 2 = 17", the last step is "20 - 3 = 17" (subtraction)
- Do NOT add a redundant step like "final: 17"

Return ONLY valid JSON:
{{
    "steps": [
        {{"step": 1, "operation": "parentheses", "expression": "(2 + 3) = 5"}},
        {{"step": 2, "operation": "multiplication", "expression": "5 × 4 = 20"}},
        {{"step": 3, "operation": "division", "expression": "6 ÷ 2 = 3"}},
        {{"step": 4, "operation": "subtraction", "expression": "20 - 3 = 17"}}
    ],
    "final_answer": "{correct_answer}"
}}

Include ALL intermediate COMPUTATIONAL steps in order. Use operation types: parentheses, exponent, multiplication, division, addition, subtraction."""
        return prompt
    
    def _build_grading_prompt(self, problem: str, correct_answer: str, 
                               expected_steps: List[Dict], student_work: str) -> str:
        # Build prompt to grade student work against expected steps
        steps_text = "\n".join([
            f"{s['step']}. {s['operation']}: {s['expression']}" 
            for s in expected_steps
        ])
        
        prompt = f"""You are grading a student's math work. Recognize EQUIVALENT approaches.

PROBLEM: {problem}
CORRECT ANSWER: {correct_answer}

EXPECTED STEPS (standard PEMDAS approach):
{steps_text}

STUDENT'S WORK:
{student_work}

GRADING RULES:
1. For each expected step, check if the student demonstrated the SAME MATHEMATICAL RESULT
2. The student may use DIFFERENT ORDER or EQUIVALENT OPERATIONS - this is acceptable if mathematically correct
3. Example: If expected is "6 × 4 = 24" but student wrote "4 × 6 = 24", mark as "present"
4. If student combined steps correctly, give credit for both steps covered
5. Focus on MATHEMATICAL CORRECTNESS, not exact format
6. If the student's final numeric answer matches {correct_answer}, the last step MUST be "present"

STATUS OPTIONS:
- "present": The mathematical result/operation is shown correctly (even if different format)
- "partial": Step attempted but has a calculation error (wrong number)
- "absent": This mathematical operation is not shown anywhere in student's work

CRITICAL: Check if student's final answer is {correct_answer}. If YES, set final_answer_correct=true.

Return ONLY valid JSON:
{{
    "steps": [
        {{"step": 1, "status": "present", "reason": "explanation"}},
        {{"step": 2, "status": "partial", "reason": "explanation"}},
        {{"step": 3, "status": "absent", "reason": "explanation"}}
    ],
    "final_answer_correct": true
}}

Include an entry for EVERY expected step."""
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
            return {"error": str(e), "steps": []}
    
    def _get_expected_steps(self, problem: str, correct_answer: str) -> List[Dict]:
        # Get PEMDAS steps from AI
        prompt = self._build_steps_prompt(problem, correct_answer)
        result = self._call_gemini(prompt)
        return result.get('steps', [])
    
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
                       student_work: str) -> Dict[str, Any]:
        # Grade a single math question
        problem = question.get('math_content', question.get('question_text', ''))
        correct_answer = str(question.get('correct_answer', ''))
        max_points = question.get('points', 10)
        q_num = question.get('question_number', '')
        
        if not problem:
            return {
                'question_number': q_num,
                'error': 'No problem/math_content provided',
                'status': 'error'
            }
        
        if not correct_answer:
            return {
                'question_number': q_num,
                'error': 'No correct_answer provided',
                'status': 'error'
            }
        
        if not student_work or not student_work.strip():
            return {
                'question_number': q_num,
                'problem': problem,
                'student_work': '',
                'final_answer_correct': False,
                'total_steps': 0,
                'step_results': [],
                'grading_passes': 0,
                'flag_for_review': False,
                'high_variance_steps': [],
                'points_earned': 0,
                'points_possible': max_points,
                'total_percentage': 0
            }
        
        # Get expected PEMDAS steps
        expected_steps = self._get_expected_steps(problem, correct_answer)
        
        if not expected_steps:
            return {
                'question_number': q_num,
                'error': 'Could not generate PEMDAS steps',
                'status': 'error'
            }
        
        # Run 3 grading passes
        grading_prompt = self._build_grading_prompt(
            problem, correct_answer, expected_steps, student_work
        )
        pass_results = []
        
        for _ in range(Config.OPEN_ENDED_GRADING_PASSES):
            result = self._call_gemini(grading_prompt)
            pass_results.append(result)
        
        # Calculate mode/median for each step and track variance
        final_statuses = []
        high_variance_steps = []
        final_answer_correct = False
        
        for i in range(len(expected_steps)):
            statuses = []
            for pr in pass_results:
                steps = pr.get('steps', [])
                if i < len(steps):
                    status = steps[i].get('status', 'partial')
                    if status not in ['present', 'partial', 'absent']:
                        status = 'partial'
                    statuses.append(status)
                else:
                    statuses.append('partial')
            
            # Flag if all 3 passes differ
            if len(set(statuses)) == len(statuses) and len(statuses) >= 3:
                high_variance_steps.append(i)
            
            final_statuses.append(self._calculate_mode_or_median(statuses))
        
        # Check final answer from ALL passes and use majority vote
        final_answer_votes = []
        for pr in pass_results:
            final_answer_votes.append(pr.get('final_answer_correct', False))
        
        # Majority vote for final answer correctness
        true_count = sum(1 for v in final_answer_votes if v)
        final_answer_correct = true_count >= 2  # At least 2 out of 3 say correct
        
        # CONSISTENCY FIX: If final answer is correct, ensure last step gets full credit
        # This prevents AI inconsistency from affecting the final score
        if final_answer_correct and final_statuses:
            # Force the last step to 'present' if final answer is correct
            # because arriving at the correct answer means the final computation was done right
            final_statuses[-1] = 'present'
        
        # Calculate scores (CODE, not AI)
        step_results = []
        points_per_step = max_points / len(expected_steps) if expected_steps else 0
        total_earned = 0.0
        
        for i, step in enumerate(expected_steps):
            status = final_statuses[i]
            
            if status == 'present':
                earned = points_per_step
            elif status == 'partial':
                earned = points_per_step * 0.5
            else:
                earned = 0
            
            total_earned += earned
            
            # Get reason from last pass
            reason = ''
            if pass_results and pass_results[-1].get('steps'):
                steps = pass_results[-1]['steps']
                if i < len(steps):
                    reason = steps[i].get('reason', '')
            
            # Convert plain text to LaTeX format
            expression_plain = step['expression']
            expression_latex = self._to_latex(expression_plain)
            
            step_results.append({
                'step': step['step'],
                'operation': step['operation'],
                'expected': expression_plain,
                'expected_latex': expression_latex,
                'status': status,
                'points_earned': round(earned, 2),
                'points_possible': round(points_per_step, 2),
                'reason': reason
            })
        
        # Build feedback text that makes sense for annotation
        # Find first error step and describe it clearly
        annotation_feedback = ""
        detailed_feedback = ""
        
        for sr in step_results:
            if sr['status'] == 'partial':
                # Partial credit - show the step with error
                annotation_feedback = f"Error: {sr['expected']}"
                detailed_feedback = f"Step {sr['step']} ({sr['operation']}): {sr['reason']}"
                break
            elif sr['status'] == 'absent':
                # Missing step - show what was expected
                annotation_feedback = f"Missing: {sr['expected']}"
                detailed_feedback = f"Step {sr['step']} ({sr['operation']}) not shown: {sr['expected']}"
                break
        
        # If all present but final answer wrong
        if not annotation_feedback and not final_answer_correct:
            annotation_feedback = f"Final: {correct_answer}"
            detailed_feedback = f"Work is correct but final answer should be {correct_answer}"
        
        return {
            'question_number': q_num,
            'question_type': 'math_equations',
            'problem': problem,
            'correct_answer': correct_answer,
            'student_work': student_work[:300] + '...' if len(student_work) > 300 else student_work,
            'final_answer_correct': final_answer_correct,
            'total_steps': len(expected_steps),
            'step_results': step_results,
            'grading_passes': Config.OPEN_ENDED_GRADING_PASSES,
            'flag_for_review': len(high_variance_steps) > 0,
            'high_variance_steps': high_variance_steps,
            'points_earned': round(total_earned, 2),
            'points_possible': max_points,
            'total_percentage': round((total_earned / max_points * 100) if max_points > 0 else 0, 2),
            # NEW: Feedback fields for annotation
            'feedback': detailed_feedback,  # Detailed for API response
            'annotation_feedback': annotation_feedback  # Short for image annotation
        }
    
    def grade_questions(self, questions: List[Dict[str, Any]], 
                        student_answers: Dict[str, str]) -> Dict[str, Any]:
        # Grade multiple math questions
        results = []
        total_earned = 0.0
        total_possible = 0.0
        flagged_count = 0
        
        for q in questions:
            q_num = str(q.get('question_number', ''))
            student_work = student_answers.get(q_num, '')
            
            result = self.grade_question(q, student_work)
            results.append(result)
            
            if 'points_earned' in result:
                total_earned += result['points_earned']
                total_possible += result['points_possible']
            if result.get('flag_for_review'):
                flagged_count += 1
        
        return {
            'question_type': 'math_equation',
            'total_questions': len(questions),
            'grading_passes_per_question': Config.OPEN_ENDED_GRADING_PASSES,
            'flagged_for_review': flagged_count,
            'points_earned': round(total_earned, 2),
            'points_possible': round(total_possible, 2),
            'percentage': round((total_earned / total_possible * 100) if total_possible > 0 else 0, 2),
            'details': results
        }
