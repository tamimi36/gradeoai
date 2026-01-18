# Test routes with GUI for evaluating all endpoints
from flask import Blueprint, render_template_string, jsonify, request, send_from_directory
import base64
import json
import os

test_bp = Blueprint('test', __name__)

# Get path to static samples
SAMPLES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'samples')

# Sample test data for all endpoints
SAMPLE_DATA = {
    'mcq': {
        'questions': [
            {'question_number': '1', 'question_text': 'What is the capital of France?', 'options': {'A': 'London', 'B': 'Paris', 'C': 'Berlin', 'D': 'Madrid'}, 'correct_answer': 'B'},
            {'question_number': '2', 'question_text': 'Which planet is largest?', 'options': {'A': 'Earth', 'B': 'Mars', 'C': 'Jupiter', 'D': 'Saturn'}, 'correct_answer': 'C'},
            {'question_number': '3', 'question_text': 'What is 2+2?', 'options': {'A': '3', 'B': '4', 'C': '5', 'D': '6'}, 'correct_answer': 'B'}
        ],
        'student_answers': {'1': 'B', '2': 'C', '3': 'A'},
        'points_per_question': 2.0
    },
    'true_false': {
        'questions': [
            {'question_number': '1', 'statement': 'The sun is a star', 'correct_answer': True},
            {'question_number': '2', 'statement': 'Water freezes at 50°C', 'correct_answer': False},
            {'question_number': '3', 'statement': 'Python is a programming language', 'correct_answer': True}
        ],
        'student_answers': {'1': True, '2': False, '3': True},
        'points_per_question': 1.0
    },
    'matching': {
        'questions': [
            {
                'question_number': '1',
                'left_column': [{'id': '1', 'text': 'Dog'}, {'id': '2', 'text': 'Cat'}, {'id': '3', 'text': 'Bird'}],
                'right_column': [{'id': 'a', 'text': 'Meows'}, {'id': 'b', 'text': 'Barks'}, {'id': 'c', 'text': 'Chirps'}],
                'correct_matches': {'1': 'b', '2': 'a', '3': 'c'}
            }
        ],
        'student_answers': {'1': {'1': 'b', '2': 'a', '3': 'c'}},
        'points_per_pair': 1.0
    },
    'fill_in_blank': {
        'questions': [
            {'question_number': '1', 'question_text': 'The capital of Japan is _____.', 'blanks': ['Tokyo']},
            {'question_number': '2', 'question_text': 'Water is made of _____ and oxygen.', 'blanks': ['hydrogen']}
        ],
        'student_answers': {'1': ['Tokyo'], '2': ['hydrogen']},
        'points_per_blank': 2.0
    },
    'ordering': {
        'questions': [
            {
                'question_number': '1',
                'question_text': 'Order these planets from closest to farthest from Sun',
                'ordering_items': [
                    {'item_id': 'A', 'content': 'Earth'},
                    {'item_id': 'B', 'content': 'Mercury'},
                    {'item_id': 'C', 'content': 'Mars'}
                ],
                'correct_order': ['B', 'A', 'C']
            }
        ],
        'student_answers': {'1': ['B', 'A', 'C']},
        'points_per_position': 1.0
    },
    'labeling': {
        'questions': [
            {
                'question_number': '1',
                'diagram_description': 'Human heart diagram',
                'labeling_items': [
                    {'label_id': '1', 'pointer_description': 'Upper left chamber', 'correct_label': 'Left Atrium'},
                    {'label_id': '2', 'pointer_description': 'Lower left chamber', 'correct_label': 'Left Ventricle'},
                    {'label_id': '3', 'pointer_description': 'Main artery', 'correct_label': 'Aorta'}
                ]
            }
        ],
        'student_answers': {'1': {'1': 'Left Atrium', '2': 'Left Ventricle', '3': 'Aorta'}},
        'points_per_label': 1.0
    },
    'labeling_image': {
        'description': 'Upload a diagram image with handwritten student labels. Uses AI Vision to OCR and grade.',
        'questions': [
            {
                'question_number': '1',
                'diagram_description': 'Human heart diagram with student handwritten labels',
                'labeling_items': [
                    {'label_id': '1', 'pointer_description': 'Upper left chamber', 'correct_label': 'Left Atrium'},
                    {'label_id': '2', 'pointer_description': 'Lower left chamber', 'correct_label': 'Left Ventricle'},
                    {'label_id': '3', 'pointer_description': 'Main artery from heart', 'correct_label': 'Aorta'}
                ],
                'points': 3.0
            }
        ],
        'student_images': {'1': 'UPLOAD_IMAGE_BASE64_HERE'}
    },
    'short_answer': {
        'questions': [
            {
                'question_number': '1',
                'question_text': 'State 4 characteristics of living organisms',
                'model_answer': 'Movement, Respiration, Sensitivity, Growth, Reproduction, Excretion, Nutrition',
                'expected_answer_count': 4,
                'points': 4.0
            },
            {
                'question_number': '2',
                'question_text': 'What is the capital of France?',
                'model_answer': 'Paris',
                'points': 1.0
            },
            {
                'question_number': '3',
                'question_text': 'Name 3 primary colors',
                'model_answer': 'Red, Blue, Yellow',
                'expected_answer_count': 3,
                'points': 3.0
            }
        ],
        'student_answers': {
            '1': 'Movement, Growth, Respiration, Reproduction',
            '2': 'Paris',
            '3': 'Red, Blue, Yellow'
        }
    },
    'open_ended': {
        'questions': [
            {
                'question_number': '1',
                'question_text': 'Explain the process of photosynthesis.',
                'model_answer': 'Photosynthesis is the process by which plants convert sunlight, water, and carbon dioxide into glucose and oxygen. It occurs in the chloroplasts using chlorophyll.',
                'expected_keywords': ['sunlight', 'water', 'carbon dioxide', 'glucose', 'oxygen', 'chlorophyll'],
                'points': 10.0,
                'answer_length': 'long'
            }
        ],
        'student_answers': {
            '1': 'Photosynthesis is when plants use sunlight and water to make food. They take in carbon dioxide and release oxygen. The process happens in the leaves using chlorophyll.'
        }
    },
    'compare_contrast': {
        'questions': [
            {
                'question_number': '1',
                'question_text': 'Compare and contrast mitosis and meiosis.',
                'compare_items': ['Mitosis', 'Meiosis'],
                'grading_table': [
                    {'item': 'Both are types of cell division', 'points': 2},
                    {'item': 'Mitosis produces 2 identical cells', 'points': 2},
                    {'item': 'Meiosis produces 4 different cells', 'points': 2},
                    {'item': 'Mitosis is for growth and repair', 'points': 2},
                    {'item': 'Meiosis is for reproduction', 'points': 2}
                ],
                'points': 10.0
            }
        ],
        'student_answers': {
            '1': 'Mitosis and meiosis are both cell division processes. Mitosis creates two identical daughter cells for growth. Meiosis produces four genetically different cells for sexual reproduction.'
        }
    },
    'definition': {
        'questions': [
            {
                'question_number': '1',
                'term_to_define': 'Photosynthesis',
                'model_answer': 'Photosynthesis is the biological process by which plants and other organisms convert light energy into chemical energy stored in glucose, using water and carbon dioxide.',
                'expected_keywords': ['light', 'energy', 'glucose', 'plants', 'carbon dioxide', 'water'],
                'points': 10.0
            }
        ],
        'student_answers': {
            '1': 'Photosynthesis is how plants make food using sunlight. They absorb water and carbon dioxide to produce glucose and release oxygen.'
        }
    },
    'table': {
        'questions': [
            {
                'question_number': '1',
                'question_text': 'Complete the table about states of matter.',
                'table_headers': ['State', 'Shape', 'Volume'],
                'grading_table': [
                    {'item': 'Solid has fixed shape', 'points': 2},
                    {'item': 'Liquid takes container shape', 'points': 2},
                    {'item': 'Gas has no fixed shape or volume', 'points': 2}
                ],
                'points': 6.0
            }
        ],
        'student_answers': {
            '1': 'Solids have a fixed shape and volume. Liquids take the shape of their container but have fixed volume. Gases have neither fixed shape nor volume.'
        }
    },
    'math_equations': {
        'questions': [
            {
                'question_number': '1',
                'question_text': 'Simple PEMDAS: (2 + 3) × 4 - 6 ÷ 2',
                'math_content': '(2 + 3) × 4 - 6 ÷ 2',
                'correct_answer': '17',
                'points': 10.0
            },
            {
                'question_number': '2',
                'question_text': 'Nested Parentheses: ((4 + 2) × 3) - (10 ÷ 2)',
                'math_content': '((4 + 2) × 3) - (10 ÷ 2)',
                'correct_answer': '13',
                'points': 10.0
            },
            {
                'question_number': '3',
                'question_text': 'With Exponent: 2³ + 4 × 5 - 10',
                'math_content': '2³ + 4 × 5 - 10',
                'correct_answer': '18',
                'points': 10.0
            },
            {
                'question_number': '4',
                'question_text': 'Complex: 100 ÷ (5 × 2) + 3² - 1',
                'math_content': '100 ÷ (5 × 2) + 3² - 1',
                'correct_answer': '18',
                'points': 10.0
            },
            {
                'question_number': '5',
                'question_text': 'Multi-step: 8 + 2 × (9 - 4) ÷ 5 - 1',
                'math_content': '8 + 2 × (9 - 4) ÷ 5 - 1',
                'correct_answer': '9',
                'points': 10.0
            }
        ],
        'student_answers': {
            '1': '2+3=5\\n5×4=20\\n6÷2=3\\n20-3=17',
            '2': '4+2=6\\n6×3=18\\n10÷2=5\\n18-5=13',
            '3': '2³=8\\n4×5=20\\n8+20=28\\n28-10=18',
            '4': '5×2=10\\n100÷10=10\\n3²=9\\n10+9=19\\n19-1=18',
            '5': '9-4=5\\n2×5=10\\n10÷5=2\\n8+2=10\\n10-1=9'
        }
    },
    'ocr_english': {
        'language': 'english',
        'description': 'Upload an exam paper image to extract questions using OCR'
    },
    'ocr_arabic': {
        'language': 'arabic', 
        'description': 'رفع صورة ورقة امتحان لاستخراج الأسئلة'
    },
    'ocr_french': {
        'language': 'french',
        'description': "Télécharger une image d'examen pour extraire les questions"
    },
    'annotation': {
        'description': 'Upload graded exam to add correction marks. Now shows correct answers for wrong MCQ/T/F and feedback for AI-graded questions.',
        'grading_results': {
            'questions': [
                {
                    'question_number': '1', 
                    'question_type': 'multiple_choice',
                    'points_earned': 2, 
                    'points_possible': 2,
                    'correct_answer': 'B'
                },
                {
                    'question_number': '2', 
                    'question_type': 'multiple_choice',
                    'points_earned': 2, 
                    'points_possible': 2,
                    'correct_answer': 'B'
                },
                {
                    'question_number': '3', 
                    'question_type': 'multiple_choice',
                    'points_earned': 0, 
                    'points_possible': 2,
                    'correct_answer': 'C',
                    'feedback': 'Jupiter is the largest planet in our solar system'
                }
            ],
            'total_earned': 4,
            'total_possible': 6
        }
    },
    'annotation_arabic': {
        'description': 'مقال الحرب العالمية الأولى - اختبار التصحيح مع الملاحظات بالعربية',
        'grading_results': {
            'questions': [
                {
                    'question_number': '1', 
                    'question_type': 'open_ended',
                    'points_earned': 7, 
                    'points_possible': 10,
                    'correct_answer': '',
                    'feedback': 'تحليل جيد لأسباب الحرب العالمية الأولى. ذكرت اغتيال الأرشيدوق فرانز فرديناند والتحالفات العسكرية. ينقصك ذكر السباق على التسلح والتنافس الاستعماري. حاول ربط الأسباب ببعضها البعض.'
                }
            ],
            'total_earned': 7,
            'total_possible': 10
        }
    },
    'annotation_french': {
        'description': 'Dissertation sur la Première Guerre mondiale - Test avec commentaires en français',
        'grading_results': {
            'questions': [
                {
                    'question_number': '1', 
                    'question_type': 'open_ended',
                    'points_earned': 8, 
                    'points_possible': 10,
                    'correct_answer': '',
                    'feedback': 'Excellente analyse des conséquences de la Première Guerre mondiale. Vous avez bien mentionné le Traité de Versailles et la création de la Société des Nations. Il manque une discussion sur les changements territoriaux en Europe de l\'Est.'
                }
            ],
            'total_earned': 8,
            'total_possible': 10
        }
    },
    'exam_report': {
        'description': 'Generate professional exam report. Supports English, Arabic (RTL), French. Includes sub-questions.',
        'student_info': {
            'name': 'Ahmed Hassan / أحمد حسن',
            'section': 'Grade 10-A',
            'date': '2026-01-17',
            'subject': 'Multilingual Science Test'
        },
        'grading_results': {
            'grading': [
                {
                    'question_number': '1',
                    'student_answer': 'B',
                    'correct_answer': 'B',
                    'earned_points': 2,
                    'possible_points': 2,
                    'feedback': ''
                },
                {
                    'question_number': '2',
                    'student_answer': 'A',
                    'correct_answer': 'C',
                    'earned_points': 0,
                    'possible_points': 2,
                    'feedback': 'Carbon is element #6'
                },
                {
                    'question_number': '3',
                    'student_answer': 'القاهرة',
                    'correct_answer': 'القاهرة',
                    'earned_points': 2,
                    'possible_points': 2,
                    'feedback': ''
                },
                {
                    'question_number': '4',
                    'student_answer': 'صح',
                    'correct_answer': 'خطأ',
                    'earned_points': 0,
                    'possible_points': 2,
                    'feedback': 'القمر يدور حول الأرض وليس العكس'
                },
                {
                    'question_number': '5',
                    'student_answer': 'Paris',
                    'correct_answer': 'Paris',
                    'earned_points': 2,
                    'possible_points': 2,
                    'feedback': ''
                },
                {
                    'question_number': '6',
                    'sub_questions': [
                        {
                            'sub_number': 'a',
                            'student_answer': 'H2O',
                            'correct_answer': 'H2O',
                            'earned_points': 1,
                            'possible_points': 1,
                            'feedback': ''
                        },
                        {
                            'sub_number': 'b',
                            'student_answer': 'NaCl',
                            'correct_answer': 'NaCl',
                            'earned_points': 1,
                            'possible_points': 1,
                            'feedback': ''
                        },
                        {
                            'sub_number': 'c',
                            'student_answer': 'CO2',
                            'correct_answer': 'CO3',
                            'earned_points': 0,
                            'possible_points': 1,
                            'feedback': 'Carbonate is CO3, not CO2'
                        }
                    ]
                },
                {
                    'question_number': '7',
                    'student_answer': 'La Révolution a changé la société',
                    'correct_answer': '',
                    'earned_points': 3,
                    'possible_points': 5,
                    'feedback': 'Bonne analyse mais il manque des détails sur les conséquences économiques'
                }
            ],
            'total_earned': 11,
            'total_possible': 18
        },
        'questions': [
            {'question_number': '1', 'question_text': 'What is the chemical symbol for water?'},
            {'question_number': '2', 'question_text': 'Which element has atomic number 6?'},
            {'question_number': '3', 'question_text': 'ما هي عاصمة مصر؟'},
            {'question_number': '4', 'question_text': 'الشمس تدور حول الأرض. (صح / خطأ)'},
            {'question_number': '5', 'question_text': 'Quelle est la capitale de la France?'},
            {'question_number': '6', 'question_text': 'Write the chemical formulas for: (a) Water (b) Salt (c) Carbonate'},
            {'question_number': '7', 'question_text': 'Expliquez le rôle de la Révolution française'}
        ],
        'format': 'docx',
        'language': 'en'
    },
    'exam_report_arabic': {
        'description': 'إنشاء تقرير امتحان احترافي بصيغة DOCX أو PDF',
        'student_info': {
            'name': 'محمد علي',
            'section': 'الصف العاشر - أ',
            'date': '2026-01-17',
            'subject': 'العلوم'
        },
        'grading_results': {
            'grading': [
                {'question_number': '1', 'student_answer': 'ب', 'correct_answer': 'ب', 'status': 'Correct', 'earned_points': 2, 'possible_points': 2},
                {'question_number': '2', 'student_answer': 'أ', 'correct_answer': 'ج', 'status': 'Incorrect', 'earned_points': 0, 'possible_points': 2, 'feedback': 'الجواب الصحيح هو الكربون'}
            ],
            'total_earned': 2,
            'total_possible': 4
        },
        'questions': [
            {'question_number': '1', 'question_text': 'ما هو الرمز الكيميائي للماء؟'},
            {'question_number': '2', 'question_text': 'أي عنصر له العدد الذري 6؟'}
        ],
        'language': 'ar'
    },
    'annotation_customize': {
        'description': 'Customize annotation positions, colors, fonts, and labels manually.',
        'settings': {
            'checkColor': '#19aa19',
            'xColor': '#be1e1e',
            'partialColor': '#c89600',
            'fontFamily': 'Segoe Script',
            'markSize': 32,
            'fontSize': 24,
            'bgOpacity': 160
        },
        'sample_annotations': [
            {'id': 'q1', 'type': 'check', 'text': '✓ 2/2', 'x': 50, 'y': 150, 'color': '#19aa19', 'width': 100, 'height': 40, 'status': 'approved'},
            {'id': 'q2', 'type': 'x', 'text': '✗ 0/2', 'x': 50, 'y': 250, 'color': '#be1e1e', 'width': 100, 'height': 40, 'status': 'pending'},
            {'id': 'q2_correct', 'type': 'correct_answer', 'text': 'Correct: Photosynthesis', 'x': 70, 'y': 300, 'width': 250, 'height': 30, 'status': 'pending'},
            {'id': 'q3', 'type': 'partial', 'text': '— 1/2', 'x': 50, 'y': 400, 'color': '#c89600', 'width': 100, 'height': 40, 'status': 'pending'},
            {'id': 'q3_fb', 'type': 'feedback', 'text': 'Mention the role of CO2 and water', 'x': 70, 'y': 450, 'width': 300, 'height': 60, 'status': 'pending'}
        ],
        'scenarios': [
            'Simple MCQ Correction',
            'High-Density Review',
            'Diagram Labeling Adjustments'
        ],
        'presets': ['Classic Teacher', 'Modern Minimal', 'Professional']
    }
}

