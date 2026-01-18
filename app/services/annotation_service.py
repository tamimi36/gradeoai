# Annotation service using grid-based positioning
# Shows: checkmarks, X marks, scores, correct answers, and feedback
import io
import base64
import json
from typing import Dict, Any
from PIL import Image, ImageDraw, ImageFont
from google import genai

from app.config import Config


class AnnotationService:
    """
    Complete annotation service:
    - Grid-based positioning for accuracy
    - Shows correct answer when wrong (for MCQ, T/F, etc.)
    - Shows feedback for AI-graded questions
    """
    
    GRID_SIZE = 20
    
    def __init__(self):
        if not Config.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not set")
        self.client = genai.Client(api_key=Config.GEMINI_API_KEY)
    
    def _create_grid_overlay(self, image: Image.Image) -> bytes:
        """Create image with grid overlay."""
        overlay = image.copy()
        draw = ImageDraw.Draw(overlay)
        
        width, height = image.size
        cell_w = width / self.GRID_SIZE
        cell_h = height / self.GRID_SIZE
        
        for i in range(1, self.GRID_SIZE):
            x = int(i * cell_w)
            draw.line([(x, 0), (x, height)], fill=(150, 150, 150), width=1)
            y = int(i * cell_h)
            draw.line([(0, y), (width, y)], fill=(150, 150, 150), width=1)
        
        try:
            font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", max(10, min(width, height) // 50))
        except:
            font = ImageFont.load_default()
        
        for i in range(self.GRID_SIZE):
            x = int((i + 0.3) * cell_w)
            draw.text((x, 2), str(i), fill=(100, 100, 100), font=font)
            y = int((i + 0.3) * cell_h)
            draw.text((2, y), str(i), fill=(100, 100, 100), font=font)
        
        buffer = io.BytesIO()
        overlay.save(buffer, format='PNG')
        return buffer.getvalue()
    
    def _detect_grid_positions(self, grid_image: bytes, num_questions: int) -> Dict[str, Any]:
        """Detect positions using grid."""
        
        prompt = f"""This image has a 20x20 grid (cols 0-19, rows 0-19).
There are {num_questions} questions on this exam.

TASK: Find the EXACT location of EACH question's answer.

For EACH question (numbered 1 to {num_questions}), identify:
1. question_row: The row where the question NUMBER appears (e.g., "1.", "2.", "3.")
2. answer_col: Column of the CENTER of THAT SPECIFIC question's answer
3. answer_row: Row of the CENTER of THAT SPECIFIC question's answer  
4. feedback_row: Row immediately below that answer (for feedback text)

CRITICAL RULES:
- Each question has its OWN answer in its OWN area
- Question 1's answer is ABOVE Question 2's answer
- Question 2's answer is ABOVE Question 3's answer
- NEVER put Question 2's mark in Question 4's area!
- Answers should be vertically ordered: q1 < q2 < q3 in terms of row numbers
- Look for circled letters (A, B, C, D), handwritten text, or filled bubbles

MULTI-COLUMN LAYOUTS:
- If exam has 2 columns (left and right sections), questions may be side-by-side
- In that case, left column has its own question numbers, right column has different ones
- Still maintain the rule: each question's mark goes on ITS answer only

Return JSON:
{{
    "score_blank_col": 14,
    "score_blank_row": 1,
    "questions": [
        {{"q": 1, "question_row": 2, "answer_col": 3, "answer_row": 4, "feedback_row": 5}},
        {{"q": 2, "question_row": 6, "answer_col": 3, "answer_row": 8, "feedback_row": 9}}
    ]
}}

DIAGRAM LABELING (CRITICAL):
- If the question is a diagram (e.g., heart anatomy), students write labels near pointers/arrows.
- Find the EXACT location of EACH student's handwritten label for EACH part.
- Do NOT stack all marks for a diagram in one place.
- Each label must have its own (answer_col, answer_row) on the handwritten text.

MATCHING QUESTIONS (EACH PAIR GETS A MARK):
- A matching question connects LEFT items (1. Dog, 2. Cat) to RIGHT answers (A. Meows, B. Barks).
- EACH matched pair is graded separately, so return MULTIPLE entries in the questions array.
- For a 4-pair matching, return 4 entries (q1, q2, q3, q4).
- Position each mark EXACTLY NEXT TO the RIGHT column answer text (A. Meows, B. Barks, etc.).
- CRITICAL: The answer_row must be the SAME as the answer row. The mark should NOT be above the text.
- Place marks slightly to the RIGHT of each answer text, aligned vertically with the center of the text.

ORDERING QUESTIONS:
- If a question asks to order items (1-4), return ONE entry with mark position near the question number.

VERIFY: Make sure answer_row increases from q1 to q2 to q3 (unless multi-column or diagram)."""

        try:
            image_b64 = base64.b64encode(grid_image).decode('utf-8')
            
            response = self.client.models.generate_content(
                model=Config.GEMINI_MODEL,
                contents=[
                    {"text": prompt},
                    {"inline_data": {"mime_type": "image/png", "data": image_b64}}
                ],
                config={"response_mime_type": "application/json"}
            )
            
            result = json.loads(response.text)
            print(f"Grid positions: {json.dumps(result, indent=2)}")
            return result
            
        except Exception as e:
            print(f"Error: {e}")
            return self._default_grid(num_questions)
    
    def _default_grid(self, n: int) -> Dict[str, Any]:
        """Default positions."""
        questions = []
        for i in range(n):
            row_base = 3 + (i * (15 // max(n, 1)))
            questions.append({
                "q": i + 1,
                "question_row": row_base,
                "answer_col": 8,
                "answer_row": row_base + 2,
                "feedback_row": row_base + 4
            })
        return {"score_blank_col": 13, "score_blank_row": 1, "questions": questions}
    
    def _grid_to_pixel(self, col: int, row: int, width: int, height: int) -> tuple:
        """Convert grid to pixels."""
        cell_w = width / self.GRID_SIZE
        cell_h = height / self.GRID_SIZE
        x = int((col + 0.5) * cell_w)
        y = int((row + 0.5) * cell_h)
        return x, y
    
    def detect_existing_annotations(self, image_bytes: bytes) -> Dict[str, Any]:
        """Detect existing annotations in an image using AI vision."""
        image = Image.open(io.BytesIO(image_bytes))
        width, height = image.size
        
        prompt = f"""Analyze this graded exam image and detect ALL existing annotations.

IMPORTANT: Each question has a COMBINED annotation with:
- An ICON (checkmark ✓, X mark ✗, or dash —) in a white circle
- A SCORE BOX (like "2/2" or "0/1") immediately to the right of the icon

These should be returned as ONE annotation per question, NOT separate entries.

Look for:
1. COMBINED MARK+SCORE: Icon circle + score box together (e.g., "✓ 2/2" or "✗ 0/2")
2. CORRECT ANSWER LABELS like "Correct: C" (separate, usually below wrong answers)
3. FEEDBACK text (separate, usually for AI-graded questions)
4. FINAL SCORE at top like "8/10" or "Score: 8/10"

For each annotation, provide:
- id: unique (q1_mark, q2_mark, final_score, q2_correct, etc.)
- type: "check", "x", "partial", "correct_answer", "feedback", "final_score"
- text: COMBINED text including both icon symbol AND score (e.g., "✓ 2/2" not just "✓")
- x: position of the LEFT EDGE of the icon circle in pixels (0-{width})
- y: position of the TOP of the icon circle in pixels (0-{height})
- color: hex (#19aa19=green, #be1e1e=red, #c89600=yellow, #143c8c=blue)
- question_number: if related to a question (null for final_score)

CRITICAL RULES:
- Do NOT create separate entries for the icon and the score - combine them
- Position (x, y) should be at the icon circle, the score box appears to its right
- Include the score pattern like "2/2" in the text field

Return JSON:
{{
    "annotations": [
        {{"id": "q1_mark", "type": "check", "text": "✓ 2/2", "x": 480, "y": 175, "color": "#19aa19", "question_number": 1}},
        {{"id": "q2_mark", "type": "x", "text": "✗ 0/2", "x": 480, "y": 255, "color": "#be1e1e", "question_number": 2}},
        {{"id": "q2_correct", "type": "correct_answer", "text": "Correct: C", "x": 485, "y": 290, "color": "#143c8c", "question_number": 2}},
        {{"id": "final_score", "type": "final_score", "text": "✓ 2/2", "x": 450, "y": 50, "color": "#19aa19", "question_number": null}}
    ]
}}"""

        try:
            image_b64 = base64.b64encode(image_bytes).decode('utf-8')
            response = self.client.models.generate_content(
                model=Config.GEMINI_MODEL,
                contents=[
                    {"text": prompt},
                    {"inline_data": {"mime_type": "image/png", "data": image_b64}}
                ],
                config={"response_mime_type": "application/json"}
            )
            result = json.loads(response.text)
            result['image_width'] = width
            result['image_height'] = height
            return result
        except Exception as e:
            return {"annotations": [], "image_width": width, "image_height": height, "error": str(e)}
    
    
    def _get_font(self, size: int, language: str = 'en'):
        """Get stylish font for scores - modern handwriting style."""
        if language == 'ar':
            paths = [
                "C:/Windows/Fonts/arialbd.ttf",
                "C:/Windows/Fonts/arial.ttf",
            ]
        else:
            # Stylish fonts for scores
            paths = [
                "C:/Windows/Fonts/segoescb.ttf",   # Segoe Script Bold
                "C:/Windows/Fonts/segoesc.ttf",    # Segoe Script
                "C:/Windows/Fonts/comicbd.ttf",    # Comic Sans Bold
                "C:/Windows/Fonts/calibriz.ttf",   # Calibri Bold Italic
            ]
        
        for path in paths:
            try:
                return ImageFont.truetype(path, size)
            except:
                continue
        return ImageFont.load_default()
    
    def _get_simple_font(self, size: int, language: str = 'en'):
        """Get modern readable font for feedback/correct answers."""
        if language == 'ar':
            paths = [
                "C:/Windows/Fonts/tradbdo.ttf",    # Traditional Arabic Bold
                "C:/Windows/Fonts/arialbd.ttf",
                "C:/Windows/Fonts/arial.ttf",
            ]
        else:
            # Clean, modern sans-serif fonts
            paths = [
                "C:/Windows/Fonts/seguisb.ttf",    # Segoe UI Semibold
                "C:/Windows/Fonts/segoeuib.ttf",   # Segoe UI Bold
                "C:/Windows/Fonts/calibrib.ttf",   # Calibri Bold
                "C:/Windows/Fonts/arialbd.ttf",    # Arial Bold
            ]
        
        for path in paths:
            try:
                return ImageFont.truetype(path, size)
            except:
                continue
        return ImageFont.load_default()
    
    def _is_arabic(self, text: str) -> bool:
        """Check if text contains Arabic characters."""
        if not text:
            return False
        # Arabic Unicode range: U+0600 to U+06FF
        return any('\u0600' <= char <= '\u06FF' for char in text)
    
    def _draw_checkmark(self, draw, x, y, size):
        # Draw white background circle for visibility
        cx, cy = x + size//2, y + size//2
        r = int(size * 0.7)
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 255, 255, 220))
        # Draw checkmark
        color = (25, 140, 25)
        lw = max(3, size // 5)
        draw.line([(x, y + size*0.5), (x + size*0.35, y + size*0.85)], fill=color, width=lw)
        draw.line([(x + size*0.35, y + size*0.85), (x + size, y + size*0.1)], fill=color, width=lw)
    
    def _draw_x_mark(self, draw, x, y, size):
        # Draw white background circle for visibility
        cx, cy = x + size//2, y + size//2
        r = int(size * 0.7)
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 255, 255, 220))
        # Draw X mark
        color = (190, 30, 30)
        lw = max(3, size // 5)
        draw.line([(x + 2, y + 2), (x + size - 2, y + size - 2)], fill=color, width=lw)
        draw.line([(x + size - 2, y + 2), (x + 2, y + size - 2)], fill=color, width=lw)
    
    def _draw_partial_mark(self, draw, x, y, size):
        # Draw white background circle for visibility
        cx, cy = x + size//2, y + size//2
        r = int(size * 0.7)
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 255, 255, 220))
        # Draw Partial mark (yellow dash/minus)
        color = (200, 150, 0) # Gold/Yellow
        lw = max(4, size // 4)
        draw.line([(x + 2, y + size//2), (x + size - 2, y + size//2)], fill=color, width=lw)

    def _draw_pill_badge(self, draw, box, fill_color, border_color=None):
        """Draw a modern rounded badge with sharper edges (modern look)."""
        x1, y1, x2, y2 = box
        # Modern look: Sharper edges - radius 3 instead of 6
        radius = 3
        
        # Draw border first if specified
        if border_color:
            border_box = (x1 - 1, y1 - 1, x2 + 1, y2 + 1)
            self._draw_rounded_rect(draw, border_box, radius + 1, border_color)
        
        # Draw main fill
        self._draw_rounded_rect(draw, box, radius, fill_color)

    def _draw_rounded_rect(self, draw, box, radius, fill):
        """Draw a rounded rectangle."""
        x1, y1, x2, y2 = box
        # Ensure radius isn't too large for box
        radius = min(radius, (y2 - y1) // 2, (x2 - x1) // 2)
        if radius < 1:
            draw.rectangle(box, fill=fill)
            return
        # Draw rounded corners using ellipses and rectangles
        draw.rectangle([x1 + radius, y1, x2 - radius, y2], fill=fill)
        draw.rectangle([x1, y1 + radius, x2, y2 - radius], fill=fill)
        draw.ellipse([x1, y1, x1 + radius * 2, y1 + radius * 2], fill=fill)
        draw.ellipse([x2 - radius * 2, y1, x2, y1 + radius * 2], fill=fill)
        draw.ellipse([x1, y2 - radius * 2, x1 + radius * 2, y2], fill=fill)
        draw.ellipse([x2 - radius * 2, y2 - radius * 2, x2, y2], fill=fill)
    
    def _draw_text_with_bg(self, draw, x, y, text, font, text_color, padding=6):
        """Draw text with semi-transparent rounded background."""
        try:
            bbox = draw.textbbox((x, y), text, font=font)
            # Add padding
            bg_box = (bbox[0] - padding, bbox[1] - padding // 2, 
                      bbox[2] + padding, bbox[3] + padding // 2)
            # Semi-transparent background (alpha 160)
            self._draw_pill_badge(draw, bg_box, (255, 255, 255, 160), (200, 200, 200, 120))
        except:
            pass
        # Draw text
        draw.text((x, y), text, fill=text_color, font=font)
    
    def _draw_correct_label(self, draw, x, y, text, font):
        """Draw a 'Correct: X' label with semi-transparent blue background."""
        try:
            bbox = draw.textbbox((x, y), text, font=font)
            # Rounded background
            bg_box = (bbox[0] - 8, bbox[1] - 3, bbox[2] + 8, bbox[3] + 3)
            # Blue semi-transparent background (alpha 140)
            self._draw_pill_badge(draw, bg_box, (230, 242, 255, 140), (100, 150, 220, 100))
        except:
            pass
        # Draw text in dark blue
        draw.text((x, y), text, fill=(20, 60, 140), font=font)
    
    def _wrap_text(self, text: str, max_chars: int = 40) -> str:
        """Wrap long text."""
        if len(text) <= max_chars:
            return text
        words = text.split()
        lines = []
        current = ""
        for word in words:
            if len(current) + len(word) + 1 <= max_chars:
                current = f"{current} {word}".strip()
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        return "\n".join(lines)  # Show ALL lines, no limit
    
    # Localized labels for different languages
    LABELS = {
        'en': {'correct': 'Correct:', 'feedback': 'Feedback:'},
        'ar': {'correct': 'الإجابة الصحيحة:', 'feedback': 'ملاحظات:'},
        'fr': {'correct': 'Réponse:', 'feedback': 'Commentaire:'}
    }
    
    def annotate_exam(self, exam_file: bytes, file_type: str,
                      grading_results: Dict[str, Any], 
                      language: str = 'en',
                      draw_on_image: bool = True) -> Dict[str, Any]:
        """Annotate exam with marks, scores, correct answers, and feedback.
        
        Args:
            language: 'en', 'ar', or 'fr' for localized labels
        """
        
        image = Image.open(io.BytesIO(exam_file))
        if image.mode != 'RGBA':
            image = image.convert('RGBA')
        
        # Save original clean image for non-destructive editing
        original_output = io.BytesIO()
        image.convert('RGB').save(original_output, format='PNG')
        original_output.seek(0)
        original_image_b64 = base64.b64encode(original_output.getvalue()).decode('utf-8')
        
        width, height = image.size
        
        questions = grading_results.get('questions', [])
        total_earned = grading_results.get('total_earned', 0)
        total_possible = grading_results.get('total_possible', 0)
        num_q = len(questions)
        
        if num_q == 0:
            output = io.BytesIO()
            image.convert('RGB').save(output, format='PNG')
            output.seek(0)
            return {
                'success': True,
                'corrected_image': base64.b64encode(output.getvalue()).decode('utf-8'),
                'corrected_pdf': base64.b64encode(output.getvalue()).decode('utf-8'),
                'filename': 'exam_corrected.png',
                'pages_processed': 1,
                'annotations_added': 0
            }
        
        # Build question data map
        q_data = {}
        for q in questions:
            qn = q.get('question_number', 0)
            earned = q.get('points_earned', 0)
            possible = q.get('points_possible', 1)
            
            # Get correct answer (for MCQ, T/F, matching, fill-in-blank, math)
            correct_answer = q.get('correct_answer', '')
            
            # Get feedback - prefer annotation_feedback for clearer display
            feedback = (q.get('annotation_feedback', '') or 
                       q.get('feedback', '') or 
                       q.get('reason', '') or 
                       q.get('explanation', ''))
            
            # Get question type
            q_type = q.get('question_type', 'unknown')
            
            q_data[str(qn)] = {
                'correct': earned >= possible,
                'earned': earned,
                'possible': possible,
                'correct_answer': correct_answer,
                'feedback': feedback,
                'q_type': q_type
            }
        
        # Detect grid positions
        grid_image = self._create_grid_overlay(image)
        grid_pos = self._detect_grid_positions(grid_image, num_q)
        
        draw = ImageDraw.Draw(image)
        
        RED = (180, 30, 30)
        GREEN = (25, 130, 25)
        YELLOW = (200, 150, 0)  # For partial credit
        DARK_BLUE = (15, 50, 130)  # For correct answer/feedback
        
        # Scale sizes based on image dimensions (proportional to sqrt of area)
        scale_factor = (width * height) ** 0.5 / 1000  # Normalize to ~1 for 1000px
        
        # Larger sizes for visibility
        mark_size = int(max(20, min(60, 32 * scale_factor)))
        font_size = int(max(18, min(48, 30 * scale_factor)))  # Score font - larger
        feedback_font_size = int(max(16, min(40, 24 * scale_factor)))  # Feedback - readable
        
        # Detect language from content
        sample_text = ""
        for q in questions:
            sample_text += str(q.get('correct_answer', '')) + str(q.get('feedback', ''))
        is_arabic = self._is_arabic(sample_text)
        lang = 'ar' if is_arabic else 'en'
        
        # Stylish font for scores, simple font for feedback/answers
        score_font = self._get_font(font_size, lang)
        simple_font = self._get_simple_font(feedback_font_size, lang)
        
        # For Arabic: marks go on LEFT side, text is RTL
        is_rtl = is_arabic
        
        # Collect annotation metadata for embedding in PNG
        annotation_metadata = []
        
        # Draw annotations for each question
        for zone in grid_pos.get("questions", []):
            qn = str(zone.get("q", ""))
            if qn not in q_data:
                continue
            
            data = q_data[qn]
            earned = data['earned']
            possible = data['possible']
            correct_answer = data.get('correct_answer', '')
            feedback = data.get('feedback', '')
            q_type = data.get('q_type', '')
            
            # Determine color and icon based on marks
            if earned >= possible and possible > 0:
                status_color = GREEN
                draw_icon_func = self._draw_checkmark
            elif earned > 0:
                status_color = YELLOW
                draw_icon_func = self._draw_partial_mark
            else:
                status_color = RED
                draw_icon_func = self._draw_x_mark

            # Get answer position from AI
            q_row = zone.get("question_row", 5)
            ans_col = zone.get("answer_col", 8)
            ans_row = zone.get("answer_row", q_row + 2)
            icon_x, icon_y = self._grid_to_pixel(ans_col, ans_row, width, height)
            
            # Draw mark FIRST
            mark_type = 'check' if earned >= possible else ('partial' if earned > 0 else 'x')
            mark_symbol = '✓' if mark_type == 'check' else ('—' if mark_type == 'partial' else '✗')
            mark_color_hex = '#19aa19' if mark_type == 'check' else ('#c89600' if mark_type == 'partial' else '#be1e1e')
            
            if draw_on_image:
                draw_icon_func(draw, icon_x - mark_size//2, icon_y - mark_size//2, mark_size)
            
            # Draw score NEXT TO the mark (offset to the right)
            e_str = str(int(earned)) if earned == int(earned) else f"{earned:.1f}"
            p_str = str(int(possible)) if possible == int(possible) else f"{possible:.1f}"
            score_text = f"{e_str}/{p_str}"
            score_x = icon_x + mark_size + 8  # Right of the mark
            score_y = icon_y - font_size//2
            
            if draw_on_image:
                self._draw_text_with_bg(draw, score_x, score_y, score_text,
                                        score_font, status_color)
            
            # Record COMBINED mark+score as single annotation (prevents duplicates)
            combined_text = f"{mark_symbol} {score_text}"
            annotation_metadata.append({
                'id': f'q{qn}_mark',
                'type': mark_type,  # 'check', 'x', or 'partial'
                'text': combined_text,
                'x': icon_x - mark_size//2,
                'y': icon_y - mark_size//2,
                'width': mark_size * 3, # Estimate for icon + score box
                'height': max(mark_size, font_size),
                'color': mark_color_hex,
                'question_number': int(qn),
                'status': 'pending'
            })
            
            # For WRONG or PARTIAL answers: show correct answer or feedback
            if earned < possible:
                # Fixed-answer types (have definitive correct answers)
                fixed_types = ['multiple_choice', 'true_false', 'matching', 'fill_in_blank', 
                               'ordering', 'math_equations']
                
                # AI-graded types (have feedback instead of fixed answer)
                ai_types = ['labeling', 'short_answer', 'open_ended', 'compare_contrast', 
                            'definition', 'table']
                
                if q_type in fixed_types and correct_answer:
                    # Format correct answer based on type
                    if q_type == 'true_false':
                        if isinstance(correct_answer, bool):
                            ans_text = "True" if correct_answer else "False"
                        else:
                            ans_text = str(correct_answer)
                    
                    elif q_type == 'matching':
                        # Matching: show key pairs like "1→B, 2→A"
                        if isinstance(correct_answer, dict):
                            pairs = [f"{k}→{v}" for k, v in list(correct_answer.items())[:3]]
                            ans_text = ", ".join(pairs)
                            if len(correct_answer) > 3:
                                ans_text += "..."
                        else:
                            ans_text = str(correct_answer)
                    
                    elif q_type == 'ordering':
                        # Ordering: show sequence like "1,2,3,4"
                        if isinstance(correct_answer, list):
                            ans_text = ",".join(str(x) for x in correct_answer[:5])
                            if len(correct_answer) > 5:
                                ans_text += "..."
                        else:
                            ans_text = str(correct_answer)
                    
                    elif q_type == 'fill_in_blank':
                        # Fill-in-blank: show answers like "cat, dog"
                        if isinstance(correct_answer, list):
                            ans_text = ", ".join(str(a) for a in correct_answer[:3])
                            if len(correct_answer) > 3:
                                ans_text += "..."
                        elif isinstance(correct_answer, dict):
                            # Multiple blanks: {1: "cat", 2: "dog"}
                            items = [f"{v}" for v in list(correct_answer.values())[:3]]
                            ans_text = ", ".join(items)
                        else:
                            ans_text = str(correct_answer)
                    
                    else:
                        # Default: MCQ, math_equations, etc.
                        if isinstance(correct_answer, list):
                            ans_text = ", ".join(str(a) for a in correct_answer)
                        else:
                            ans_text = str(correct_answer)
                    
                    # Position: BELOW the X mark (use feedback_row from AI detection)
                    feedback_row = zone.get("feedback_row", ans_row + 1)
                    fb_col = zone.get("answer_col", 8)
                    ans_x, ans_y = self._grid_to_pixel(fb_col, feedback_row, width, height)
                    # Use localized label for correct answer
                    label = self.LABELS.get(language, self.LABELS['en'])['correct']
                    text = f"{label} {ans_text}"
                    if draw_on_image:
                        self._draw_correct_label(draw, ans_x, ans_y, text, simple_font)
                    
                    # Record correct answer annotation
                    annotation_metadata.append({
                        'id': f'q{qn}_correct',
                        'type': 'correct_answer',
                        'text': text,
                        'x': ans_x,
                        'y': ans_y,
                        'width': font_size * 5,
                        'height': font_size + 10,
                        'color': '#143c8c',
                        'question_number': int(qn),
                        'status': 'pending'
                    })
                
                # AI-graded types or any type with feedback
                elif feedback or q_type in ai_types:
                    fb_text = feedback if feedback else ""
                    if fb_text:
                        # Position: BELOW the mark (use feedback_row)
                        feedback_row = zone.get("feedback_row", ans_row + 1)
                        fb_col = zone.get("answer_col", 8)
                        fb_x, fb_y = self._grid_to_pixel(fb_col, feedback_row, width, height)
                        wrapped = self._wrap_text(fb_text, 40)  # More chars per line
                        if draw_on_image:
                            self._draw_text_with_bg(draw, fb_x, fb_y, wrapped, simple_font, DARK_BLUE)
                        
                        # Record feedback annotation
                        annotation_metadata.append({
                            'id': f'q{qn}_feedback',
                            'type': 'feedback',
                            'text': wrapped,
                            'x': fb_x,
                            'y': fb_y,
                            'width': font_size * 8,
                            'height': font_size * 3,
                            'color': '#143c8c',
                            'question_number': int(qn),
                            'status': 'pending'
                        })
        
        # Save with embedded annotation metadata
        from PIL.PngImagePlugin import PngInfo
        metadata = PngInfo()
        metadata.add_text("gradeo_annotations", json.dumps({
            'annotations': annotation_metadata,
            'image_width': width,
            'image_height': height,
            'version': '1.0'
        }))
        
        output = io.BytesIO()
        # In non-destructive mode, the "output" image is still the clean one (nothing was drawn on it)
        image.convert('RGB').save(output, format='PNG', pnginfo=metadata)
        output.seek(0)
        
        final_bytes = output.getvalue()
        
        return {
            'success': True,
            'corrected_image': base64.b64encode(final_bytes).decode('utf-8'),
            'original_image': original_image_b64,  # Clean image for editing
            'corrected_pdf': base64.b64encode(final_bytes).decode('utf-8'),
            'filename': 'exam_corrected.png',
            'image_filename': 'exam_corrected.png',
            'pages_processed': 1,
            'annotations_added': num_q,
            'annotation_metadata': annotation_metadata,  # Positions for editing
            'method': 'grid_complete',
            'is_draft': not draw_on_image
        }
