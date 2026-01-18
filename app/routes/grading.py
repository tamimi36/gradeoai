# Grading endpoints for exam answers
from flask import request
from flask_restx import Namespace, Resource, fields

from app.services.grading import GradingService


grading_ns = Namespace('grading', description='Exam grading')

# ============ Request Models ============

mcq_question_model = grading_ns.model('MCQQuestion', {
    'question_number': fields.Raw(required=True, description='Question number (int or string)'),
    'question_text': fields.String(description='Question text'),
    'options': fields.Raw(description='Options dict: {"A": "text", "B": "text"}'),
    'correct_answer': fields.String(required=True, description='Correct answer (A, B, C, D or 1, 2, 3, 4)')
})

tf_question_model = grading_ns.model('TFQuestion', {
    'question_number': fields.Raw(required=True, description='Question number (int or string)'),
    'statement': fields.String(description='Statement text'),
    'correct_answer': fields.Raw(required=True, description='Correct answer (true/false or boolean)')
})

matching_question_model = grading_ns.model('MatchingQuestion', {
    'question_number': fields.String(required=True, description='Question number'),
    'left_column': fields.List(fields.Raw, description='Left items: [{"id": "1", "text": "item"}]'),
    'right_column': fields.List(fields.Raw, description='Right items: [{"id": "a", "text": "item"}]'),
    'correct_matches': fields.Raw(required=True, description='Correct pairings: {"1": "a", "2": "b", "3": "c"}'),
    'points': fields.Float(default=1.0, description='Points for all pairs')
})

fill_blank_question_model = grading_ns.model('FillBlankQuestion', {
    'question_number': fields.String(required=True, description='Question number'),
    'question_text': fields.String(description='Sentence with _____ blanks'),
    'blanks': fields.List(fields.String, required=True, description='Correct answers in order: ["answer1", "answer2"]'),
    'points': fields.Float(default=1.0, description='Points for all blanks')
})

mcq_request_model = grading_ns.model('MCQGradingRequest', {
    'questions': fields.List(fields.Nested(mcq_question_model), required=True,
                             description='List of MCQ questions with correct answers'),
    'student_answers': fields.Raw(required=True,
                                   description='Student answers: {"1": "A", "2": "B"}'),
    'points_per_question': fields.Float(default=1.0, description='Points per question')
})

tf_request_model = grading_ns.model('TFGradingRequest', {
    'questions': fields.List(fields.Nested(tf_question_model), required=True,
                             description='List of T/F questions with correct answers'),
    'student_answers': fields.Raw(required=True,
                                   description='Student answers: {"1": true, "2": "false"}'),
    'points_per_question': fields.Float(default=1.0, description='Points per question')
})

matching_request_model = grading_ns.model('MatchingGradingRequest', {
    'questions': fields.List(fields.Nested(matching_question_model), required=True,
                             description='List of matching questions'),
    'student_answers': fields.Raw(required=True,
                                   description='Student matches: {"1": {"1": "a", "2": "b"}} or flat {"1": "a", "2": "b"}'),
    'points_per_pair': fields.Float(default=1.0, description='Points per correct pair')
})

fill_blank_request_model = grading_ns.model('FillBlankGradingRequest', {
    'questions': fields.List(fields.Nested(fill_blank_question_model), required=True,
                             description='List of fill-in-blank questions'),
    'student_answers': fields.Raw(required=True,
                                   description='Student answers: {"1": ["ans1", "ans2"]} or {"1": "single_answer"}'),
    'points_per_blank': fields.Float(default=1.0, description='Points per correct blank')
})

ordering_question_model = grading_ns.model('OrderingQuestion', {
    'question_number': fields.String(required=True, description='Question number'),
    'question_text': fields.String(description='Question text'),
    'ordering_items': fields.List(fields.Raw, description='Items: [{"item_id": "A", "content": "text"}]'),
    'correct_order': fields.List(fields.String, required=True, description='Correct sequence: ["C", "A", "B"]'),
    'points': fields.Float(default=1.0, description='Points for all positions')
})

ordering_request_model = grading_ns.model('OrderingGradingRequest', {
    'questions': fields.List(fields.Nested(ordering_question_model), required=True,
                             description='List of ordering questions'),
    'student_answers': fields.Raw(required=True,
                                   description='Student order: {"1": ["C", "A", "B"]} or {"1": "C,A,B"}'),
    'points_per_position': fields.Float(default=1.0, description='Points per correct position')
})

open_ended_question_model = grading_ns.model('OpenEndedQuestion', {
    'question_number': fields.String(required=True, description='Question number/ID', example='1'),
    'question_text': fields.String(required=True, description='The full question text', 
                                    example='Explain the process of photosynthesis'),
    'model_answer': fields.String(required=True, 
                                   description='Perfect/model answer for AI comparison. The AI compares student answer against this.',
                                   example='Photosynthesis is the process by which plants use sunlight, water, and carbon dioxide to produce glucose and oxygen. Chlorophyll in leaves absorbs light energy.'),
    'expected_keywords': fields.List(fields.String, 
                                      description='Keywords that should appear in student answer (for key_terms criterion)',
                                      example=['chlorophyll', 'sunlight', 'glucose', 'carbon dioxide']),
    'points': fields.Float(default=10.0, description='Maximum points for this question', example=10.0),
    'answer_length': fields.String(description='Expected length: "short" or "long"', example='long')
})

open_ended_request_model = grading_ns.model('OpenEndedGradingRequest', {
    'questions': fields.List(fields.Nested(open_ended_question_model), required=True,
                             description='List of open-ended questions. Each must include model_answer for comparison.'),
    'student_answers': fields.Raw(required=True, 
                                   description='Dict mapping question_number to student answer text',
                                   example={'1': 'Plants use sunlight to make food through chlorophyll'})
})

