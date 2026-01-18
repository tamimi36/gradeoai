# Report routes for generating exam reports
from flask import Blueprint, request, jsonify, send_file
from app.services.exam_report_service import ExamReportService
import io

report_bp = Blueprint('report', __name__)
report_service = ExamReportService()


@report_bp.route('/api/exam/report', methods=['POST'])
def generate_exam_report():
    """Generate professional exam report in DOCX or PDF format.
    
    Request JSON:
    {
        "student_info": {
            "name": "John Doe",
            "section": "Grade 10-A",
            "date": "2026-01-17",
            "subject": "Mathematics"
        },
        "grading_results": {
            "grading": [...],
            "total_earned": 85,
            "total_possible": 100
        },
        "questions": [...],
        "format": "docx" or "pdf",
        "language": "en", "ar", or "fr"
    }
    
    Returns: Downloadable file
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        student_info = data.get('student_info', {})
        grading_results = data.get('grading_results', {})
        questions = data.get('questions', [])
        file_format = data.get('format', 'docx').lower()
        language = data.get('language', 'en')
        
        if file_format not in ['docx', 'pdf']:
            return jsonify({'error': 'Format must be "docx" or "pdf"'}), 400
        
        # Generate report
        report_bytes = report_service.generate_report(
            student_info=student_info,
            grading_results=grading_results,
            questions=questions,
            format=file_format,
            language=language
        )
        
        # Prepare file for download
        student_name = student_info.get('name', 'Student').replace(' ', '_')
        filename = f"Exam_Report_{student_name}.{file_format}"
        
        if file_format == 'docx':
            mimetype = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        else:
            mimetype = 'application/pdf'
        
        return send_file(
            io.BytesIO(report_bytes),
            mimetype=mimetype,
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
