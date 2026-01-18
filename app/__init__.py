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
    
    # Flask-RESTX Namespaces (visible in Swagger UI)
    from app.routes.ocr import ocr_ns
    from app.routes.grading import grading_ns
    from app.routes.annotation import annotation_ns
    from app.routes.review_swagger import review_ns
    from app.routes.report_swagger import report_ns
    
    api.add_namespace(ocr_ns, path='/api/ocr')
    api.add_namespace(grading_ns, path='/api/grading')
    api.add_namespace(annotation_ns, path='/api/annotation')
    api.add_namespace(review_ns, path='/api/review')
    api.add_namespace(report_ns, path='/api/report')
    
    # Hidden from Swagger (registered as Blueprints only)
    from app.routes.test import test_bp
    from app.routes.report import report_bp
    from app.routes.review import review_bp
    
    # Register blueprints for direct route access (not in Swagger)
    app.register_blueprint(test_bp, url_prefix='/test')
    app.register_blueprint(report_bp)  # /api/exam/report still works
    app.register_blueprint(review_bp)  # /review still works
    
    return app