# Compare/Contrast request models
compare_grading_item = grading_ns.model('CompareGradingItem', {
    'item': fields.String(required=True, 
                          description='The idea/concept to check for in student answer (semantic matching)',
                          example='Both involve cell division'),
    'points': fields.Float(description='Points for this specific item. If not set, total points divided evenly among all items.',
                           example=2.5)
})

compare_contrast_question_model = grading_ns.model('CompareContrastQuestion', {
    'question_number': fields.String(required=True, description='Question identifier', example='1'),
    'question_text': fields.String(required=True, 
                                    description='The full question text asking for comparison',
                                    example='Compare and contrast mitosis and meiosis. Discuss their similarities and differences.'),
    'compare_items': fields.List(fields.String, 
                                  description='The two or more items being compared (for reference)',
                                  example=['mitosis', 'meiosis']),
    'grading_table': fields.List(fields.Nested(compare_grading_item), required=True,
                                  description='Checklist of ideas/concepts to grade against. Each item marked as present/partial/absent.',
                                  example=[
                                      {'item': 'Both involve cell division', 'points': 2},
                                      {'item': 'Mitosis produces 2 identical cells', 'points': 2.5},
                                      {'item': 'Meiosis produces 4 different cells', 'points': 2.5},
                                      {'item': 'Mitosis is for growth, meiosis for reproduction', 'points': 3}
                                  ]),
    'points': fields.Float(default=10.0, 
                           description='Total points for question. Used to divide evenly if item points not specified.',
                           example=10.0)
})

compare_contrast_request_model = grading_ns.model('CompareContrastGradingRequest', {
    'questions': fields.List(fields.Nested(compare_contrast_question_model), required=True,
                             description='List of compare/contrast questions. Teacher must provide grading_table for each.'),
    'student_answers': fields.Raw(required=True,
                                   description='Dict mapping question_number to student answer text',
                                   example={'1': 'Mitosis and meiosis are both cell division processes. Mitosis creates two identical cells for growth. Meiosis makes four different cells for reproduction.'})
})

# Definition request models
definition_question_model = grading_ns.model('DefinitionQuestion', {
    'question_number': fields.String(required=True, description='Question identifier', example='1'),
    'term_to_define': fields.String(required=True, 
                                     description='The term/concept the student must define',
                                     example='Photosynthesis'),
    'model_definition': fields.String(required=True,
                                        description='Perfect/model definition provided by teacher. AI compares student answer against this using semantic matching.',
                                        example='Photosynthesis is the process by which green plants and some other organisms use sunlight, water, and carbon dioxide to synthesize glucose and release oxygen as a byproduct.'),
    'required_keywords': fields.List(fields.String,
                                      description='Key terms/properties that should appear in the definition (used for required_properties criterion)',
                                      example=['sunlight', 'water', 'carbon dioxide', 'glucose', 'oxygen', 'chlorophyll']),
    'points': fields.Float(default=10.0, description='Maximum points for this definition question', example=10.0)
})

definition_request_model = grading_ns.model('DefinitionGradingRequest', {
    'questions': fields.List(fields.Nested(definition_question_model), required=True,
                             description='List of definition questions. Each must include term_to_define and model_definition.'),
    'student_answers': fields.Raw(required=True,
                                   description='Dict mapping question_number to student definition text',
                                   example={'1': 'Photosynthesis is when plants use sunlight and water to make food and release oxygen.'})
})

math_question_model = grading_ns.model('MathQuestion', {
    'question_number': fields.String(required=True, description='Question number'),
    'question_markdown': fields.String(required=True, description='Question in LaTeX'),
    'answer_markdown': fields.String(required=True, description='Correct answer in LaTeX'),
    'points': fields.Float(default=1.0, description='Points')
})

math_request_model = grading_ns.model('MathGradingRequest', {
    'questions': fields.List(fields.Nested(math_question_model), required=True),
    'student_answers': fields.Raw(required=True, description='{"1": "$2x + 3$"}')
})

# ============ Response Models ============

error_model = grading_ns.model('GradingError', {
    'success': fields.Boolean(default=False),
    'error': fields.String(description='Error message')
})

# MCQ/TF result
mcq_tf_grading_result = grading_ns.model('MCQTFGradingResult', {
    'question_type': fields.String(description='multiple_choice or true_false'),
    'total_questions': fields.Integer(),
    'correct_count': fields.Integer(),
    'incorrect_count': fields.Integer(),
    'points_earned': fields.Float(),
    'points_possible': fields.Float(),
    'percentage': fields.Float(description='Score 0-100'),
    'details': fields.List(fields.Raw, description='Per-question breakdown')
})

mcq_tf_success_model = grading_ns.model('MCQTFSuccess', {
    'success': fields.Boolean(default=True),
    'data': fields.Nested(mcq_tf_grading_result)
})

# Matching result
matching_pair_result = grading_ns.model('MatchingPairResult', {
    'left_id': fields.String(description='Left item ID'),
    'student_match': fields.String(description='Student\'s paired right ID'),
    'correct_match': fields.String(description='Correct right ID'),
    'is_correct': fields.Boolean()
})

matching_question_result = grading_ns.model('MatchingQuestionResult', {
    'question_number': fields.String(),
    'question_type': fields.String(default='matching'),
    'total_pairs': fields.Integer(),
    'correct_pairs': fields.Integer(),
    'points_earned': fields.Float(),
    'points_possible': fields.Float(),
    'pair_details': fields.List(fields.Nested(matching_pair_result))
})

matching_grading_result = grading_ns.model('MatchingGradingResult', {
    'question_type': fields.String(default='matching'),
    'total_questions': fields.Integer(),
    'total_pairs': fields.Integer(description='Total pairs across all questions'),
    'correct_pairs': fields.Integer(),
    'incorrect_pairs': fields.Integer(),
    'points_earned': fields.Float(),
    'points_possible': fields.Float(),
    'percentage': fields.Float(description='Score 0-100'),
    'details': fields.List(fields.Nested(matching_question_result))
})

