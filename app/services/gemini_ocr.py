# Gemini OCR service for exam extraction
import io
from PIL import Image
import fitz
from google import genai

from app.config import Config
from app.models.schemas import OCRResponse


class GeminiOCRService:
    # OCR using Gemini 2.0 Flash with structured output
    
    PROMPTS = {
        'english': """You are an expert exam paper OCR system. Extract ALL questions IN DOCUMENT ORDER.

QUESTION TYPES (13 types) - Identify EXACTLY:

1. multiple_choice - Has lettered/numbered options (A, B, C, D)
   - options: {"A": "text", "B": "text"}
   
2. true_false - Statement to evaluate as true/false
   
3. matching - Two columns to connect
   - left_column: [{"id": "1", "text": "item"}]
   - right_column: [{"id": "a", "text": "item"}]
   - correct_matches: {"1": "a", "2": "b"}

4. fill_in_blank - Sentence with blanks (_____) 
   - blanks: ["answer1", "answer2"] in order

5. ordering - Items to arrange in sequence
   - ordering_items: [{"item_id": "A", "content": "text"}]
   - correct_order: ["C", "A", "B"]

6. short_answer - Brief factual response (NOT analytical)
   - Use for: "State 4...", "What is...?", "Name...", "List...", "Give examples of..."
   - Questions asking for FACTS, not analysis or explanation
   - expected_answer_count: number of items if specified (e.g., "State 4" = 4)
   - acceptable_answers: list of correct answers if known

7. open_ended - Analytical questions requiring explanation/reasoning
   - Use for: "Explain why...", "Discuss...", "Analyze...", "Give reasons...", "Justify..."
   - Questions requiring THINKING and ANALYSIS, not just facts
   - answer_length: "short" or "long"
   - expected_keywords: key terms expected

8. compare_contrast - Compare two+ items
   - compare_items: ["item1", "item2"]
   
9. definition - Define a term
    - term_to_define: the term

10. labeling - Label parts on a diagram/shape by WRITING ON IT
    - Use when: students must write/draw labels directly on the diagram or fill numbered blanks pointing to parts
    - diagram_description: what diagram shows
    - labeling_items: [{"label_id": "1", "pointer_description": "points to...", "correct_label": "..."}]

11. labeling_image - Same as labeling but student handwriting needs image OCR
    - Use when: labels are handwritten on the actual image

12. math_equation - Mathematical problem to solve
    - math_content: The equation/expression
    - correct_answer: Final answer (if shown on answer key)

13. table - Table to complete
    - table_headers, table_rows

CRITICAL RULES:
- question_number: EXACT as shown
- For short_answer vs open_ended: short_answer = FACTS, open_ended = ANALYSIS
- student_answer: Identify what the student marked/wrote
- student_markings: Describe visual marks
- Include correct_answer ONLY if marked on paper
- extracted_text: Include FULL RAW OCR text """,

        'arabic': """أنت نظام OCR متخصص لأوراق الامتحانات. استخرج جميع الأسئلة بترتيب المستند.

أنواع الأسئلة (13 نوع):

1. multiple_choice - الاختيار من متعدد (أ، ب، ج، د)
2. true_false - الصواب والخطأ
3. matching - المزاوجة / التوصيل
4. fill_in_blank - ملء الفراغات
5. ordering - إعادة الترتيب
6. short_answer - إجابات قصيرة (حقائق فقط، ليس تحليل)
   - مثل: "اذكر 4..."، "ما هو...؟"، "عدد..."
   - expected_answer_count: عدد العناصر المطلوبة
7. open_ended - أسئلة مفتوحة تحليلية (تتطلب تفكير وتحليل)
   - مثل: "اشرح لماذا..."، "ناقش..."، "برر..."
   - answer_length: "short" (1-3 جمل) أو "long" (فقرة+)
8. compare_contrast - المقارنة والمقابلة
9. definition - التعريفات
10. labeling - تحديد الأجزاء على الرسم/الشكل (كتابة أو رسم على المخطط)
11. labeling_image - تحديد الأجزاء (كتابة يدوية على الصورة تحتاج OCR)
12. math_equation - معادلات رياضية
13. table - جداول

قواعد:
- short_answer = حقائق، open_ended = تحليل
- student_answer: استخرج إجابة الطالب
- student_markings: وصف العلامات المرئية
- extracted_text: النص الكامل """,

        'french': """Système OCR expert pour examens. Extraire TOUTES les questions DANS L'ORDRE.

TYPES DE QUESTIONS (13 types):

1. multiple_choice - Choix multiples (A, B, C, D)
2. true_false - Vrai/Faux
3. matching - Appariement (deux colonnes)
4. fill_in_blank - Textes à trous
5. ordering - Mise en ordre
6. short_answer - Réponses courtes (FAITS, pas analyse)
   - Pour: "Citez 4...", "Qu'est-ce que...?", "Nommez..."
   - expected_answer_count: nombre d'éléments demandés
7. open_ended - Questions analytiques (nécessite réflexion)
   - Pour: "Expliquez pourquoi...", "Discutez...", "Justifiez..."
   - answer_length: "short" ou "long"
8. compare_contrast - Comparer et contraster
9. definition - Définitions
10. labeling - Étiqueter les parties d'un diagramme (écrire/dessiner dessus)
11. labeling_image - Étiquetage manuscrit sur l'image
12. math_equation - Équations mathématiques
13. table - Tableaux

RÈGLES:
- short_answer = FAITS, open_ended = ANALYSE
- student_answer: Ce que l'étudiant a écrit
- student_markings: Décrire les marques visuelles
- extracted_text: Texte complet du document"""
    }
    
    def __init__(self):
        if not Config.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not set")
        self.client = genai.Client(api_key=Config.GEMINI_API_KEY)
    
    def process_image(self, image_data: bytes, language: str) -> dict:
        prompt = self.PROMPTS.get(language, self.PROMPTS['english'])
        image = Image.open(io.BytesIO(image_data))
        
        response = self.client.models.generate_content(
            model=Config.GEMINI_MODEL,
            contents=[prompt, image],
            config={
                "response_mime_type": "application/json",
                "response_json_schema": OCRResponse.model_json_schema(),
            }
        )
        
        result = OCRResponse.model_validate_json(response.text)
        result_dict = result.model_dump()
        result_dict['language'] = language
        return result_dict
    
    def process_pdf(self, pdf_data: bytes, language: str) -> dict:
        prompt = self.PROMPTS.get(language, self.PROMPTS['english'])
        
        pdf_doc = fitz.open(stream=pdf_data, filetype="pdf")
        images = []
        
        for page_num in range(len(pdf_doc)):
            page = pdf_doc.load_page(page_num)
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            images.append(Image.open(io.BytesIO(pix.tobytes("png"))))
        
        pdf_doc.close()
        
        response = self.client.models.generate_content(
            model=Config.GEMINI_MODEL,
            contents=[prompt] + images,
            config={
                "response_mime_type": "application/json",
                "response_json_schema": OCRResponse.model_json_schema(),
            }
        )
        
        result = OCRResponse.model_validate_json(response.text)
        result_dict = result.model_dump()
        result_dict['language'] = language
        return result_dict
