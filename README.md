# Gradeo API - Complete System Report

## Executive Summary

Gradeo is a production-ready API for automated exam grading. It combines:
- **OCR** - Extracts questions from scanned exam papers using Gemini AI
- **Grading** - Grades 13 different question types with AI and code-based scoring
- **Annotation** - Overlays teacher-style correction marks on scanned papers using OpenAI

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         GRADEO API                                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────┐    ┌─────────────────┐    ┌──────────────────┐    │
│  │   OCR       │    │    GRADING      │    │   ANNOTATION     │    │
│  │             │    │                 │    │                  │    │
│  │ • English   │    │ • 13 Types      │    │ • OpenAI DALL-E  │    │
│  │ • Arabic    │───▶│ • AI + Code     │───▶│ • Teacher Style  │    │
│  │ • French    │    │ • Multi-pass    │    │ • Green/Red Pen  │    │
│  │             │    │ • Feedback      │    │                  │    │
│  └─────────────┘    └─────────────────┘    └──────────────────┘    │
│                                                                     │
│                    Powered by: Gemini 2.0 Flash                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Part 1: OCR System

### Overview
Extracts structured question data from scanned exam papers (PDF or images).

### Supported Languages
- **English** - Full detailed prompts
- **Arabic** - Native Arabic prompts (أسئلة عربية)
- **French** - French language support

### 13 Question Types

| # | Type | Description | Key Fields |
|---|------|-------------|------------|
| 1 | `multiple_choice` | A, B, C, D options | `options`, `correct_answer` |
| 2 | `true_false` | True/False statements | `correct_answer` |
| 3 | `matching` | Two columns to connect | `left_column`, `right_column`, `correct_matches` |
| 4 | `fill_in_blank` | Sentences with blanks | `blanks` |
| 5 | `ordering` | Items to arrange | `ordering_items`, `correct_order` |
| 6 | **`short_answer`** | Brief factual answers | `expected_answer_count`, `acceptable_answers` |
| 7 | `open_ended` | Analytical written responses | `answer_length`, `expected_keywords`, `model_answer` |
| 8 | `compare_contrast` | Compare 2+ items | `compare_items`, `grading_table` |
| 9 | `definition` | Define a term | `term_to_define`, `model_answer` |
| 10 | `labeling` | Label diagram parts (write/draw on shape) | `labeling_items`, `diagram_description` |
| 11 | `labeling_image` | Label on image (handwriting OCR) | `labeling_items`, `diagram_description` |
| 12 | `math_equation` | Math problems (PEMDAS) | `math_content`, `correct_answer` |
| 13 | `table` | Table completion | `table_headers`, `grading_table` |

> **NEW: short_answer** - For brief factual questions like "State 4...", "What is...?", "Name..."
> **Updated: open_ended** - Now specifically for analytical questions requiring explanation
> **Updated: labeling** - Now specifically for diagram labeling where students write/draw on shapes

### How OCR Works

```python
# 1. Upload exam paper (PDF or image)
# 2. Select language (english/arabic/french)
# 3. Gemini AI extracts all questions with structured output

response = client.models.generate_content(
    model="gemini-2.0-flash",
    contents=[prompt, image],
    config={
        "response_mime_type": "application/json",
        "response_schema": OCRResponse  # Pydantic model
    }
)
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/ocr/english` | POST | OCR with English prompts |
| `/api/ocr/arabic` | POST | OCR with Arabic prompts |
| `/api/ocr/french` | POST | OCR with French prompts |

---

## Part 2: Grading System

### Grading Categories

**Category A: Direct Answer (Code-Based)**
- Multiple Choice, True/False, Matching, Fill-in-Blank, Ordering, Labeling

**Category B: AI-Graded with Multi-Pass**
- Open-Ended, Compare/Contrast, Definition, Table, Math Equations, Labeling-Image

---

### Category A: Code-Based Grading

#### Multiple Choice & True/False
```python
def grade_multiple_choice(questions, student_answers, points):
    for q in questions:
        correct = q['correct_answer']
        student = student_answers.get(q['question_number'])
        is_correct = normalize(student) == normalize(correct)
        # Award points if correct
```

#### Matching
```python
def grade_matching(question, student_matches):
    correct_matches = question['correct_matches']  # {"1": "a", "2": "b"}
    for left_id, expected_right in correct_matches.items():
        student_right = student_matches.get(left_id)
        if normalize(student_right) == normalize(expected_right):
            points_earned += points_per_pair
```

#### Fill-in-Blank
```python
def grade_fill_blank(question, student_blanks):
    correct_blanks = question['blanks']  # ["answer1", "answer2"]
    for i, correct in enumerate(correct_blanks):
        student = student_blanks[i] if i < len(student_blanks) else ""
        if answers_match(student, correct):
            points_earned += points_per_blank
```

#### Ordering
```python
def grade_ordering(question, student_order):
    correct_order = question['correct_order']  # ["C", "A", "B"]
    for i, correct_id in enumerate(correct_order):
        if i < len(student_order) and student_order[i] == correct_id:
            points_earned += points_per_position
```