matching_success_model = grading_ns.model('MatchingSuccess', {
    'success': fields.Boolean(default=True),
    'data': fields.Nested(matching_grading_result)
})

# Fill in blank result
blank_result = grading_ns.model('BlankResult', {
    'blank_number': fields.Integer(description='Blank position (1-based)'),
    'student_answer': fields.String(),
    'correct_answer': fields.String(),
    'is_correct': fields.Boolean()
})

fill_blank_question_result = grading_ns.model('FillBlankQuestionResult', {
    'question_number': fields.String(),
    'question_type': fields.String(default='fill_in_blank'),
    'question_text': fields.String(description='Truncated question text'),
    'total_blanks': fields.Integer(),
    'correct_blanks': fields.Integer(),
    'points_earned': fields.Float(),
    'points_possible': fields.Float(),
    'blank_details': fields.List(fields.Nested(blank_result))
})

fill_blank_grading_result = grading_ns.model('FillBlankGradingResult', {
    'question_type': fields.String(default='fill_in_blank'),
    'total_questions': fields.Integer(),
    'total_blanks': fields.Integer(description='Total blanks across all questions'),
    'correct_blanks': fields.Integer(),
    'incorrect_blanks': fields.Integer(),
    'points_earned': fields.Float(),
    'points_possible': fields.Float(),
    'percentage': fields.Float(description='Score 0-100'),
    'details': fields.List(fields.Nested(fill_blank_question_result))
})

fill_blank_success_model = grading_ns.model('FillBlankSuccess', {
    'success': fields.Boolean(default=True),
    'data': fields.Nested(fill_blank_grading_result)
})

# Ordering result
position_result = grading_ns.model('PositionResult', {
    'position': fields.Integer(description='Position (1-based)'),
    'expected_item': fields.String(description='Expected item ID'),
    'student_item': fields.String(description='Student\'s item ID'),
    'is_correct': fields.Boolean()
})

ordering_question_result = grading_ns.model('OrderingQuestionResult', {
    'question_number': fields.String(),
    'question_type': fields.String(default='ordering'),
    'total_positions': fields.Integer(),
    'correct_positions': fields.Integer(),
    'points_earned': fields.Float(),
    'points_possible': fields.Float(),
    'position_details': fields.List(fields.Nested(position_result))
})

ordering_grading_result = grading_ns.model('OrderingGradingResult', {
    'question_type': fields.String(default='ordering'),
    'total_questions': fields.Integer(),
    'total_positions': fields.Integer(description='Total positions across all questions'),
    'correct_positions': fields.Integer(),
    'incorrect_positions': fields.Integer(),
    'points_earned': fields.Float(),
    'points_possible': fields.Float(),
    'percentage': fields.Float(description='Score 0-100'),
    'details': fields.List(fields.Nested(ordering_question_result))
})

ordering_success_model = grading_ns.model('OrderingSuccess', {
    'success': fields.Boolean(default=True),
    'data': fields.Nested(ordering_grading_result)
})

# Labeling (text input) request
labeling_item_model = grading_ns.model('LabelingItem', {
    'label_id': fields.String(required=True, description='Label identifier (1, 2, A)'),
    'pointer_description': fields.String(description='What the pointer/arrow indicates'),
    'correct_label': fields.String(required=True, description='Correct label text')
})

labeling_question_model = grading_ns.model('LabelingQuestion', {
    'question_number': fields.String(required=True),
    'diagram_description': fields.String(description='Description of the diagram'),
    'labeling_items': fields.List(fields.Nested(labeling_item_model), required=True),
    'points': fields.Float(default=1.0)
})

labeling_request_model = grading_ns.model('LabelingGradingRequest', {
    'questions': fields.List(fields.Nested(labeling_question_model), required=True),
    'student_answers': fields.Raw(required=True,
                                   description='{"1": {"1": "Left Atrium", "2": "Left Ventricle"}}'),
    'points_per_label': fields.Float(default=1.0)
})

# Labeling response
label_result = grading_ns.model('LabelResult', {
    'label_id': fields.String(),
    'pointer_description': fields.String(),
    'student_label': fields.String(),
    'correct_label': fields.String(),
    'is_correct': fields.Boolean()
})

labeling_question_result = grading_ns.model('LabelingQuestionResult', {
    'question_number': fields.String(),
    'question_type': fields.String(default='labeling'),
    'diagram_description': fields.String(),
    'total_labels': fields.Integer(),
    'correct_labels': fields.Integer(),
    'points_earned': fields.Float(),
    'points_possible': fields.Float(),
    'label_details': fields.List(fields.Nested(label_result))
})

labeling_grading_result = grading_ns.model('LabelingGradingResult', {
    'question_type': fields.String(default='labeling'),
    'total_questions': fields.Integer(),
    'total_labels': fields.Integer(),
    'correct_labels': fields.Integer(),
    'incorrect_labels': fields.Integer(),
    'points_earned': fields.Float(),
    'points_possible': fields.Float(),
    'percentage': fields.Float(),
    'details': fields.List(fields.Nested(labeling_question_result))
})

labeling_success_model = grading_ns.model('LabelingSuccess', {
    'success': fields.Boolean(default=True),
    'data': fields.Nested(labeling_grading_result)
})

# Labeling Image (handwriting) request - uses same labeling_item_model
labeling_image_question_model = grading_ns.model('LabelingImageQuestion', {
    'question_number': fields.String(required=True, description='Question identifier', example='1'),
    'diagram_description': fields.String(description='Description of the diagram', 
                                           example='Human heart diagram with numbered pointers'),
    'labeling_items': fields.List(fields.Nested(labeling_item_model), required=True,
                                   description='Labels to check in the image'),
    'points': fields.Float(default=1.0, description='Total points for this question')
})

