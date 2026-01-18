# Flask-RESTX namespace for Review Studio endpoints (Swagger documentation)
# This wraps the existing review_bp blueprint functions for Swagger UI visibility

from flask import request
from flask_restx import Namespace, Resource, fields

review_ns = Namespace('review', description='Review Studio - Teacher annotation review and finalization')

# Request/Response models for Swagger documentation
annotation_model = review_ns.model('AnnotationObject', {
    'id': fields.String(required=True, description='Unique identifier', example='q1_mark'),
    'type': fields.String(required=True, description='check, x, partial, label, correct_answer, feedback, final_score', example='check'),
    'text': fields.String(required=True, description='Display text', example='✓ 5/5'),
    'x': fields.Integer(required=True, description='X position in pixels', example=100),
    'y': fields.Integer(required=True, description='Y position in pixels', example=200),
    'width': fields.Integer(description='Width in pixels', example=140),
    'height': fields.Integer(description='Height in pixels', example=48),
    'color': fields.String(description='Hex color', example='#19aa19'),
    'opacity': fields.Float(description='0.0 to 1.0 transparency', example=1.0),
    'question_number': fields.Integer(description='Related question number', example=1),
    'status': fields.String(description='pending or approved', example='pending')
})

finalize_settings_model = review_ns.model('FinalizeSettings', {
    'annotations': fields.List(fields.Nested(annotation_model), description='Array of annotation objects')
})

finalize_request_model = review_ns.model('FinalizeRequest', {
    'image': fields.String(required=True, description='Base64 encoded image'),
    'settings': fields.Nested(finalize_settings_model, description='Settings with annotations array')
})

detect_request_model = review_ns.model('DetectRequest', {
    'image': fields.String(required=True, description='Base64 encoded annotated image')
})

detect_response_model = review_ns.model('DetectResponse', {
    'annotations': fields.List(fields.Nested(annotation_model), description='Detected annotations'),
    'image_width': fields.Integer(description='Image width in pixels'),
    'image_height': fields.Integer(description='Image height in pixels')
})

error_model = review_ns.model('ReviewError', {
    'error': fields.String(description='Error message')
})


# Note: The /review GET endpoint (Review Studio GUI) is accessed via blueprint at /review
# It is not exposed in Swagger as it returns HTML, not JSON API.


@review_ns.route('/finalize')
class FinalizeReview(Resource):
    @review_ns.doc('finalize_review')
    @review_ns.expect(finalize_request_model)
    @review_ns.response(200, 'PNG image download')
    @review_ns.response(400, 'Bad Request', error_model)
    @review_ns.response(500, 'Server Error', error_model)
    def post(self):
        """Render annotations onto the exam image
        
        Takes the teacher's customized annotations and renders them
        onto the original exam image with pixel-perfect fidelity.
        
        Returns a downloadable PNG image with all annotations applied.
        
        Annotation types:
        - check: Green checkmark with score (✓ 5/5)
        - x: Red X mark with score (✗ 0/5)
        - partial: Yellow dash with score (— 3/5)
        - label: Text feedback label
        - correct_answer: Shows correct answer for wrong questions
        - feedback: AI/teacher feedback text
        - final_score: Large final score display (TOTAL: 85/100)
        """
        from app.routes.review import finalize_review
        return finalize_review()


@review_ns.route('/detect')
class DetectAnnotations(Resource):
    @review_ns.doc('detect_annotations')
    @review_ns.expect(detect_request_model)
    @review_ns.response(200, 'Detection results', detect_response_model)
    @review_ns.response(500, 'Server Error', error_model)
    def post(self):
        """Detect existing annotations in an image
        
        Analyzes an already-annotated exam image and extracts
        the annotation metadata (positions, types, colors).
        
        First checks for embedded Gradeo metadata in the PNG.
        Falls back to AI vision detection if not found.
        
        Useful for re-editing previously annotated exams.
        """
        from app.routes.review import detect_existing
        return detect_existing()
