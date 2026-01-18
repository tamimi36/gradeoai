from flask import Blueprint, render_template_string, request, jsonify, send_file
import base64
import io
import json
from PIL import Image, ImageDraw, ImageFont

review_bp = Blueprint('review', __name__)

REVIEW_HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Gradeo | Review Studio</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&family=Outfit:wght@400;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-dark: #0f172a;
            --sidebar-bg: #1e293b;
            --accent: #4facfe;
            --accent-glow: rgba(79, 172, 254, 0.3);
            --success: #22c55e;
            --warning: #f59e0b;
            --danger: #ef4444;
            --text-main: #f8fafc;
            --text-dim: #94a3b8;
            --border: #334155;
            --card-bg: rgba(30, 41, 59, 0.7);
            --panel-bg: rgba(15, 23, 42, 0.95);
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Inter', sans-serif;
        }

        body {
            background-color: var(--bg-dark);
            color: var(--text-main);
            height: 100vh;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }

        /* Header */
        header {
            height: 64px;
            background: rgba(15, 23, 42, 0.9);
            backdrop-filter: blur(20px);
            border-bottom: 1px solid var(--border);
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 24px;
            z-index: 1000;
        }

        .logo {
            font-family: 'Outfit', sans-serif;
            font-size: 22px;
            font-weight: 700;
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .header-actions {
            display: flex;
            gap: 12px;
        }

        /* Sidebar Redesign */
        .sidebar {
            width: 360px;
            background: var(--sidebar-bg);
            border-right: 1px solid var(--border);
            display: flex;
            flex-direction: column;
            z-index: 500;
            box-shadow: 10px 0 30px rgba(0,0,0,0.3);
        }

        .sidebar-header {
            padding: 20px;
            border-bottom: 1px solid var(--border);
            background: rgba(0,0,0,0.2);
        }

        .section {
            padding: 24px;
            border-bottom: 1px solid var(--border);
        }

        .section-title {
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            color: var(--text-dim);
            margin-bottom: 16px;
            font-weight: 700;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .control-row {
            margin-bottom: 16px;
        }

        .label {
            display: block;
            font-size: 12px;
            margin-bottom: 6px;
            color: var(--text-dim);
        }

        input[type="text"], textarea {
            width: 100%;
            background: rgba(15, 23, 42, 0.5);
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 10px 12px;
            color: white;
            font-size: 13px;
            transition: all 0.2s;
        }

        input[type="text"]:focus, textarea:focus {
            outline: none;
            border-color: var(--accent);
            box-shadow: 0 0 0 3px var(--accent-glow);
        }

        .btn {
            border: none;
            padding: 10px 16px;
            border-radius: 6px;
            font-weight: 600;
            font-size: 13px;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            transition: all 0.2s;
        }

        .btn-primary { background: var(--accent); color: white; }
        .btn-secondary { background: var(--border); color: white; }
        .btn-success { background: var(--success); color: white; }
        .btn-danger { background: var(--danger); color: white; }
        .btn:hover { opacity: 0.9; transform: translateY(-1px); }

        .color-grid {
            display: grid;
            grid-template-columns: repeat(6, 1fr);
            gap: 8px;
        }

        .color-circle {
            width: 32px;
            height: 32px;
            border-radius: 50%;
            cursor: pointer;
            border: 2px solid transparent;
            transition: all 0.2s;
        }

        .color-circle:hover { transform: scale(1.1); }
        .color-circle.active { border-color: white; transform: scale(1.1); }

        /* Document Modal */
        #doc-modal {
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            width: 600px;
            max-height: 80vh;
            background: var(--sidebar-bg);
            border: 1px solid var(--border);
            border-radius: 12px;
            z-index: 1001;
            padding: 30px;
            box-shadow: 0 30px 60px rgba(0,0,0,0.6);
            display: none;
            overflow-y: auto;
        }

        .overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.7);
            z-index: 1000;
            display: none;
        }

        code {
            background: rgba(0,0,0,0.3);
            padding: 2px 5px;
            border-radius: 4px;
            font-family: monospace;
            color: var(--accent);
        }

        pre {
            background: rgba(0,0,0,0.4);
            padding: 15px;
            border-radius: 8px;
            font-size: 12px;
            margin: 10px 0;
            overflow-x: auto;
            border: 1px solid var(--border);
        }

        /* Editor Area */
        .editor-container {
            flex: 1;
            background: #020617;
            position: relative;
            overflow: auto;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 40px;
        }

        #canvas-wrapper {
            position: relative;
            box-shadow: 0 40px 100px rgba(0, 0, 0, 0.7);
            border-radius: 8px;
            overflow: hidden;
            background: #1e293b;
        }

        #bg-image { display: block; }
        .annotation-container { position: absolute; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none; }

        .ann-object {
            position: absolute;
            pointer-events: all;
            cursor: move;
            user-select: none;
            border: 2px solid transparent;
            transition: border-color 0.2s, opacity 0.2s;
            display: flex;
            align-items: center;
            border-radius: 6px;
        }

        .ann-object.selected {
            border-color: var(--accent);
            background: rgba(79, 172, 254, 0.1) !important;
            box-shadow: 0 0 30px var(--accent-glow);
        }

        .ann-object.mark-mode { background: transparent !important; }
        .mark-pill { display: flex; align-items: center; gap: 12px; height: 100%; width: 100%; }
        .icon-circle {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            flex-shrink: 0;
            box-shadow: 0 4px 12px rgba(0,0,0,0.25);
        }

        .score-text-preview {
            background: rgba(255, 255, 255, 1);
            padding: 4px 16px;
            border-radius: 4px;
            font-weight: 800;
            font-size: 1.1em;
            color: inherit;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
            min-width: 60px;
            text-align: center;
        }

        .ann-object.label-mode {
            border-radius: 6px;
            padding: 0 20px;
            color: white !important;
            font-weight: 600;
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.3);
        }

        .ann-object.final-score-mode {
            background: #000 !important;
            border: 3px solid var(--accent);
            color: var(--accent) !important;
            font-size: 1.6em;
            padding: 12px 30px;
            font-weight: 900;
            border-radius: 10px;
            box-shadow: 0 20px 50px rgba(0,0,0,0.5);
        }

        /* 8-Direction Resize Handles */
        .resize-handle {
            position: absolute;
            width: 12px;
            height: 12px;
            background: white;
            border: 2px solid var(--accent);
            border-radius: 3px;
            opacity: 0;
            transition: opacity 0.2s;
            z-index: 100;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }

        .resize-handle.tl { top: -7px; left: -7px; cursor: nw-resize; }
        .resize-handle.tr { top: -7px; right: -7px; cursor: ne-resize; }
        .resize-handle.bl { bottom: -7px; left: -7px; cursor: sw-resize; }
        .resize-handle.br { bottom: -7px; right: -7px; cursor: se-resize; }
        .resize-handle.tm { top: -7px; left: calc(50% - 6px); cursor: n-resize; }
        .resize-handle.bm { bottom: -7px; left: calc(50% - 6px); cursor: s-resize; }
        .resize-handle.ml { top: calc(50% - 6px); left: -7px; cursor: w-resize; }
        .resize-handle.mr { top: calc(50% - 6px); right: -7px; cursor: e-resize; }

        .ann-object.selected .resize-handle { opacity: 1; }

        #loading {
            position: fixed;
            inset: 0;
            background: rgba(15, 23, 42, 0.9);
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            z-index: 10000;
        }

        .spinner {
            width: 50px;
            height: 50px;
            border: 4px solid var(--accent-glow);
            border-top: 4px solid var(--accent);
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }

        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }

        /* Custom scrollbar */
        ::-webkit-scrollbar { width: 8px; }
        ::-webkit-scrollbar-track { background: var(--bg-dark); }
        ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 10px; }
        ::-webkit-scrollbar-thumb:hover { background: var(--text-dim); }

        .toggle-container {
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: rgba(0,0,0,0.2);
            padding: 10px 12px;
            border-radius: 6px;
            border: 1px solid var(--border);
        }

        .switch {
            position: relative;
            display: inline-block;
            width: 44px;
            height: 22px;
        }

        .switch input { opacity: 0; width: 0; height: 0; }
        .slider {
            position: absolute;
            cursor: pointer;
            top: 0; left: 0; right: 0; bottom: 0;
            background-color: var(--border);
            transition: .4s;
            border-radius: 34px;
        }

        .slider:before {
            position: absolute;
            content: "";
            height: 16px;
            width: 16px;
            left: 3px;
            bottom: 3px;
            background-color: white;
            transition: .4s;
            border-radius: 50%;
        }

        input:checked + .slider { background-color: var(--accent); }
        input:checked + .slider:before { transform: translateX(22px); }
    </style>