labeling_image_request_model = grading_ns.model('LabelingImageGradingRequest', {
    'questions': fields.List(fields.Nested(labeling_image_question_model), required=True,
                             description='Questions with labeling_items'),
    'student_images': fields.Raw(required=True, 
                                  description='Dict mapping question_number to base64 image',
                                  example={'1': 'data:image/jpeg;base64,/9j/4AAQ...'})
})

# Labeling Image response
labeling_image_question_result = grading_ns.model('LabelingImageQuestionResult', {
    'question_number': fields.String(),
    'question_type': fields.String(default='labeling_image'),
    'ocr_status': fields.String(description='success, no_image, or ocr_error'),
    'diagram_description': fields.String(),
    'total_labels': fields.Integer(),
    'correct_labels': fields.Integer(),
    'points_earned': fields.Float(),
    'points_possible': fields.Float(),
    'label_details': fields.List(fields.Nested(label_result))
})

labeling_image_grading_result = grading_ns.model('LabelingImageGradingResult', {
    'question_type': fields.String(default='labeling_image'),
    'total_questions': fields.Integer(),
    'total_labels': fields.Integer(),
    'correct_labels': fields.Integer(),
    'incorrect_labels': fields.Integer(),
    'points_earned': fields.Float(),
    'points_possible': fields.Float(),
    'percentage': fields.Float(),
    'details': fields.List(fields.Nested(labeling_image_question_result))
})

labeling_image_success_model = grading_ns.model('LabelingImageSuccess', {
    'success': fields.Boolean(default=True),
    'data': fields.Nested(labeling_image_grading_result)
})

# Open-ended result
criterion_result = grading_ns.model('CriterionResult', {
    'status': fields.String(description='Grading status: "full" (100%), "partial" (50%), or "absent" (0%)', 
                            example='full'),
    'weight': fields.Float(description='Weight of this criterion (from config)', example=0.40),
    'score': fields.Float(description='Earned percentage for this criterion (status_score * weight)', example=0.40),
    'reason': fields.String(description='AI explanation for this score', 
                            example='Student correctly explained the main concept of photosynthesis'),
    'found': fields.List(fields.String, description='Keywords found in answer (key_terms criterion only)',
                         example=['chlorophyll', 'sunlight'])
})

open_ended_question_result = grading_ns.model('OpenEndedQuestionResult', {
    'question_number': fields.String(description='Question identifier', example='1'),
    'student_answer': fields.String(description='Student answer (truncated to 200 chars)', 
                                     example='Plants use sunlight to make food...'),
    'criteria_results': fields.Raw(description='Object with results for each criterion: core_concept, logical_explanation, key_terms, clarity_structure',
                                    example={
                                        'core_concept': {'status': 'full', 'weight': 0.4, 'score': 0.4, 'reason': '...'},
                                        'logical_explanation': {'status': 'partial', 'weight': 0.3, 'score': 0.15, 'reason': '...'},
                                        'key_terms': {'status': 'full', 'weight': 0.2, 'score': 0.2, 'found': ['chlorophyll']},
                                        'clarity_structure': {'status': 'full', 'weight': 0.1, 'score': 0.1, 'reason': '...'}
                                    }),
    'grading_passes': fields.Integer(description='Number of AI grading passes performed', example=3),
    'flag_for_review': fields.Boolean(description='True if high variance detected across passes', example=False),
    'high_variance_criteria': fields.List(fields.String, description='Criteria with all different results across passes', example=[]),
    'total_percentage': fields.Float(description='Total score as percentage (0-100)', example=85.0),
    'points_earned': fields.Float(description='Points earned for this question', example=8.5),
    'points_possible': fields.Float(description='Maximum points for this question', example=10.0)
})

open_ended_grading_result = grading_ns.model('OpenEndedGradingResult', {
    'question_type': fields.String(default='open_ended', description='Always "open_ended"'),
    'total_questions': fields.Integer(description='Number of questions graded', example=1),
    'grading_passes_per_question': fields.Integer(description='AI passes per question (from config)', example=3),
    'criteria_used': fields.List(fields.String, 
                                  description='Criteria names used for grading',
                                  example=['core_concept', 'logical_explanation', 'key_terms', 'clarity_structure']),
    'flagged_for_review': fields.Integer(description='Count of questions flagged for manual review', example=0),
    'points_earned': fields.Float(description='Total points earned across all questions', example=8.5),
    'points_possible': fields.Float(description='Total maximum points', example=10.0),
    'percentage': fields.Float(description='Overall percentage score (0-100)', example=85.0),
    'details': fields.List(fields.Nested(open_ended_question_result), 
                           description='Detailed results for each question')
})

open_ended_success_model = grading_ns.model('OpenEndedSuccess', {
    'success': fields.Boolean(default=True),
    'data': fields.Nested(open_ended_grading_result)
})

# Compare/Contrast response models
compare_item_result = grading_ns.model('CompareItemResult', {
    'item': fields.String(description='The checklist item text', example='Both involve cell division'),
    'status': fields.String(description='present (100%), partial (50%), or absent (0%)', example='present'),
    'points_earned': fields.Float(description='Points earned for this item', example=2.0),
    'points_possible': fields.Float(description='Max points for this item', example=2.0),
    'reason': fields.String(description='AI explanation for this score', 
                            example='Student correctly stated both are types of cell division')
})

compare_question_result = grading_ns.model('CompareQuestionResult', {
    'question_number': fields.String(example='1'),
    'student_answer': fields.String(description='Student answer (truncated to 200 chars)', 
                                     example='Mitosis and meiosis are both cell division...'),
    'item_results': fields.List(fields.Nested(compare_item_result), 
                                 description='Grading result for each checklist item'),
    'grading_passes': fields.Integer(description='Number of AI grading passes', example=3),
    'flag_for_review': fields.Boolean(description='True if high variance across passes', example=False),
    'high_variance_items': fields.List(fields.Integer, 
                                        description='Indices of items where all 3 passes differed',
                                        example=[]),
    'points_earned': fields.Float(description='Total points earned', example=8.0),
    'points_possible': fields.Float(description='Total possible points', example=10.0),
    'total_percentage': fields.Float(description='Percentage score (0-100)', example=80.0)
})

