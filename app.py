import os
import time
import re
from flask import Flask, render_template_string, request, abort
from logic import BooleanSearch

app = Flask(__name__)

# Inicializace vyhledávacího systému
try:
    searcher = BooleanSearch('index.json')
    print("STATUS: SYSTEM ONLINE")
except Exception as e:
    print(f"ERROR: {e}")

# --- ŠABLONA PRO DETAIL DOKUMENTU SE ZVÝRAZNĚNÍM ---
DOCUMENT_VIEW_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>DOC_VIEW // {{ doc_id }}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { background-color: #f3f3f3; color: #000; font-family: ui-monospace, monospace; }
        .container-box { border: 2px solid #000; background: #fff; padding: 40px; box-shadow: 8px 8px 0px #000; }
        mark { background: #ff0000; color: #fff; font-weight: bold; padding: 0 2px; }
        .back-link { border: 1px solid #000; padding: 4px 12px; font-weight: bold; text-decoration: none; color: #000; font-size: 12px; }
        .back-link:hover { background: #000; color: #fff; }
    </style>
</head>
<body class="p-12">
    <div class="max-w-4xl mx-auto">
        <a href="javascript:history.back()" class="back-link uppercase"><- Return to results</a>
        <div class="mt-12 container-box">
            <div class="mb-4 text-xs font-bold uppercase tracking-widest text-red-600">// Document Content</div>
            <h1 class="text-4xl font-black uppercase mb-8 tracking-tighter">{{ doc_id }}</h1>
            <pre class="whitespace-pre-wrap text-sm leading-relaxed border-t border-black pt-8">{{ content|safe }}</pre>
        </div>
    </div>
</body>
</html>
"""

# --- HLAVNÍ ŠABLONA (BRUTALIST STYLE WITH HOVER HELP) ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>STACK SEARCH // ENGINE</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;900&display=swap');
        body { background-color: #f3f3f3; color: #000; font-family: 'Inter', sans-serif; }
        .brutalist-shadow { box-shadow: 4px 4px 0px #000; }
        .brutalist-border { border: 2px solid #000; }
        .search-input { border: 2px solid #000; padding: 12px 16px; width: 100%; font-family: monospace; border-bottom: none; }
        
        .p-slider-container { 
            border: 2px solid #000; 
            background: #fff; 
            padding: 10px 16px; 
            display: flex; 
            align-items: center; 
            gap: 12px; 
            font-size: 11px; 
            font-weight: 900; 
            position: relative;
        }

        /* Hover nápověda */
        .help-wrapper { position: relative; display: flex; align-items: center; }
        
        .help-dot {
            width: 18px; height: 18px; border: 1.5px solid #000; border-radius: 50%;
            display: flex; align-items: center; justify-content: center;
            font-size: 10px; cursor: help; transition: all 0.2s; background: #fff;
        }

        .info-box { 
            position: absolute; top: 30px; right: 0; z-index: 50;
            background: #fff; border: 2px solid #000; padding: 15px; 
            font-size: 11px; width: 280px; line-height: 1.4;
            display: none; /* Skryto v základu */
        }

        /* Zobrazení při hoveru na wrapper */
        .help-wrapper:hover .info-box { display: block; }
        .help-wrapper:hover .help-dot { background: #000; color: #fff; }

        .result-table { width: 100%; border-collapse: collapse; background: #fff; border: 2px solid #000; }
        .result-table th { background: #000; color: #fff; text-align: left; padding: 8px 16px; font-size: 10px; text-transform: uppercase; }
        .result-table td { padding: 12px 16px; border-bottom: 1px solid #000; }
        
        .tag-red { color: #ff0000; font-weight: 900; font-size: 9px; border: 1px solid #ff0000; padding: 1px 4px; text-transform: uppercase; }
        .btn-open { border: 1px solid #000; padding: 4px 8px; font-size: 10px; font-weight: 900; text-transform: uppercase; transition: 0.2s; }
        .btn-open:hover { background: #000; color: #fff; }
        input[type=range] { accent-color: #ff0000; cursor: pointer; flex-grow: 1; }
    </style>
</head>
<body class="p-8 md:p-16">

    <div class="max-w-6xl mx-auto">
        <div class="flex flex-col md:flex-row justify-between items-start gap-8 mb-20">
            <div class="text-left">
                <h1 class="text-7xl font-black leading-[0.8] tracking-tighter uppercase mb-4 italic">
                    STACK<br><span class="text-red-600">SEARCH</span>
                </h1>
                
                <div class="mb-8 p-4 bg-white brutalist-border brutalist-shadow max-w-md">
                    <span class="text-red-600 font-black text-[10px] uppercase tracking-widest">// Quick Guide</span>
                    <p class="text-[11px] mt-2 font-bold leading-tight uppercase">
                        Supports: <span class="bg-gray-200 px-1">AND</span>, <span class="bg-gray-200 px-1">OR</span>, <span class="bg-gray-200 px-1">NOT</span> and <span class="bg-gray-200 px-1">( )</span>. <br>
                        <span class="text-gray-400 italic font-normal mt-1 block">Example: "(python OR java) AND aws"</span>
                    </p>
                </div>

                <div class="mt-8 max-w-md brutalist-shadow">
                    <form method="get" id="searchForm">
                        <input type="text" name="q" class="search-input" placeholder="> Search database..." value="{{ query }}">
                        <div class="p-slider-container">
                             <span class="whitespace-nowrap uppercase tracking-tighter">Norm (p):</span>
                             <input type="range" name="p" min="1" max="10" step="0.5" value="{{ p_val }}" oninput="updateP(this.value)">
                             <output id="p_out" class="text-red-600 min-w-[20px]">{{ p_val }}</output>
                             
                             <div class="help-wrapper">
                                 <div class="help-dot">?</div>
                                 <div class="info-box brutalist-shadow">
                                     <div class="text-red-600 font-black mb-2 uppercase tracking-widest">// Mathematical Norm Influence</div>
                                     <ul class="space-y-2 font-bold uppercase text-[10px]">
                                         <li><span class="text-red-600">p = 1.0</span> &rarr; Soft logic (Average). High recall, accepts partial matches.</li>
                                         <li><span class="text-red-600">p = 2.0</span> &rarr; Euclidean distance. Balanced retrieval.</li>
                                         <li><span class="text-red-600">p > 5.0</span> &rarr; Strict Boolean. High precision, requires all terms to be present.</li>
                                     </ul>
                                 </div>
                             </div>

                             <button type="submit" class="ml-2 bg-black text-white px-4 py-1 text-[10px] uppercase font-black hover:bg-red-600 transition-colors">Query</button>
                        </div>
                    </form>
                </div>
            </div>

            <div class="bg-white brutalist-border p-4 brutalist-shadow w-[220px]">
                <div class="text-[10px] font-black bg-black text-white px-2 py-1 mb-3">SYSTEM_STATUS</div>
                <table class="w-full text-[11px] font-bold">
                    <tr class="border-b"><td>DOCUMENTS</td><td class="text-right">5000</td></tr>
                    <tr class="border-b"><td>ALGORITHM</td><td class="text-right italic">p-NORM</td></tr>
                    <tr class="border-b"><td>WEIGHTS</td><td class="text-right">TF-IDF</td></tr>
                    <tr><td>STATUS</td><td class="text-right text-green-600 font-black italic">UP TO DATE</td></tr>
                </table>
            </div>
        </div>

        <div class="mb-4 text-left">
            <span class="text-xs font-bold text-red-600 tracking-widest uppercase">// Results</span>
            {% if results %}
                <span class="float-right text-[10px] font-bold text-gray-400 uppercase">Total: {{ results|length }} | Latency: {{ search_time }}s</span>
            {% endif %}
        </div>

        {% if results %}
            <table class="result-table brutalist-shadow">
                <thead>
                    <tr>
                        <th width="60%">Filename / Document</th>
                        <th width="20%">Rel. Score</th>
                        <th width="20%">Action</th>
                    </tr>
                </thead>
                <tbody>
                    {% for doc_id, score in results %}
                    <tr>
                        <td class="text-left italic">
                            <div class="flex items-center gap-3">
                                <span class="tag-red">DOC</span>
                                <span class="font-bold text-sm tracking-tight">{{ doc_id }}</span>
                            </div>
                        </td>
                        <td class="text-left font-black text-sm">{{ (score * 100)|round(1) }} %</td>
                        <td class="text-left">
                            <a href="/document/{{ doc_id }}?q={{ query }}" class="btn-open">View Source</a>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        {% elif query %}
            <div class="bg-white brutalist-border p-12 brutalist-shadow text-center">
                <div class="text-2xl font-black uppercase italic">Zero Matches</div>
                <p class="text-xs font-bold text-gray-500 mt-2">No records found for query: "{{ query }}"</p>
            </div>
        {% else %}
            <div class="py-20 text-center border-2 border-dashed border-gray-400">
                <p class="text-xs font-black text-gray-400 uppercase tracking-[0.3em]">Engine ready to index 5,000 documents</p>
            </div>
        {% endif %}

        <div class="mt-32 pt-4 border-t-2 border-black flex justify-between items-center text-[9px] font-black uppercase tracking-widest">
            <div>Stack Search Engine v1.1.0 </div>
            <div>BI-VWM // FIT CTU // 2026</div>
        </div>
    </div>

    <script>
        function updateP(val) {
            document.getElementById('p_out').value = parseFloat(val).toFixed(1);
        }
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    query = request.args.get('q', '')
    p_val = request.args.get('p', 2.0, type=float)
    results = []
    search_time = 0
    if query:
        start = time.perf_counter()
        results = searcher.search(query, p=p_val)
        search_time = round(time.perf_counter() - start, 4)
    return render_template_string(HTML_TEMPLATE, results=results, query=query, search_time=search_time, p_val=p_val)

@app.route('/document/<doc_id>')
def view_document(doc_id):
    query = request.args.get('q', '')
    doc_path = os.path.join('documents', doc_id)
    if not os.path.exists(doc_path):
        abort(404)
    try:
        with open(doc_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Zvýraznění slov z dotazu
        if query:
            words = re.findall(r'[a-zA-Z#+.-]+', query)
            for word in words:
                if word.upper() not in ['AND', 'OR', 'NOT']:
                    pattern = re.compile(re.escape(word), re.IGNORECASE)
                    content = pattern.sub(f'<mark>{word}</mark>', content)

        return render_template_string(DOCUMENT_VIEW_TEMPLATE, content=content, doc_id=doc_id)
    except Exception as e:
        return f"SYSTEM_ERROR: {e}", 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)