</head>
<body>
    <div id="loading">
        <div class="spinner"></div>
        <p style="margin-top: 20px; font-weight: 600; color: var(--text-dim);">initializing workspace...</p>
    </div>

    <div class="overlay" id="overlay" onclick="toggleDocs()"></div>
    <div id="doc-modal">
        <h2 style="margin-bottom: 20px; font-family: 'Outfit', sans-serif;">Grading JSON Structure</h2>
        <p style="color: var(--text-dim); margin-bottom: 15px; font-size: 14px;">Teachers can paste their raw grading results or pre-defined metadata. The studio expects one of these formats:</p>
        
        <div style="margin-bottom: 20px;">
            <p style="font-weight: 600; font-size: 14px; margin-bottom: 8px;">1. Standard Metadata Array</p>
            <pre>[
  {
    "type": "check",
    "text": "✓ 5/5",
    "x": 100, "y": 200
  },
  { "type": "label", "text": "Good work!", "x": 150, "y": 300 }
]</pre>
        </div>

        <div>
            <p style="font-weight: 600; font-size: 14px; margin-bottom: 8px;">2. Nested Metadata (Gradeo Format)</p>
            <pre>{
  "annotation_metadata": [ ... ],
  "status": "complete"
}</pre>
        </div>
        
        <button class="btn btn-primary" style="width: 100%; margin-top: 20px;" onclick="toggleDocs()">Close Guide</button>
    </div>

    <header>
        <div class="logo">
            <span>🖋️</span> Gradeo Studio
        </div>
        <div class="header-actions">
            <button class="btn btn-secondary" onclick="exportJSON()">💾 Export State</button>
            <button class="btn btn-secondary" onclick="approveAll()">✅ Approve All</button>
            <button class="btn btn-primary" onclick="finalizeAndDownload()">⬇️ Final Download</button>
        </div>
    </header>

    <main style="flex: 1; display: flex; overflow: hidden;">
        <div class="sidebar">
            <div class="sidebar-header">
                <div class="section-title">Workspace Initialization</div>
                <div class="control-row">
                    <label class="label">Step 1: Upload Scan</label>
                    <input type="file" id="imageInput" accept="image/*" onchange="handleImageUpload(event)">
                </div>
                <div class="control-row" style="margin-bottom: 0;">
                    <div class="section-title" style="margin-bottom: 8px;">
                        Step 2: Load Data
                        <span style="color: var(--accent); cursor: pointer; text-transform: none; font-size: 12px; font-weight: 600;" onclick="toggleDocs()">Data Structure</span>
                    </div>
                    <textarea id="jsonInput" rows="3" placeholder='Paste results here...'></textarea>
                    <button class="btn btn-secondary" style="width: 100%; margin-top: 10px; background: rgba(255,255,255,0.1);" onclick="loadFromJSON()">⚡ Populate Studio</button>
                </div>
            </div>

            <div id="inspector" class="hidden">
                <div class="section" style="background: rgba(79, 172, 254, 0.05);">
                    <div class="section-title">Object Properties</div>
                    <div class="control-row">
                        <label class="label">Display Text</label>
                        <input type="text" id="prop-text" oninput="updateSelected('text', this.value)">
                    </div>
                    
                    <div class="control-row">
                        <label class="label">Color Palette</label>
                        <div class="color-grid" id="color-palette">
                            <!-- Colors generated by JS -->
                        </div>
                    </div>

                    <div class="control-row" style="margin-bottom: 0;">
                        <div class="toggle-container">
                            <span class="label" style="margin-bottom: 0;">Transparent Mode</span>
                            <label class="switch">
                                <input type="checkbox" id="prop-transparent" onchange="updateSelected('opacity', this.checked ? 0.3 : 1.0)">
                                <span class="slider"></span>
                            </label>
                        </div>
                    </div>
                </div>

                <div class="section" style="border-bottom: 2px solid rgba(0,0,0,0.3);">
                    <div class="section-title">Layer Control</div>
                    <div style="display: flex; gap: 8px;">
                        <button class="btn btn-danger" style="flex: 1;" onclick="deleteSelected()">🗑️ Delete</button>
                        <button class="btn btn-success" style="flex: 1;" onclick="approveSelected()">✅ Approve</button>
                    </div>
                </div>
            </div>

            <div class="section">
                <div class="section-title">Quick Add</div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
                    <button class="btn btn-secondary" onclick="quickAdd('label')">📝 Label</button>
                    <button class="btn btn-secondary" onclick="quickAdd('score')">🏆 Mark</button>
                    <button class="btn btn-primary" style="grid-column: span 2;" onclick="quickAdd('final_score')">🎓 Add Final Score</button>
                </div>
            </div>

            <div class="section" style="flex: 1; overflow-y: auto;">
                <div class="section-title">Annotation Queue <span id="queue-count" style="background: var(--accent); color: white; padding: 2px 8px; border-radius: 10px; font-size: 10px;">0</span></div>
                <div id="queue-list" style="display: flex; flex-direction: column; gap: 8px;">
                    <!-- Queue items -->
                </div>
            </div>
        </div>

        <div class="editor-container">
            <div id="canvas-wrapper">
                <img id="bg-image" src="" alt="">
                <div id="ann-layer" class="annotation-container"></div>
            </div>
        </div>
    </main>

    <script>
        // --- State Management ---
        const state = {
            annotations: [],
            selectedId: null,
            imageScale: 1,
            isDragging: false,
            isResizing: false,
            dragOffset: { x: 0, y: 0 },
            initialSize: { w: 0, h: 0 },
            initialPos: { x: 0, y: 0 }
        };

        const elements = {
            wrapper: document.getElementById('canvas-wrapper'),
            image: document.getElementById('bg-image'),
            layer: document.getElementById('ann-layer'),
            inspector: document.getElementById('inspector'),
            loading: document.getElementById('loading'),
            queue: document.getElementById('queue-list'),
            count: document.getElementById('queue-count')
        };

        // --- Core Functions ---
        window.onload = () => {
            initPalette();
            setTimeout(() => elements.loading.style.display = 'none', 800);
            
            // Global listeners
            document.addEventListener('mousemove', handleGlobalMove);
            document.addEventListener('mouseup', handleGlobalEnd);
            document.addEventListener('keydown', (e) => {
                if (e.key === 'Delete' || e.key === 'Backspace') {
                    if (state.selectedId && !['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName)) {
                        deleteSelected();
                    }
                }
            });
        };

        function initPalette() {
            const colors = ['#19aa19', '#be1e1e', '#c89600', '#0ea5e9', '#8b5cf6', '#f43f5e', '#10b981', '#64748b', '#000000', '#ffffff'];
            const grid = document.getElementById('color-palette');
            colors.forEach(c => {
                const div = document.createElement('div');
                div.className = 'color-circle';
                div.style.background = c;
                div.onclick = () => updateSelected('color', c);
                grid.appendChild(div);
            });
        }

        function toggleDocs() {
            const modal = document.getElementById('doc-modal');
            const overlay = document.getElementById('overlay');
            const isVisible = modal.style.display === 'block';
            modal.style.display = isVisible ? 'none' : 'block';
            overlay.style.display = isVisible ? 'none' : 'block';
        }

        function handleImageUpload(e) {
            const file = e.target.files[0];
            if (!file) return;

            const reader = new FileReader();
            reader.onload = (e) => {
                elements.image.src = e.target.result;
                elements.image.onload = () => {
                    state.imageScale = elements.image.naturalWidth / elements.image.clientWidth;
                    renderWorkspace();
                };
            };
            reader.readAsDataURL(file);
        }

        async function loadFromJSON() {
            const jsonText = document.getElementById('jsonInput').value;
            if (!jsonText) {
                alert('Please paste some JSON data first.');
                return;
            }
            if (!elements.image.src || elements.image.src === window.location.href) {
                alert('Please upload an image first so we can map the coordinates.');
                return;
            }

            try {
                const inputData = JSON.parse(jsonText);
                
                function findMetadata(obj) {
                    if (Array.isArray(obj)) return obj;
                    if (obj.annotation_metadata) return obj.annotation_metadata;
                    if (obj.data && obj.data.annotation_metadata) return obj.data.annotation_metadata;
                    if (obj.results && obj.results.annotation_metadata) return obj.results.annotation_metadata;
                    return null;
                }

                const rawMetadata = findMetadata(inputData);
                
                if (rawMetadata && Array.isArray(rawMetadata)) {
                    state.annotations = rawMetadata.map((ann, i) => ({
                        ...ann,
                        id: ann.id || `ann_${Date.now()}_${i}`,
                        status: ann.status || 'pending',
                        width: ann.width || 120,
                        height: ann.height || 40,
                        x: parseFloat(ann.x) || 0,
                        y: parseFloat(ann.y) || 0,
                        color: ann.color || '#4facfe',
                        text: ann.text || '',
                        opacity: ann.opacity !== undefined ? ann.opacity : 1.0
                    }));
                    renderWorkspace();
                    alert(`Successfully loaded ${state.annotations.length} annotations!`);
                    return;
                }

                elements.loading.style.display = 'flex';

                const response = await fetch('/api/annotation/generate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        exam_file: elements.image.src.split(',')[1],
                        file_type: 'png',
                        grading_results: inputData
                    })
                });

                const metadata = await response.json();
                if (metadata.success && metadata.data.annotation_metadata) {
                    state.annotations = metadata.data.annotation_metadata.map((ann, i) => ({
                        ...ann,
                        id: ann.id || `gen_${Date.now()}_${i}`,
                        status: ann.status || 'pending',
                        width: ann.width || 120,
                        height: ann.height || 40,
                        opacity: 1.0
                    }));
                    renderWorkspace();
                    alert(`Generated ${state.annotations.length} AI annotations!`);
                } else {
                    const errorMsg = metadata.error || (metadata.data ? metadata.data.error : 'Unknown error');
                    alert('Could not generate annotations: ' + errorMsg);
                }
            } catch (err) {
                alert('Invalid JSON format or load error: ' + err.message);
            } finally {
                elements.loading.style.display = 'none';
            }
        }

        function renderWorkspace() {
            elements.layer.innerHTML = '';
            elements.queue.innerHTML = '';
            
            const imgW = elements.image.naturalWidth || 1000;
            const imgH = elements.image.naturalHeight || 1400;
            const dispW = elements.image.clientWidth || 800;
            const dispH = elements.image.clientHeight || 1120;
            
            const scaleX = dispW / imgW;
            const scaleY = dispH / imgH;

            if (state.annotations.length === 0) {
                elements.count.innerText = '0';
                return;
            }

            state.annotations.forEach(ann => {
                const div = document.createElement('div');
                div.id = `ann-${ann.id}`;
                
                const isMark = ['check', 'x', 'partial', 'mark'].includes(ann.type);
                const isFinal = ann.type === 'final_score';
                
                div.className = `ann-object ${ann.status} ${state.selectedId === ann.id ? 'selected' : ''} ${ann.type}-mode`;
                if (isMark) div.className += ' mark-mode';
                if (isFinal) div.className += ' final-score-mode';

                div.style.left = `${ann.x * scaleX}px`;
                div.style.top = `${ann.y * scaleY}px`;
                div.style.width = `${ann.width * scaleX}px`;
                div.style.height = `${ann.height * scaleY}px`;
                
                if (ann.type === 'label') {
                    div.style.backgroundColor = ann.color;
                    div.style.border = 'none';
                }

                if (isMark) {
                    const symbol = ann.text.split(' ')[0] || '✓';
                    const score = ann.text.split(' ').slice(1).join(' ') || '';
                    div.innerHTML = `
                        <div class="mark-pill" style="color: ${ann.color}">
                            <div class="icon-circle" style="width: ${ann.height * scaleY * 0.8}px; height: ${ann.height * scaleY * 0.8}px; font-size: ${ann.height * scaleY * 0.5}px; color: ${ann.color};">
                                ${symbol}
                            </div>
                            ${score ? `<div class="score-text-preview" style="color: ${ann.color}">${score}</div>` : ''}
                        </div>
                    `;
                } else if (isFinal) {
                    div.innerText = ann.text || 'TOTAL: 0/0';
                    div.style.fontSize = `${(ann.height * scaleY) * 0.45}px`;
                } else {
                    div.style.color = 'white';
                    div.style.fontSize = `${(ann.height * scaleY) * 0.45}px`;
                    div.innerText = ann.text;
                }

                // Transparency Support
                div.style.opacity = ann.opacity !== undefined ? ann.opacity : 1.0;

                // 8 Resize Handles
                ['tl', 'tm', 'tr', 'mr', 'br', 'bm', 'bl', 'ml'].forEach(dir => {
                    const h = document.createElement('div');
                    h.className = `resize-handle ${dir}`;
                    h.onmousedown = (e) => startResize(e, ann.id, dir);
                    div.appendChild(h);
                });

                div.onmousedown = (e) => {
                    if (e.target.classList.contains('resize-handle')) return;
                    startDrag(e, ann.id);
                };

                elements.layer.appendChild(div);

                const queueItem = document.createElement('div');
                queueItem.style.cssText = `
                    padding: 10px; background: rgba(0,0,0,0.2); border-left: 3px solid ${ann.status === 'approved' ? 'var(--success)' : 'var(--warning)'};
                    border-radius: 4px; display: flex; justify-content: space-between; align-items: center; cursor: pointer;
                `;
                queueItem.onclick = () => selectObject(ann.id);
                queueItem.innerHTML = `
                    <div style="font-size: 13px;">
                        <strong>${ann.question_number ? 'Q'+ann.question_number : ann.type.toUpperCase()}</strong>
                        <div style="color: var(--text-dim); font-size: 11px;">${ann.text}</div>
                    </div>
                `;
                elements.queue.appendChild(queueItem);
            });

            elements.count.innerText = state.annotations.length;
            updateInspector();
        }

        function hexToRgb(hex, asString=false) {
            if (!hex || hex.length < 6) return asString ? 'rgb(0, 0, 0)' : '0, 0, 0';
            const r = parseInt(hex.slice(1, 3), 16);
            const g = parseInt(hex.slice(3, 5), 16);
            const b = parseInt(hex.slice(5, 7), 16);
            return asString ? `rgb(${r}, ${g}, ${b})` : `${r}, ${g}, ${b}`;
        }

        // --- Interactions ---
        function selectObject(id) {
            state.selectedId = id;
            renderWorkspace();
        }

        function updateInspector() {
            const selected = state.annotations.find(a => a.id === state.selectedId);
            if (selected) {
                elements.inspector.classList.remove('hidden');
                document.getElementById('prop-text').value = selected.text;
                document.getElementById('prop-transparent').checked = (selected.opacity < 0.9);
                
                document.querySelectorAll('.color-circle').forEach(c => {
                    const circleColor = c.style.backgroundColor;
                    const selectedColor = hexToRgb(selected.color, true);
                    c.classList.toggle('active', circleColor === selectedColor);
                });
            } else {
                elements.inspector.classList.add('hidden');
            }
        }

        function startDrag(e, id) {
            state.selectedId = id;
            state.isDragging = true;
            const ann = state.annotations.find(a => a.id === id);
            
            const rect = elements.wrapper.getBoundingClientRect();
            const scaleX = elements.image.clientWidth / elements.image.naturalWidth;
            const scaleY = elements.image.clientHeight / elements.image.naturalHeight;

            state.dragOffset.x = (e.clientX - rect.left) / scaleX - ann.x;
            state.dragOffset.y = (e.clientY - rect.top) / scaleY - ann.y;
            
            renderWorkspace();
        }

        function startResize(e, id, dir) {
            e.stopPropagation();
            state.selectedId = id;
            state.isResizing = true;
            state.resizeDir = dir;
            const ann = state.annotations.find(a => a.id === id);
            
            state.initialPos.x = e.clientX;
            state.initialPos.y = e.clientY;
            state.initialSize.w = ann.width;
            state.initialSize.h = ann.height;
            state.initialPos.ax = ann.x;
            state.initialPos.ay = ann.y;
        }

        function handleGlobalMove(e) {
            if (!state.selectedId) return;

            const ann = state.annotations.find(a => a.id === state.selectedId);
            const scaleX = elements.image.clientWidth / elements.image.naturalWidth;
            const scaleY = elements.image.clientHeight / elements.image.naturalHeight;

            if (state.isDragging) {
                const rect = elements.wrapper.getBoundingClientRect();
                ann.x = (e.clientX - rect.left) / scaleX - state.dragOffset.x;
                ann.y = (e.clientY - rect.top) / scaleY - state.dragOffset.y;
                syncVisuals(ann);
            } else if (state.isResizing) {
                const dx = (e.clientX - state.initialPos.x) / scaleX;
                const dy = (e.clientY - state.initialPos.y) / scaleY;
                const dir = state.resizeDir;

                if (dir.includes('r')) ann.width = Math.max(20, state.initialSize.w + dx);
                if (dir.includes('b')) ann.height = Math.max(20, state.initialSize.h + dy);
                if (dir.includes('l')) {
                    const newW = Math.max(20, state.initialSize.w - dx);
                    ann.x = state.initialPos.ax + (state.initialSize.w - newW);
                    ann.width = newW;
                }
                if (dir.includes('t')) {
                    const newH = Math.max(20, state.initialSize.h - dy);
                    ann.y = state.initialPos.ay + (state.initialSize.h - newH);
                    ann.height = newH;
                }
                syncVisuals(ann);
            }
        }

        function handleGlobalEnd() {
            state.isDragging = false;
            state.isResizing = false;
            state.resizeDir = null;
            if (state.selectedId) renderWorkspace();
        }

        function syncVisuals(ann) {
            const el = document.getElementById(`ann-${ann.id}`);
            const scaleX = elements.image.clientWidth / elements.image.naturalWidth;
            const scaleY = elements.image.clientHeight / elements.image.naturalHeight;
            
            el.style.left = `${ann.x * scaleX}px`;
            el.style.top = `${ann.y * scaleY}px`;
            el.style.width = `${ann.width * scaleX}px`;
            el.style.height = `${ann.height * scaleY}px`;
        }

        // --- Actions ---
        function updateSelected(key, val) {
            const ann = state.annotations.find(a => a.id === state.selectedId);
            if (ann) {
                ann[key] = val;
                renderWorkspace();
            }
        }

        function deleteSelected() {
            state.annotations = state.annotations.filter(a => a.id !== state.selectedId);
            state.selectedId = null;
            renderWorkspace();
        }

        function approveSelected() {
            const ann = state.annotations.find(a => a.id === state.selectedId);
            if (ann) {
                ann.status = 'approved';
                renderWorkspace();
            }
        }

        function approveAll() {
            state.annotations.forEach(a => a.status = 'approved');
            renderWorkspace();
        }

        function quickAdd(type) {
            const id = `manual_${Date.now()}`;
            const isFinal = type === 'final_score';
            
            state.annotations.push({
                id: id,
                type: isFinal ? 'final_score' : (type === 'score' ? 'check' : 'label'),
                text: isFinal ? 'TOTAL: 0/100' : (type === 'score' ? '✓ 5/5' : 'New Feedback'),
                x: 100,
                y: 100,
                width: isFinal ? 240 : 140,
                height: isFinal ? 80 : 48,
                color: type === 'score' ? '#19aa19' : (isFinal ? '#4facfe' : '#0ea5e9'),
                status: 'pending'
            });
            state.selectedId = id;
            renderWorkspace();
        }

        async function finalizeAndDownload() {
            if (!elements.image.src || state.annotations.length === 0) return;
            
            elements.loading.style.display = 'flex';
            try {
                const response = await fetch('/api/review/finalize', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        image: elements.image.src,
                        settings: {
                            annotations: state.annotations
                        }
                    })
                });

                if (response.ok) {
                    const blob = await response.blob();
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = 'gradeo_review_final.png';
                    a.click();
                } else {
                    const err = await response.json();
                    alert('Rendering failed: ' + err.error);
                }
            } catch (err) {
                alert('Export failed: ' + err.message);
            } finally {
                elements.loading.style.display = 'none';
            }
        }

        function exportJSON() {
            const data = JSON.stringify(state.annotations, null, 2);
            const blob = new Blob([data], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'gradeo_review_state.json';
            a.click();
        }
    </script>
</body>
</html>
'''

@review_bp.route('/review')
def review_page():
    return render_template_string(REVIEW_HTML)

@review_bp.route('/api/review/finalize', methods=['POST'])
def finalize_review():
    """Pixel-perfect high-fidelity rendering of the teacher's refined annotations."""
    from PIL import Image, ImageDraw, ImageFont
    import re
    
    try:
        data = request.get_json()
        image_data = data.get('image', '')
        settings = data.get('settings', {})
        annotations = settings.get('annotations', [])
        
        if ',' in image_data:
            image_data = image_data.split(',')[1]
        image_bytes = base64.b64decode(image_data)
        
        image = Image.open(io.BytesIO(image_bytes))
        if image.mode != 'RGBA':
            image = image.convert('RGBA')
        
        draw = ImageDraw.Draw(image)
        width, height = image.size
        
        def get_font(size, weight='regular'):
            # Professional fonts - falling back to system defaults
            paths = {
                'bold': ["C:/Windows/Fonts/segoeuib.ttf", "C:/Windows/Fonts/arialbd.ttf"],
                'regular': ["C:/Windows/Fonts/seguisb.ttf", "C:/Windows/Fonts/arial.ttf"]
            }
            target_list = paths.get(weight, paths['regular'])
            for path in target_list:
                try: return ImageFont.truetype(path, int(size))
                except: continue
            return ImageFont.load_default()

        # Premium Rendering Primitives
        def draw_pill(d, box, fill, radius=6):
            x1, y1, x2, y2 = box
            d.rectangle([x1+radius, y1, x2-radius, y2], fill=fill)
            d.rectangle([x1, y1+radius, x2, y2-radius], fill=fill)
            for cx, cy in [(x1+radius, y1+radius), (x2-radius, y1+radius), (x1+radius, y2-radius), (x2-radius, y2-radius)]:
                d.ellipse([cx-radius, cy-radius, cx+radius, cy+radius], fill=fill)

        def draw_geometric_check(d, x, y, size, color):
            # Circular backing
            r = size // 2
            cx, cy = x + r, y + r
            d.ellipse([cx-r, cy-r, cx+r, cy+r], fill=(255,255,255,240))
            # The checkmark shape
            lw = max(2, size // 8)
            d.line([(x + size*0.25, y + size*0.5), (x + size*0.45, y + size*0.75)], fill=color, width=lw)
            d.line([(x + size*0.45, y + size*0.75), (x + size*0.8, y + size*0.25)], fill=color, width=lw)

        def draw_geometric_x(d, x, y, size, color):
            # Circular backing
            r = size // 2
            cx, cy = x + r, y + r
            d.ellipse([cx-r, cy-r, cx+r, cy+r], fill=(255,255,255,240))
            # The X shape
            lw = max(2, size // 8)
            p = size * 0.3
            d.line([(x+p, y+p), (x+size-p, y+size-p)], fill=color, width=lw)
            d.line([(x+size-p, y+p), (x+p, y+size-p)], fill=color, width=lw)

        for ann in annotations:
            x, y = int(ann['x']), int(ann['y'])
            w, h = int(ann.get('width', 120)), int(ann.get('height', 40))
            text = str(ann.get('text', ''))
            color_hex = ann.get('color', '#19aa19')
            opacity = float(ann.get('opacity', 1.0))
            
            # Parse RGBA
            try: 
                rgb = tuple(int(color_hex.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
                color = rgb + (int(255 * opacity),)
            except: 
                color = (25, 140, 25, int(255 * opacity))

            if ann['type'] in ['check', 'x', 'partial', 'mark']:
                # Draw the circular icon
                icon_size = int(h * 0.9)
                icon_x, icon_y = x, y + (h - icon_size)//2
                
                symbol = text.split(' ')[0] if ' ' in text else text
                if symbol == '✓' or ann['type'] == 'check':
                    draw_geometric_check(draw, icon_x, icon_y, icon_size, color)
                else:
                    draw_geometric_x(draw, icon_x, icon_y, icon_size, color)
                
                # Draw score text in a sharper, wider box
                score_match = re.search(r'(\d+\/\d+)', text)
                if score_match:
                    score_text = score_match.group(1)
                    s_font = get_font(h * 0.5, 'bold')
                    tw = draw.textlength(score_text, font=s_font)
                    label_w = max(60, int(tw + 24))
                    tx = x + icon_size + 12
                    ty = y + (h - int(h*0.5)) // 2 - 2
                    
                    # Score label background (White, high contrast)
                    draw_pill(draw, [tx-2, y+2, tx+label_w, y+h-2], (255,255,255,int(255 * opacity)), radius=4)
                    draw.text((tx + (label_w - tw)//2, ty), score_text, fill=color, font=s_font)
            elif ann['type'] == 'final_score':
                # Premium Final Score Design
                font = get_font(h * 0.5, 'bold')
                tw = draw.textlength(text, font=font)
                target_w = max(w, int(tw + 50))
                # Black background with accent border
                draw_pill(draw, [x, y, x + target_w, y + h], (0, 0, 0, int(255 * opacity)), radius=8)
                # Drawing a pseudo-border
                draw.rectangle([x+1, y+1, x+target_w-1, y+h-1], outline=color, width=3)
                draw.text((x + (target_w-tw)//2, y + (h-int(h*0.5))//2 - 2), text, fill=color, font=font)
            else:
                # Professional label (feedback, etc) - Sharper edges
                font = get_font(h * 0.45, 'bold')
                tw = draw.textlength(text, font=font)
                target_w = max(w, int(tw + 32))
                label_color = color[:3] + (int(240 * opacity),)
                draw_pill(draw, [x, y, x + target_w, y + h], label_color, radius=6)
                draw.text((x + 16, y + (h-int(h*0.45))//2 - 2), text, fill=(255,255,255,int(255 * opacity)), font=font)

        output = io.BytesIO()
        image.convert('RGB').save(output, format='PNG')
        output.seek(0)
        return send_file(output, mimetype='image/png')
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@review_bp.route('/api/review/detect', methods=['POST'])
def detect_existing():
    """Integrated detection for existing annotations in the review workflow."""
    from app.services import annotation_service
    try:
        data = request.get_json()
        image_data = data.get('image', '')
        if ',' in image_data: image_data = image_data.split(',')[1]
        image_bytes = base64.b64decode(image_data)
        
        # Check embedded first
        image = Image.open(io.BytesIO(image_bytes))
        if hasattr(image, 'info') and 'gradeo_annotations' in image.info:
            return jsonify(json.loads(image.info['gradeo_annotations']))
            
        # Fallback to AI
        return jsonify(annotation_service.detect_existing_annotations(image_bytes))
    except Exception as e:
        return jsonify({'error': str(e)}), 500