compare_grading_result = grading_ns.model('CompareContrastGradingResult', {
    'question_type': fields.String(default='compare_contrast'),
    'total_questions': fields.Integer(description='Number of questions graded', example=1),
    'grading_passes_per_question': fields.Integer(description='AI passes per question', example=3),
    'flagged_for_review': fields.Integer(description='Questions needing manual review', example=0),
    'points_earned': fields.Float(description='Total points earned', example=8.0),
    'points_possible': fields.Float(description='Total possible', example=10.0),
    'percentage': fields.Float(description='Overall percentage (0-100)', example=80.0),
    'details': fields.List(fields.Nested(compare_question_result), description='Per-question results')
})

compare_contrast_success_model = grading_ns.model('CompareContrastSuccess', {
    'success': fields.Boolean(default=True),
    'data': fields.Nested(compare_grading_result)
})

# Definition response models
definition_criterion_result = grading_ns.model('DefinitionCriterionResult', {
    'status': fields.String(description='present (100%), partial (50%), or absent (0%)', example='present'),
    'weight': fields.Float(description='Weight of this meaning unit (from config)', example=0.50),
    'score': fields.Float(description='Earned score (status_score * weight)', example=0.50),
    'reason': fields.String(description='AI explanation', example='Student captured the main concept accurately')
})

definition_question_result = grading_ns.model('DefinitionQuestionResult', {
    'question_number': fields.String(example='1'),
    'term': fields.String(description='The term being defined', example='Photosynthesis'),
    'student_answer': fields.String(description='Student definition (truncated)', 
                                     example='Photosynthesis is when plants make food...'),
    'criteria_results': fields.Raw(description='Results per meaning unit: core_concept (50%), required_properties (30%), scope_context (20%)',
                                    example={
                                        'core_concept': {'status': 'present', 'weight': 0.5, 'score': 0.5, 'reason': '...'},
                                        'required_properties': {'status': 'partial', 'weight': 0.3, 'score': 0.15, 'reason': '...'},
                                        'scope_context': {'status': 'present', 'weight': 0.2, 'score': 0.2, 'reason': '...'}
                                    }),
    'grading_passes': fields.Integer(description='Number of AI passes', example=3),
    'flag_for_review': fields.Boolean(description='True if high variance across passes', example=False),
    'high_variance_criteria': fields.List(fields.String, description='Meaning units with variance', example=[]),
    'total_percentage': fields.Float(description='Total score (0-100)', example=85.0),
    'points_earned': fields.Float(example=8.5),
    'points_possible': fields.Float(example=10.0)
})

definition_grading_result = grading_ns.model('DefinitionGradingResult', {
    'question_type': fields.String(default='definition'),
    'total_questions': fields.Integer(description='Questions graded', example=1),
    'grading_passes_per_question': fields.Integer(example=3),
    'criteria_used': fields.List(fields.String, description='Meaning units: core_concept, required_properties, scope_context',
                                  example=['core_concept', 'required_properties', 'scope_context']),
    'flagged_for_review': fields.Integer(description='Questions needing review', example=0),
    'points_earned': fields.Float(example=8.5),
    'points_possible': fields.Float(example=10.0),
    'percentage': fields.Float(description='Overall percentage (0-100)', example=85.0),
    'details': fields.List(fields.Nested(definition_question_result), description='Per-question results')
})

definition_success_model = grading_ns.model('DefinitionSuccess', {
    'success': fields.Boolean(default=True),
    'data': fields.Nested(definition_grading_result)
})

# Table grading models (same logic as compare_contrast)
table_grading_item = grading_ns.model('TableGradingItem', {
    'item': fields.String(required=True, 
                          description='The idea/concept/cell value to check for (semantic matching)',
                          example='Cell 1,1: Mitochondria'),
    'points': fields.Float(description='Points for this item', example=2.0)
})

table_question_model = grading_ns.model('TableQuestion', {
    'question_number': fields.String(required=True, description='Question identifier', example='1'),
    'question_text': fields.String(required=True, 
                                    description='The table question text',
                                    example='Fill in the missing cells in the table about cell organelles'),
    'grading_table': fields.List(fields.Nested(table_grading_item), required=True,
                                  description='Checklist of items/cells to grade against'),
    'points': fields.Float(default=10.0, description='Total points for question')
})

table_request_model = grading_ns.model('TableGradingRequest', {
    'questions': fields.List(fields.Nested(table_question_model), required=True,
                             description='List of table questions. Teacher provides grading_table.'),
    'student_answers': fields.Raw(required=True,
                                   description='Dict mapping question_number to student answer text',
                                   example={'1': 'Mitochondria produces energy. Nucleus contains DNA.'})
})

# Table response models (same structure as compare_contrast)
table_item_result = grading_ns.model('TableItemResult', {
    'item': fields.String(description='The checklist item text'),
    'status': fields.String(description='present (100%), partial (50%), or absent (0%)'),
    'points_earned': fields.Float(),
    'points_possible': fields.Float(),
    'reason': fields.String(description='AI explanation')
})

table_question_result = grading_ns.model('TableQuestionResult', {
    'question_number': fields.String(),
    'student_answer': fields.String(description='Student answer (truncated)'),
    'item_results': fields.List(fields.Nested(table_item_result)),
    'grading_passes': fields.Integer(),
    'flag_for_review': fields.Boolean(),
    'high_variance_items': fields.List(fields.Integer),
    'points_earned': fields.Float(),
    'points_possible': fields.Float(),
    'total_percentage': fields.Float()
})

