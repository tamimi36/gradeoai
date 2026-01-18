# Annotation routes for marking corrected exam papers
from flask import request
from flask_restx import Namespace, Resource, fields
import base64

annotation_ns = Namespace('annotation', description='Exam paper annotation and correction')

# Request models
grading_question_model = annotation_ns.model('GradingQuestion', {
    'question_number': fields.String(required=True, description='Question identifier', example='1'),
    'points_earned': fields.Float(required=True, description='Points student earned', example=3),
    'points_possible': fields.Float(required=True, description='Total possible points', example=5)
})

grading_results_model = annotation_ns.model('GradingResults', {
    'questions': fields.List(fields.Nested(grading_question_model), required=True,
                             description='List of graded questions'),
    'total_earned': fields.Float(required=True, description='Total points earned', example=85),
    'total_possible': fields.Float(required=True, description='Total possible points', example=100)
})

annotation_request_model = annotation_ns.model('AnnotationRequest', {
    'exam_file': fields.String(required=True, 
                                description='Base64 encoded PDF or image file'),
    'file_type': fields.String(required=True, 
                                description='File type: pdf, png, jpg',
                                example='pdf'),
    'grading_results': fields.Nested(grading_results_model, required=True,
                                      description='Grading results to annotate')
})

# Response models
annotation_result_model = annotation_ns.model('AnnotationResult', {
    'corrected_pdf': fields.String(description='Base64 encoded corrected PDF'),
    'filename': fields.String(description='Suggested filename'),
    'pages_processed': fields.Integer(description='Number of pages processed'),
    'annotations_added': fields.Integer(description='Number of question marks added'),
    'score_box_detected': fields.Boolean(description='Whether existing score box was found')
})

annotation_success_model = annotation_ns.model('AnnotationSuccess', {
    'success': fields.Boolean(default=True),
    'data': fields.Nested(annotation_result_model)
})

error_model = annotation_ns.model('AnnotationError', {
    'success': fields.Boolean(default=False),
    'error': fields.String(description='Error message')
})


@annotation_ns.route('/generate')
class GenerateAnnotation(Resource):
    @annotation_ns.doc('generate_annotation')
    @annotation_ns.expect(annotation_request_model)
    @annotation_ns.response(200, 'Success', annotation_success_model)
    @annotation_ns.response(400, 'Bad Request', error_model)
    @annotation_ns.response(500, 'Server Error', error_model)
    def post(self):
        """Generate corrected exam paper with annotation marks
        
        Takes a scanned student exam and grading results, then overlays:
        - ✓ checkmarks for correct answers
        - ✗ marks for incorrect answers  
        - Point scores next to each question
        - Final score in header (uses existing box if detected)
        
        Returns a new PDF with all annotations (original unchanged).
        """
        try:
            data = request.get_json()
            if not data:
                return {'success': False, 'error': 'No JSON data'}, 400
            
            exam_file_b64 = data.get('exam_file')
            file_type = data.get('file_type', 'pdf')
            grading_results = data.get('grading_results')
            
            if not exam_file_b64:
                return {'success': False, 'error': 'No exam_file provided'}, 400
            
            if not grading_results:
                return {'success': False, 'error': 'No grading_results provided'}, 400
            
            # Decode base64 file
            try:
                exam_bytes = base64.b64decode(exam_file_b64)
            except Exception:
                return {'success': False, 'error': 'Invalid base64 encoding'}, 400
            
            # Generate annotations (dry run - metadata only for teacher review)
            from app.services.annotation_service import AnnotationService
            service = AnnotationService()
            result = service.annotate_exam(exam_bytes, file_type, grading_results, draw_on_image=False)
            
            return {'success': True, 'data': result}, 200
            
        except Exception as e:
            return {'success': False, 'error': str(e)}, 500
