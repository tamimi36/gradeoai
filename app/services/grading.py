# Grading service for MCQ, T/F, Matching, Fill-in-blank, and ordered questions
import re
from typing import List, Dict, Any, Optional


class GradingService:
    # Flexible answer grading with normalization
    
    LETTER_TO_NUMBER = {'a': '1', 'b': '2', 'c': '3', 'd': '4', 'e': '5'}
    NUMBER_TO_LETTER = {'1': 'a', '2': 'b', '3': 'c', '4': 'd', '5': 'e'}
    ARABIC_LETTERS = {'أ': 'a', 'ا': 'a', 'ب': 'b', 'ج': 'c', 'د': 'd', 'ه': 'e'}
    
    @classmethod
    def normalize_answer(cls, answer: Any) -> str:
        # Normalize: lowercase, strip, letter/number mapping
        if answer is None:
            return ""
        
        answer_str = str(answer).strip().lower()
        answer_str = re.sub(r'[.,:;!?\-_()[\]{}]', '', answer_str)
        answer_str = re.sub(r'\s+', ' ', answer_str).strip()
        
        for arabic, latin in cls.ARABIC_LETTERS.items():
            answer_str = answer_str.replace(arabic, latin)
        
        if len(answer_str) == 1 and answer_str in cls.NUMBER_TO_LETTER:
            return cls.NUMBER_TO_LETTER[answer_str]
        
        return answer_str
    
    @classmethod
    def answers_match(cls, student: Any, correct: Any) -> bool:
        # Compare with flexible matching
        if student is None or correct is None:
            return False
        
        norm_student = cls.normalize_answer(student)
        norm_correct = cls.normalize_answer(correct)
        
        if not norm_student or not norm_correct:
            return False
        
        if norm_student == norm_correct:
            return True
        
        # Letter/number equivalence
        if len(norm_student) == 1 and len(norm_correct) == 1:
            s = cls.NUMBER_TO_LETTER.get(norm_student, norm_student)
            c = cls.NUMBER_TO_LETTER.get(norm_correct, norm_correct)
            return s == c
        
        # Boolean matching
        true_vals = {'true', 't', 'yes', 'y', '1', 'صحيح', 'صح', 'vrai', 'oui'}
        false_vals = {'false', 'f', 'no', 'n', '0', 'خطأ', 'خاطئ', 'faux', 'non'}
        
        if norm_student in true_vals and norm_correct in true_vals:
            return True
        if norm_student in false_vals and norm_correct in false_vals:
            return True
        
        return False
    
    def _make_key(self, q_num: str, sub_id: Optional[str] = None) -> str:
        key = str(q_num).strip()
        return f"{key}.{sub_id.strip()}".lower() if sub_id else key.lower()
    
    # ============ Matching Questions ============
    
    def grade_matching(self, questions: List[Dict[str, Any]], 
                       student_answers: Dict[str, Any],
                       points_per_pair: float = 1.0) -> Dict[str, Any]:
        # Grade matching questions
        # student_answers format: {"1": {"1": "a", "2": "b"}} or {"1": "a", "2": "b"}
        results = []
        total_points = 0.0
        earned_points = 0.0
        correct_pairs = 0
        total_pairs = 0
        
        for q in questions:
            q_num = str(q.get('question_number', ''))
            correct_matches = q.get('correct_matches', {})
            q_points = q.get('points', len(correct_matches) * points_per_pair)
            
            # Get student's matches for this question
            if q_num in student_answers:
                student_matches = student_answers[q_num]
                if not isinstance(student_matches, dict):
                    student_matches = {}
            else:
                student_matches = student_answers  # Flat format
            
            pair_results = []
            q_earned = 0.0
            q_correct = 0
            points_each = q_points / len(correct_matches) if correct_matches else points_per_pair
            
            for left_id, correct_right_id in correct_matches.items():
                student_right = student_matches.get(left_id) or student_matches.get(str(left_id))
                is_correct = self.answers_match(student_right, correct_right_id)
                
                total_pairs += 1
                total_points += points_each
                
                if is_correct:
                    q_earned += points_each
                    q_correct += 1
                    correct_pairs += 1
                
                pair_results.append({
                    'left_id': left_id,
                    'student_match': student_right,
                    'correct_match': correct_right_id,
                    'is_correct': is_correct
                })
            
            earned_points += q_earned
            
            results.append({
                'question_number': q_num,
                'question_type': 'matching',
                'total_pairs': len(correct_matches),
                'correct_pairs': q_correct,
                'points_earned': q_earned,
                'points_possible': q_points,
                'pair_details': pair_results
            })
        
        return {
            'question_type': 'matching',
            'total_questions': len(questions),
            'total_pairs': total_pairs,
            'correct_pairs': correct_pairs,
            'incorrect_pairs': total_pairs - correct_pairs,
            'points_earned': earned_points,
            'points_possible': total_points,
            'percentage': (earned_points / total_points * 100) if total_points > 0 else 0,
            'details': results
        }
    
    # ============ Ordering Questions ============
    
    def grade_ordering(self, questions: List[Dict[str, Any]],
                       student_answers: Dict[str, Any],
                       points_per_position: float = 1.0) -> Dict[str, Any]:
        # Grade ordering/sequencing questions
        # student_answers format: {"1": ["C", "A", "B"]} or {"1": "C,A,B"}
        results = []
        total_points = 0.0
        earned_points = 0.0
        correct_positions = 0
        total_positions = 0
        
        for q in questions:
            q_num = str(q.get('question_number', ''))
            correct_order = q.get('correct_order', [])
            q_points = q.get('points', len(correct_order) * points_per_position)
            
            # Get student's answer
            student_order = student_answers.get(q_num) or student_answers.get(q_num.lower())
            
            # Normalize to list
            if student_order is None:
                student_list = []
            elif isinstance(student_order, list):
                student_list = [str(x).strip() for x in student_order]
            elif isinstance(student_order, str):
                # Support comma-separated: "C,A,B" or "C, A, B"
                student_list = [x.strip() for x in student_order.split(',')]
            else:
                student_list = [str(student_order)]
            
            position_results = []
            q_earned = 0.0
            q_correct = 0
            points_each = q_points / len(correct_order) if correct_order else points_per_position
            
            for i, correct_item in enumerate(correct_order):
                student_item = student_list[i] if i < len(student_list) else None
                is_correct = self.answers_match(student_item, correct_item)
                
                total_positions += 1
                total_points += points_each
                
                if is_correct:
                    q_earned += points_each
                    q_correct += 1
                    correct_positions += 1
                
                position_results.append({
                    'position': i + 1,
                    'expected_item': correct_item,
                    'student_item': student_item,
                    'is_correct': is_correct
                })
            
            earned_points += q_earned
            
            results.append({
                'question_number': q_num,
                'question_type': 'ordering',
                'total_positions': len(correct_order),
                'correct_positions': q_correct,
                'points_earned': q_earned,
                'points_possible': q_points,
                'position_details': position_results
            })
        
        return {
            'question_type': 'ordering',
            'total_questions': len(questions),
            'total_positions': total_positions,
            'correct_positions': correct_positions,
            'incorrect_positions': total_positions - correct_positions,
            'points_earned': earned_points,
            'points_possible': total_points,
            'percentage': (earned_points / total_points * 100) if total_points > 0 else 0,
            'details': results
        }
    
    # ============ Labeling (Text Input) ============
    
    def grade_labeling(self, questions: List[Dict[str, Any]],
                       student_answers: Dict[str, Any],
                       points_per_label: float = 1.0) -> Dict[str, Any]:
        # Grade labeling questions (text input - students type in blanks)
        # student_answers format: {"1": {"1": "Left Atrium", "2": "Left Ventricle"}}
        results = []
        total_points = 0.0
        earned_points = 0.0
        correct_labels = 0
        total_labels = 0
        
        for q in questions:
            q_num = str(q.get('question_number', ''))
            labeling_items = q.get('labeling_items', [])
            q_points = q.get('points', len(labeling_items) * points_per_label)
            
            # Get student's labels for this question
            student_labels = student_answers.get(q_num) or student_answers.get(q_num.lower())
            if not isinstance(student_labels, dict):
                student_labels = {}
            
            label_results = []
            q_earned = 0.0
            q_correct = 0
            points_each = q_points / len(labeling_items) if labeling_items else points_per_label
            
            for item in labeling_items:
                label_id = str(item.get('label_id', ''))
                correct_label = item.get('correct_label', '')
                pointer_desc = item.get('pointer_description', '')
                
                student_label = student_labels.get(label_id) or student_labels.get(label_id.lower())
                is_correct = self.answers_match(student_label, correct_label)
                
                total_labels += 1
                total_points += points_each
                
                if is_correct:
                    q_earned += points_each
                    q_correct += 1
                    correct_labels += 1
                
                label_results.append({
                    'label_id': label_id,
                    'pointer_description': pointer_desc,
                    'student_label': student_label,
                    'correct_label': correct_label,
                    'is_correct': is_correct
                })
            
            earned_points += q_earned
            
            results.append({
                'question_number': q_num,
                'question_type': 'labeling',
                'diagram_description': q.get('diagram_description', ''),
                'total_labels': len(labeling_items),
                'correct_labels': q_correct,
                'points_earned': q_earned,
                'points_possible': q_points,
                'label_details': label_results
            })
        
        return {
            'question_type': 'labeling',
            'total_questions': len(questions),
            'total_labels': total_labels,
            'correct_labels': correct_labels,
            'incorrect_labels': total_labels - correct_labels,
            'points_earned': earned_points,
            'points_possible': total_points,
            'percentage': (earned_points / total_points * 100) if total_points > 0 else 0,
            'details': results
        }
    
    # ============ Fill in the Blank ============
    
    def grade_fill_in_blank(self, questions: List[Dict[str, Any]],
                             student_answers: Dict[str, Any],
                             points_per_blank: float = 1.0) -> Dict[str, Any]:
        # Grade fill-in-the-blank questions
        # student_answers format: {"1": ["ans1", "ans2"]} or {"1": "single_answer"}
        results = []
        total_points = 0.0
        earned_points = 0.0
        correct_blanks = 0
        total_blanks = 0
        
        for q in questions:
            q_num = str(q.get('question_number', ''))
            correct_blanks_list = q.get('blanks', [])
            q_text = q.get('question_text', '')
            q_points = q.get('points', len(correct_blanks_list) * points_per_blank)
            
            # Get student's answers
            student_ans = student_answers.get(q_num) or student_answers.get(q_num.lower())
            
            # Normalize to list
            if student_ans is None:
                student_ans_list = []
            elif isinstance(student_ans, list):
                student_ans_list = student_ans
            else:
                student_ans_list = [student_ans]
            
            blank_results = []
            q_earned = 0.0
            q_correct = 0
            points_each = q_points / len(correct_blanks_list) if correct_blanks_list else points_per_blank
            
            for i, correct_blank in enumerate(correct_blanks_list):
                student_blank = student_ans_list[i] if i < len(student_ans_list) else None
                is_correct = self.answers_match(student_blank, correct_blank)
                
                total_blanks += 1
                total_points += points_each
                
                if is_correct:
                    q_earned += points_each
                    q_correct += 1
                    correct_blanks += 1
                
                blank_results.append({
                    'blank_number': i + 1,
                    'student_answer': student_blank,
                    'correct_answer': correct_blank,
                    'is_correct': is_correct
                })
            
            earned_points += q_earned
            
            results.append({
                'question_number': q_num,
                'question_type': 'fill_in_blank',
                'question_text': q_text[:100] + '...' if len(q_text) > 100 else q_text,
                'total_blanks': len(correct_blanks_list),
                'correct_blanks': q_correct,
                'points_earned': q_earned,
                'points_possible': q_points,
                'blank_details': blank_results
            })
        
        return {
            'question_type': 'fill_in_blank',
            'total_questions': len(questions),
            'total_blanks': total_blanks,
            'correct_blanks': correct_blanks,
            'incorrect_blanks': total_blanks - correct_blanks,
            'points_earned': earned_points,
            'points_possible': total_points,
            'percentage': (earned_points / total_points * 100) if total_points > 0 else 0,
            'details': results
        }
    
    # ============ MCQ and T/F ============
    
    def grade_multiple_choice(self, questions, student_answers, points_per_question=1.0):
        return self._grade_section(questions, student_answers, points_per_question, 'multiple_choice')
    
    def grade_true_false(self, questions, student_answers, points_per_question=1.0):
        return self._grade_section(questions, student_answers, points_per_question, 'true_false')
    
    def _grade_section(self, questions, student_answers, points, q_type):
        results = []
        total = 0.0
        earned = 0.0
        correct = 0
        
        for q in questions:
            q_num = q.get('question_number')
            correct_ans = q.get('correct_answer')
            pts = q.get('points', points)
            student_ans = student_answers.get(q_num)
            
            total += pts
            is_correct = self.answers_match(student_ans, correct_ans)
            
            if is_correct:
                earned += pts
                correct += 1
            
            results.append({
                'question_number': q_num,
                'student_answer': student_ans,
                'correct_answer': correct_ans,
                'is_correct': is_correct,
                'points_earned': pts if is_correct else 0,
                'points_possible': pts
            })
        
        return {
            'question_type': q_type,
            'total_questions': len(questions),
            'correct_count': correct,
            'incorrect_count': len(questions) - correct,
            'points_earned': earned,
            'points_possible': total,
            'percentage': (earned / total * 100) if total > 0 else 0,
            'details': results
        }
    
    # ============ Ordered Format ============
    
    def grade_ordered_questions(self, questions: List[Dict[str, Any]], 
                                 student_answers: Dict[str, Any],
                                 default_points: float = 1.0) -> Dict[str, Any]:
        # Grade ordered format - all gradable types
        results = []
        total_points = 0.0
        earned_points = 0.0
        correct_count = 0
        total_gradable = 0
        
        gradable_types = ['multiple_choice', 'true_false', 'matching', 'fill_in_blank']
        
        for q in questions:
            q_num = str(q.get('question_number', ''))
            q_type = q.get('question_type', '')
            points = q.get('points', default_points) or default_points
            sub_questions = q.get('sub_questions', [])
            
            # Parent with sub-questions
            if q_type == 'parent' and sub_questions:
                sub_results = []
                parent_earned = 0.0
                parent_possible = 0.0
                
                for sq in sub_questions:
                    sq_id = sq.get('sub_id', '')
                    sq_type = sq.get('question_type', '')
                    sq_points = sq.get('points', default_points / len(sub_questions))
                    sq_correct = sq.get('correct_answer')
                    
                    if sq_type not in gradable_types:
                        continue
                    
                    total_gradable += 1
                    parent_possible += sq_points
                    
                    key = self._make_key(q_num, sq_id)
                    student_answer = None
                    
                    if q_num in student_answers and isinstance(student_answers.get(q_num), dict):
                        student_answer = student_answers[q_num].get(sq_id)
                    elif key in student_answers:
                        student_answer = student_answers[key]
                    elif sq_id in student_answers:
                        student_answer = student_answers[sq_id]
                    
                    is_correct = self.answers_match(student_answer, sq_correct)
                    
                    if is_correct:
                        parent_earned += sq_points
                        correct_count += 1
                    
                    sub_results.append({
                        'sub_id': sq_id,
                        'question_type': sq_type,
                        'student_answer': student_answer,
                        'correct_answer': sq_correct,
                        'is_correct': is_correct,
                        'points_earned': sq_points if is_correct else 0,
                        'points_possible': sq_points
                    })
                
                if sub_results:
                    total_points += parent_possible
                    earned_points += parent_earned
                    results.append({
                        'question_number': q_num,
                        'question_type': 'parent',
                        'sub_questions': sub_results,
                        'points_earned': parent_earned,
                        'points_possible': parent_possible
                    })
            
            # MCQ or T/F
            elif q_type in ['multiple_choice', 'true_false']:
                total_gradable += 1
                correct_answer = q.get('correct_answer')
                student_answer = student_answers.get(q_num) or student_answers.get(q_num.lower())
                is_correct = self.answers_match(student_answer, correct_answer)
                
                total_points += points
                if is_correct:
                    earned_points += points
                    correct_count += 1
                
                results.append({
                    'question_number': q_num,
                    'question_type': q_type,
                    'student_answer': student_answer,
                    'correct_answer': correct_answer,
                    'is_correct': is_correct,
                    'points_earned': points if is_correct else 0,
                    'points_possible': points
                })
            
            # Matching
            elif q_type == 'matching':
                correct_matches = q.get('correct_matches', {})
                if correct_matches:
                    student_matches = student_answers.get(q_num, {})
                    if not isinstance(student_matches, dict):
                        student_matches = {}
                    
                    points_each = points / len(correct_matches)
                    pair_results = []
                    
                    for left_id, correct_right in correct_matches.items():
                        total_gradable += 1
                        student_right = student_matches.get(left_id) or student_matches.get(str(left_id))
                        is_correct = self.answers_match(student_right, correct_right)
                        
                        total_points += points_each
                        if is_correct:
                            earned_points += points_each
                            correct_count += 1
                        
                        pair_results.append({
                            'left_id': left_id,
                            'student_match': student_right,
                            'correct_match': correct_right,
                            'is_correct': is_correct
                        })
                    
                    results.append({
                        'question_number': q_num,
                        'question_type': 'matching',
                        'pair_details': pair_results,
                        'points_earned': sum(p['is_correct'] for p in pair_results) * points_each,
                        'points_possible': points
                    })
            
            # Fill in blank
            elif q_type == 'fill_in_blank':
                blanks = q.get('blanks', [])
                if blanks:
                    student_ans = student_answers.get(q_num)
                    if isinstance(student_ans, list):
                        student_list = student_ans
                    elif student_ans:
                        student_list = [student_ans]
                    else:
                        student_list = []
                    
                    points_each = points / len(blanks)
                    blank_results = []
                    
                    for i, correct_blank in enumerate(blanks):
                        total_gradable += 1
                        student_blank = student_list[i] if i < len(student_list) else None
                        is_correct = self.answers_match(student_blank, correct_blank)
                        
                        total_points += points_each
                        if is_correct:
                            earned_points += points_each
                            correct_count += 1
                        
                        blank_results.append({
                            'blank_number': i + 1,
                            'student_answer': student_blank,
                            'correct_answer': correct_blank,
                            'is_correct': is_correct
                        })
                    
                    results.append({
                        'question_number': q_num,
                        'question_type': 'fill_in_blank',
                        'blank_details': blank_results,
                        'points_earned': sum(b['is_correct'] for b in blank_results) * points_each,
                        'points_possible': points
                    })
        
        return {
            'format': 'ordered',
            'total_questions': len(questions),
            'total_gradable': total_gradable,
            'correct_count': correct_count,
            'incorrect_count': total_gradable - correct_count,
            'points_earned': earned_points,
            'points_possible': total_points,
            'percentage': (earned_points / total_points * 100) if total_points > 0 else 0,
            'details': results
        }
