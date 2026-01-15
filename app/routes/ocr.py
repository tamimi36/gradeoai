# OCR endpoints for exam paper extraction
from flask import request
from flask_restx import Namespace, Resource, fields
from werkzeug.datastructures import FileStorage

from app.config import Config
from app.services.gemini_ocr import GeminiOCRService


ocr_ns = Namespace('ocr', description='Exam paper OCR')

upload_parser = ocr_ns.parser()
upload_parser.add_argument('file', location='files', type=FileStorage, required=True,
                           help='Image (PNG, JPG, WEBP) or PDF file')

# ============ Response Models ============

metadata_model = ocr_ns.model('ExamMetadata', {
    'exam_title': fields.String(description='Title of the exam'),
    'subject': fields.String(description='Subject/course'),
    'grade_level': fields.String(description='Grade/class level'),
    'total_questions': fields.Integer(description='Total number of questions'),
    'total_points': fields.Float(description='Total points'),
    'duration': fields.String(description='Exam duration'),
    'instructions': fields.String(description='General instructions'),
    'date': fields.String(description='Exam date'),
    'sections': fields.List(fields.String, description='Section names')
})

# Type-specific fields
matching_pair_model = ocr_ns.model('MatchingPair', {
    'left_item': fields.String(description='Item from left column'),
    'left_id': fields.String(description='Left item ID (1, 2, A)'),
    'right_item': fields.String(description='Item from right column'),
    'right_id': fields.String(description='Right item ID (a, b, i)'),
    'correct_match': fields.String(description='Correct right_id for left_id')
})

ordering_item_model = ocr_ns.model('OrderingItem', {
    'item_id': fields.String(description='Item identifier'),
    'content': fields.String(description='Item content/text'),
    'correct_position': fields.Integer(description='Correct position (1-based)')
})

labeling_item_model = ocr_ns.model('LabelingItem', {
    'label_id': fields.String(description='Label identifier'),
    'pointer_description': fields.String(description='What the pointer/arrow indicates'),
    'correct_label': fields.String(description='Correct label text')
})

sub_question_model = ocr_ns.model('SubQuestion', {
    'sub_id': fields.String(description='Sub-question ID (a, b, 1, 2)'),
    'question_type': fields.String(description='Type of sub-question'),
    'question_text': fields.String(description='Question text'),
    'options': fields.Raw(description='MCQ options'),
    'blanks': fields.List(fields.String, description='Fill-in-blank answers'),
    'correct_answer': fields.Raw(description='Correct answer'),
    'points': fields.Float(description='Points')
})

question_model = ocr_ns.model('Question', {
    'order': fields.Integer(required=True, description='Position in document (1-based)'),
    'question_number': fields.String(required=True, description='Number as shown (1, Q1, س1)'),
    'question_type': fields.String(required=True, description='Type: multiple_choice, true_false, matching, fill_in_blank, ordering, open_ended, compare_contrast, definition, labeling, labeling_image, math_equation, table, parent'),
    'question_text': fields.String(required=True, description='Question text'),
    
    # MCQ
    'options': fields.Raw(description='MCQ options: {"A": "text", "B": "text"}'),
    
    # Fill in blank
    'blanks': fields.List(fields.String, description='Correct answers for blanks in order'),
    
    # Matching
    'left_column': fields.List(fields.Raw, description='Left column items'),
    'right_column': fields.List(fields.Raw, description='Right column items'),
    'correct_matches': fields.Raw(description='Correct pairings: {"1": "a", "2": "b"}'),
    
    # Ordering
    'ordering_items': fields.List(fields.Nested(ordering_item_model), description='Items to order'),
    'correct_order': fields.List(fields.String, description='Correct sequence of IDs'),
    
    # Labeling
    'labeling_items': fields.List(fields.Nested(labeling_item_model), description='Diagram labels'),
    'diagram_description': fields.String(description='Description of diagram'),
    
    # Compare/Contrast
    'compare_items': fields.List(fields.String, description='Items to compare'),
    'comparison_aspects': fields.List(fields.String, description='Aspects to compare on'),
    
    # Definition
    'term_to_define': fields.String(description='Term requiring definition'),
    
    # Math
    'math_content': fields.String(description='Math in LaTeX format'),
    
    # Table
    'table_headers': fields.List(fields.String, description='Table column headers'),
    'table_rows': fields.List(fields.Raw, description='Table rows'),
    
    # Answers
    'correct_answer': fields.Raw(description='Correct answer if marked'),
    'answer_markdown': fields.String(description='Answer in LaTeX'),
    'expected_keywords': fields.List(fields.String, description='Expected keywords'),
    'model_answer': fields.String(description='Model/sample answer'),
    
    # Sub-questions
    'sub_questions': fields.List(fields.Nested(sub_question_model), description='Sub-questions for parent type'),
    
    # Scoring
    'points': fields.Float(description='Points for question'),
    'instructions': fields.String(description='Question-specific instructions')
})

