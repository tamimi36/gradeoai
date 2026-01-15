# Annotation service using OpenAI for image generation
import io
import base64
from typing import Dict, Any
from PIL import Image
import openai

from app.config import Config


class AnnotationService:
    """Uses OpenAI to generate teacher-style annotated exam papers."""
    
    def __init__(self):
        if not Config.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY not set")
        self.client = openai.OpenAI(api_key=Config.OPENAI_API_KEY)
    
    def annotate_exam(self, exam_file: bytes, file_type: str,
                      grading_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate annotated exam using OpenAI."""
        
        # Prepare grading info
        questions = grading_results.get('questions', [])
        total_earned = grading_results.get('total_earned', 0)
        total_possible = grading_results.get('total_possible', 100)
        
        grading_text = ""
        for q in questions:
            q_num = q.get('question_number', '?')
            earned = q.get('points_earned', 0)
            possible = q.get('points_possible', 1)
            is_correct = earned >= possible
            mark = "CORRECT" if is_correct else "WRONG"
            grading_text += f"Q{q_num}: {mark} ({earned}/{possible})\n"
        
        # Simple teacher-style prompt - let AI decide naturally
        prompt = f"""You are a teacher grading this exam with a red and green pen.

{grading_text}
Total: {total_earned}/{total_possible}

Mark it like a real teacher would:
- Green ✓ for correct answers
- Red ✗ for wrong answers
- Write the score in the score box

Use natural teacher handwriting style."""

        try:
            # Load image
            image = Image.open(io.BytesIO(exam_file))
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Resize if too large for DALL-E (max 4MB, 1024x1024 for edit)
            max_size = 1024
            if image.width > max_size or image.height > max_size:
                ratio = min(max_size / image.width, max_size / image.height)
                new_size = (int(image.width * ratio), int(image.height * ratio))
                image = image.resize(new_size, Image.Resampling.LANCZOS)
            
            # Make square for DALL-E
            size = max(image.width, image.height)
            square_img = Image.new('RGB', (size, size), (255, 255, 255))
            offset = ((size - image.width) // 2, (size - image.height) // 2)
            square_img.paste(image, offset)
            
            # Save to bytes
            img_buffer = io.BytesIO()
            square_img.save(img_buffer, format='PNG')
            img_buffer.seek(0)
            
            # Create mask (full image - we want to add overlay everywhere)
            mask = Image.new('RGBA', (size, size), (0, 0, 0, 128))  # Semi-transparent
            mask_buffer = io.BytesIO()
            mask.save(mask_buffer, format='PNG')
            mask_buffer.seek(0)
            
            print("Calling OpenAI DALL-E for image edit...")
            
            # Use DALL-E image edit - need to pass as file tuples with mimetype
            response = self.client.images.edit(
                model="dall-e-2",
                image=("image.png", img_buffer.getvalue(), "image/png"),
                mask=("mask.png", mask_buffer.getvalue(), "image/png"),
                prompt=prompt,
                n=1,
                size="1024x1024"
            )
            
            # Get result
            image_url = response.data[0].url
            print(f"OpenAI returned image URL: {image_url[:50]}...")
            
            # Download
            import requests
            img_response = requests.get(image_url)
            result_image = img_response.content
            
            return {
                'success': True,
                'corrected_image': base64.b64encode(result_image).decode('utf-8'),
                'corrected_pdf': base64.b64encode(result_image).decode('utf-8'),
                'filename': 'exam_corrected.png',
                'image_filename': 'exam_corrected.png',
                'pages_processed': 1,
                'annotations_added': len(questions),
                'method': 'openai_dalle'
            }
            
        except Exception as e:
            print(f"OpenAI error: {e}")
            # Fallback to simple PIL drawing
            return self._fallback(exam_file, grading_results, str(e))
    
    def _fallback(self, exam_file: bytes, grading_results: Dict[str, Any], error: str) -> Dict[str, Any]:
        """PIL-based fallback if OpenAI fails."""
        from PIL import ImageDraw, ImageFont
        
        image = Image.open(io.BytesIO(exam_file))
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        draw = ImageDraw.Draw(image)
        width, height = image.size
        
        RED = (220, 35, 35)
        GREEN = (35, 160, 35)
        
        size = max(30, min(50, min(width, height) // 15))
        
        questions = grading_results.get('questions', [])
        total_earned = grading_results.get('total_earned', 0)
        
        # Total score
        try:
            font = ImageFont.truetype("arial.ttf", int(size * 1.2))
        except:
            font = ImageFont.load_default()
        
        score_text = str(int(total_earned) if total_earned == int(total_earned) else total_earned)
        draw.text((int(width * 0.75), int(height * 0.05)), score_text, fill=RED, font=font)
        
        # Question marks
        y_positions = [0.18, 0.42, 0.70]
        for i, q in enumerate(questions):
            if i >= len(y_positions):
                break
            
            earned = q.get('points_earned', 0)
            possible = q.get('points_possible', 1)
            is_correct = earned >= possible
            
            x = int(width * 0.58)
            y = int(height * y_positions[i])
            
            color = GREEN if is_correct else RED
            
            if is_correct:
                draw.line([(x, y + size * 0.4), (x + size * 0.35, y + size)], fill=color, width=4)
                draw.line([(x + size * 0.35, y + size), (x + size, y)], fill=color, width=4)
            else:
                draw.line([(x, y), (x + size, y + size)], fill=color, width=4)
                draw.line([(x + size, y), (x, y + size)], fill=color, width=4)
        
        output = io.BytesIO()
        image.save(output, format='PNG')
        output.seek(0)
        
        return {
            'success': True,
            'corrected_image': base64.b64encode(output.getvalue()).decode('utf-8'),
            'corrected_pdf': base64.b64encode(output.getvalue()).decode('utf-8'),
            'filename': 'exam_corrected.png',
            'pages_processed': 1,
            'annotations_added': len(questions),
            'method': 'pil_fallback',
            'fallback_reason': error
        }