# HTML Template for Test GUI
TEST_HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Gradeo API - Test Console</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            color: #eee;
        }
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
        header {
            text-align: center;
            padding: 30px 0;
            border-bottom: 1px solid #333;
            margin-bottom: 30px;
        }
        header h1 { font-size: 2.5rem; color: #4fc3f7; margin-bottom: 10px; }
        header p { color: #888; font-size: 1.1rem; }
        
        .grid { display: grid; grid-template-columns: 380px 1fr; gap: 30px; }
        
        .sidebar {
            background: #1e293b;
            border-radius: 12px;
            padding: 20px;
            height: fit-content;
            position: sticky;
            top: 20px;
        }
        .sidebar h2 { color: #4fc3f7; margin-bottom: 15px; font-size: 1.2rem; }
        .sidebar h3 { color: #888; margin: 20px 0 10px; font-size: 0.9rem; text-transform: uppercase; }
        
        .endpoint-list { list-style: none; }
        .endpoint-list li {
            padding: 12px 15px;
            margin-bottom: 8px;
            background: #0f172a;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.3s;
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 0.9rem;
        }
        .endpoint-list li:hover { background: #1e40af; transform: translateX(5px); }
        .endpoint-list li.active { background: #2563eb; border-left: 4px solid #4fc3f7; }
        .endpoint-list li .method {
            background: #22c55e;
            color: #000;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.7rem;
            font-weight: bold;
        }
        .endpoint-list li .method.ocr { background: #f59e0b; }
        .endpoint-list li .method.annotate { background: #8b5cf6; }
        
        .main-content { min-height: 600px; }
        
        .panel {
            background: #1e293b;
            border-radius: 12px;
            padding: 25px;
            margin-bottom: 20px;
        }
        .panel h3 {
            color: #4fc3f7;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 1px solid #334155;
        }
        
        .code-block {
            background: #0f172a;
            border-radius: 8px;
            padding: 15px;
            overflow-x: auto;
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 0.85rem;
            max-height: 400px;
            overflow-y: auto;
        }
        .code-block pre { white-space: pre-wrap; word-wrap: break-word; }
        
        .btn {
            padding: 12px 24px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 1rem;
            font-weight: 600;
            transition: all 0.3s;
        }
        .btn-primary {
            background: linear-gradient(135deg, #2563eb, #1d4ed8);
            color: white;
        }
        .btn-primary:hover { background: linear-gradient(135deg, #3b82f6, #2563eb); transform: translateY(-2px); }
        .btn-secondary {
            background: #475569;
            color: white;
            margin-left: 10px;
        }
        .btn-secondary:hover { background: #64748b; }
        
        .response-panel { margin-top: 20px; }
        .response-header {
            display: flex;
            align-items: center;
            gap: 15px;
            margin-bottom: 15px;
        }
        .status-badge {
            padding: 5px 15px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 0.9rem;
        }
        .status-success { background: #22c55e; color: #000; }
        .status-error { background: #ef4444; color: #fff; }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 15px;
            margin-bottom: 20px;
        }
        .stat-card {
            background: #0f172a;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
        }
        .stat-card .value { font-size: 1.8rem; font-weight: bold; color: #4fc3f7; }
        .stat-card .label { color: #888; font-size: 0.8rem; margin-top: 5px; }
        
        .loading {
            display: none;
            text-align: center;
            padding: 40px;
        }
        .loading.active { display: block; }
        .spinner {
            width: 50px;
            height: 50px;
            border: 4px solid #334155;
            border-top-color: #4fc3f7;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 0 auto 15px;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
        
        .description {
            background: #0f172a;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            border-left: 4px solid #4fc3f7;
        }
        .description p { line-height: 1.6; }
        
        textarea {
            width: 100%;
            min-height: 200px;
            background: #0f172a;
            border: 1px solid #334155;
            border-radius: 8px;
            padding: 15px;
            color: #eee;
            font-family: 'Consolas', monospace;
            font-size: 0.85rem;
            resize: vertical;
        }
        textarea:focus { outline: none; border-color: #4fc3f7; }
        
        .upload-area {
            border: 2px dashed #475569;
            border-radius: 12px;
            padding: 40px;
            text-align: center;
            margin-bottom: 20px;
            cursor: pointer;
            transition: all 0.3s;
        }
        .upload-area:hover { border-color: #4fc3f7; background: rgba(79, 195, 247, 0.1); }
        .upload-area.has-file { border-color: #22c55e; background: rgba(34, 197, 94, 0.1); }
        .upload-area input { display: none; }
        .upload-area .icon { font-size: 3rem; margin-bottom: 10px; }
        
        .preview-image {
            max-width: 100%;
            max-height: 300px;
            border-radius: 8px;
            margin-top: 15px;
        }
        
        .sample-images {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
            margin-top: 15px;
        }
        .sample-card {
            background: #0f172a;
            border-radius: 8px;
            padding: 15px;
            cursor: pointer;
            transition: all 0.3s;
            text-align: center;
        }
        .sample-card:hover { background: #1e40af; }
        .sample-card img { max-width: 100%; height: 120px; object-fit: cover; border-radius: 4px; margin-bottom: 10px; }
        .sample-card p { font-size: 0.85rem; color: #888; }
        
        .json-key { color: #f472b6; }
        .json-string { color: #22c55e; }
        .json-number { color: #fbbf24; }
        .json-boolean { color: #60a5fa; }
        
        /* Documentation Modal Styles */
        .modal-overlay {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.8);
            z-index: 1000;
            overflow-y: auto;
            padding: 40px 20px;
        }
        .modal-overlay.active { display: block; }
        .modal-content {
            background: #1e293b;
            max-width: 900px;
            margin: 0 auto;
            border-radius: 12px;
            padding: 30px;
            position: relative;
        }
        .modal-close {
            position: absolute;
            top: 15px;
            right: 20px;
            font-size: 2rem;
            cursor: pointer;
            color: #888;
        }
        .modal-close:hover { color: #fff; }
        .doc-title { color: #4fc3f7; margin-bottom: 20px; font-size: 1.5rem; }
        .doc-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: bold;
            margin-bottom: 20px;
        }
        .doc-badge.ai { background: linear-gradient(135deg, #8b5cf6, #6366f1); color: #fff; }
        .doc-badge.code { background: #22c55e; color: #000; }
        .doc-badge.vision { background: #f59e0b; color: #000; }
        
        .doc-section {
            background: #0f172a;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 15px;
        }
        .doc-section h4 { color: #4fc3f7; margin-bottom: 15px; }
        .doc-section ul, .doc-section ol { padding-left: 25px; line-height: 1.8; }
        .doc-section li { margin-bottom: 5px; }
        .doc-section pre {
            background: #1a1a2e;
            padding: 15px;
            border-radius: 6px;
            overflow-x: auto;
            font-size: 0.85rem;
            margin-top: 10px;
        }
        
        .doc-tabs {
            display: flex;
            gap: 10px;
            margin-bottom: 15px;
        }
        .doc-tab {
            padding: 8px 16px;
            background: #334155;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.9rem;
        }
        .doc-tab:hover { background: #475569; }
        .doc-tab.active { background: #4fc3f7; color: #000; font-weight: bold; }
        
        .btn-docs {
            background: linear-gradient(135deg, #8b5cf6, #6366f1);
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 1rem;
            margin-left: 15px;
        }
        .btn-docs:hover { opacity: 0.9; }
        

    </style>
</head>
<body>
    <!-- Documentation Modal -->
    <div class="modal-overlay" id="docs-modal">
        <div class="modal-content">
            <span class="modal-close" onclick="closeDocs()">&times;</span>
            <h2 class="doc-title" id="doc-title">📝 Endpoint Documentation</h2>
            <span class="doc-badge" id="doc-badge">CODE-BASED</span>
            
            <div class="doc-tabs">
                <div class="doc-tab active" onclick="showDocTab('logic')">📚 Logic</div>
                <div class="doc-tab" onclick="showDocTab('request')">📤 Request</div>
                <div class="doc-tab" onclick="showDocTab('response')">📥 Response</div>
            </div>
            
            <div id="doc-logic" class="doc-section"></div>
            <div id="doc-request" class="doc-section" style="display: none;">
                <h4>📤 Request Format</h4>
                <pre id="doc-request-code"></pre>
            </div>
            <div id="doc-response" class="doc-section" style="display: none;">
                <h4>📥 Response Format</h4>
                <pre id="doc-response-code"></pre>
            </div>
        </div>
    </div>
    
    <div class="container">
        <header>
            <h1>🎓 Gradeo API Test Console</h1>
            <p>Test all endpoints with sample data, upload images, and view responses</p>
            <div style="margin-top: 10px; color: #4fc3f7; font-size: 0.8rem; background: rgba(79, 195, 247, 0.1); display: inline-block; padding: 4px 12px; border-radius: 20px;">✨ <b>Update:</b> New Priority Samples & Side-by-Side View Live! (Refresh if needed)</div>
        </header>
        
        <div class="grid">
            <aside class="sidebar">
                <h2>� Grading Endpoints</h2>
                <ul class="endpoint-list">
                    <li data-endpoint="mcq" class="active">
                        <span class="method">POST</span>
                        <span>/grading/mcq</span>
                    </li>
                    <li data-endpoint="true_false">
                        <span class="method">POST</span>
                        <span>/grading/true-false</span>
                    </li>
                    <li data-endpoint="matching">
                        <span class="method">POST</span>
                        <span>/grading/matching</span>
                    </li>
                    <li data-endpoint="fill_in_blank">
                        <span class="method">POST</span>
                        <span>/grading/fill-in-blank</span>
                    </li>
                    <li data-endpoint="ordering">
                        <span class="method">POST</span>
                        <span>/grading/ordering</span>
                    </li>
                    <li data-endpoint="labeling">
                        <span class="method">POST</span>
                        <span>/grading/labeling</span>
                    </li>
                    <li data-endpoint="short_answer">
                        <span class="method">POST</span>
                        <span>/grading/short-answer</span>
                    </li>
                    <li data-endpoint="open_ended">
                        <span class="method">POST</span>
                        <span>/grading/open-ended</span>
                    </li>
                    <li data-endpoint="compare_contrast">
                        <span class="method">POST</span>
                        <span>/grading/compare-contrast</span>
                    </li>
                    <li data-endpoint="definition">
                        <span class="method">POST</span>
                        <span>/grading/definition</span>
                    </li>
                    <li data-endpoint="table">
                        <span class="method">POST</span>
                        <span>/grading/table</span>
                    </li>
                    <li data-endpoint="math_equations">
                        <span class="method">POST</span>
                        <span>/grading/math-equations</span>
                    </li>
                </ul>
                
                <h3>🔍 OCR Endpoints</h3>
                <ul class="endpoint-list">
                    <li data-endpoint="ocr_english">
                        <span class="method ocr">POST</span>
                        <span>/ocr/english</span>
                    </li>
                    <li data-endpoint="ocr_french">
                        <span class="method ocr">POST</span>
                        <span>/ocr/french</span>
                    </li>
                    <li data-endpoint="ocr_arabic">
                        <span class="method ocr">POST</span>
                        <span>/ocr/arabic</span>
                    </li>
                </ul>
                
                <h3>✏️ Annotation</h3>
                <ul class="endpoint-list">
                    <li data-endpoint="annotation">
                        <span class="method annotate">POST</span>
                        <span>/annotation/generate</span>
                    </li>
                </ul>
                
                <h3>📄 Reports</h3>
                <ul class="endpoint-list">
                    <li data-endpoint="exam_report">
                        <span class="method" style="background: #ec4899;">POST</span>
                        <span>/exam/report</span>
                    </li>
                </ul>
            </aside>
            
            <main class="main-content">
                <div class="panel">
                    <h3 id="endpoint-title">📝 Multiple Choice Questions</h3>
                    <div class="description" id="endpoint-description">
                        <p>Grade multiple choice questions by comparing student answers with correct answers.</p>
                    </div>
                    
                    <!-- Upload area for OCR/Annotation -->
                    <div id="upload-section" style="display: none;">
                        <div class="upload-area" id="upload-area" onclick="document.getElementById('file-input').click()">
                            <div class="icon">📄</div>
                            <p>Click to upload an exam image or PDF</p>
                            <p style="font-size: 0.8rem; color: #666; margin-top: 5px;">Supports: JPG, PNG, PDF</p>
                            <input type="file" id="file-input" accept="image/*,.pdf" onchange="handleFileUpload(event)">
                        </div>
                        <img id="preview-image" class="preview-image" style="display: none;">
               g         
                        <h4 style="margin: 20px 0 10px; color: #888;">Or use sample images:</h4>
                        <div class="sample-images" id="sample-images"></div>
                    </div>
                    
                    <!-- JSON input for grading endpoints -->
                    <div id="json-section">
                        <h4 style="margin-bottom: 10px; color: #888;">Request Body:</h4>
                        <textarea id="request-body"></textarea>
                    </div>
                    
                    <div style="margin-top: 15px;">
                        <button class="btn btn-primary" onclick="runTest()">▶ Run Test</button>
                        <button class="btn btn-secondary" onclick="loadSampleData()">📄 Load Sample Data</button>
                        <button class="btn-docs" onclick="showDocs()">📖 View Docs</button>
                        <button class="btn btn-secondary" onclick="clearResponse()">🗑 Clear</button>
                    </div>
                </div>
                
                <div class="loading" id="loading">
                    <div class="spinner"></div>
                    <p>Processing request...</p>
                </div>
                
                <div class="panel response-panel" id="response-panel" style="display: none;">
                    <div class="response-header">
                        <h3>📊 Response</h3>
                        <span class="status-badge" id="status-badge">200 OK</span>
                        <span id="response-time" style="color: #888;"></span>
                    </div>
                    
                    <div class="stats-grid" id="stats-grid"></div>
                    

                    
                    <div class="code-block">
                        <pre id="response-body"></pre>
                    </div>
                </div>
            </main>
        </div>
    </div>
    
    <script>
        const ENDPOINTS = {
            mcq: { path: '/api/grading/mcq', title: 'Multiple Choice Questions', desc: 'Grade MCQ by comparing student answers with correct answers.', type: 'grading' },
            true_false: { path: '/api/grading/true-false', title: 'True/False Questions', desc: 'Grade true/false statements by comparing boolean answers.', type: 'grading' },
            matching: { path: '/api/grading/matching', title: 'Matching Questions', desc: 'Grade matching questions by comparing pair connections.', type: 'grading' },
            fill_in_blank: { path: '/api/grading/fill-in-blank', title: 'Fill in the Blank', desc: 'Grade fill-in-blank questions with flexible text matching.', type: 'grading' },
            ordering: { path: '/api/grading/ordering', title: 'Ordering Questions', desc: 'Grade ordering questions by comparing sequence positions.', type: 'grading' },
            labeling: { path: '/api/grading/labeling', title: 'Labeling (AI Multi-Pass)', desc: 'AI grades diagram labels with 3-pass consistency.', type: 'grading' },
            short_answer: { path: '/api/grading/short-answer', title: 'Short Answer (AI Multi-Pass)', desc: 'AI grades brief factual answers using 3-pass consistency with present/partial/absent.', type: 'grading' },
            open_ended: { path: '/api/grading/open-ended', title: 'Open-Ended Questions', desc: 'AI grades using 5 fixed criteria with 3-pass consistency.', type: 'grading' },
            compare_contrast: { path: '/api/grading/compare-contrast', title: 'Compare/Contrast', desc: 'AI grades using teacher-defined checklist items.', type: 'grading' },
            definition: { path: '/api/grading/definition', title: 'Definition Questions', desc: 'AI grades using 3 meaning units: core concept, properties, scope.', type: 'grading' },
            table: { path: '/api/grading/table', title: 'Table Questions', desc: 'AI grades table completion using checklist-based grading.', type: 'grading' },
            math_equations: { path: '/api/grading/math-equations', title: 'Math Equations (PEMDAS)', desc: 'AI generates PEMDAS steps and grades with 3-pass consistency.', type: 'grading' },
            ocr_english: { path: '/api/ocr/english', title: 'OCR - English', desc: 'Extract questions from exam paper image using AI Vision.', type: 'ocr' },
            ocr_arabic: { path: '/api/ocr/arabic', title: 'OCR - العربية', desc: 'استخراج الأسئلة من صورة ورقة امتحان.', type: 'ocr' },
            ocr_french: { path: '/api/ocr/french', title: 'OCR - Français', desc: "Extraire les questions d'une image d'examen.", type: 'ocr' },
            workflow: { path: '/api/workflow/full', title: 'Full Workflow (OCR + Grade + Annotate)', desc: 'Run complete extraction, grading, and annotation in one call.', type: 'ocr' },
            annotation: { path: '/api/annotation/generate', title: 'Generate Corrected Paper', desc: 'Overlay correction marks on exam paper.', type: 'annotation' },
            annotation_arabic_sample: { path: '/api/annotation/generate', title: '🇸🇦 Arabic Open Question Sample', desc: 'Test Arabic feedback with open-ended question annotation.', type: 'annotation', sampleKey: 'annotation_arabic' },
            annotation_french_sample: { path: '/api/annotation/generate', title: '🇫🇷 French Open Question Sample', desc: 'Test French feedback with open-ended question annotation.', type: 'annotation', sampleKey: 'annotation_french' },
            exam_report: { path: '/api/exam/report', title: '📄 Generate Exam Report (DOCX/PDF)', desc: 'Generate professional report with student info, questions, answers, corrections.', type: 'exam_report' }
        };
        
        // ============ COMPREHENSIVE ENDPOINT DOCUMENTATION ============
        const ENDPOINT_DOCS = {
            mcq: {
                title: '📝 Multiple Choice Questions',
                method: 'CODE-BASED (No AI)',
                logic: `<h4>🔧 How It Works</h4>
<ol>
<li><strong>Normalization:</strong> Both student and correct answers are normalized:
    <ul>
        <li>Lowercase conversion</li>
        <li>Strip punctuation and whitespace</li>
        <li>Letter/number equivalence: A=1, B=2, C=3, D=4</li>
        <li>Arabic letter mapping: أ=A, ب=B, ج=C, د=D</li>
    </ul>
</li>
<li><strong>Comparison:</strong> Normalized student answer vs correct answer</li>
<li><strong>Scoring:</strong> Full points for exact match, 0 for mismatch</li>
</ol>

<h4>📊 Scoring Formula</h4>
<pre>points_earned = correct_count × points_per_question</pre>

<h4>✅ Example Match</h4>
<pre>Student: "B" → normalized: "b"
Correct: "2" → normalized: "b" (2→b)
Result: ✓ CORRECT</pre>`,
                request: `{
  "questions": [
    {
      "question_number": "1",
      "question_text": "What is the capital of France?",
      "options": {"A": "London", "B": "Paris", "C": "Berlin"},
      "correct_answer": "B"
    }
  ],
  "student_answers": {
    "1": "B"  // Can also use "2" or "b"
  },
  "points_per_question": 2.0
}`,
                response: `{
  "question_type": "multiple_choice",
  "total_questions": 1,
  "correct_count": 1,
  "points_earned": 2.0,
  "points_possible": 2.0,
  "percentage": 100.0,
  "details": [{
    "question_number": "1",
    "student_answer": "B",
    "correct_answer": "B",
    "is_correct": true
  }]
}`
            },
            
            true_false: {
                title: '✅ True/False Questions',
                method: 'CODE-BASED (No AI)',
                logic: `<h4>🔧 How It Works</h4>
<ol>
<li><strong>Boolean Normalization:</strong> Various inputs map to true/false:
    <ul>
        <li><strong>True:</strong> true, t, yes, y, 1, صحيح, صح, vrai, oui</li>
        <li><strong>False:</strong> false, f, no, n, 0, خطأ, خاطئ, faux, non</li>
    </ul>
</li>
<li><strong>Comparison:</strong> Normalized boolean comparison</li>
<li><strong>Scoring:</strong> Full points for match, 0 for mismatch</li>
</ol>

<h4>📊 Scoring Formula</h4>
<pre>points_earned = correct_count × points_per_question</pre>

<h4>✅ Example</h4>
<pre>Student: "صحيح" → normalized: true
Correct: true
Result: ✓ CORRECT</pre>`,
                request: `{
  "questions": [
    {
      "question_number": "1",
      "statement": "The Earth is round",
      "correct_answer": true
    }
  ],
  "student_answers": {
    "1": true  // Can also use "yes", "صحيح", "vrai"
  },
  "points_per_question": 1.0
}`,
                response: `{
  "question_type": "true_false",
  "correct_count": 1,
  "points_earned": 1.0,
  "percentage": 100.0
}`
            },
            
            matching: {
                title: '🔗 Matching Questions',
                method: 'CODE-BASED (No AI)',
                logic: `<h4>🔧 How It Works</h4>
<ol>
<li><strong>Structure:</strong> Left column items matched to right column items</li>
<li><strong>Per-pair grading:</strong> Each correct pair = points_per_pair</li>
<li><strong>Normalization:</strong> Same as MCQ (letter/number equivalence)</li>
</ol>

<h4>📊 Scoring Formula</h4>
<pre>points_earned = correct_pairs × points_per_pair</pre>

<h4>📋 Data Structure</h4>
<pre>left_column: [{id: "1", text: "Dog"}]
right_column: [{id: "a", text: "Barks"}]
correct_matches: {"1": "a"}
student_answers: {"1": {"1": "a"}}</pre>`,
                request: `{
  "questions": [{
    "question_number": "1",
    "left_column": [
      {"id": "1", "text": "Dog"},
      {"id": "2", "text": "Cat"}
    ],
    "right_column": [
      {"id": "a", "text": "Barks"},
      {"id": "b", "text": "Meows"}
    ],
    "correct_matches": {"1": "a", "2": "b"}
  }],
  "student_answers": {
    "1": {"1": "a", "2": "b"}
  },
  "points_per_pair": 1.0
}`,
                response: `{
  "total_pairs": 2,
  "correct_pairs": 2,
  "points_earned": 2.0
}`
            },
            
            fill_in_blank: {
                title: '📝 Fill in the Blank',
                method: 'CODE-BASED (No AI)',
                logic: `<h4>🔧 How It Works</h4>
<ol>
<li><strong>Blank Detection:</strong> Each _____ is a blank position</li>
<li><strong>Text Normalization:</strong>
    <ul>
        <li>Case-insensitive comparison</li>
        <li>Strip extra whitespace</li>
        <li>Remove punctuation</li>
    </ul>
</li>
<li><strong>Per-blank scoring:</strong> Each correct blank = points_per_blank</li>
</ol>

<h4>📊 Scoring Formula</h4>
<pre>points_earned = correct_blanks × points_per_blank</pre>

<h4>⚠️ Limitations</h4>
<p>Exact text match required. "Tokyo" ≠ "Tokyo city". For flexible matching, use open_ended endpoint.</p>`,
                request: `{
  "questions": [{
    "question_number": "1",
    "question_text": "The capital of Japan is _____.",
    "blanks": ["Tokyo"]
  }],
  "student_answers": {
    "1": ["Tokyo"]
  },
  "points_per_blank": 2.0
}`,
                response: `{
  "correct_blanks": 1,
  "points_earned": 2.0
}`
            },
            
            ordering: {
                title: '🔢 Ordering Questions',
                method: 'CODE-BASED (No AI)',
                logic: `<h4>🔧 How It Works</h4>
<ol>
<li><strong>Position-by-position comparison:</strong> Check each position in sequence</li>
<li><strong>Partial credit:</strong> Points for each correct position</li>
<li><strong>Normalization:</strong> Same letter/number equivalence</li>
</ol>

<h4>📊 Scoring Formula</h4>
<pre>points_earned = correct_positions × points_per_position</pre>

<h4>📋 Example</h4>
<pre>Correct order: [B, A, C]
Student order: [B, A, D]
Position 1: B=B ✓
Position 2: A=A ✓
Position 3: C≠D ✗
Score: 2/3 positions</pre>`,
                request: `{
  "questions": [{
    "question_number": "1",
    "ordering_items": [
      {"item_id": "A", "content": "Earth"},
      {"item_id": "B", "content": "Mercury"},
      {"item_id": "C", "content": "Mars"}
    ],
    "correct_order": ["B", "A", "C"]
  }],
  "student_answers": {
    "1": ["B", "A", "C"]
  },
  "points_per_position": 1.0
}`,
                response: `{
  "correct_positions": 3,
  "points_earned": 3.0
}`
            },
            
            labeling: {
                title: '🏷️ Labeling (Text Input)',
                method: '⭐ AI MULTI-PASS (3 passes)',
                logic: `<h4>🔧 How It Works</h4>
<ol>
<li><strong>AI Prompt:</strong> Send correct label + student answer to Gemini AI</li>
<li><strong>3-Pass Grading:</strong> Run grading 3 times for consistency</li>
<li><strong>Status Determination:</strong>
    <ul>
        <li><strong>present:</strong> Correct or equivalent (synonyms, minor spelling OK)</li>
        <li><strong>partial:</strong> Shows some understanding, partially correct</li>
        <li><strong>absent:</strong> Wrong, missing, or unrelated</li>
    </ul>
</li>
<li><strong>Mode/Median:</strong>
    <ul>
        <li>If 2+ passes agree → Use that status</li>
        <li>If all 3 different → Use median + flag_for_review</li>
    </ul>
</li>
</ol>

<h4>📊 Scoring Formula</h4>
<pre>present = 100% of label points
partial = 50% of label points
absent = 0%</pre>

<h4>🎯 AI Accepts</h4>
<ul>
<li>Synonyms: "Left Atrium" = "LA" = "left atrium"</li>
<li>Minor spelling: "Aorta" = "aorta" = "Aotra"</li>
<li>Equivalent terms: "Heart valve" = "Cardiac valve"</li>
</ul>`,
                request: `{
  "questions": [{
    "question_number": "1",
    "diagram_description": "Human heart diagram",
    "labeling_items": [
      {"label_id": "1", "pointer_description": "Main artery", "correct_label": "Aorta"},
      {"label_id": "2", "pointer_description": "Upper left", "correct_label": "Left Atrium"}
    ],
    "points": 4.0
  }],
  "student_answers": {
    "1": {"1": "Aorta", "2": "LA"}
  }
}`,
                response: `{
  "present": 2, "partial": 0, "absent": 0,
  "flagged_for_review": 0,
  "grading_passes_per_question": 3,
  "label_details": [{
    "label_id": "1",
    "status": "present",
    "reason": "Correct answer",
    "all_pass_statuses": ["present", "present", "present"],
    "flag_for_review": false
  }]
}`
            },
            
            open_ended: {
                title: '📄 Open-Ended Questions',
                method: '⭐ AI MULTI-PASS (3 passes)',
                logic: `<h4>🔧 How It Works</h4>
<ol>
<li><strong>5 Fixed Criteria:</strong> Every answer graded on:
    <ul>
        <li><strong>relevance (25%):</strong> Does it address the question?</li>
        <li><strong>completeness (25%):</strong> Are all aspects covered?</li>
        <li><strong>accuracy (20%):</strong> Is information factually correct?</li>
        <li><strong>key_terms (15%):</strong> Are expected keywords present?</li>
        <li><strong>clarity (15%):</strong> Is the answer well-organized?</li>
    </ul>
</li>
<li><strong>3-Pass Grading:</strong> Each criterion graded 3 times</li>
<li><strong>Status per Criterion:</strong>
    <ul>
        <li><strong>strong:</strong> 100% of weight</li>
        <li><strong>adequate:</strong> 60% of weight</li>
        <li><strong>weak:</strong> 30% of weight</li>
        <li><strong>missing:</strong> 0%</li>
    </ul>
</li>
</ol>

<h4>📊 Scoring Formula</h4>
<pre>score = Σ(criterion_weight × status_multiplier) × total_points</pre>

<h4>📋 answer_length Field</h4>
<ul>
<li><strong>"short":</strong> 1-3 sentences expected (name, list, what is)</li>
<li><strong>"long":</strong> Paragraph+ expected (explain, analyze, discuss)</li>
</ul>`,
                request: `{
  "questions": [{
    "question_number": "1",
    "question_text": "Explain photosynthesis.",
    "model_answer": "Plants convert sunlight...",
    "expected_keywords": ["sunlight", "glucose", "oxygen"],
    "points": 10.0,
    "answer_length": "long"
  }],
  "student_answers": {
    "1": "Photosynthesis is when plants use sunlight..."
  }
}`,
                response: `{
  "criteria_results": [
    {"criterion": "relevance", "weight": 0.25, "status": "strong"},
    {"criterion": "completeness", "weight": 0.25, "status": "adequate"}
  ],
  "points_earned": 8.5,
  "grading_passes_per_question": 3
}`
            },
            
            compare_contrast: {
                title: '⚖️ Compare/Contrast',
                method: '⭐ AI MULTI-PASS (3 passes)',
                logic: `<h4>🔧 How It Works</h4>
<ol>
<li><strong>Teacher-Defined Checklist:</strong> grading_table contains expected points</li>
<li><strong>AI Checks Each Item:</strong> Does student answer include this concept?</li>
<li><strong>Status per Item:</strong>
    <ul>
        <li><strong>present:</strong> 100% of item points</li>
        <li><strong>partial:</strong> 50% of item points</li>
        <li><strong>absent:</strong> 0%</li>
    </ul>
</li>
<li><strong>3-Pass with Mode/Median</strong></li>
</ol>

<h4>📊 Scoring Formula</h4>
<pre>score = Σ(item_points × status_multiplier)</pre>

<h4>📋 grading_table Structure</h4>
<pre>[
  {"item": "Both are cell division", "points": 2},
  {"item": "Mitosis produces 2 cells", "points": 2}
]</pre>

<h4>💡 Key Point</h4>
<p>Teacher controls EXACTLY what to grade for by defining the checklist items!</p>`,
                request: `{
  "questions": [{
    "question_number": "1",
    "question_text": "Compare mitosis and meiosis.",
    "compare_items": ["Mitosis", "Meiosis"],
    "grading_table": [
      {"item": "Both are cell division", "points": 2},
      {"item": "Mitosis produces 2 cells", "points": 2}
    ],
    "points": 6.0
  }],
  "student_answers": {
    "1": "Mitosis and meiosis are both cell division..."
  }
}`,
                response: `{
  "checklist_results": [
    {"item": "Both are cell division", "status": "present", "points_earned": 2}
  ],
  "points_earned": 6.0,
  "grading_passes_per_question": 3
}`
            },
            
            definition: {
                title: '📖 Definition Questions',
                method: '⭐ AI MULTI-PASS (3 passes)',
                logic: `<h4>🔧 How It Works</h4>
<ol>
<li><strong>3 Meaning Units:</strong>
    <ul>
        <li><strong>core_concept (50%):</strong> Basic definition essence</li>
        <li><strong>required_properties (30%):</strong> Key characteristics</li>
        <li><strong>scope_context (20%):</strong> Where/when it applies</li>
    </ul>
</li>
<li><strong>AI Evaluates Semantics:</strong> Not exact wording, but meaning</li>
<li><strong>Status per Unit:</strong> present/partial/absent</li>
<li><strong>3-Pass with Mode/Median</strong></li>
</ol>

<h4>📊 Scoring Formula</h4>
<pre>score = (core×0.5 + properties×0.3 + scope×0.2) × total_points</pre>

<h4>✅ Example</h4>
<pre>Term: Photosynthesis
Core: Light energy → chemical energy (50%)
Properties: Uses CO2, water, produces glucose (30%)
Scope: Occurs in plants/chloroplasts (20%)</pre>`,
                request: `{
  "questions": [{
    "question_number": "1",
    "term_to_define": "Photosynthesis",
    "model_answer": "The process by which plants...",
    "expected_keywords": ["light", "glucose", "plants"],
    "points": 10.0
  }],
  "student_answers": {
    "1": "Photosynthesis is how plants make food..."
  }
}`,
                response: `{
  "meaning_units": [
    {"unit": "core_concept", "weight": 0.5, "status": "present"},
    {"unit": "required_properties", "weight": 0.3, "status": "partial"}
  ],
  "points_earned": 8.0,
  "grading_passes_per_question": 3
}`
            },
            
            table: {
                title: '📊 Table Questions',
                method: '⭐ AI MULTI-PASS (3 passes)',
                logic: `<h4>🔧 How It Works</h4>
<p>Works exactly like Compare/Contrast - uses grading_table checklist.</p>

<ol>
<li><strong>Teacher-Defined Checklist:</strong> Expected table content as items</li>
<li><strong>AI Checks Each Item:</strong> present/partial/absent</li>
<li><strong>3-Pass with Mode/Median</strong></li>
</ol>

<h4>📋 Example grading_table</h4>
<pre>[
  {"item": "Solid has fixed shape", "points": 2},
  {"item": "Liquid takes container shape", "points": 2},
  {"item": "Gas has no fixed volume", "points": 2}
]</pre>

<h4>💡 Student Answer Format</h4>
<p>Student can write as paragraph - AI extracts concepts regardless of format.</p>`,
                request: `{
  "questions": [{
    "question_number": "1",
    "question_text": "Complete the states of matter table.",
    "table_headers": ["State", "Shape", "Volume"],
    "grading_table": [
      {"item": "Solid has fixed shape", "points": 2}
    ],
    "points": 6.0
  }],
  "student_answers": {
    "1": "Solids have fixed shape and volume..."
  }
}`,
                response: `{
  "checklist_results": [...],
  "points_earned": 6.0,
  "grading_passes_per_question": 3
}`
            },
            
            math_equations: {
                title: '🔢 Math Equations (PEMDAS)',
                method: '⭐ AI MULTI-PASS (3 passes)',
                logic: `<h4>🔧 How It Works</h4>
<ol>
<li><strong>Step Generation:</strong> AI breaks problem into PEMDAS steps:
    <ul>
        <li><strong>P:</strong> Parentheses (innermost first)</li>
        <li><strong>E:</strong> Exponents (powers, roots)</li>
        <li><strong>M/D:</strong> Multiplication/Division (left to right)</li>
        <li><strong>A/S:</strong> Addition/Subtraction (left to right)</li>
    </ul>
</li>
<li><strong>3-Pass Grading:</strong> Each step graded 3 times against student work</li>
<li><strong>Status per Step:</strong>
    <ul>
        <li><strong>present:</strong> Step shown correctly</li>
        <li><strong>partial:</strong> Attempted but calculation error</li>
        <li><strong>absent:</strong> Step not shown</li>
    </ul>
</li>
<li><strong>Equivalent Approaches:</strong> AI accepts different valid methods (6×4 = 4×6)</li>
</ol>

<h4>📊 Scoring Formula</h4>
<pre>score = steps_present × step_points + final_answer_bonus</pre>

<h4>📋 Response Includes LaTeX</h4>
<p>Each step includes both plain text and LaTeX format for display.</p>`,
                request: `{
  "questions": [{
    "question_number": "1",
    "math_content": "(2 + 3) × 4 - 6 ÷ 2",
    "correct_answer": "17",
    "points": 10.0
  }],
  "student_answers": {
    "1": "2+3=5\\n5×4=20\\n6÷2=3\\n20-3=17"
  }
}`,
                response: `{
  "step_results": [
    {"step": 1, "operation": "parentheses", "expected": "2+3=5", "expected_latex": "$2+3=5$", "status": "present"}
  ],
  "final_answer_correct": true,
  "grading_passes_per_question": 3
}`
            },
            
            ocr_english: {
                title: '🔍 OCR - English',
                method: 'AI VISION (Gemini)',
                logic: `<h4>🔧 How It Works</h4>
<ol>
<li><strong>Image Upload:</strong> Accept JPG, PNG, or PDF</li>
<li><strong>AI Vision Analysis:</strong> Gemini analyzes the exam paper</li>
<li><strong>Question Detection:</strong> Identifies 12 question types:
    <ul>
        <li>multiple_choice, true_false, matching</li>
        <li>fill_in_blank, ordering, labeling, labeling_image</li>
        <li>open_ended, compare_contrast, definition</li>
        <li>table, math_equation</li>
    </ul>
</li>
<li><strong>Field Extraction:</strong> Extracts type-specific fields</li>
</ol>

<h4>📋 Extracted Fields by Type</h4>
<pre>MCQ: options, correct_answer
Matching: left_column, right_column, correct_matches
Open-ended: answer_length ("short"/"long")
Math: math_content, correct_answer</pre>

<h4>⚠️ Important</h4>
<p>correct_answer only extracted if visible on answer key!</p>`,
                request: `multipart/form-data:
file: [image.jpg or exam.pdf]`,
                response: `{
  "questions": [
    {
      "order": 1,
      "question_number": "1",
      "type": "multiple_choice",
      "question_text": "What is 2+2?",
      "options": {"A": "3", "B": "4"},
      "correct_answer": "B"
    }
  ],
  "total_questions": 5,
  "language": "english"
}`
            },
            
            ocr_arabic: {
                title: '🔍 OCR - العربية',
                method: 'AI VISION (Gemini)',
                logic: `<h4>🔧 آلية العمل</h4>
<ol>
<li><strong>رفع الصورة:</strong> يقبل JPG، PNG، أو PDF</li>
<li><strong>تحليل الذكاء الاصطناعي:</strong> Gemini يحلل ورقة الامتحان</li>
<li><strong>كشف الأسئلة:</strong> يحدد 12 نوع من الأسئلة</li>
<li><strong>استخراج الحقول:</strong> يستخرج الحقول حسب النوع</li>
</ol>

<h4>📋 أنواع الأسئلة المدعومة</h4>
<pre>الاختيار من متعدد، صح وخطأ، التوصيل
ملء الفراغات، الترتيب، التسمية
الأسئلة المقالية، المقارنة، التعريف
الجداول، المعادلات الرياضية</pre>

<h4>⚠️ ملاحظة</h4>
<p>الإجابة الصحيحة تُستخرج فقط إذا كانت مرئية!</p>`,
                request: `multipart/form-data:
file: [image.jpg أو exam.pdf]`,
                response: `{
  "questions": [...],
  "language": "arabic"
}`
            },
            
            ocr_french: {
                title: '🔍 OCR - Français',
                method: 'AI VISION (Gemini)',
                logic: `<h4>🔧 Comment ça marche</h4>
<ol>
<li><strong>Téléchargement:</strong> Accepte JPG, PNG, ou PDF</li>
<li><strong>Analyse IA:</strong> Gemini analyse le document</li>
<li><strong>Détection:</strong> Identifie 12 types de questions</li>
<li><strong>Extraction:</strong> Extrait les champs spécifiques</li>
</ol>

<h4>📋 Types supportés</h4>
<pre>QCM, Vrai/Faux, Appariement
Texte à trous, Ordonnancement
Questions ouvertes, Définitions
Tableaux, Équations mathématiques</pre>`,
                request: `multipart/form-data:
file: [image.jpg ou exam.pdf]`,
                response: `{
  "questions": [...],
  "language": "french"
}`
            },
            
            workflow: {
                title: '⚡ Full Workflow Orchestration',
                method: 'AI VISION + LOGIC + PDF GENERATION',
                logic: `<h4>🔧 The Pipeline</h4>
<ol>
<li><strong>Step 1: OCR Extraction</strong>
    <ul>
        <li>Extracts questions AND student answers/markings</li>
        <li>Identifies 12 question types</li>
    </ul>
</li>
<li><strong>Step 2: Intelligent Routing</strong>
    <ul>
        <li>Routes each question to its specific grading service</li>
        <li>Handles MCQ, T/F, Math, Open-ended, etc.</li>
    </ul>
</li>
<li><strong>Step 3: Automated Annotation</strong>
    <ul>
        <li>Overlays checkmarks and X-marks at detected positions</li>
        <li>Calculates and writes final score in header</li>
    </ul>
</li>
</ol>
<h4>📊 Output</h4>
<pre>OCR Results + Grading Summary + Corrected PDF (Base64)</pre>`,
                request: `multipart/form-data:
file: [Answered exam image/PDF]
language: "english" | "arabic" | "french"`,
                response: `{
  "success": true,
  "ocr_data": {...},
  "grading_summary": {...},
  "annotation_output": {
    "corrected_pdf": "...",
    "annotations_added": 12
  }
}`
            },
            
            annotation: {
                title: '✍️ Annotation Generation',
                method: '⭐ AI VISION + GRID',
                logic: `<h4>🔧 How It Works</h4>
<ol>
<li><strong>Grid Overlay:</strong> Service draws a 20x20 grid on image for accuracy</li>
<li><strong>AI Detection:</strong> Gemini identifies answer positions in grid coordinates</li>
<li><strong>Non-Destructive:</strong> System returns original image + metadata (Editable)</li>
<li><strong>Unified Logic:</strong> Connects mark + score as a single draggable unit</li>
</ol>

<h4>📝 Metadata Structure</h4>
<pre>{
  "id": "q1_mark",
  "type": "check",
  "text": "✓ 2/2",
  "x": 450, "y": 120,
  "width": 100, "height": 40,
  "status": "pending"
}</pre>`,
                request: `{
  "exam_file": "base64_data...",
  "file_type": "png",
  "grading_results": {
    "questions": [{"question_number": "1", "points_earned": 2, "points_possible": 2}]
  }
}`,
                response: `{
  "success": true,
  "data": {
    "original_image": "base64...",
    "annotation_metadata": [...],
    "is_draft": true
  }
}`
            }
        };
        
        const SAMPLE_IMAGES = {
            english: {
                'Multiple Choice': [
                    { name: 'Eng MCQ 1', file: 'exam_mcq_english_1_1768495064966.png', desc: 'Capital of Australia (Answered)' },
                    { name: 'Eng MCQ 2', file: 'exam_mcq_english_2_1768495083905.png', desc: 'WWII History (Answered)' },
                    { name: 'Eng MCQ 3', file: 'exam_mcq_english_3_1768495100072.png', desc: 'Science Quiz (Answered)' },
                    { name: 'Eng MCQ 4', file: 'exam_mcq_english_4_1768495115562.png', desc: 'CS 101 (Answered)' },
                    { name: 'Eng MCQ 5', file: 'exam_mcq_english_5_1768495130440.png', desc: 'Literature (Answered)' },
                    { name: 'Sample MCQ', file: 'sample_mcq.png', desc: 'Standard MCQ' }
                ],
                'True/False': [
                    { name: 'Eng T/F 1', file: 'exam_tf_english_1_1768495340182.png', desc: 'Science T/F' },
                    { name: 'Eng T/F 2', file: 'exam_tf_english_2_1768495356545.png', desc: 'History T/F' },
                    { name: 'Eng T/F Mixed', file: 'exam_english_tf.png', desc: 'General T/F' }
                ],
                'Other Types': [
                    { name: 'Matching', file: 'exam_english_matching.png', desc: 'Matching columns' },
                    { name: 'Fill-in-Blank', file: 'exam_english_fill.png', desc: 'Fill blanks' },
                    { name: 'Text Labeling', file: 'gen_label_3.png', desc: 'Grammar labeling' }
                ],
                'Mixed Exams': [
                    { name: 'Mixed Exam 1', file: 'sample_exam_mixed.png', desc: 'Mixed question types' },
                    { name: 'Mixed Exam 2', file: 'sample_mixed.png', desc: 'Standard layout' }
                ],
                'Open Ended': [
                    { name: 'History Essay', file: 'gen_open_1.png', desc: 'Handwritten WWI causes' },
                    { name: 'Enviro Science', file: 'gen_open_2.png', desc: 'Plastic pollution discussion' }
                ],
                'Math Equations': [
                    { name: 'Algebra I', file: 'gen_math_1.png', desc: 'Linear equations' },
                    { name: 'Calculus', file: 'gen_math_2.png', desc: 'Derivatives & Integrals' },
                    { name: 'Geometry', file: 'gen_math_3.png', desc: 'Area calculation' }
                ],
                'Short Answer': [
                    { name: 'General Science', file: 'short_answer_sample1.png', desc: 'Living organisms, capital, colors' },
                    { name: 'All Correct', file: 'short_answer_sample2.png', desc: 'States of matter, H2O, planets' },
                    { name: 'Arabic Bilingual', file: 'short_answer_sample3.png', desc: 'Mammals, photosynthesis, formula' }
                ],
                'Diagram Labeling': [
                    { name: 'Heart Diagram', file: 'labeling_sample1.png', desc: 'Heart chambers & arteries' },
                    { name: 'Plant Cell', file: 'labeling_sample2.png', desc: 'Cell organelles' },
                    { name: 'Water Cycle', file: 'labeling_sample3.png', desc: 'Evaporation, condensation' }
                ]
            },
            arabic: {
                'الاختيار من متعدد': [
                    { name: 'عربي MCQ 1', file: 'exam_mcq_arabic_1_1768495160559.png', desc: 'عاصمة السعودية' },
                    { name: 'عربي MCQ 2', file: 'exam_mcq_arabic_2_1768495176459.png', desc: 'تاريخ الدولة الأموية' },
                    { name: 'عربي MCQ 3', file: 'exam_mcq_arabic_3_1768495193641.png', desc: 'علوم - كواكب' },
                    { name: 'عربي MCQ 4', file: 'exam_mcq_arabic_4_1768495210087.png', desc: 'لغة عربية - نحو' },
                    { name: 'عربي MCQ 5', file: 'exam_mcq_arabic_5_1768495225894.png', desc: 'جغرافيا الوطن العربي' }
                ],
                'صح وخطأ': [
                    { name: 'صح وخطأ', file: 'exam_arabic_tf.png', desc: 'صواب وخطأ' }
                ],
                'نماذج مختلطة': [
                    { name: 'نموذج عربي', file: 'exam_arabic_mcq.png', desc: 'اختبار تجريبي' },
                    { name: 'إجابات عربي', file: 'exam_annotate_arabic.png', desc: 'Answered' }
                ]
            },
            french: {
                'QCM': [
                    { name: 'Fr QCM 1', file: 'exam_mcq_french_1_1768495251206.png', desc: 'Capitale de la France' },
                    { name: 'Fr QCM 2', file: 'exam_mcq_french_2_1768495268065.png', desc: 'Histoire Révolution' },
                    { name: 'Fr QCM 3', file: 'exam_mcq_french_3_1768495283871.png', desc: 'Sciences - Cœur' },
                    { name: 'Fr QCM 4', file: 'exam_mcq_french_4_1768495299676.png', desc: 'Littérature - Hugo' },
                    { name: 'Fr QCM 5', file: 'exam_mcq_french_5_1768495314207.png', desc: 'Géographie Monde' }
                ],
                'Autres Types': [
                    { name: 'Texte à trous', file: 'exam_french_fill.png', desc: 'Remplir les blancs' },
                    { name: 'Modèle FR', file: 'exam_french_mcq.png', desc: 'Examen type' },
                    { name: 'Réponses', file: 'exam_annotate_french.png', desc: 'Answered' }
                ]
            },
            annotation: {
                'Question Types': [
                    { name: 'True/False', file: 'sample_true_false_1768604780787.png', desc: '4 T/F questions, Q2 wrong' },
                    { name: 'Matching', file: 'sample_matching_1768604794476.png', desc: '4 matches, Q3 wrong' },
                    { name: 'Fill-in-Blank', file: 'sample_fill_blank_1768604807738.png', desc: '3 blanks, Q2 wrong' },
                    { name: 'Ordering', file: 'sample_ordering_1768604821872.png', desc: 'Water cycle order, 2 wrong' },
                    { name: 'Short Answer', file: 'sample_short_answer_1768604836287.png', desc: '2 short answers' },
                    { name: 'Math Equations', file: 'sample_math_equations_1768604851308.png', desc: '2 PEMDAS problems, Q2 error' },
                    { name: 'Open-Ended', file: 'sample_open_ended_1768604864960.png', desc: 'WWI essay question' }
                ],
                'Full Exam Samples': [
                    { name: 'Mixed Exam', file: 'sample_exam_mixed.png', desc: 'Full exam (MCQ, Fill, Open)' },
                    { name: 'Standard Layout', file: 'sample_mixed.png', desc: 'Clean layout' },
                    { name: 'Arabic Marked', file: 'exam_annotate_arabic.png', desc: 'Arabic with marks' },
                    { name: 'French Marked', file: 'exam_annotate_french.png', desc: 'French with marks' }
                ],
                'Priority Types': [
                    { name: 'Math Algebra', file: 'gen_math_1.png', desc: 'Algebra annotations' },
                    { name: 'Bio Labeling', file: 'gen_label_1.png', desc: 'Diagram labeling marks' },
                    { name: 'History Open', file: 'gen_open_1.png', desc: 'Essay annotations' }
                ]
            }
        };

        // Helper to get sample JSON for annotation based on image type
        function getAnnotationSampleJSON(filename) {
            // True/False sample
            if (filename.includes('true_false')) {
                return {
                    "questions": [
                        {"question_number": "1", "question_type": "true_false", "points_earned": 2, "points_possible": 2, "correct_answer": true},
                        {"question_number": "2", "question_type": "true_false", "points_earned": 0, "points_possible": 2, "correct_answer": false},
                        {"question_number": "3", "question_type": "true_false", "points_earned": 2, "points_possible": 2, "correct_answer": true},
                        {"question_number": "4", "question_type": "true_false", "points_earned": 2, "points_possible": 2, "correct_answer": false}
                    ],
                    "total_earned": 6, "total_possible": 8
                };
            }
            // Matching sample - each pair is a separate question for annotation
            else if (filename.includes('matching')) {
                return {
                    "questions": [
                        {"question_number": "1", "question_type": "matching", "points_earned": 2, "points_possible": 2, "correct_answer": "B"},
                        {"question_number": "2", "question_type": "matching", "points_earned": 2, "points_possible": 2, "correct_answer": "A"},
                        {"question_number": "3", "question_type": "matching", "points_earned": 0, "points_possible": 2, "correct_answer": "C"},
                        {"question_number": "4", "question_type": "matching", "points_earned": 2, "points_possible": 2, "correct_answer": "D"}
                    ],
                    "total_earned": 6, "total_possible": 8
                };
            }
            // Fill-in-blank sample
            else if (filename.includes('fill_blank')) {
                return {
                    "questions": [
                        {"question_number": "1", "question_type": "fill_in_blank", "points_earned": 2, "points_possible": 2, "correct_answer": "Paris"},
                        {"question_number": "2", "question_type": "fill_in_blank", "points_earned": 0, "points_possible": 2, "correct_answer": "oxygen"},
                        {"question_number": "3", "question_type": "fill_in_blank", "points_earned": 2, "points_possible": 2, "correct_answer": "Jupiter"}
                    ],
                    "total_earned": 4, "total_possible": 6
                };
            }
            // Ordering sample
            else if (filename.includes('ordering')) {
                return {
                    "questions": [
                        {"question_number": "1", "question_type": "ordering", "points_earned": 2, "points_possible": 5, "correct_answer": [1, 2, 3, 4], "feedback": "Correct order: Evaporation, Condensation, Precipitation, Collection"}
                    ],
                    "total_earned": 2, "total_possible": 5
                };
            }
            // Short answer sample
            else if (filename.includes('short_answer')) {
                return {
                    "questions": [
                        {"question_number": "1", "question_type": "short_answer", "points_earned": 5, "points_possible": 5, "feedback": "Excellent explanation of photosynthesis"},
                        {"question_number": "2", "question_type": "short_answer", "points_earned": 5, "points_possible": 5, "feedback": "All three states correctly named"}
                    ],
                    "total_earned": 10, "total_possible": 10
                };
            }
            // Math equations sample
            else if (filename.includes('math')) {
                return {
                    "questions": [
                        {"question_number": "1", "question_type": "math_equations", "points_earned": 10, "points_possible": 10, "correct_answer": "12"},
                        {"question_number": "2", "question_type": "math_equations", "points_earned": 3, "points_possible": 10, "correct_answer": "13", "annotation_feedback": "Error: 4×2=8 not 12"}
                    ],
                    "total_earned": 13, "total_possible": 20
                };
            }
            // Open-ended sample
            else if (filename.includes('open')) {
                return {
                    "questions": [
                        {"question_number": "1", "question_type": "open_ended", "points_earned": 12, "points_possible": 15, "feedback": "Good points on assassination and alliances, missing economic factors"}
                    ],
                    "total_earned": 12, "total_possible": 15
                };
            }
            // Labeling sample
            else if (filename.includes('label')) {
                return {
                    "questions": [
                        {"question_number": "1", "question_type": "labeling", "points_earned": 1, "points_possible": 1, "correct_answer": "Aorta"},
                        {"question_number": "2", "question_type": "labeling", "points_earned": 0, "points_possible": 1, "correct_answer": "Left Ventricle", "feedback": "This is the right ventricle"},
                        {"question_number": "3", "question_type": "labeling", "points_earned": 1, "points_possible": 1, "correct_answer": "Pulmonary Artery"}
                    ],
                    "total_earned": 2, "total_possible": 3
                };
            }
            // Default: MCQ
            return {
                "questions": [
                    {"question_number": "1", "question_type": "multiple_choice", "points_earned": 1, "points_possible": 1, "correct_answer": "B"},
                    {"question_number": "2", "question_type": "multiple_choice", "points_earned": 1, "points_possible": 1, "correct_answer": "B"},
                    {"question_number": "3", "question_type": "multiple_choice", "points_earned": 0, "points_possible": 1, "correct_answer": "C", "feedback": "Jupiter is the largest planet"}
                ],
                "total_earned": 2, "total_possible": 3
            };
        }

        
        let currentEndpoint = 'mcq';
        let sampleData = {};
        let uploadedFile = null;
        
        // Load sample data from server
        fetch('/test/sample-data')
            .then(r => r.json())
            .then(data => {
                sampleData = data;
                loadSampleData();
            });
        
        // Endpoint selection
        document.querySelectorAll('.endpoint-list li').forEach(li => {
            li.addEventListener('click', () => {
                document.querySelectorAll('.endpoint-list li').forEach(l => l.classList.remove('active'));
                li.classList.add('active');
                currentEndpoint = li.dataset.endpoint;
                updateEndpointUI();
            });
        });
        
        function updateEndpointUI() {
            const ep = ENDPOINTS[currentEndpoint];
            document.getElementById('endpoint-title').textContent = '📝 ' + ep.title;
            document.getElementById('endpoint-description').innerHTML = '<p>' + ep.desc + '</p>';
            
            // Show/hide upload or JSON sections
            const uploadSection = document.getElementById('upload-section');
            const jsonSection = document.getElementById('json-section');
            
            if (ep.type === 'ocr' || ep.type === 'annotation' || currentEndpoint === 'workflow') {
                uploadSection.style.display = 'block';
                jsonSection.style.display = (ep.type === 'annotation' || currentEndpoint === 'workflow') ? 'block' : 'none';
                
                // For workflow, show language selector instead of JSON editor
                if (currentEndpoint === 'workflow') {
                    jsonSection.innerHTML = `
                        <h3>🌍 Select Language</h3>
                        <select id="workflow-lang" onchange="loadSampleImages()" style="width: 100%; padding: 12px; border-radius: 8px; background: #0f172a; color: #eee; border: 1px solid #334155;">
                            <option value="english">English</option>
                            <option value="arabic">Arabic (العربية)</option>
                            <option value="french">French (Français)</option>
                        </select>
                    `;
                } else {
                    // Restore default JSON view
                    jsonSection.innerHTML = `
                        <h3>📤 Request Body (JSON)</h3>
                        <textarea id="request-body" placeholder="Enter JSON request..."></textarea>
                    `;
                    loadSampleData();
                }
                
                loadSampleImages();
            } else {
                uploadSection.style.display = 'none';
                jsonSection.style.display = 'block';
                jsonSection.innerHTML = `
                    <h3>📤 Request Body (JSON)</h3>
                    <textarea id="request-body" placeholder="Enter JSON request..."></textarea>
                `;
            }
            
            loadSampleData();
            clearResponse();
            uploadedFile = null;
            document.getElementById('upload-area').classList.remove('has-file');
            document.getElementById('preview-image').style.display = 'none';
        }
        
        function loadSampleImages() {
            const container = document.getElementById('sample-images');
            const ep = ENDPOINTS[currentEndpoint];
            let data = {};
            
            // Select appropriate sample data based on endpoint
            if (currentEndpoint === 'ocr_english' || (currentEndpoint === 'workflow' && document.getElementById('workflow-lang')?.value === 'english')) {
                data = SAMPLE_IMAGES.english;
            } else if (currentEndpoint === 'ocr_arabic' || (currentEndpoint === 'workflow' && document.getElementById('workflow-lang')?.value === 'arabic')) {
                data = SAMPLE_IMAGES.arabic;
            } else if (currentEndpoint === 'ocr_french' || (currentEndpoint === 'workflow' && document.getElementById('workflow-lang')?.value === 'french')) {
                data = SAMPLE_IMAGES.french;
            } else if (currentEndpoint === 'annotation' || ep.type === 'annotation') {
                data = SAMPLE_IMAGES.annotation;
            } else {
                data = { 'All Samples': [...Object.values(SAMPLE_IMAGES.english).flat(), ...Object.values(SAMPLE_IMAGES.arabic).flat(), ...Object.values(SAMPLE_IMAGES.french).flat()] };
            }
            
            container.innerHTML = '';
            container.style.display = 'block';

            for (const [category, images] of Object.entries(data)) {
        const section = document.createElement('div');
        section.className = 'sample-category';
        section.style.marginBottom = '25px';
        section.innerHTML = `
            <h4 style="margin: 15px 0 10px; color: #4fc3f7; border-bottom: 2px solid #334155; padding-bottom: 8px; font-size: 0.9rem; display: flex; align-items: center; gap: 8px;">
                <span>📁</span> ${category}
            </h4>`;
        
        const grid = document.createElement('div');
        grid.className = 'sample-images';
        grid.style.display = 'grid';
        grid.style.gridTemplateColumns = 'repeat(2, 1fr)';
        grid.style.gap = '15px';
        
        grid.innerHTML = images.map(img => `
            <div class="sample-card" style="border: 1px solid #334155; background: #0f172a; padding: 12px; border-radius: 10px; transition: all 0.2s;">
                <div onclick="loadSampleImage('${img.file}')" style="cursor: pointer;">
                    <div style="height: 120px; overflow: hidden; border-radius: 6px; background: #000; margin-bottom: 10px; display: flex; align-items: center; justify-content: center;">
                        <img src="/test/samples/${img.file}" alt="${img.name}" 
                             style="max-width: 100%; max-height: 100%; object-fit: contain;"
                             onerror="this.parentElement.innerHTML='<div style=\'color:#444;font-size:2rem\'>🖼️</div>'">
                    </div>
                    <p style="margin-bottom: 8px;"><strong style="color: #eee;">${img.name}</strong><br><small style="color: #888;">${img.desc}</small></p>
                </div>
                <div style="display: flex; gap: 8px;">
                    <button class="btn btn-secondary" style="padding: 6px; font-size: 0.75rem; flex: 1; background: #2563eb; color: white; border: none;" onclick="loadSampleImage('${img.file}')">Select</button>
                    <a href="/test/samples/${img.file}" target="_blank" class="btn btn-secondary" style="padding: 6px; font-size: 0.75rem; flex: 1; text-decoration: none; display: flex; align-items: center; justify-content: center; background: #334155;">View</a>
                </div>
            </div>
        `).join('');
        
        section.appendChild(grid);
        container.appendChild(section);
    }
}
        
        async function loadSampleImage(filename) {
            try {
                const response = await fetch('/test/samples/' + filename);
                const blob = await response.blob();
                uploadedFile = new File([blob], filename, { type: 'image/png' });
                
                const reader = new FileReader();
                reader.onload = function(e) {
                    document.getElementById('preview-image').src = e.target.result;
                    document.getElementById('preview-image').style.display = 'block';
                    document.getElementById('upload-area').classList.add('has-file');
                    
                    // Specific logic for annotation route: pre-fill matching JSON
                    if (currentEndpoint === 'annotation') {
                        const sampleJSON = getAnnotationSampleJSON(filename);
                        document.getElementById('request-body').value = JSON.stringify(sampleJSON, null, 2);
                    }
                };
                reader.readAsDataURL(blob);
            } catch (err) {
                console.error('Failed to load sample image:', err);
            }
        }
        
        function handleFileUpload(event) {
            const file = event.target.files[0];
            if (file) {
                uploadedFile = file;
                const reader = new FileReader();
                reader.onload = function(e) {
                    document.getElementById('preview-image').src = e.target.result;
                    document.getElementById('preview-image').style.display = 'block';
                    document.getElementById('upload-area').classList.add('has-file');
                };
                reader.readAsDataURL(file);
            }
        }
        
        function loadSampleData() {
            const data = sampleData[currentEndpoint] || {};
            const ep = ENDPOINTS[currentEndpoint];
            
            if (ep.type === 'annotation') {
                document.getElementById('request-body').value = JSON.stringify(data.grading_results || {}, null, 2);
            } else if (ep.type !== 'ocr') {
                document.getElementById('request-body').value = JSON.stringify(data, null, 2);
            }
        }
        
        function clearResponse() {
            document.getElementById('response-panel').style.display = 'none';
            document.getElementById('stats-grid').innerHTML = '';
        }
        
        async function runTest() {
            const ep = ENDPOINTS[currentEndpoint];
            
            document.getElementById('loading').classList.add('active');
            document.getElementById('response-panel').style.display = 'none';
            
            const startTime = performance.now();
            
            try {
                let response;
                
                if (currentEndpoint === 'workflow') {
                    if (!uploadedFile) {
                        alert('Please upload an exam image first');
                        document.getElementById('loading').classList.remove('active');
                        return;
                    }
                    const formData = new FormData();
                    formData.append('file', uploadedFile);
                    formData.append('language', document.getElementById('workflow-lang').value);
                    
                    response = await fetch(ep.path, {
                        method: 'POST',
                        body: formData
                    });
                } else if (ep.type === 'ocr') {
                    if (!uploadedFile) {
                        alert('Please upload an image first');
                        document.getElementById('loading').classList.remove('active');
                        return;
                    }
                    
                    const formData = new FormData();
                    formData.append('file', uploadedFile);
                    
                    response = await fetch(ep.path, {
                        method: 'POST',
                        body: formData
                    });
                } else if (ep.type === 'annotation') {
                    if (!uploadedFile) {
                        alert('Please upload an image first');
                        document.getElementById('loading').classList.remove('active');
                        return;
                    }
                    
                    // Convert file to base64
                    const base64 = await fileToBase64(uploadedFile);
                    const gradingResults = JSON.parse(document.getElementById('request-body').value);
                    
                    response = await fetch(ep.path, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            exam_file: base64,
                            file_type: uploadedFile.type.includes('pdf') || uploadedFile.name.endsWith('.pdf') ? 'pdf' : 'png',
                            grading_results: gradingResults
                        })
                    });
                } else if (ep.type === 'exam_report') {
                    // Exam report - downloads file
                    const body = document.getElementById('request-body').value;
                    response = await fetch(ep.path, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: body
                    });
                    
                    if (response.ok) {
                        // Download the file
                        const blob = await response.blob();
                        const url = URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = url;
                        const format = JSON.parse(body).format || 'docx';
                        a.download = `Exam_Report.${format}`;
                        a.click();
                        displayResponse(200, { success: true, message: 'Report downloaded!' }, performance.now() - startTime);
                        document.getElementById('loading').classList.remove('active');
                        return;
                    }
                } else {
                    const body = document.getElementById('request-body').value;
                    response = await fetch(ep.path, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: body
                    });
                }
                
                const endTime = performance.now();
                const data = await response.json();
                
                displayResponse(response.status, data, endTime - startTime);
            } catch (error) {
                displayResponse(500, { success: false, error: error.message }, 0);
            }
            
            document.getElementById('loading').classList.remove('active');
        }
        
        function fileToBase64(file) {
            return new Promise((resolve, reject) => {
                const reader = new FileReader();
                reader.readAsDataURL(file);
                reader.onload = () => {
                    const base64 = reader.result.split(',')[1];
                    resolve(base64);
                };
                reader.onerror = error => reject(error);
            });
        }
        
        function displayResponse(status, data, time) {
            document.getElementById('response-panel').style.display = 'block';
            
            const badge = document.getElementById('status-badge');
            badge.textContent = status + (status === 200 ? ' OK' : ' Error');
            badge.className = 'status-badge ' + (status === 200 ? 'status-success' : 'status-error');
            
            document.getElementById('response-time').textContent = time.toFixed(0) + 'ms';
            
            const statsGrid = document.getElementById('stats-grid');
            statsGrid.innerHTML = '';
            
            if (data.success) {
                let d = data.data || data; // Handle both nested and direct data
                
                // If workflow response, use grading_summary and annotation_output
                if (currentEndpoint === 'workflow' && data.grading_summary) {
                    d = data.grading_summary;
                    d.corrected_pdf = data.annotation_output?.corrected_pdf;
                    d.filename = data.annotation_output?.filename;
                }

                const stats = [];
                
                if (d.total_questions !== undefined) stats.push({ label: 'Questions', value: d.total_questions });
                if (d.correct_count !== undefined) stats.push({ label: 'Correct', value: d.correct_count });
                if (d.total_earned !== undefined) stats.push({ label: 'Points', value: d.total_earned + '/' + (d.total_possible || '?') });
                else if (d.points_earned !== undefined) stats.push({ label: 'Points', value: d.points_earned + '/' + (d.points_possible || d.total_points_possible || '?') });
                
                if (d.percentage !== undefined) stats.push({ label: 'Score', value: Math.round(d.percentage) + '%' });
                if (d.grading_passes_per_question !== undefined) stats.push({ label: 'AI Passes', value: d.grading_passes_per_question });
                if (d.flagged_for_review !== undefined && d.flagged_for_review > 0) stats.push({ label: 'Flagged', value: d.flagged_for_review });
                if (d.annotations_added !== undefined) stats.push({ label: 'Annotations', value: d.annotations_added });
                else if (data.annotation_output?.annotations_added !== undefined) stats.push({ label: 'Annotations', value: data.annotation_output.annotations_added });
                
                // For annotation/workflow, just show a download button
                if (currentEndpoint === 'annotation' || currentEndpoint === 'workflow') {
                    const imageData = d.corrected_image || data.annotation_output?.corrected_image;
                    if (imageData) {
                        statsGrid.innerHTML = `<div class="stat-card" style="background: linear-gradient(135deg, #22c55e, #16a34a); cursor: pointer; padding: 20px;" onclick="downloadData('data:image/png;base64,${imageData}', 'annotated_result.png')">
                            <div class="value" style="font-size: 2rem;">�</div>
                            <div class="label">Download Annotated Image</div>
                        </div>`;
                    }
                } else {
                    stats.forEach(s => {
                        statsGrid.innerHTML += `<div class="stat-card"><div class="value">${s.value}</div><div class="label">${s.label}</div></div>`;
                    });
                }
            }
            
            document.getElementById('response-body').innerHTML = syntaxHighlight(JSON.stringify(data, null, 2));
        }
        


        function downloadData(dataUrl, filename) {
            const link = document.createElement('a');
            link.href = dataUrl;
            link.download = filename;
            link.click();
        }
        
        function syntaxHighlight(json) {
            json = json.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
            return json.replace(/"([^"]+)":/g, '<span class="json-key">"$1"</span>:')
                       .replace(/: "([^"]*)"/g, ': <span class="json-string">"$1"</span>')
                       .replace(/: (\\d+\\.?\\d*)/g, ': <span class="json-number">$1</span>')
                       .replace(/: (true|false)/g, ': <span class="json-boolean">$1</span>');
        }
        
        // ============ DOCUMENTATION MODAL FUNCTIONS ============
        function showDocs() {
            const doc = ENDPOINT_DOCS[currentEndpoint];
            if (!doc) return;
            
            document.getElementById('doc-title').textContent = doc.title;
            
            // Set badge
            const badge = document.getElementById('doc-badge');
            badge.textContent = doc.method;
            badge.className = 'doc-badge';
            if (doc.method.includes('AI')) badge.classList.add('ai');
            else if (doc.method.includes('VISION')) badge.classList.add('vision');
            else badge.classList.add('code');
            
            // Set content
            document.getElementById('doc-logic').innerHTML = doc.logic;
            document.getElementById('doc-request-code').textContent = doc.request;
            document.getElementById('doc-response-code').textContent = doc.response;
            
            // Reset to logic tab
            showDocTab('logic');
            
            // Show modal
            document.getElementById('docs-modal').classList.add('active');
        }
        
        function closeDocs() {
            document.getElementById('docs-modal').classList.remove('active');
        }
        
        function showDocTab(tab) {
            // Update tabs
            document.querySelectorAll('.doc-tab').forEach(t => t.classList.remove('active'));
            event.target.classList.add('active');
            
            // Show selected section
            document.getElementById('doc-logic').style.display = tab === 'logic' ? 'block' : 'none';
            document.getElementById('doc-request').style.display = tab === 'request' ? 'block' : 'none';
            document.getElementById('doc-response').style.display = tab === 'response' ? 'block' : 'none';
        }
        
        // Close modal on outside click
        document.getElementById('docs-modal').addEventListener('click', function(e) {
            if (e.target === this) closeDocs();
        });
    </script>
</body>
</html>
'''

@test_bp.route('/')
def test_console():
    """Test console GUI"""
    return render_template_string(TEST_HTML)

@test_bp.route('/sample-data')
def get_sample_data():
    """Return sample data for all endpoints"""
    return jsonify(SAMPLE_DATA)

@test_bp.route('/samples/<filename>')
def serve_sample(filename):
    """Serve sample images"""
    return send_from_directory(SAMPLES_DIR, filename)