#### Labeling (Text Input)
```python
def grade_labeling(question, student_labels):
    for item in question['labeling_items']:
        label_id = item['label_id']
        correct = item['correct_label']
        student = student_labels.get(label_id)
        if answers_match(student, correct):
            points_earned += points_per_label
```

---

### Category B: AI-Graded with Multi-Pass

#### Core Logic: 3-Pass Grading

All AI-graded questions use 3 passes for consistency:

```python
# Run grading 3 times
pass_results = []
for _ in range(3):
    result = call_gemini(grading_prompt)
    pass_results.append(result)

# For each criterion/item, take MODE (most common result)
for criterion in criteria:
    statuses = [pass[criterion]['status'] for pass in pass_results]
    final_status = get_mode(statuses)  # e.g., ["present", "present", "absent"] → "present"
    
    # If all 3 differ → FLAG for human review, use MEDIAN
    if len(set(statuses)) == 3:
        flag_for_review = True
        final_status = get_median(statuses)  # absent < partial < present
```

#### Open-Ended Questions

**Fixed Criteria (5):**
| Criterion | Weight | Description |
|-----------|--------|-------------|
| `relevance` | 25% | Answers the question asked |
| `completeness` | 25% | Covers all required points |
| `accuracy` | 20% | Factually correct |
| `key_terms` | 15% | Uses expected keywords |
| `clarity` | 15% | Well-organized, clear |

**Grading Prompt:**
```
For each criterion, evaluate:
- "strong": Fully demonstrated (100%)
- "adequate": Partially demonstrated (60%)
- "weak": Minimally shown (30%)
- "missing": Not present (0%)

Return JSON with status and reason for each criterion.
```

**Scoring (Code-Based):**
```python
STATUS_SCORES = {'strong': 1.0, 'adequate': 0.6, 'weak': 0.3, 'missing': 0.0}

for criterion, weight in CRITERIA.items():
    status = results[criterion]['status']
    earned += weight * STATUS_SCORES[status] * max_points
```

---

#### Compare/Contrast & Table Questions

**Checklist-Based Grading:**

Teacher provides expected points as a grading table:
```python
grading_table = [
    {"item": "Mitosis produces 2 identical cells", "points": 2.5},
    {"item": "Meiosis produces 4 different cells", "points": 2.5},
    {"item": "Mitosis is for growth", "points": 2.5}
]
```

**AI Grading Prompt:**
```
For each item in the checklist:
- "present": Student clearly stated this point
- "partial": Partially mentioned or implied
- "absent": Not mentioned

Return status and reason for each item.
```

**Scoring:**
```python
for item in grading_table:
    if status == 'present':
        earned += item['points']  # 100%
    elif status == 'partial':
        earned += item['points'] * 0.5  # 50%
    # absent = 0%
```

---

#### Definition Questions

**3 Meaning Units:**
| Unit | Weight | Description |
|------|--------|-------------|
| `core_concept` | 50% | Main/essential meaning |
| `required_properties` | 30% | Key characteristics |
| `scope_context` | 20% | Correct scope/application |

**AI evaluates each unit as present/partial/absent with reasoning.**

---

#### Math Equations (PEMDAS)

**Step 1: AI generates PEMDAS steps**
```python
prompt = f"""
Analyze: {problem}
Final answer: {correct_answer}

Break into PEMDAS steps:
1. Parentheses
2. Exponents
3. Multiplication/Division (left to right)
4. Addition/Subtraction (left to right)

Return steps as JSON.
"""
```

**Step 2: AI grades student work against steps (3 passes)**
```python
# For each expected step:
# - "present": Student showed this correctly
# - "partial": Attempted with error
# - "absent": Not shown

# AI recognizes equivalent approaches:
# "6 × 4 = 24" same as "4 × 6 = 24"
```

**Step 3: Code calculates final score**
```python
points_per_step = total_points / num_steps
for step in steps:
    if status == 'present': earned += points_per_step
    elif status == 'partial': earned += points_per_step * 0.5
```

**Output includes:**
```json
{
  "expected": "2 + 3 = 5",
  "expected_latex": "$2 + 3 = 5$",
  "status": "present",
  "reason": "Student correctly computed 2+3=5"
}
```

---

#### Labeling-Image (Handwriting OCR)

Uses Gemini Vision to read handwritten labels on diagrams:

```python
prompt = f"""
Look at this diagram image with student's handwritten labels.
For each label position, identify what the student wrote.

Expected labels:
{labeling_items}

Return JSON mapping label_id to student's handwritten text.
"""

result = client.models.generate_content(
    model="gemini-2.0-flash",
    contents=[prompt, student_image]
)
```

Then grades extracted text against correct labels.

---

### All Grading Endpoints