structured_data_model = ocr_ns.model('StructuredData', {
    'questions': fields.List(fields.Nested(question_model), required=True, description='All questions in document order'),
    'metadata': fields.Nested(metadata_model, description='Exam metadata')
})

ocr_result_model = ocr_ns.model('OCRResult', {
    'extracted_text': fields.String(required=True, description='Complete raw text from document'),
    'structured_data': fields.Nested(structured_data_model, required=True, description='Structured questions'),
    'confidence_score': fields.Float(required=True, description='Extraction confidence (0.0-1.0)'),
    'language': fields.String(required=True, description='Language used for extraction')
})

success_model = ocr_ns.model('OCRSuccess', {
    'success': fields.Boolean(default=True, description='Request success'),
    'data': fields.Nested(ocr_result_model, description='OCR results')
})

error_model = ocr_ns.model('OCRError', {
    'success': fields.Boolean(default=False, description='Request failed'),
    'error': fields.String(description='Error message')
})


def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in Config.get_allowed_extensions()


def get_file_type(filename: str) -> str:
    ext = filename.rsplit('.', 1)[1].lower()
    return 'pdf' if ext in Config.ALLOWED_PDF_EXTENSIONS else 'image'


def process_ocr(language: str):
    if 'file' not in request.files:
        return {'success': False, 'error': 'No file provided'}, 400
    
    file = request.files['file']
    
    if file.filename == '':
        return {'success': False, 'error': 'No file selected'}, 400
    
    if not allowed_file(file.filename):
        return {'success': False, 'error': f'Invalid file type. Allowed: {", ".join(Config.get_allowed_extensions())}'}, 400
    
    try:
        ocr = GeminiOCRService()
        data = file.read()
        
        if get_file_type(file.filename) == 'pdf':
            result = ocr.process_pdf(data, language)
        else:
            result = ocr.process_image(data, language)
        
        return {'success': True, 'data': result}, 200
        
    except ValueError as e:
        return {'success': False, 'error': str(e)}, 500
    except Exception as e:
        return {'success': False, 'error': f'OCR failed: {str(e)}'}, 500


@ocr_ns.route('/english')
class EnglishOCR(Resource):
    @ocr_ns.doc('ocr_english', description='Extract English exam paper with all question types')
    @ocr_ns.expect(upload_parser)
    @ocr_ns.response(200, 'Extraction successful', success_model)
    @ocr_ns.response(400, 'Invalid request', error_model)
    @ocr_ns.response(500, 'Server error', error_model)
    def post(self):
        # Extract English exam - all question types
        return process_ocr('english')


@ocr_ns.route('/arabic')
class ArabicOCR(Resource):
    @ocr_ns.doc('ocr_arabic', description='Extract Arabic exam paper (الاختيار من متعدد, الصواب والخطأ, المزاوجة, etc.)')
    @ocr_ns.expect(upload_parser)
    @ocr_ns.response(200, 'Extraction successful', success_model)
    @ocr_ns.response(400, 'Invalid request', error_model)
    @ocr_ns.response(500, 'Server error', error_model)
    def post(self):
        # Extract Arabic exam - all question types
        return process_ocr('arabic')


@ocr_ns.route('/french')
class FrenchOCR(Resource):
    @ocr_ns.doc('ocr_french', description='Extract French exam paper (Choix multiples, Vrai/Faux, Appariement, etc.)')
    @ocr_ns.expect(upload_parser)
    @ocr_ns.response(200, 'Extraction successful', success_model)
    @ocr_ns.response(400, 'Invalid request', error_model)
    @ocr_ns.response(500, 'Server error', error_model)
    def post(self):
        # Extract French exam - all question types
        return process_ocr('french')