table_grading_result = grading_ns.model('TableGradingResult', {
    'question_type': fields.String(default='table'),
    'total_questions': fields.Integer(),
    'grading_passes_per_question': fields.Integer(),
    'flagged_for_review': fields.Integer(),
    'points_earned': fields.Float(),
    'points_possible': fields.Float(),
    'percentage': fields.Float(),
    'details': fields.List(fields.Nested(table_question_result))
})

table_success_model = grading_ns.model('TableSuccess', {
    'success': fields.Boolean(default=True),
    'data': fields.Nested(table_grading_result)
})

# Math request models
math_question_model = grading_ns.model('MathQuestion', {
    'question_number': fields.String(required=True, description='Question identifier', example='1'),
    'question_text': fields.String(description='Full question text', example='Solve: (2 + 3) × 4 - 6 ÷ 2'),
    'math_content': fields.String(required=True, description='The equation/expression', example='(2 + 3) × 4 - 6 ÷ 2'),
    'correct_answer': fields.String(required=True, description='Final answer only', example='17'),
    'points': fields.Float(default=10.0, description='Total points')
})

math_request_model = grading_ns.model('MathGradingRequest', {
    'questions': fields.List(fields.Nested(math_question_model), required=True,
                             description='List of math questions. Provide equation and final answer.'),
    'student_answers': fields.Raw(required=True,
                                   description='Dict mapping question_number to student work (steps)',
                                   example={'1': '2+3=5\n5×4=20\n6÷2=3\n20-3=17'})
})

# Math response models
math_step_result = grading_ns.model('MathStepResult', {
    'step': fields.Integer(description='Step number'),
    'operation': fields.String(description='PEMDAS operation type'),
    'expected': fields.String(description='Expected expression (plain text)'),
    'expected_latex': fields.String(description='Expected expression (LaTeX format)'),
    'status': fields.String(description='present (100%), partial (50%), absent (0%)'),
    'points_earned': fields.Float(),
    'points_possible': fields.Float(),
    'reason': fields.String(description='AI explanation')
})

math_question_result = grading_ns.model('MathQuestionResult', {
    'question_number': fields.String(),
    'problem': fields.String(description='The math problem'),
    'student_work': fields.String(description='Student work (truncated)'),
    'final_answer_correct': fields.Boolean(),
    'total_steps': fields.Integer(description='Number of PEMDAS steps'),
    'step_results': fields.List(fields.Nested(math_step_result)),
    'grading_passes': fields.Integer(),
    'flag_for_review': fields.Boolean(),
    'high_variance_steps': fields.List(fields.Integer),
    'points_earned': fields.Float(),
    'points_possible': fields.Float(),
    'total_percentage': fields.Float()
})

math_grading_result = grading_ns.model('MathGradingResult', {
    'question_type': fields.String(default='math_equation'),
    'total_questions': fields.Integer(),
    'grading_passes_per_question': fields.Integer(),
    'flagged_for_review': fields.Integer(),
    'points_earned': fields.Float(),
    'points_possible': fields.Float(),
    'percentage': fields.Float(),
    'details': fields.List(fields.Nested(math_question_result))
})

math_success_model = grading_ns.model('MathSuccess', {
    'success': fields.Boolean(default=True),
    'data': fields.Nested(math_grading_result)
})

# ============ Endpoints ============

@grading_ns.route('/mcq')
class GradeMultipleChoice(Resource):
    @grading_ns.doc('grade_multiple_choice')
    @grading_ns.expect(mcq_request_model)
    @grading_ns.response(200, 'Success', mcq_tf_success_model)
    @grading_ns.response(400, 'Bad Request', error_model)
    def post(self):
        # Grade MCQ
        try:
            data = request.get_json()
            if not data:
                return {'success': False, 'error': 'No JSON data'}, 400
            
            questions = data.get('questions', [])
            student_answers = data.get('student_answers', {})
            points = data.get('points_per_question', 1.0)
            
            grading = GradingService()
            # Always use grade_multiple_choice for this endpoint
            result = grading.grade_multiple_choice(questions, student_answers, points)
            
            return {'success': True, 'data': result}, 200
        except Exception as e:
            return {'success': False, 'error': str(e)}, 500


@grading_ns.route('/true-false')
class GradeTrueFalse(Resource):
    @grading_ns.doc('grade_true_false')
    @grading_ns.expect(tf_request_model)
    @grading_ns.response(200, 'Success', mcq_tf_success_model)
    @grading_ns.response(400, 'Bad Request', error_model)
    def post(self):
        # Grade T/F
        try:
            data = request.get_json()
            if not data:
                return {'success': False, 'error': 'No JSON data'}, 400
            
            questions = data.get('questions', [])
            student_answers = data.get('student_answers', {})
            points = data.get('points_per_question', 1.0)
            
            grading = GradingService()
            # Always use grade_true_false for this endpoint
            result = grading.grade_true_false(questions, student_answers, points)
            
            return {'success': True, 'data': result}, 200
        except Exception as e:
            return {'success': False, 'error': str(e)}, 500


@grading_ns.route('/matching')
class GradeMatching(Resource):
    @grading_ns.doc('grade_matching')
    @grading_ns.expect(matching_request_model)
    @grading_ns.response(200, 'Success', matching_success_model)
    @grading_ns.response(400, 'Bad Request', error_model)
    def post(self):
        # Grade matching questions
        try:
            data = request.get_json()
            if not data:
                return {'success': False, 'error': 'No JSON data'}, 400
            
            questions = data.get('questions', [])
            student_answers = data.get('student_answers', {})
            points_per_pair = data.get('points_per_pair', 1.0)
            
            result = GradingService().grade_matching(questions, student_answers, points_per_pair)
            return {'success': True, 'data': result}, 200
        except Exception as e:
            return {'success': False, 'error': str(e)}, 500


