# Flask app factory
from flask import Flask
from flask_restx import Api
from dotenv import load_dotenv

load_dotenv()


def create_app():
    app = Flask(__name__)
    
    api = Api(
        app,
        version='1.0',
        title='Gradeo OCR API',
        description='Exam paper OCR and grading API powered by gemini 3.0',
        doc='/'
    )
    
    from app.routes.ocr import ocr_ns
    from app.routes.grading import grading_ns
    from app.routes.annotation import annotation_ns
    from app.routes.workflow import workflow_ns
    from app.routes.test import test_bp
    
    api.add_namespace(ocr_ns, path='/api/ocr')
    api.add_namespace(grading_ns, path='/api/grading')
    api.add_namespace(annotation_ns, path='/api/annotation')
    api.add_namespace(workflow_ns, path='/api/workflow')
    
    # Register test console blueprint
    app.register_blueprint(test_bp, url_prefix='/test')
    
    return app