| Endpoint | Question Type | Method |
|----------|--------------|--------|
| `/api/grading/mcq` | Multiple Choice | Code |
| `/api/grading/true-false` | True/False | Code |
| `/api/grading/matching` | Matching | Code |
| `/api/grading/fill-in-blank` | Fill in Blank | Code |
| `/api/grading/ordering` | Ordering | Code |
| `/api/grading/labeling` | Labeling (diagram) | AI 3-pass |
| `/api/grading/short-answer` | **Short Answer (NEW)** | AI 3-pass |
| `/api/grading/labeling-image` | Labeling (image) | AI + Code |
| `/api/grading/open-ended` | Open-Ended (analytical) | AI 3-pass |
| `/api/grading/compare-contrast` | Compare/Contrast | AI 3-pass |
| `/api/grading/definition` | Definition | AI 3-pass |
| `/api/grading/table` | Table | AI 3-pass |
| `/api/grading/math-equations` | Math | AI 3-pass |

---

### Short Answer Grading (NEW)

**Purpose:** Grade brief factual answers (not analytical)

**Examples:** "State 4 characteristics of...", "What is the capital of...?", "Name 3 primary colors"

**Criteria (3):**
| Criterion | Weight | Description |
|-----------|--------|-------------|
| `factual_accuracy` | 60% | Is the answer factually correct? |
| `completeness` | 30% | Are all requested items present? |
| `terminology` | 10% | Uses correct terms? |

**Status Scores:**
- `present` = 100%
- `partial` = 50%
- `absent` = 0%

**Uses 3-pass grading with mode/median for consistency.**

---

### Labeling Grading (Updated)

**Purpose:** Grade diagram labeling questions using LLM semantic matching

**How it works:**
1. Send label pairs to Gemini AI (correct vs student answer)
2. AI returns `present/partial/absent` for each label
3. Run 3 times for consistency (3-pass)
4. Use mode/median for final status

**Benefits:**
- Accepts synonyms ("LA" = "Left Atrium")
- Handles minor spelling errors
- Semantic understanding (not exact string match)

---

## Part 3: Annotation System

### Overview
Takes graded exams and overlays teacher-style correction marks using OpenAI DALL-E image generation.

### How It Works (Updated)

```
1. INPUT: Scanned exam (image) + grading results

2. AI IMAGE GENERATION (OpenAI DALL-E):
   - Simple teacher-style prompt
   - Green ✓ for correct answers
   - Red ✗ for wrong answers
   - Write score in score box
   - Natural teacher handwriting style

3. FALLBACK (PIL):
   - If OpenAI fails, uses local PIL drawing
   - Handwritten-style marks with random offsets

4. OUTPUT: Annotated image with teacher corrections
```

### Simple AI Prompt

```python
prompt = f"""You are a teacher grading this exam with a red and green pen.

Q1: CORRECT (1/1)
Q2: WRONG (0/1)
...
Total: 2/3

Mark it like a real teacher would:
- Green ✓ for correct answers
- Red ✗ for wrong answers
- Write the score in the score box

Use natural teacher handwriting style."""
```

### OpenAI Integration

```python
import openai

client = openai.OpenAI(api_key=OPENAI_API_KEY)

response = client.images.edit(
    model="dall-e-2",
    image=exam_image_bytes,
    mask=mask_bytes,  # Full image mask
    prompt=prompt,
    n=1,
    size="1024x1024"
)

annotated_url = response.data[0].url
```

### Annotation Endpoint

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/annotation/generate` | POST | Generate teacher-annotated image |

---

## Technical Stack

| Component | Technology |
|-----------|------------|
| Framework | Flask + Flask-RESTx |
| OCR & Grading AI | Google Gemini 2.0 Flash |
| Annotation AI | OpenAI DALL-E 2 |
| PDF Processing | PyMuPDF (fitz) |
| Image Processing | Pillow |
| Validation | Pydantic |
| Documentation | Swagger/OpenAPI |

---

## Key Design Decisions

1. **Multi-Pass Grading**: 3 AI passes with mode/median for consistency
2. **Code-Based Scoring**: AI assesses quality, code calculates points
3. **Feedback per Item**: Each criterion/step includes AI reasoning
4. **High Variance Flagging**: Flags inconsistent grades for human review
5. **Template-Free Annotation**: AI Vision detects positions dynamically
6. **Dual Format Output**: Plain text + LaTeX for math expressions

---

## Files Structure

```
app/
├── __init__.py              # Flask app factory
├── config.py                # Configuration
├── models/
│   └── schemas.py           # Pydantic models (12 types)
├── routes/
│   ├── ocr.py               # /api/ocr endpoints
│   ├── grading.py           # /api/grading endpoints (12)
│   └── annotation.py        # /api/annotation endpoint
└── services/
    ├── gemini_ocr.py        # OCR with 3 language prompts
    ├── grading.py           # Code-based grading
    ├── short_answer_grading.py  # NEW: Short answer grading
    ├── labeling_grading.py  # Diagram labeling with LLM
    ├── open_ended_grading.py
    ├── compare_contrast_grading.py
    ├── definition_grading.py
    ├── math_grading.py
    ├── table_grading.py
    ├── labeling_image_grading.py
    └── annotation_service.py
```

---

## Summary

Gradeo API provides end-to-end automated exam processing:

1. **OCR**: Extract questions from any exam format (3 languages, 13 types)
2. **Grade**: AI + code hybrid grading with 3-pass consistency and feedback
3. **Annotate**: Teacher-style correction marks using OpenAI image generation

All components are production-ready with Swagger documentation.
