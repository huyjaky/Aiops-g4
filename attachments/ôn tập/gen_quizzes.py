import json

def generate_html(title, file_name, questions):
    html = f"""<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-color: #0f172a;
            --glass-bg: rgba(30, 41, 59, 0.7);
            --glass-border: rgba(255, 255, 255, 0.1);
            --primary: #3b82f6;
            --primary-hover: #2563eb;
            --accent: #8b5cf6;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --success: #10b981;
            --danger: #ef4444;
        }}
        
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        
        body {{
            font-family: 'Outfit', sans-serif;
            background: var(--bg-color);
            background-image: 
                radial-gradient(at 0% 0%, rgba(59, 130, 246, 0.15) 0px, transparent 50%),
                radial-gradient(at 100% 100%, rgba(139, 92, 246, 0.15) 0px, transparent 50%);
            color: var(--text-main);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 2rem;
            background-attachment: fixed;
        }}

        .container {{
            background: var(--glass-bg);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border: 1px solid var(--glass-border);
            border-radius: 24px;
            padding: 3rem;
            width: 100%;
            max-width: 800px;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
            position: relative;
            overflow: hidden;
            transition: all 0.4s ease;
        }}

        .header {{
            text-align: center;
            margin-bottom: 2.5rem;
        }}

        h1 {{
            font-size: 2.5rem;
            font-weight: 800;
            background: linear-gradient(to right, #60a5fa, #a78bfa);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 1rem;
        }}

        .progress-container {{
            width: 100%;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 99px;
            height: 8px;
            margin-bottom: 2rem;
            overflow: hidden;
        }}

        .progress-bar {{
            height: 100%;
            background: linear-gradient(to right, var(--primary), var(--accent));
            width: 0%;
            transition: width 0.5s cubic-bezier(0.4, 0, 0.2, 1);
            border-radius: 99px;
        }}

        .question-meta {{
            display: flex;
            justify-content: space-between;
            color: var(--text-muted);
            font-size: 0.9rem;
            margin-bottom: 1rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}

        .difficulty-badge {{
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.8rem;
            font-weight: 800;
        }}

        .diff-easy {{ background: rgba(16, 185, 129, 0.2); color: #34d399; }}
        .diff-medium {{ background: rgba(245, 158, 11, 0.2); color: #fbbf24; }}
        .diff-hard {{ background: rgba(239, 68, 68, 0.2); color: #f87171; }}

        .question-text {{
            font-size: 1.5rem;
            line-height: 1.4;
            margin-bottom: 2rem;
            font-weight: 600;
        }}

        .options-grid {{
            display: grid;
            gap: 1rem;
        }}

        .option-btn {{
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.1);
            color: var(--text-main);
            padding: 1.2rem 1.5rem;
            border-radius: 16px;
            font-size: 1.1rem;
            font-family: inherit;
            cursor: pointer;
            text-align: left;
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
        }}

        .option-btn::before {{
            content: '';
            display: inline-block;
            width: 24px;
            height: 24px;
            border-radius: 50%;
            border: 2px solid rgba(255, 255, 255, 0.2);
            margin-right: 15px;
            flex-shrink: 0;
            transition: all 0.2s;
        }}

        .option-btn:hover:not(:disabled) {{
            background: rgba(255, 255, 255, 0.08);
            transform: translateY(-2px);
            border-color: var(--primary);
        }}

        .option-btn.selected {{
            background: rgba(59, 130, 246, 0.15);
            border-color: var(--primary);
        }}
        
        .option-btn.selected::before {{
            border-color: var(--primary);
            background: var(--primary);
            box-shadow: inset 0 0 0 4px var(--bg-color);
        }}

        .option-btn.correct {{
            background: rgba(16, 185, 129, 0.15) !important;
            border-color: var(--success) !important;
        }}

        .option-btn.correct::before {{
            background: var(--success) !important;
            border-color: var(--success) !important;
            box-shadow: inset 0 0 0 4px var(--bg-color) !important;
        }}

        .option-btn.wrong {{
            background: rgba(239, 68, 68, 0.15) !important;
            border-color: var(--danger) !important;
        }}

        .option-btn.wrong::before {{
            background: var(--danger) !important;
            border-color: var(--danger) !important;
            box-shadow: inset 0 0 0 4px var(--bg-color) !important;
        }}

        .controls {{
            margin-top: 2.5rem;
            display: flex;
            justify-content: flex-end;
        }}

        .next-btn {{
            background: linear-gradient(to right, var(--primary), var(--accent));
            color: white;
            border: none;
            padding: 1rem 2.5rem;
            border-radius: 99px;
            font-size: 1.1rem;
            font-weight: 600;
            cursor: pointer;
            font-family: inherit;
            transition: all 0.3s ease;
            opacity: 0;
            transform: translateY(10px);
            pointer-events: none;
        }}

        .next-btn.visible {{
            opacity: 1;
            transform: translateY(0);
            pointer-events: auto;
        }}

        .next-btn:hover {{
            box-shadow: 0 10px 25px -5px rgba(59, 130, 246, 0.5);
            transform: translateY(-2px);
        }}

        .result-screen {{
            text-align: center;
            display: none;
        }}

        .score-circle {{
            width: 200px;
            height: 200px;
            border-radius: 50%;
            background: conic-gradient(var(--primary) calc(var(--score-pct) * 1%), rgba(255,255,255,0.05) 0);
            display: flex;
            justify-content: center;
            align-items: center;
            margin: 0 auto 2rem;
            position: relative;
        }}

        .score-circle::after {{
            content: '';
            position: absolute;
            width: 170px;
            height: 170px;
            background: var(--bg-color);
            border-radius: 50%;
        }}

        .score-value {{
            position: relative;
            z-index: 1;
            font-size: 3rem;
            font-weight: 800;
        }}

        @keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(10px); }} to {{ opacity: 1; transform: translateY(0); }} }}
        .animate-fade {{ animation: fadeIn 0.4s ease forwards; }}
    </style>
</head>
<body>

<div class="container" id="app">
    <div id="quiz-screen">
        <div class="header">
            <h1>{title}</h1>
            <p>Trắc nghiệm kiến thức AIOps</p>
        </div>
        
        <div class="progress-container">
            <div class="progress-bar" id="progress"></div>
        </div>

        <div class="question-meta">
            <span id="q-counter">Câu hỏi 1 / 50</span>
            <span id="q-difficulty" class="difficulty-badge diff-easy">Mức độ: Dễ</span>
        </div>

        <div class="question-text" id="q-text">Đang tải câu hỏi...</div>

        <div class="options-grid" id="options"></div>

        <div class="controls">
            <button class="next-btn" id="next-btn">Tiếp theo →</button>
        </div>
    </div>

    <div class="result-screen" id="result-screen">
        <h1>Hoàn Thành!</h1>
        <p style="margin-bottom: 2rem; color: var(--text-muted); font-size: 1.2rem;">Kết quả phân tích AIOps của bạn</p>
        
        <div class="score-circle" id="score-circle" style="--score-pct: 0;">
            <div class="score-value" id="score-text">0%</div>
        </div>
        
        <div style="font-size: 1.5rem; margin-bottom: 2rem;">
            Đúng <span id="correct-count" style="color: var(--success); font-weight: bold;">0</span> / <span id="total-count">50</span> câu
        </div>

        <button class="next-btn visible" onclick="location.reload()">Thử lại</button>
    </div>
</div>

<script>
const questions = {json.dumps(questions, ensure_ascii=False)};

let currentQ = 0;
let score = 0;
let answered = false;

const qText = document.getElementById('q-text');
const optionsDiv = document.getElementById('options');
const nextBtn = document.getElementById('next-btn');
const progress = document.getElementById('progress');
const qCounter = document.getElementById('q-counter');
const qDiff = document.getElementById('q-difficulty');

function loadQuestion() {{
    answered = false;
    nextBtn.classList.remove('visible');
    
    const q = questions[currentQ];
    qText.textContent = q.question;
    
    // Update Meta
    qCounter.textContent = `Câu hỏi ${{currentQ + 1}} / ${{questions.length}}`;
    progress.style.width = `${{(currentQ / questions.length) * 100}}%`;
    
    let diffClass = "diff-easy";
    let diffText = "Mức độ: Dễ";
    if (q.difficulty === "medium") {{ diffClass = "diff-medium"; diffText = "Mức độ: Trung Bình"; }}
    if (q.difficulty === "hard") {{ diffClass = "diff-hard"; diffText = "Mức độ: Khó"; }}
    
    qDiff.className = `difficulty-badge ${{diffClass}}`;
    qDiff.textContent = diffText;

    optionsDiv.innerHTML = '';
    
    q.options.forEach((opt, idx) => {{
        const btn = document.createElement('button');
        btn.className = 'option-btn animate-fade';
        btn.style.animationDelay = `${{idx * 0.1}}s`;
        btn.textContent = opt;
        btn.onclick = () => selectOption(idx, btn);
        optionsDiv.appendChild(btn);
    }});
}}

function selectOption(idx, btnElement) {{
    if (answered) return;
    answered = true;
    
    const q = questions[currentQ];
    const btns = optionsDiv.querySelectorAll('.option-btn');
    
    btns.forEach(b => b.disabled = true);
    
    if (idx === q.answer) {{
        btnElement.classList.add('correct');
        score++;
    }} else {{
        btnElement.classList.add('wrong');
        btns[q.answer].classList.add('correct');
    }}
    
    nextBtn.classList.add('visible');
}}

nextBtn.onclick = () => {{
    currentQ++;
    if (currentQ < questions.length) {{
        loadQuestion();
    }} else {{
        showResult();
    }}
}};

function showResult() {{
    document.getElementById('quiz-screen').style.display = 'none';
    const resScreen = document.getElementById('result-screen');
    resScreen.style.display = 'block';
    resScreen.classList.add('animate-fade');
    
    const pct = Math.round((score / questions.length) * 100);
    document.getElementById('score-circle').style.setProperty('--score-pct', pct);
    document.getElementById('score-text').textContent = `${{pct}}%`;
    document.getElementById('correct-count').textContent = score;
    document.getElementById('total-count').textContent = questions.length;
}}

// Start
loadQuestion();
</script>
</body>
</html>"""
    with open(file_name, 'w', encoding='utf-8') as f:
        f.write(html)
