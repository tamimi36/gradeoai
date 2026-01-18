from flask import request
from flask_restx import Namespace, Resource, fields
from werkzeug.datastructures import FileStorage

from app.services.workflow_service (leave it)  import WorkflowService

workflow_ns = Namespace('workflow', description='Full exam processing workflow')

upload_parser = workflow_ns.parser()
upload_parser.add_argument('file', location='files', type=FileStorage, required=True,
                           help='Image or PDF of an answered exam paper')
upload_parser.add_argument('language', type=str, default='english',
                           help='Language of the exam (english, arabic, french)')

@workflow_ns.route('/full')
class FullWorkflow(Resource):
    @workflow_ns.doc('process_full_workflow', description='Run OCR, Grade, and Annotate in one call')
    @workflow_ns.expect(upload_parser)
    def post(self):
        args = upload_parser.parse_args()
        file = args['file']
        language = args['language']
        
        if not file:
            return {'success': False, 'error': 'No file provided'}, 400
            
        try:
            workflow = WorkflowService()
            file_data = file.read()
            result = workflow.process_full_workflow(file_data, file.filename, language)
            return result, 200
            
        except Exception as e:
            return {'success': False, 'error': f'Workflow failed: {str(e)}'}, 500
