# Annotation customization routes with GUI
from flask import Blueprint, render_template_string, request, jsonify
from app.services.annotation_service import AnnotationService
import base64
import io

customize_bp = Blueprint('customize', __name__)
annotation_service = AnnotationService()

# Customization GUI HTML
CUSTOMIZE_HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Annotation Customizer</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #1a1a2e; color: #eee; min-height: 100vh; }
        .header { background: linear-gradient(135deg, #0a0a1a, #1a1a3a); padding: 20px; text-align: center; border-bottom: 1px solid #333; }
        .header h1 { font-size: 24px; background: linear-gradient(90deg, #4facfe, #00f2fe); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .container { display: flex; height: calc(100vh - 80px); }
        .sidebar { width: 320px; background: #16213e; padding: 20px; overflow-y: auto; border-right: 1px solid #333; }
        .preview { flex: 1; padding: 20px; display: flex; flex-direction: column; align-items: center; }
        .preview-canvas { position: relative; max-width: 100%; max-height: 80vh; border: 2px solid #333; border-radius: 8px; overflow: hidden; }
        .preview-canvas img { max-width: 100%; max-height: 100%; }
            .draggable {
                position: absolute;
                cursor: move;
                user-select: none;
                z-index: 1000;
                display: flex;
                align-items: center;
                gap: 8px;
                background-color: transparent;
                padding: 4px;
                border-radius: 4px; /* Sharper edges - modern sleek look */
                font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
                font-weight: 600;
                transition: transform 0.1s ease, box-shadow 0.1s ease;
            }
            
            .draggable:hover {
                transform: scale(1.02);
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            }
        /* Icon circle (checkmark, X, dash) */
        .draggable .icon-circle {
            width: 36px;
            height: 36px;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.95);
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.25);
            font-size: 24px;
        }
        /* Score box */
        .draggable .score-box {
            padding: 4px 10px;
            border-radius: 8px;
            background: rgba(255, 255, 255, 0.95);
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
            font-size: 18px;
        }
        /* Feedback box - dark blue background like PIL */
            .draggable.feedback-label {
                background: #143c8c;
                color: white;
                padding: 6px 14px;
                border-radius: 4px; /* Sharper edges */
                box-shadow: 0 2px 8px rgba(20, 60, 140, 0.3);
                border: 1px solid rgba(255, 255, 255, 0.1);
            }
            
            .draggable.correct-label {
                background: #e6f2ff;
                color: #143c8c;
                padding: 6px 14px;
                border-radius: 4px; /* Sharper edges */
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
                border: 1px solid #d0e8ff;
            }
            
            .draggable.text-label {
                background: rgba(255, 255, 255, 0.95);
                padding: 6px 14px;
                border-radius: 4px; /* Sharper edges */
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
                border: 1px solid #ddd;
            }
            
            .draggable .score-box {
                background: white;
                padding: 4px 10px;
                border-radius: 4px; /* Sharper edges */
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
                font-family: 'Segoe UI', sans-serif;
                font-weight: 700;
                border: 1px solid #eee;
            }
        .control-group label { display: block; margin-bottom: 8px; color: #aaa; font-size: 12px; text-transform: uppercase; }
        .control-group input, .control-group select { width: 100%; padding: 10px; border: 1px solid #333; border-radius: 6px; background: #0a0a1a; color: #eee; font-size: 14px; }
        .color-picker { display: flex; gap: 10px; align-items: center; }
        .color-picker input[type="color"] { width: 50px; height: 40px; border: none; border-radius: 6px; cursor: pointer; }
        .btn { padding: 12px 24px; border: none; border-radius: 8px; cursor: pointer; font-size: 14px; font-weight: 600; transition: all 0.2s; }
        .btn-primary { background: linear-gradient(135deg, #4facfe, #00f2fe); color: #000; }
        .btn-primary:hover { transform: translateY(-2px); box-shadow: 0 4px 15px rgba(79, 172, 254, 0.3); }
        .btn-secondary { background: #2a2a4a; color: #eee; }
        .slider-container { margin: 10px 0; }
        .slider-container input[type="range"] { width: 100%; }
        .annotation-list { margin-top: 20px; }
        .annotation-item { background: #0a0a1a; padding: 15px; border-radius: 8px; margin-bottom: 10px; }
        .annotation-item h4 { margin-bottom: 10px; color: #4facfe; }
        .upload-zone { border: 2px dashed #333; border-radius: 12px; padding: 40px; text-align: center; cursor: pointer; transition: all 0.2s; margin-bottom: 20px; }
        .upload-zone:hover { border-color: #4facfe; background: rgba(79, 172, 254, 0.05); }
        .actions { display: flex; gap: 10px; margin-top: 20px; }
        .position-display { font-size: 11px; color: #888; margin-top: 5px; }
        
        /* Resizing handles */
        .resizer {
            width: 10px;
            height: 10px;
            background: #4facfe;
            position: absolute;
            right: -5px;
            bottom: -5px;
            cursor: nwse-resize;
            border-radius: 50%;
            display: none;
            z-index: 100;
        }
        .draggable:hover .resizer { display: block; }
        
        /* Action buttons on annotations */
        .ann-actions {
            position: absolute;
            top: -25px;
            left: 0;
            display: none;
            background: rgba(0,0,0,0.8);
            border-radius: 4px;
            padding: 2px 5px;
            gap: 5px;
            z-index: 101;
        }
        .draggable:hover .ann-actions { display: flex; }
        .ann-btn {
            cursor: pointer;
            font-size: 12px;
            padding: 2px 4px;
            border-radius: 3px;
        }
        .ann-btn.approve { color: #22c55e; }
        .ann-btn.remove { color: #ef4444; }
        
        /* Status badge */
        .status-badge {
            position: absolute;
            top: -15px;
            right: -10px;
            font-size: 10px;
            padding: 1px 4px;
            border-radius: 4px;
            font-weight: bold;
            text-transform: uppercase;
        }
        .status-pending { background: #f59e0b; color: #000; }
        .status-approved { background: #22c55e; color: #000; }
        
        /* Active/Pending styles */
        .draggable.pending { border: 1px dashed #f59e0b; }
        .draggable.approved { border: 1px solid #22c55e; }
    </style>
</head>
<body>
    <div id="loadingIndicator" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.7); z-index:9999; display:flex; flex-direction:column; align-items:center; justify-content:center;">
        <div style="width:50px; height:50px; border:5px solid #333; border-top:5px solid #4facfe; border-radius:50%; animation:spin 1s linear infinite;"></div>
        <p style="margin-top:20px; font-weight:bold; color:white;">Processing Annotations...</p>
    </div>
    <style>@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }</style>
    <div class="header">
        <h1>📝 Annotation Customizer</h1>
        <p style="color: #888; margin-top: 5px;">Drag annotations, customize colors, fonts, and labels</p>
    </div>
    
    <div class="container">
        <div class="sidebar">
            <div class="control-group">
                <label>📎 Step 1: Upload ORIGINAL Image (clean, no annotations)</label>
                <div class="upload-zone" style="padding: 20px;" onclick="document.getElementById('originalUpload').click()">
                    <input type="file" id="originalUpload" accept="image/*" style="display: none;" onchange="loadOriginalImage(event)">
                    <p id="originalStatus">Click to upload original exam</p>
                </div>
            </div>
            
            <div class="control-group">
                <label>📎 Step 2: Upload ANNOTATED Image (with labels)</label>
                <div class="upload-zone" style="padding: 20px;" onclick="document.getElementById('annotatedUpload').click()">
                    <input type="file" id="annotatedUpload" accept="image/*" style="display: none;" onchange="loadAnnotatedImage(event)">
                    <p id="annotatedStatus">Click to upload annotated exam</p>
                </div>
            </div>

            <div class="control-group">
                <label>📎 Step 3: JSON Request Data (Optional Preview)</label>
                <textarea id="jsonInput" style="width: 100%; height: 100px; background: #0a0a1a; color: #eee; border: 1px solid #333; border-radius: 6px; padding: 10px; font-family: monospace; font-size: 11px;" placeholder='{"questions": [...]}'></textarea>
                <div style="display: flex; gap: 5px; margin-top: 10px;">
                    <button class="btn btn-secondary" style="flex: 1; font-size: 11px;" onclick="loadSampleJSON()">Load Sample</button>
                    <button class="btn btn-secondary" style="flex: 1; font-size: 11px;" onclick="previewFromJSON()">Preview Metadata</button>
                </div>
            </div>
            
            <button class="btn btn-primary" id="detectBtn" style="width: 100%; margin: 10px 0;" onclick="detectAndDisplay()" disabled>
                🔍 Detect Labels & Review
            </button>
            
            <div class="actions" style="margin-bottom: 20px;">
                <button class="btn btn-secondary" style="flex: 1; font-size: 12px;" onclick="approveAll()">✅ Approve All</button>
                <button class="btn btn-secondary" style="flex: 1; font-size: 12px;" onclick="annotations = []; renderAnnotations()">🗑️ Clear All</button>
            </div>
            
            <div class="control-group">
                <label>Check Mark Color (Correct)</label>
                <div class="color-picker">
                    <input type="color" id="checkColor" value="#19aa19">
                    <input type="text" id="checkColorText" value="#19aa19" onchange="syncColor('checkColor', this.value)">
                </div>
            </div>
            
            <div class="control-group">
                <label>X Mark Color (Incorrect)</label>
                <div class="color-picker">
                    <input type="color" id="xColor" value="#be1e1e">
                    <input type="text" id="xColorText" value="#be1e1e" onchange="syncColor('xColor', this.value)">
                </div>
            </div>
            
            <div class="control-group">
                <label>Partial Credit Color</label>
                <div class="color-picker">
                    <input type="color" id="partialColor" value="#c89600">
                    <input type="text" id="partialColorText" value="#c89600" onchange="syncColor('partialColor', this.value)">
                </div>
            </div>
            
            <div class="control-group">
                <label>Font Family</label>
                <select id="fontFamily">
                    <option value="Segoe Script">Segoe Script (Handwritten)</option>
                    <option value="Calibri">Calibri (Clean)</option>
                    <option value="Arial">Arial (Simple)</option>
                    <option value="Comic Sans MS">Comic Sans MS</option>
                    <option value="Georgia">Georgia (Serif)</option>
                </select>
            </div>
            
            <div class="control-group">
                <label>Mark Size</label>
                <div class="slider-container">
                    <input type="range" id="markSize" min="15" max="60" value="32" oninput="updateSliderValue('markSize')">
                    <span id="markSizeValue">32px</span>
                </div>
            </div>
            
            <div class="control-group">
                <label>Font Size</label>
                <div class="slider-container">
                    <input type="range" id="fontSize" min="12" max="48" value="24" oninput="updateSliderValue('fontSize')">
                    <span id="fontSizeValue">24px</span>
                </div>
            </div>
            
            <div class="control-group">
                <label>Background Opacity</label>
                <div class="slider-container">
                    <input type="range" id="bgOpacity" min="0" max="255" value="160" oninput="updateSliderValue('bgOpacity')">
                    <span id="bgOpacityValue">160</span>
                </div>
            </div>
            
            <div class="control-group">
                <label>Add Custom Label</label>
                <input type="text" id="customLabel" placeholder="Enter label text...">
                <button class="btn btn-secondary" style="width: 100%; margin-top: 10px;" onclick="addLabel()">+ Add Label</button>
            </div>
            
            <div class="control-group">
                <label>Quick Add</label>
                <div style="display: flex; gap: 5px; flex-wrap: wrap;">
                    <button class="btn btn-secondary" style="padding: 8px 12px; font-size: 12px;" onclick="addQuickAnnotation('check')">✓ Check</button>
                    <button class="btn btn-secondary" style="padding: 8px 12px; font-size: 12px;" onclick="addQuickAnnotation('x')">✗ X Mark</button>
                    <button class="btn btn-secondary" style="padding: 8px 12px; font-size: 12px;" onclick="addQuickAnnotation('partial')">— Partial</button>
                    <button class="btn btn-secondary" style="padding: 8px 12px; font-size: 12px; background: linear-gradient(135deg, #f59e0b, #f97316);" onclick="addFinalScore()">🏆 Final Score</button>
                </div>
            </div>
            
            <div class="annotation-list" id="annotationList">
                <h4>Annotations <span style="font-size: 11px; color: #666;">(Click text to edit)</span></h4>
                <p style="color: #666; font-size: 12px;">Drag items in preview to reposition</p>
            </div>
            
            <div class="actions">
                <button class="btn btn-primary" onclick="applyAndDownload()">💾 Apply & Download</button>
                <button class="btn btn-secondary" onclick="resetPositions()">🔄 Reset</button>
            </div>
            
            <div class="control-group" style="margin-top: 15px;">
                <label>Image Options</label>
                <button class="btn btn-secondary" style="width: 100%; margin-bottom: 8px;" onclick="clearAllAnnotations()">🗑️ Clear All Annotations</button>
                <button class="btn btn-secondary" style="width: 100%; background: linear-gradient(135deg, #6366f1, #8b5cf6);" onclick="useOriginalImage()">📷 Use Original Image</button>
            </div>
        </div>
        
        <div class="preview">
            <div class="preview-canvas" id="previewCanvas">
                <img id="previewImage" src="" alt="Upload an image to preview">
                <div id="annotationsContainer"></div>
            </div>
            <p class="position-display" id="positionDisplay">Position: (0, 0)</p>
        </div>
    </div>
    
    <script>
        let annotations = [];
        let imageData = null;
        let originalImageData = null;
        let annotatedImageData = null;
        let draggedElement = null;
        let offsetX, offsetY;
        
        function loadOriginalImage(event) {
            const file = event.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    originalImageData = e.target.result;
                    document.getElementById('originalStatus').textContent = '✅ ' + file.name;
                    document.getElementById('originalStatus').style.color = '#4ade80';
                    checkBothUploaded();
                };
                reader.readAsDataURL(file);
            }
        }
        
        function loadAnnotatedImage(event) {
            const file = event.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    annotatedImageData = e.target.result;
                    document.getElementById('annotatedStatus').textContent = '✅ ' + file.name;
                    document.getElementById('annotatedStatus').style.color = '#4ade80';
                    checkBothUploaded();
                };
                reader.readAsDataURL(file);
            }
        }
        
        function checkBothUploaded() {
            const detectBtn = document.getElementById('detectBtn');
            if (originalImageData && annotatedImageData) {
                detectBtn.disabled = false;
                detectBtn.style.opacity = '1';
            }
        }
        
        async function detectAndDisplay() {
            const loader = document.getElementById('loadingIndicator');
            loader.style.display = 'flex';
            
            try {
                // Show original clean image
                imageData = originalImageData;
                document.getElementById('previewImage').src = originalImageData;
                
                // Get image dimensions for scaling
                const img = document.getElementById('previewImage');
                await new Promise(resolve => {
                    const timeout = setTimeout(resolve, 3000);
                    if (img.complete) {
                        clearTimeout(timeout);
                        resolve();
                    } else {
                        img.onload = () => { clearTimeout(timeout); resolve(); };
                        img.onerror = () => { clearTimeout(timeout); resolve(); };
                    }
                });
                
                const imgWidth = img.naturalWidth || 1000;
                const imgHeight = img.naturalHeight || 1400;
                window.detectedImageWidth = imgWidth;
                window.detectedImageHeight = imgHeight;
                
                // Detect labels from annotated image
                const response = await fetch('/api/annotation/detect-existing', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ image: annotatedImageData })
                });
                
                if (response.ok) {
                    const result = await response.json();
                    if (result.annotations && result.annotations.length > 0) {
                        // Merge annotations by question_number (combine mark + score into single entry)
                        const mergedMap = new Map();
                        
                        result.annotations.forEach((ann, i) => {
                            const qNum = ann.question_number;
                            const annType = ann.type || 'label';
                            
                            // For mark types, don't merge - they should already be combined
                            if (annType === 'check' || annType === 'x' || annType === 'partial' || annType === 'mark') {
                                const key = qNum ? `q${qNum}_mark` : `ann_${Date.now()}_${i}`;
                                // Ensure text has both icon and score
                                let text = ann.text || '';
                                if (!text.match(/\d+\/\d+/) && qNum) {
                                    // No score pattern found, it might be separate - we'll merge later
                                }
                                mergedMap.set(key, {
                                    id: key,
                                    type: annType,
                                    text: text,
                                    x: ann.x || 50,
                                    y: ann.y || 50,
                                    color: ann.color || '#19aa19',
                                    question_number: qNum,
                                    detected: true
                                });
                            } else if (annType === 'score' && qNum) {
                                // Merge score into existing mark if found
                                const markKey = `q${qNum}_mark`;
                                if (mergedMap.has(markKey)) {
                                    const existing = mergedMap.get(markKey);
                                    // Append score to text if not already present
                                    if (!existing.text.match(/\d+\/\d+/)) {
                                        existing.text = existing.text.trim() + ' ' + (ann.text || '').trim();
                                    }
                                } else {
                                    // No mark found yet, create as mark with score
                                    mergedMap.set(markKey, {
                                        id: markKey,
                                        type: 'check', // Default, may be updated
                                        text: ann.text || '',
                                        x: ann.x || 50,
                                        y: ann.y || 50,
                                        color: ann.color || '#19aa19',
                                        question_number: qNum,
                                        detected: true
                                    });
                                }
                            } else {
                                // Keep other types (correct_answer, feedback, final_score, label) as-is
                                const key = ann.id || `${annType}_${qNum || i}_${Date.now()}`;
                                mergedMap.set(key, {
                                    id: key,
                                    type: annType,
                                    text: ann.text || '',
                                    x: ann.x || 50,
                                    y: ann.y || 50,
                                    color: ann.color || '#143c8c',
                                    question_number: qNum,
                                    detected: true
                                });
                            }
                        });
                        
                        annotations = Array.from(mergedMap.values());
                        console.log('Processed ' + annotations.length + ' annotations (merged by question)');
                    } else {
                        alert('No annotations detected. Add manually.');
                        annotations = [];
                    }
                }
            } catch (err) {
                console.error('Detection failed:', err);
                alert('Detection failed: ' + err.message);
                annotations = [];
            } finally {
                loader.style.display = 'none';
                renderAnnotations();
            }
        }
        
        function addSampleAnnotations() {
            annotations = [
                { id: 1, type: 'check', text: '✓ 2/2', x: 100, y: 100, color: '#19aa19' },
                { id: 2, type: 'x', text: '✗ 0/2', x: 100, y: 200, color: '#be1e1e' },
                { id: 3, type: 'label', text: 'Correct: B', x: 120, y: 230, color: '#143c8c' }
            ];
            renderAnnotations();
        }
        
        function renderAnnotations() {
            const container = document.getElementById('annotationsContainer');
            container.innerHTML = '';
            
            // Calculate scale factor based on image dimensions (matching PIL logic)
            const img = document.getElementById('previewImage');
            const imgWidth = img.naturalWidth || window.detectedImageWidth || 1000;
            const imgHeight = img.naturalHeight || window.detectedImageHeight || 1400;
            const displayWidth = img.clientWidth || img.width || 800;
            const displayHeight = img.clientHeight || img.height || 600;
            
            // Scale factor for converting between natural image coords and display coords
            const displayScaleX = displayWidth / imgWidth;
            const displayScaleY = displayHeight / imgHeight;
            
            // Size scale factor matching PIL: (width * height) ** 0.5 / 1000
            const sizeScale = Math.sqrt(imgWidth * imgHeight) / 1000;
            
            // Scaled sizes matching annotation_service.py
            const iconSize = Math.max(30, Math.min(56, Math.round(36 * sizeScale)));  // Circle diameter
            const iconFontSize = Math.max(20, Math.min(40, Math.round(24 * sizeScale)));  // Icon symbol
            const scoreFontSize = Math.max(16, Math.min(32, Math.round(18 * sizeScale)));  // Score text
            
            annotations.forEach(ann => {
                const div = document.createElement('div');
                div.className = `draggable ${ann.status || 'pending'}`;
                div.id = 'ann-' + ann.id;
                
                // Scale position from image coordinates to display coordinates
                const scaledX = ann.x * displayScaleX;
                const scaledY = ann.y * displayScaleY;
                div.style.left = scaledX + 'px';
                div.style.top = scaledY + 'px';
                
                // Set size if stored
                if (ann.width) div.style.width = (ann.width * displayScaleX) + 'px';
                if (ann.height) div.style.height = (ann.height * displayScaleY) + 'px';
                
                // Store original image coordinates for download
                div.dataset.imgX = ann.x;
                div.dataset.imgY = ann.y;
                
                // Add Status Badge
                const badge = document.createElement('span');
                badge.className = `status-badge status-${ann.status || 'pending'}`;
                badge.textContent = ann.status || 'pending';
                div.appendChild(badge);
                
                // Add Action Buttons
                const actions = document.createElement('div');
                actions.className = 'ann-actions';
                actions.innerHTML = `
                    <span class="ann-btn approve" onclick="approveAnn('${ann.id}')" title="Approve">✓</span>
                    <span class="ann-btn remove" onclick="removeAnn('${ann.id}')" title="Remove">✕</span>
                `;
                div.appendChild(actions);
                
                // Add Resize Handle
                const resizer = document.createElement('div');
                resizer.className = 'resizer';
                div.appendChild(resizer);
                
                // Check if this is a mark+score annotation (check, x, partial)
                if (ann.type === 'mark' || ann.type === 'check' || ann.type === 'x' || ann.type === 'partial') {
                    // Create icon circle with scaled size
                    const circle = document.createElement('span');
                    circle.className = 'icon-circle';
                    
                    // Fixed size for icons unless explicitly resized
                    const curIconSize = (ann.width ? ann.width * displayScaleX : iconSize);
                    circle.style.width = curIconSize + 'px';
                    circle.style.height = curIconSize + 'px';
                    circle.style.fontSize = (iconFontSize * (curIconSize/iconSize)) + 'px';
                    
                    if (ann.type === 'check' || (ann.text && ann.text.includes('✓'))) {
                        circle.innerHTML = '✓';
                        circle.style.color = '#19aa19';
                    } else if (ann.type === 'x' || (ann.text && ann.text.includes('✗'))) {
                        circle.innerHTML = '✗';
                        circle.style.color = '#be1e1e';
                    } else {
                        circle.innerHTML = '—';
                        circle.style.color = '#c89600';
                    }
                    div.appendChild(circle);
                    
                    // Create score box with scaled size
                    const scoreBox = document.createElement('span');
                    scoreBox.className = 'score-box';
                    scoreBox.style.fontSize = scoreFontSize + 'px';
                    scoreBox.style.padding = Math.round(4 * sizeScale) + 'px ' + Math.round(8 * sizeScale) + 'px';
                    
                    const scoreMatch = ann.text.match(/(\\d+\\/\\d+)/);
                    scoreBox.textContent = scoreMatch ? scoreMatch[1] : ann.text.replace(/[✓✗—]/g, '').trim();
                    scoreBox.style.color = ann.color;
                    div.appendChild(scoreBox);
                    
                } else if (ann.type === 'feedback') {
                    div.classList.add('feedback-label');
                    div.style.fontSize = scoreFontSize + 'px';
                    div.textContent = ann.text;
                } else if (ann.type === 'correct_answer' || (ann.text && ann.text.toLowerCase().includes('correct'))) {
                    div.classList.add('correct-label');
                    div.style.fontSize = scoreFontSize + 'px';
                    div.textContent = ann.text;
                } else {
                    div.classList.add('text-label');
                    div.style.fontSize = scoreFontSize + 'px';
                    div.textContent = ann.text;
                    div.style.color = ann.color;
                }
                
                div.addEventListener('mousedown', startDrag);
                div.addEventListener('touchstart', startDragTouch, {passive: false});
                container.appendChild(div);
            });
            
            updateAnnotationList();
        }
        
        function startDrag(e) {
            if (e.target.classList.contains('resizer')) {
                startResize(e);
                return;
            }
            if (e.target.classList.contains('ann-btn')) return;
            
            draggedElement = e.target.closest('.draggable');
            if (!draggedElement) return;
            
            const rect = draggedElement.getBoundingClientRect();
            offsetX = e.clientX - rect.left;
            offsetY = e.clientY - rect.top;
            document.addEventListener('mousemove', drag);
            document.addEventListener('mouseup', stopDrag);
        }
        
        function startDragTouch(e) {
            if (e.target.classList.contains('resizer') || e.target.classList.contains('ann-btn')) return;
            
            e.preventDefault();
            draggedElement = e.target.closest('.draggable');
            if (!draggedElement) return;
            
            const rect = draggedElement.getBoundingClientRect();
            const touch = e.touches[0];
            offsetX = touch.clientX - rect.left;
            offsetY = touch.clientY - rect.top;
            document.addEventListener('touchmove', dragTouch, {passive: false});
            document.addEventListener('touchend', stopDrag);
        }
        
        let isResizing = false;
        let resizeStartWidth, resizeStartHeight, resizeStartX, resizeStartY;
        
        function startResize(e) {
            e.preventDefault();
            e.stopPropagation();
            isResizing = true;
            draggedElement = e.target.closest('.draggable');
            resizeStartWidth = parseFloat(getComputedStyle(draggedElement).width);
            resizeStartHeight = parseFloat(getComputedStyle(draggedElement).height);
            resizeStartX = e.clientX;
            resizeStartY = e.clientY;
            document.addEventListener('mousemove', resizing);
            document.addEventListener('mouseup', stopResize);
        }
        
        function resizing(e) {
            if (!isResizing || !draggedElement) return;
            const newWidth = resizeStartWidth + (e.clientX - resizeStartX);
            const newHeight = resizeStartHeight + (e.clientY - resizeStartY);
            
            if (newWidth > 20) draggedElement.style.width = newWidth + 'px';
            if (newHeight > 20) draggedElement.style.height = newHeight + 'px';
            
            // Sync with annotation data
            const img = document.getElementById('previewImage');
            const imgWidth = img.naturalWidth || window.detectedImageWidth || 1000;
            const displayWidth = img.clientWidth || 800;
            const sizeScale = imgWidth / displayWidth;
            
            const id = draggedElement.id.replace('ann-', '');
            const ann = annotations.find(a => String(a.id) === id);
            if (ann) {
                ann.width = newWidth * sizeScale;
                ann.height = newHeight * sizeScale;
            }
        }
        
        function stopResize() {
            isResizing = false;
            document.removeEventListener('mousemove', resizing);
            document.removeEventListener('mouseup', stopResize);
        }
        
        function approveAnn(id) {
            const ann = annotations.find(a => String(a.id) === String(id));
            if (ann) {
                ann.status = 'approved';
                renderAnnotations();
            }
        }
        
        function removeAnn(id) {
            annotations = annotations.filter(a => String(a.id) !== String(id));
            renderAnnotations();
        }
        
        function approveAll() {
            annotations.forEach(a => a.status = 'approved');
            renderAnnotations();
        }

        function drag(e) {
            if (!draggedElement || isResizing) return;
            const canvas = document.getElementById('previewCanvas');
            const rect = canvas.getBoundingClientRect();
            const x = e.clientX - rect.left - offsetX;
            const y = e.clientY - rect.top - offsetY;
            
            draggedElement.style.left = x + 'px';
            draggedElement.style.top = y + 'px';
            
            syncCoordinates(draggedElement, x, y);
        }
        
        function dragTouch(e) {
            e.preventDefault();
            if (!draggedElement || isResizing) return;
            const touch = e.touches[0];
            const canvas = document.getElementById('previewCanvas');
            const rect = canvas.getBoundingClientRect();
            const x = touch.clientX - rect.left - offsetX;
            const y = touch.clientY - rect.top - offsetY;
            
            draggedElement.style.left = x + 'px';
            draggedElement.style.top = y + 'px';
            
            syncCoordinates(draggedElement, x, y);
        }
        
        function syncCoordinates(el, x, y) {
            const img = document.getElementById('previewImage');
            const imgWidth = img.naturalWidth || window.detectedImageWidth || 1000;
            const imgHeight = img.naturalHeight || window.detectedImageHeight || 1400;
            const displayWidth = img.clientWidth || 800;
            const displayHeight = img.clientHeight || 600;
            
            const imgX = (x / displayWidth) * imgWidth;
            const imgY = (y / displayHeight) * imgHeight;
            
            document.getElementById('positionDisplay').textContent = `Position: (${Math.round(imgX)}, ${Math.round(imgY)})`;
            
            const id = el.id.replace('ann-', '');
            const ann = annotations.find(a => String(a.id) === id);
            if (ann) { ann.x = imgX; ann.y = imgY; }
        }

        function stopDrag() {
            if (isResizing) {
                stopResize();
                return;
            }
            draggedElement = null;
            document.removeEventListener('mousemove', drag);
            document.removeEventListener('mouseup', stopDrag);
            document.removeEventListener('touchmove', dragTouch);
            document.removeEventListener('touchend', stopDrag);
            updateAnnotationList();
        }
        
        function updateAnnotationList() {
            const list = document.getElementById('annotationList');
            list.innerHTML = '<h4>Annotations <span style="font-size: 11px; color: #666;">(Click to edit)</span></h4>';
            annotations.forEach(ann => {
                const item = document.createElement('div');
                item.className = 'annotation-item';
                const detectedBadge = ann.detected ? '<span style="background: #8b5cf6; color: white; padding: 2px 6px; border-radius: 4px; font-size: 10px; margin-left: 5px;">Detected</span>' : '';
                const qLabel = ann.question_number ? ` Q${ann.question_number}` : '';
                item.innerHTML = `
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <input type="text" value="${ann.text}" style="background: #1a1a3a; border: 1px solid #333; padding: 5px 8px; border-radius: 4px; color: #fff; flex: 1; margin-right: 10px;" onchange="updateAnnotationText('${ann.id}', this.value)">
                        <input type="color" value="${ann.color}" style="width: 35px; height: 30px; border: none; border-radius: 4px; cursor: pointer;" onchange="updateAnnotationColor('${ann.id}', this.value)">
                    </div>
                    <p style="font-size: 11px; color: #666; margin-top: 8px;">${ann.type}${qLabel} | (${Math.round(ann.x)}, ${Math.round(ann.y)}) ${detectedBadge}</p>
                    <button class="btn btn-secondary" style="padding: 4px 10px; margin-top: 5px; font-size: 11px;" onclick="removeAnnotation('${ann.id}')">🗑️ Remove</button>
                `;
                list.appendChild(item);
            });
        }
        
        function updateAnnotationText(id, newText) {
            const ann = annotations.find(a => a.id === id);
            if (ann) {
                ann.text = newText;
                renderAnnotations();
            }
        }
        
        function updateAnnotationColor(id, newColor) {
            const ann = annotations.find(a => a.id === id);
            if (ann) {
                ann.color = newColor;
                renderAnnotations();
            }
        }
        
        function addLabel() {
            const text = document.getElementById('customLabel').value.trim();
            if (text) {
                const id = Date.now();
                annotations.push({
                    id: id,
                    type: 'label',
                    text: text,
                    x: 50,
                    y: 50 + annotations.length * 30,
                    color: '#143c8c'
                });
                renderAnnotations();
                document.getElementById('customLabel').value = '';
            }
        }
        
        function addQuickAnnotation(type) {
            const id = Date.now();
            const colors = {
                'check': document.getElementById('checkColor').value,
                'x': document.getElementById('xColor').value,
                'partial': document.getElementById('partialColor').value
            };
            const texts = {
                'check': '✓ 1/1',
                'x': '✗ 0/1',
                'partial': '— 0.5/1'
            };
            annotations.push({
                id: id,
                type: type,
                text: texts[type],
                x: 50 + Math.random() * 100,
                y: 50 + annotations.length * 30,
                color: colors[type]
            });
            renderAnnotations();
        }
        
        function addFinalScore() {
            const id = Date.now();
            annotations.push({
                id: id,
                type: 'final_score',
                text: '🏆 Total: 8/10',
                x: 50,
                y: 30,
                color: '#f59e0b'
            });
            renderAnnotations();
        }
        
        function removeAnnotation(id) {
            annotations = annotations.filter(a => a.id !== id);
            renderAnnotations();
        }
        
        function clearAllAnnotations() {
            if (confirm('Remove all annotations?')) {
                annotations = [];
                renderAnnotations();
            }
        }
        
        function useOriginalImage() {
            // Check if we have stored original image
            if (window.originalImageData) {
                document.getElementById('previewImage').src = window.originalImageData;
                imageData = window.originalImageData;
                annotations = [];
                renderAnnotations();
                alert('Loaded original image without annotations. You can now add new annotations.');
            } else {
                alert('No original image stored. Upload an image first - if it was generated by Gradeo, the original will be extracted.');
            }
        }
        
        function syncColor(inputId, value) {
            document.getElementById(inputId).value = value;
            document.getElementById(inputId + 'Text').value = value;
        }
        
        function updateSliderValue(id) {
            const value = document.getElementById(id).value;
            document.getElementById(id + 'Value').textContent = id === 'bgOpacity' ? value : value + 'px';
            if (id === 'fontSize' || id === 'fontFamily') {
                renderAnnotations();
            }
        }
        
        function resetPositions() {
            addSampleAnnotations();
        }
        
        function getCustomizationSettings() {
            return {
                checkColor: document.getElementById('checkColor').value,
                xColor: document.getElementById('xColor').value,
                partialColor: document.getElementById('partialColor').value,
                fontFamily: document.getElementById('fontFamily').value,
                markSize: parseInt(document.getElementById('markSize').value),
                fontSize: parseInt(document.getElementById('fontSize').value),
                bgOpacity: parseInt(document.getElementById('bgOpacity').value),
                annotations: annotations
            };
        }
        
        async function applyAndDownload() {
            if (!imageData) {
                alert('Please upload an image first');
                return;
            }
            
            const loader = document.getElementById('loadingIndicator');
            loader.style.display = 'flex';
            const settings = getCustomizationSettings();
            
            try {
                const response = await fetch('/api/annotation/apply-custom', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        image: imageData,
                        settings: settings
                    })
                });
                
                if (response.ok) {
                    const blob = await response.blob();
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = 'annotated_exam.png';
                    a.click();
                } else {
                    alert('Error applying annotations');
                }
            } catch (e) {
                alert('Error: ' + e.message);
            } finally {
                loader.style.display = 'none';
            }
        }
        
        // Color picker sync
        ['checkColor', 'xColor', 'partialColor'].forEach(id => {
            document.getElementById(id).addEventListener('input', function() {
                document.getElementById(id + 'Text').value = this.value;
            });
        });
        
        function loadSampleJSON() {
            const sample = {
                "questions": [
                    {"question_number": "1", "points_earned": 2, "points_possible": 2, "feedback": "Excellent response"},
                    {"question_number": "2", "points_earned": 0, "points_possible": 2, "feedback": "Incorrect formula"},
                    {"question_number": "3", "points_earned": 1, "points_possible": 2, "feedback": "Partial credit for steps"}
                ],
                "total_earned": 3,
                "total_possible": 6
            };
            document.getElementById('jsonInput').value = JSON.stringify(sample, null, 2);
        }

        async function previewFromJSON() {
            const loader = document.getElementById('loadingIndicator');
            const jsonText = document.getElementById('jsonInput').value;
            if (!jsonText) {
                alert('Please enter or load JSON data');
                return;
            }
            if (!originalImageData) {
                alert('Please upload an original image first (Step 1)');
                return;
            }

            try {
                const grading_results = JSON.parse(jsonText);
                loader.style.display = 'flex';
                
                // Show original clean image and wait for it
                const img = document.getElementById('previewImage');
                img.src = originalImageData;
                
                await new Promise(resolve => {
                    const timeout = setTimeout(resolve, 3000);
                    if (img.complete) {
                        clearTimeout(timeout);
                        resolve();
                    } else {
                        img.onload = () => { clearTimeout(timeout); resolve(); };
                        img.onerror = () => { clearTimeout(timeout); resolve(); };
                    }
                });
                
                window.detectedImageWidth = img.naturalWidth || 1000;
                window.detectedImageHeight = img.naturalHeight || 1400;

                const response = await fetch('/api/annotation/generate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        exam_file: originalImageData.split(',')[1],
                        file_type: 'png',
                        grading_results: grading_results
                    })
                });

                if (response.ok) {
                    const result = await response.json();
                    if (result.data && result.data.annotation_metadata) {
                        annotations = result.data.annotation_metadata;
                        imageData = originalImageData;
                        renderAnnotations();
                    } else {
                        alert('No metadata returned from server');
                    }
                } else {
                    const error = await response.json();
                    alert('Error: ' + (error.error || 'Failed to generate annotations'));
                }
            } catch (e) {
                alert('Preview failed: ' + e.message);
            } finally {
                loader.style.display = 'none';
            }
        }

        // Font change
        document.getElementById('fontFamily').addEventListener('change', renderAnnotations);
    </script>
</body>
</html>
'''


@customize_bp.route('/customize')
def customize_page():
    """Serve the annotation customization GUI."""
    return render_template_string(CUSTOMIZE_HTML)


@customize_bp.route('/api/annotation/apply-custom', methods=['POST'])
def apply_custom_annotations():
    """Apply custom annotations to an image.
    
    Uses the EXACT same drawing logic as annotation_service.py to ensure
    the downloaded image matches the preview and original annotations.
    """
    from PIL import Image, ImageDraw, ImageFont
    import re
    
    try:
        data = request.get_json()
        image_data = data.get('image', '')
        settings = data.get('settings', {})
        
        # Decode base64 image
        if ',' in image_data:
            image_data = image_data.split(',')[1]
        image_bytes = base64.b64decode(image_data)
        
        image = Image.open(io.BytesIO(image_bytes))
        if image.mode != 'RGBA':
            image = image.convert('RGBA')
        
        draw = ImageDraw.Draw(image)
        width, height = image.size
        
        # ===== EXACT SAME SCALING AS annotation_service.py =====
        scale_factor = (width * height) ** 0.5 / 1000  # Normalize to ~1 for 1000px
        
        # Mark/icon sizes (matching annotation_service.py)
        mark_size = int(max(20, min(60, 32 * scale_factor)))
        font_size = int(max(18, min(48, 30 * scale_factor)))  # Score font
        feedback_font_size = int(max(16, min(40, 24 * scale_factor)))
        
        bg_opacity = settings.get('bgOpacity', 200)
        
        # ===== EXACT SAME FONT LOADING AS annotation_service.py =====
        def get_score_font(size):
            """Stylish font for scores - handwriting style."""
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
        
        def get_simple_font(size):
            """Modern readable font for feedback/correct answers."""
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
        
        score_font = get_score_font(font_size)
        simple_font = get_simple_font(feedback_font_size)
        
        # ===== EXACT SAME DRAWING FUNCTIONS AS annotation_service.py =====
        def draw_checkmark(d, x, y, size):
            """Draw checkmark with white circle background - EXACT copy from annotation_service.py"""
            cx, cy = x + size//2, y + size//2
            r = int(size * 0.7)
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 255, 255, 220))
            color = (25, 140, 25)
            lw = max(3, size // 5)
            d.line([(x, y + size*0.5), (x + size*0.35, y + size*0.85)], fill=color, width=lw)
            d.line([(x + size*0.35, y + size*0.85), (x + size, y + size*0.1)], fill=color, width=lw)
        
        def draw_x_mark(d, x, y, size):
            """Draw X mark with white circle background - EXACT copy from annotation_service.py"""
            cx, cy = x + size//2, y + size//2
            r = int(size * 0.7)
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 255, 255, 220))
            color = (190, 30, 30)
            lw = max(3, size // 5)
            d.line([(x + 2, y + 2), (x + size - 2, y + size - 2)], fill=color, width=lw)
            d.line([(x + size - 2, y + 2), (x + 2, y + size - 2)], fill=color, width=lw)
        
        def draw_partial_mark(d, x, y, size):
            """Draw partial mark with white circle background - EXACT copy from annotation_service.py"""
            cx, cy = x + size//2, y + size//2
            r = int(size * 0.7)
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 255, 255, 220))
            color = (200, 150, 0)
            lw = max(4, size // 4)
            d.line([(x + 2, y + size//2), (x + size - 2, y + size//2)], fill=color, width=lw)
        
        def draw_pill_badge(d, box, fill_color, border_color=None):
            """Draw rounded badge - sharper edges for modern look"""
            x1, y1, x2, y2 = box
            radius = 3
            if border_color:
                border_box = (x1 - 1, y1 - 1, x2 + 1, y2 + 1)
                draw_rounded_rect(d, border_box, radius + 1, border_color)
            draw_rounded_rect(d, box, radius, fill_color)
        
        def draw_rounded_rect(d, box, radius, fill):
            """Draw rounded rectangle - EXACT copy from annotation_service.py"""
            x1, y1, x2, y2 = box
            radius = min(radius, (y2 - y1) // 2, (x2 - x1) // 2)
            if radius < 1:
                d.rectangle(box, fill=fill)
                return
            d.rectangle([x1 + radius, y1, x2 - radius, y2], fill=fill)
            d.rectangle([x1, y1 + radius, x2, y2 - radius], fill=fill)
            d.ellipse([x1, y1, x1 + radius * 2, y1 + radius * 2], fill=fill)
            d.ellipse([x2 - radius * 2, y1, x2, y1 + radius * 2], fill=fill)
            d.ellipse([x1, y2 - radius * 2, x1 + radius * 2, y2], fill=fill)
            d.ellipse([x2 - radius * 2, y2 - radius * 2, x2, y2], fill=fill)
        
        def draw_text_with_bg(d, x, y, text, font, text_color, padding=6):
            """Draw text with semi-transparent rounded background - EXACT copy from annotation_service.py"""
            try:
                bbox = d.textbbox((x, y), text, font=font)
                bg_box = (bbox[0] - padding, bbox[1] - padding // 2, 
                          bbox[2] + padding, bbox[3] + padding // 2)
                draw_pill_badge(d, bg_box, (255, 255, 255, 160), (200, 200, 200, 120))
            except:
                pass
            d.text((x, y), text, fill=text_color, font=font)
        
        def draw_correct_label(d, x, y, text, font):
            """Draw correct answer label - EXACT copy from annotation_service.py"""
            try:
                bbox = d.textbbox((x, y), text, font=font)
                bg_box = (bbox[0] - 8, bbox[1] - 3, bbox[2] + 8, bbox[3] + 3)
                draw_pill_badge(d, bg_box, (230, 242, 255, 140), (100, 150, 220, 100))
            except:
                pass
            d.text((x, y), text, fill=(20, 60, 140), font=font)
        
        # Color constants matching annotation_service.py
        RED = (180, 30, 30)
        GREEN = (25, 130, 25)
        YELLOW = (200, 150, 0)
        DARK_BLUE = (15, 50, 130)
        
        # Draw each annotation
        for ann in settings.get('annotations', []):
            x = int(ann.get('x', 0))
            y = int(ann.get('y', 0))
            text = ann.get('text', '')
            ann_type = ann.get('type', 'label')
            color_hex = ann.get('color', '#000000')
            
            # Local scaling based on user resize
            local_mark_size = mark_size
            local_font_size = font_size
            if 'width' in ann:
                # If it's a mark+score group, width covers both. 
                # Icon is usually 1/3 of the total width we set in metadata.
                local_mark_size = int(ann['width'] / 3)
                local_font_size = int(ann['width'] / 3 * 0.9) # Proportional font
            if 'height' in ann:
                local_mark_size = min(local_mark_size, int(ann['height']))
            
            # Parse color
            try:
                color = tuple(int(color_hex.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
            except:
                color = (0, 0, 0)
            
            if ann_type in ['mark', 'check', 'x', 'partial']:
                # Determine icon type from text or type
                if '✓' in text or ann_type == 'check':
                    draw_checkmark(draw, x, y, local_mark_size)
                    status_color = GREEN
                elif '✗' in text or ann_type == 'x':
                    draw_x_mark(draw, x, y, local_mark_size)
                    status_color = RED
                else:
                    draw_partial_mark(draw, x, y, local_mark_size)
                    status_color = YELLOW
                
                # Draw score NEXT TO the mark
                score_match = re.search(r'(\d+\.?\d*)/(\d+\.?\d*)', text)
                if score_match:
                    score_text = f"{score_match.group(1)}/{score_match.group(2)}"
                    score_x = x + local_mark_size + 8
                    score_y = y + local_mark_size//2 - local_font_size//2
                    # Use local font size if changed
                    l_score_font = get_score_font(local_font_size) if local_font_size != font_size else score_font
                    draw_text_with_bg(draw, score_x, score_y, score_text, l_score_font, status_color)
                        
            elif ann_type == 'feedback':
                l_simple_font = get_simple_font(local_font_size) if local_font_size != font_size else simple_font
                try:
                    bbox = draw.textbbox((x, y), text, font=l_simple_font)
                    bg_box = (bbox[0] - 8, bbox[1] - 4, bbox[2] + 8, bbox[3] + 4)
                    draw_pill_badge(draw, bg_box, (20, 60, 140, 230))
                    draw.text((x, y), text, fill=(255, 255, 255), font=l_simple_font)
                except:
                    draw.text((x, y), text, fill=DARK_BLUE, font=l_simple_font)
                    
            elif ann_type == 'correct_answer' or (text and 'correct' in text.lower()):
                l_simple_font = get_simple_font(local_font_size) if local_font_size != font_size else simple_font
                draw_correct_label(draw, x, y, text, l_simple_font)
                
            else:
                # Generic text with white background
                l_simple_font = get_simple_font(local_font_size) if local_font_size != font_size else simple_font
                draw_text_with_bg(draw, x, y, text, l_simple_font, color)
        
        # Save to bytes
        output = io.BytesIO()
        image.convert('RGB').save(output, format='PNG')
        output.seek(0)
        
        from flask import send_file
        return send_file(output, mimetype='image/png')
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@customize_bp.route('/api/annotation/presets', methods=['GET'])
def get_presets():
    """Get available annotation presets."""
    return jsonify({
        'presets': [
            {
                'name': 'Classic Teacher',
                'checkColor': '#19aa19',
                'xColor': '#be1e1e',
                'partialColor': '#c89600',
                'fontFamily': 'Segoe Script',
                'markSize': 32,
                'fontSize': 24
            },
            {
                'name': 'Modern Minimal',
                'checkColor': '#2ecc71',
                'xColor': '#e74c3c',
                'partialColor': '#f39c12',
                'fontFamily': 'Calibri',
                'markSize': 28,
                'fontSize': 20
            },
            {
                'name': 'Professional',
                'checkColor': '#27ae60',
                'xColor': '#c0392b',
                'partialColor': '#d35400',
                'fontFamily': 'Arial',
                'markSize': 30,
                'fontSize': 22
            }
        ]
    })


@customize_bp.route('/api/annotation/detect-existing', methods=['POST'])
def detect_existing_annotations():
    """Detect existing annotations in an already-graded image.
    
    First checks for embedded metadata (from Gradeo annotation service).
    Falls back to AI detection if no embedded metadata found.
    """
    from PIL import Image
    import json
    
    try:
        # Get image from request
        if 'image' in request.files:
            image_bytes = request.files['image'].read()
        else:
            data = request.get_json()
            image_data = data.get('image', '')
            if ',' in image_data:
                image_data = image_data.split(',')[1]
            image_bytes = base64.b64decode(image_data)
        
        # Try to extract embedded metadata first
        try:
            image = Image.open(io.BytesIO(image_bytes))
            width, height = image.size
            
            # Check for embedded Gradeo annotation metadata
            if hasattr(image, 'info') and 'gradeo_annotations' in image.info:
                metadata_json = image.info['gradeo_annotations']
                result = json.loads(metadata_json)
                result['source'] = 'embedded'
                print(f"Found embedded metadata: {len(result.get('annotations', []))} annotations")
                return jsonify(result)
        except Exception as e:
            print(f"No embedded metadata: {e}")
        
        # Fall back to AI detection
        result = annotation_service.detect_existing_annotations(image_bytes)
        result['source'] = 'ai_detected'
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e), 'annotations': []}), 500


@customize_bp.route('/api/annotation/get-annotations', methods=['POST'])
def get_annotations_from_grading():
    """Get annotation positions from grading results (for mobile app to render as overlays).
    
    Request JSON:
    {
        "grading_results": {...},
        "image_width": 1000,
        "image_height": 1400
    }
    
    Returns: JSON with annotation positions
    """
    try:
        data = request.get_json()
        grading_results = data.get('grading_results', {})
        width = data.get('image_width', 1000)
        height = data.get('image_height', 1400)
        
        annotations = []
        grading = grading_results.get('grading', grading_results.get('questions', []))
        
        for i, q in enumerate(grading):
            earned = float(q.get('earned_points', q.get('points_earned', 0)))
            possible = float(q.get('possible_points', q.get('points_possible', 1)))
            
            # Determine type
            if earned >= possible and possible > 0:
                ann_type = 'check'
                color = '#19aa19'
                symbol = '✓'
            elif earned > 0:
                ann_type = 'partial'
                color = '#c89600'
                symbol = '—'
            else:
                ann_type = 'x'
                color = '#be1e1e'
                symbol = '✗'
            
            # Calculate position (simplified - evenly spaced)
            y = int(100 + i * (height / (len(grading) + 1)))
            x = int(width * 0.7)
            
            annotations.append({
                'id': f"q{q.get('question_number', i+1)}",
                'question_number': q.get('question_number', i+1),
                'type': ann_type,
                'text': f"{symbol} {int(earned) if earned == int(earned) else earned}/{int(possible) if possible == int(possible) else possible}",
                'x': x,
                'y': y,
                'color': color,
                'earned': earned,
                'possible': possible,
                'feedback': q.get('feedback', ''),
                'correct_answer': q.get('correct_answer', '')
            })
        
        # Add final score
        total_earned = grading_results.get('total_earned', sum(a['earned'] for a in annotations))
        total_possible = grading_results.get('total_possible', sum(a['possible'] for a in annotations))
        
        annotations.append({
            'id': 'final_score',
            'type': 'final_score',
            'text': f"🏆 Total: {int(total_earned) if total_earned == int(total_earned) else total_earned}/{int(total_possible) if total_possible == int(total_possible) else total_possible}",
            'x': int(width * 0.7),
            'y': 30,
            'color': '#f59e0b'
        })
        
        return jsonify({
            'annotations': annotations,
            'settings': {
                'checkColor': '#19aa19',
                'xColor': '#be1e1e',
                'partialColor': '#c89600',
                'fontSize': 24,
                'markSize': 32
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@customize_bp.route('/api/annotation/save-metadata', methods=['POST'])
def save_annotation_metadata():
    """Save annotation metadata for later editing (mobile app use case).
    
    Request JSON:
    {
        "exam_id": "unique_exam_id",
        "annotations": [...],
        "settings": {...}
    }
    """
    import json
    import os
    
    try:
        data = request.get_json()
        exam_id = data.get('exam_id', 'default')
        annotations = data.get('annotations', [])
        settings = data.get('settings', {})
        
        # Store in a JSON file (in production, use database)
        storage_dir = os.path.join(os.path.dirname(__file__), '..', 'static', 'annotation_data')
        os.makedirs(storage_dir, exist_ok=True)
        
        filepath = os.path.join(storage_dir, f"{exam_id}.json")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({'annotations': annotations, 'settings': settings}, f, ensure_ascii=False)
        
        return jsonify({'success': True, 'exam_id': exam_id})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@customize_bp.route('/api/annotation/load-metadata/<exam_id>', methods=['GET'])
def load_annotation_metadata(exam_id):
    """Load saved annotation metadata for editing."""
    import json
    import os
    
    try:
        storage_dir = os.path.join(os.path.dirname(__file__), '..', 'static', 'annotation_data')
        filepath = os.path.join(storage_dir, f"{exam_id}.json")
        
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return jsonify(data)
        else:
            return jsonify({'error': 'Not found', 'annotations': [], 'settings': {}}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500