@grading_ns.route('/fill-in-blank')
class GradeFillInBlank(Resource):
    @grading_ns.doc('grade_fill_blank')
    @grading_ns.expect(fill_blank_request_model)
    @grading_ns.response(200, 'Success', fill_blank_success_model)
    @grading_ns.response(400, 'Bad Request', error_model)
    def post(self):
        # Grade fill-in-the-blank questions
        try:
            data = request.get_json()
            if not data:
                return {'success': False, 'error': 'No JSON data'}, 400
            
            questions = data.get('questions', [])
            student_answers = data.get('student_answers', {})
            points_per_blank = data.get('points_per_blank', 1.0)
            
            result = GradingService().grade_fill_in_blank(questions, student_answers, points_per_blank)
            return {'success': True, 'data': result}, 200
        except Exception as e:
            return {'success': False, 'error': str(e)}, 500


@grading_ns.route('/ordering')
class GradeOrdering(Resource):
    @grading_ns.doc('grade_ordering')
    @grading_ns.expect(ordering_request_model)
    @grading_ns.response(200, 'Success', ordering_success_model)
    @grading_ns.response(400, 'Bad Request', error_model)
    def post(self):
        # Grade ordering/sequencing questions
        try:
            data = request.get_json()
            if not data:
                return {'success': False, 'error': 'No JSON data'}, 400
            
            questions = data.get('questions', [])
            student_answers = data.get('student_answers', {})
            points_per_position = data.get('points_per_position', 1.0)
            
            result = GradingService().grade_ordering(questions, student_answers, points_per_position)
            return {'success': True, 'data': result}, 200
        except Exception as e:
            return {'success': False, 'error': str(e)}, 500


@grading_ns.route('/labeling')
class GradeLabeling(Resource):
    @grading_ns.doc('grade_labeling')
    @grading_ns.expect(labeling_request_model)
    @grading_ns.response(200, 'Success', labeling_success_model)
    @grading_ns.response(400, 'Bad Request', error_model)
    def post(self):
        # Grade labeling questions using AI multi-pass grading
        try:
            data = request.get_json()
            if not data:
                return {'success': False, 'error': 'No JSON data'}, 400
            
            questions = data.get('questions', [])
            student_answers = data.get('student_answers', {})
            
            if not questions:
                return {'success': False, 'error': 'No questions provided'}, 400
            
            from app.services.labeling_grading import LabelingGradingService
            grading_service = LabelingGradingService()
            result = grading_service.grade_questions(questions, student_answers)
            
            return {'success': True, 'data': result}, 200
        except Exception as e:
            return {'success': False, 'error': str(e)}, 500


#@grading_ns.route('/labeling-image')
#class GradeLabelingImage(Resource):
  #@grading_ns.doc('grade_labeling_image', visible=False)
  #@grading_ns.expect(labeling_image_request_model)
  #@grading_ns.response(200, 'Success', labeling_image_success_model)
  #@grading_ns.response(400, 'Bad Request', error_model)
  #def post(self):
        #Grade labeling questions using Gemini Vision to OCR handwritten labels
        #try:
         #data = request.get_json()
            #if not data:
             #return {'success': False, 'error': 'No JSON data'}, 400
            
           # questions = data.get('questions', [])
            #student_images = data.get('student_images', {})
            
            #if not questions:
              #  return {'success': False, 'error': 'No questions provided'}, 400
            
            #from app.services.labeling_image_grading import LabelingImageGradingService
            #grading_service = LabelingImageGradingService()
            #result = grading_service.grade_questions(questions, student_images)
            
            #return {'success': True, 'data': result}, 200
        #except Exception as e:
            #return {'success': False, 'error': str(e)}, 500


@grading_ns.route('/compare-contrast')
class GradeCompareContrast(Resource):
    @grading_ns.doc('grade_compare_contrast')
    @grading_ns.expect(compare_contrast_request_model)
    @grading_ns.response(200, 'Success', compare_contrast_success_model)
    @grading_ns.response(400, 'Bad Request', error_model)
    def post(self):
        # Grade compare/contrast questions using checklist items
        try:
            data = request.get_json()
            if not data:
                return {'success': False, 'error': 'No JSON data'}, 400
            
            questions = data.get('questions', [])
            student_answers = data.get('student_answers', {})
            
            if not questions:
                return {'success': False, 'error': 'No questions provided'}, 400
            
            from app.services.compare_contrast_grading import CompareContrastGradingService
            grading_service = CompareContrastGradingService()
            result = grading_service.grade_questions(questions, student_answers)
            
            return {'success': True, 'data': result}, 200
        except Exception as e:
            return {'success': False, 'error': str(e)}, 500


@grading_ns.route('/table')
class GradeTable(Resource):
    @grading_ns.doc('grade_table')
    @grading_ns.expect(table_request_model)
    @grading_ns.response(200, 'Success', table_success_model)
    @grading_ns.response(400, 'Bad Request', error_model)
    def post(self):
        # Grade table questions using same logic as compare/contrast
        try:
            data = request.get_json()
            if not data:
                return {'success': False, 'error': 'No JSON data'}, 400
            
            questions = data.get('questions', [])
            student_answers = data.get('student_answers', {})
            
            if not questions:
                return {'success': False, 'error': 'No questions provided'}, 400
            
            from app.services.table_grading import TableGradingService
            grading_service = TableGradingService()
            result = grading_service.grade_questions(questions, student_answers)
            
            return {'success': True, 'data': result}, 200
        except Exception as e:
            return {'success': False, 'error': str(e)}, 500


