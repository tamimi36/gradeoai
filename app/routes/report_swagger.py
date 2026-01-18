# Flask-RESTX namespace for Report endpoints (Swagger documentation)
# This wraps the existing report_bp blueprint functions for Swagger UI visibility

from flask import request
from flask_restx import Namespace, Resource, fields

report_ns = Namespace('report', description='Exam Report Generation - Professional DOCX/PDF reports')

# Request models for Swagger documentation
student_info_model = report_ns.model('StudentInfo', {
    'name': fields.String(required=True, description='Student name', example='Ahmed Hassan'),
    'section': fields.String(description='Class/section', example='Grade 10-A'),
    'date': fields.String(description='Exam date', example='2026-01-17'),
    'subject': fields.String(description='Subject name', example='Science')
})

sub_question_model = report_ns.model('SubQuestion', {
    'sub_number': fields.String(required=True, description='Sub-question identifier', example='a'),
    'student_answer': fields.String(required=True, description='Student answer', example='H2O'),
    'correct_answer': fields.String(description='Correct answer', example='H2O'),
    'status': fields.String(description='Correct, Incorrect, or Partial', example='Correct'),
    'earned_points': fields.Float(required=True, description='Points earned', example=1.0),
    'possible_points': fields.Float(required=True, description='Max points', example=1.0),
    'feedback': fields.String(description='Teacher feedback', example='')
})

grading_item_model = report_ns.model('GradingItem', {
    'question_number': fields.String(required=True, description='Question number', example='1'),
    'student_answer': fields.String(description='Student answer', example='B'),
    'correct_answer': fields.String(description='Correct answer', example='B'),
    'status': fields.String(description='Correct, Incorrect, or Partial', example='Correct'),
    'earned_points': fields.Float(required=True, description='Points earned', example=2.0),
    'possible_points': fields.Float(required=True, description='Max points', example=2.0),
    'feedback': fields.String(description='Teacher/AI feedback', example=''),
    'sub_questions': fields.List(fields.Nested(sub_question_model), description='Sub-questions (6a, 6b, 6c)')
})

grading_results_model = report_ns.model('GradingResultsReport', {
    'grading': fields.List(fields.Nested(grading_item_model), required=True, description='Graded questions'),
    'total_earned': fields.Float(required=True, description='Total points earned', example=85),
    'total_possible': fields.Float(required=True, description='Total possible points', example=100)
})

question_text_model = report_ns.model('QuestionText', {
    'question_number': fields.String(required=True, description='Question number', example='1'),
    'question_text': fields.String(description='Question text', example='What is the capital of France?')
})

report_request_model = report_ns.model('ReportRequest', {
    'student_info': fields.Nested(student_info_model, required=True, description='Student information'),
    'grading_results': fields.Nested(grading_results_model, required=True, description='Grading data'),
    'questions': fields.List(fields.Nested(question_text_model), description='Original question texts'),
    'format': fields.String(required=True, description='docx or pdf', example='docx'),
    'language': fields.String(required=True, description='en, ar, or fr', example='en')
})

error_model = report_ns.model('ReportError', {
    'error': fields.String(description='Error message')
})


@report_ns.route('/generate')
class GenerateReport(Resource):
    @report_ns.doc('generate_report')
    @report_ns.expect(report_request_model)
    @report_ns.response(200, 'Downloadable file (DOCX or PDF)')
    @report_ns.response(400, 'Bad Request', error_model)
    @report_ns.response(500, 'Server Error', error_model)
    def post(self):
        """Generate professional exam report
        
        Creates a formatted exam report document with:
        - Student information header
        - Question-by-question breakdown
        - Correct/incorrect status with feedback
        - Sub-question support (6a, 6b, 6c)
        - Final score summary
        
        Supports:
        - English (LTR)
        - Arabic (RTL with proper formatting)
        - French
        
        Output formats:
        - DOCX (Microsoft Word)
        - PDF (via conversion)
        
        Returns the file as a direct download.
        """
        from app.routes.report import generate_exam_report
        return generate_exam_report()