@grading_ns.route('/definition')
class GradeDefinition(Resource):
    @grading_ns.doc('grade_definition')
    @grading_ns.expect(definition_request_model)
    @grading_ns.response(200, 'Success', definition_success_model)
    @grading_ns.response(400, 'Bad Request', error_model)
    def post(self):
        # Grade definition questions using meaning units
        try:
            data = request.get_json()
            if not data:
                return {'success': False, 'error': 'No JSON data'}, 400
            
            questions = data.get('questions', [])
            student_answers = data.get('student_answers', {})
            
            if not questions:
                return {'success': False, 'error': 'No questions provided'}, 400
            
            from app.services.definition_grading import DefinitionGradingService
            grading_service = DefinitionGradingService()
            result = grading_service.grade_questions(questions, student_answers)
            
            return {'success': True, 'data': result}, 200
        except Exception as e:
            return {'success': False, 'error': str(e)}, 500


# Short Answer grading models
short_answer_question_model = grading_ns.model('ShortAnswerQuestion', {
    'question_number': fields.String(required=True, description='Question number', example='1'),
    'question_text': fields.String(required=True, description='The question text', 
                                    example='State 4 characteristics of living organisms'),
    'model_answer': fields.String(required=True, 
                                   description='Expected answer(s)',
                                   example='Movement, Respiration, Sensitivity, Growth, Reproduction, Excretion, Nutrition'),
    'expected_answer_count': fields.Integer(description='Number of items expected (e.g., "State 4" = 4)', example=4),
    'acceptable_answers': fields.List(fields.String, description='List of acceptable answer variants'),
    'points': fields.Float(default=5.0, description='Maximum points', example=5.0)
})

short_answer_request_model = grading_ns.model('ShortAnswerGradingRequest', {
    'questions': fields.List(fields.Nested(short_answer_question_model), required=True,
                             description='List of short answer questions'),
    'student_answers': fields.Raw(required=True, 
                                   description='Dict mapping question_number to student answer',
                                   example={'1': 'Movement, Growth, Reproduction, Sensitivity'})
})

short_answer_grading_result = grading_ns.model('ShortAnswerGradingResult', {
    'question_type': fields.String(default='short_answer'),
    'total_questions': fields.Integer(),
    'grading_passes_per_question': fields.Integer(example=3),
    'criteria_used': fields.List(fields.String, example=['factual_accuracy', 'completeness', 'terminology']),
    'flagged_for_review': fields.Integer(),
    'points_earned': fields.Float(),
    'points_possible': fields.Float(),
    'percentage': fields.Float(),
    'details': fields.List(fields.Raw)
})

short_answer_success_model = grading_ns.model('ShortAnswerSuccess', {
    'success': fields.Boolean(default=True),
    'data': fields.Nested(short_answer_grading_result)
})


@grading_ns.route('/short-answer')
class GradeShortAnswer(Resource):
    @grading_ns.doc('grade_short_answer')
    @grading_ns.expect(short_answer_request_model)
    @grading_ns.response(200, 'Success', short_answer_success_model)
    @grading_ns.response(400, 'Bad Request', error_model)
    def post(self):
        """Grade short answer questions (brief factual responses)
        
        Uses 3-pass AI grading with present/partial/absent status for each criterion:
        - factual_accuracy (60%): Is the answer factually correct?
        - completeness (30%): Are all requested items present?
        - terminology (10%): Uses correct terms?
        """
        try:
            data = request.get_json()
            if not data:
                return {'success': False, 'error': 'No JSON data'}, 400
            
            questions = data.get('questions', [])
            student_answers = data.get('student_answers', {})
            
            # Ensure student_answers is a dict
            if not isinstance(student_answers, dict):
                return {'success': False, 'error': 'student_answers must be a dict mapping question_number to answer text, e.g. {"1": "Movement, Growth"}'}, 400
            
            if not questions:
                return {'success': False, 'error': 'No questions provided'}, 400
            
            from app.services.short_answer_grading import ShortAnswerGradingService
            grading_service = ShortAnswerGradingService()
            result = grading_service.grade_questions(questions, student_answers)
            
            return {'success': True, 'data': result}, 200
        except Exception as e:
            return {'success': False, 'error': str(e)}, 500


# Placeholder endpoints

@grading_ns.route('/open-ended')
class GradeOpenEnded(Resource):
    @grading_ns.doc('grade_open_ended')
    @grading_ns.expect(open_ended_request_model)
    @grading_ns.response(200, 'Success', open_ended_success_model)
    @grading_ns.response(400, 'Bad Request', error_model)
    def post(self):
        # Grade open-ended questions using AI with fixed criteria
        try:
            data = request.get_json()
            if not data:
                return {'success': False, 'error': 'No JSON data'}, 400
            
            questions = data.get('questions', [])
            student_answers = data.get('student_answers', {})
            
            if not questions:
                return {'success': False, 'error': 'No questions provided'}, 400
            
            from app.services.open_ended_grading import OpenEndedGradingService
            grading_service = OpenEndedGradingService()
            result = grading_service.grade_questions(questions, student_answers)
            
            return {'success': True, 'data': result}, 200
        except Exception as e:
            return {'success': False, 'error': str(e)}, 500


@grading_ns.route('/math-equations')
class GradeMathEquations(Resource):
    @grading_ns.doc('grade_math')
    @grading_ns.expect(math_request_model)
    @grading_ns.response(200, 'Success', math_success_model)
    @grading_ns.response(400, 'Bad Request', error_model)
    def post(self):
        # Grade math equations using PEMDAS step breakdown
        try:
            data = request.get_json()
            if not data:
                return {'success': False, 'error': 'No JSON data'}, 400
            
            questions = data.get('questions', [])
            student_answers = data.get('student_answers', {})
            
            if not questions:
                return {'success': False, 'error': 'No questions provided'}, 400
            
            from app.services.math_grading import MathGradingService
            grading_service = MathGradingService()
            result = grading_service.grade_questions(questions, student_answers)
            
            return {'success': True, 'data': result}, 200
        except Exception as e:
            return {'success': False, 'error': str(e)}, 500
