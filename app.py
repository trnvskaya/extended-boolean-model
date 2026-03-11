import os
import time
import re
import urllib.parse
from flask import Flask, render_template_string, request, abort
from logic import BooleanSearch

app = Flask(__name__)

try:
    searcher = BooleanSearch('index.json')
    print("STATUS: SYSTEM ONLINE")
except Exception as e:
    print(f"ERROR: {e}")

def highlight_keywords(text, query):
    if not query:
        return text
        
    tokens = re.findall(r'[a-zA-Z0-9#+.-]+', query)
    keywords = set([t for t in tokens if t.upper() not in ['AND', 'OR', 'NOT']])
    
    for word in keywords:
        escaped_word = re.escape(word)
        pattern = re.compile(r'(?<!\w)(' + escaped_word + r')(?!\w)', re.IGNORECASE)
        text = pattern.sub(r'<mark>\1</mark>', text)
        
    return text


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
        mark { background: #ff0000; color: #fff; font-weight: bold; padding: 0 4px; border-radius: 2px;}
        .back-link { border: 1px solid #000; padding: 4px 12px; font-weight: bold; text-decoration: none; color: #000; font-size: 12px; }
        .back-link:hover { background: #000; color: #fff; }
    </style>
</head>
<body class="p-12">
    <div class="max-w-4xl mx-auto">
        <a href="javascript:history.back()" class="back-link uppercase"><- Return to results</a>
        <div class="mt-12 container-box">
            <div class="mb-4 text-xs font-bold uppercase tracking-widest text-gray-400">
                // DOCUMENT ID: {{ doc_id }}
            </div>
            <h1 class="text-3xl font-black mb-8 tracking-tight text-red-600 leading-tight">
                {{ title|safe }}
            </h1>
            <pre class="whitespace-pre-wrap text-sm leading-relaxed border-t border-black pt-8 font-sans">{{ content|safe }}</pre>
        </div>
    </div>
</body>
</html>
"""

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
            border: 2px solid #000; background: #fff; padding: 10px 16px; 
            display: flex; align-items: center; gap: 12px; font-size: 11px; 
            font-weight: 900; position: relative;
        }

        .help-wrapper { position: relative; display: flex; align-items: center; }
        .help-dot { width: 18px; height: 18px; border: 1.5px solid #000; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 10px; cursor: help; transition: all 0.2s; background: #fff; }
        .info-box { position: absolute; top: 30px; right: 0; z-index: 50; background: #fff; border: 2px solid #000; padding: 15px; font-size: 11px; width: 280px; line-height: 1.4; display: none; }
        .help-wrapper:hover .info-box { display: block; }
        .help-wrapper:hover .help-dot { background: #000; color: #fff; }

        .result-table { width: 100%; border-collapse: collapse; background: #fff; border: 2px solid #000; }
        .result-table th { background: #000; color: #fff; text-align: left; padding: 8px 16px; font-size: 10px; text-transform: uppercase; }
        .result-table td { padding: 12px 16px; border-bottom: 1px solid #000; }
        
        .tag-red { color: #ff0000; font-weight: 900; font-size: 9px; border: 1px solid #ff0000; padding: 1px 4px; text-transform: uppercase; }
        .btn-open { border: 1px solid #000; padding: 4px 8px; font-size: 10px; font-weight: 900; text-transform: uppercase; transition: 0.2s; white-space: nowrap;}
        .btn-open:hover { background: #000; color: #fff; }
        
        .btn-show-more { border: 2px solid #000; background: #fff; color: #000; font-weight: 900; text-transform: uppercase; padding: 8px 24px; font-size: 12px; cursor: pointer; transition: 0.2s; box-shadow: 4px 4px 0px #000; }
        .btn-show-more:hover { background: #000; color: #fff; box-shadow: 2px 2px 0px #ff0000; transform: translate(2px, 2px); }
        
        input[type=range] { accent-color: #ff0000; cursor: pointer; flex-grow: 1; }
        
        /* CSS třída pro skrytí řádků nad limit */
        .hidden-row { display: none; }
    </style>
</head>
<body class="p-8 md:p-16">

    <div class="max-w-6xl mx-auto">
        <div class="flex flex-col md:flex-row justify-between items-start gap-8 mb-20">
            <div class="text-left w-full">
                <h1 class="text-7xl font-black leading-[0.8] tracking-tighter uppercase mb-4 italic">
                    STACK<br><span class="text-red-600">SEARCH</span>
                </h1>
                
                <div class="mb-8 p-4 bg-white brutalist-border brutalist-shadow max-w-md">
                    <span class="text-red-600 font-black text-[10px] uppercase tracking-widest">// Quick Guide</span>
                    <p class="text-[11px] mt-2 font-bold leading-tight uppercase">
                        Supports: <span class="bg-gray-200 px-1">AND</span>, <span class="bg-gray-200 px-1">OR</span>, <span class="bg-gray-200 px-1">NOT</span> and <span class="bg-gray-200 px-1">( )</span>. <br>
                        <span class="text-gray-400 italic font-normal mt-1 block">Example: "(c++ OR java) AND aws"</span>
                    </p>
                </div>

                <div class="mt-8 max-w-xl brutalist-shadow">
                    <form method="get" action="/" id="searchForm">
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

            <div class="bg-white brutalist-border p-4 brutalist-shadow w-[220px] flex-shrink-0 mt-8 md:mt-0">
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
                <span class="float-right text-[10px] font-bold text-gray-400 uppercase mt-1">Total: {{ results|length }} | Latency: {{ search_time }}s</span>
            {% endif %}
        </div>

        {% if results %}
            <table class="result-table brutalist-shadow" id="resultsTable">
                <thead>
                    <tr>
                        <th width="70%">Document Title</th>
                        <th width="15%">Rel. Score</th>
                        <th width="15%">Action</th>
                    </tr>
                </thead>
                <tbody>
                    {% for item in results %}
                    <tr class="result-row {% if loop.index0 >= 5 %}hidden-row{% endif %}">
                        <td class="text-left">
                            <div class="flex flex-col gap-1">
                                <div class="font-black text-sm tracking-tight text-blue-800">{{ item.title }}</div>
                                <div class="text-[9px] font-bold text-gray-400 uppercase tracking-widest flex items-center gap-2">
                                    <span class="tag-red">DOC</span> {{ item.id }}
                                </div>
                            </div>
                        </td>
                        <td class="text-left font-black text-sm">{{ (item.score * 100)|round(1) }} %</td>
                        <td class="text-left">
                            <a href="/document/{{ item.id }}?q={{ encoded_query }}" class="btn-open">View Source</a>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
            
            {% if results|length > 5 %}
            <div id="showMoreContainer" class="text-center mt-8">
                <button onclick="showMoreResults()" class="btn-show-more">
                    + Show More ({{ results|length - 5 }})
                </button>
            </div>
            {% endif %}

        {% elif query %}
            <div class="bg-white brutalist-border p-12 brutalist-shadow text-center">
                <div class="text-2xl font-black uppercase italic">Zero Matches</div>
                <p class="text-xs font-bold text-gray-500 mt-2">No records found for query: "{{ query }}"</p>
            </div>
        {% else %}
            <div class="py-20 text-center border-2 border-dashed border-gray-400 bg-white opacity-50">
                <p class="text-xs font-black text-gray-400 uppercase tracking-[0.3em]">Engine ready. Enter your query above.</p>
            </div>
        {% endif %}

        <div class="mt-32 pt-4 border-t-2 border-black flex justify-between items-center text-[9px] font-black uppercase tracking-widest">
            <div>Stack Search Engine v1.4.0 </div>
            <div>BI-VWM // FIT CTU // 2026</div>
        </div>
    </div>

    <script>
        // Funkce pro aktualizaci hodnoty p-normy vedle posuvníku
        function updateP(val) {
            document.getElementById('p_out').value = parseFloat(val).toFixed(1);
        }

        // JS funkce pro zobrazení všech skrytých výsledků
        function showMoreResults() {
            // Najde všechny skryté řádky a odstraní jim třídu, která je skrývá
            const hiddenRows = document.querySelectorAll('.hidden-row');
            hiddenRows.forEach(row => {
                row.classList.remove('hidden-row');
            });
            // Skryje samotné tlačítko "Show More", protože už není potřeba
            document.getElementById('showMoreContainer').style.display = 'none';
        }
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    query = request.args.get('q', '')
    p_val = request.args.get('p', 2.0, type=float)
    enriched_results = []
    search_time = 0
    
    encoded_query = urllib.parse.quote(query) if query else ""
    
    if query:
        start = time.perf_counter()
        raw_results = searcher.search(query, p=p_val)
        search_time = round(time.perf_counter() - start, 4)

        for doc_id, score in raw_results[:100]:
            doc_path = os.path.join('documents', doc_id)
            title = "Unknown Title"
            if os.path.exists(doc_path):
                with open(doc_path, 'r', encoding='utf-8') as f:
                    title = f.readline().strip() 
            
            enriched_results.append({
                'id': doc_id, 
                'score': score, 
                'title': title
            })

    return render_template_string(HTML_TEMPLATE, results=enriched_results, query=query, encoded_query=encoded_query, search_time=search_time, p_val=p_val)


@app.route('/document/<doc_id>')
def view_document(doc_id):
    query = request.args.get('q', '')
    doc_path = os.path.join('documents', doc_id)
    
    if not os.path.exists(doc_path):
        abort(404)
        
    try:
        with open(doc_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        title = lines[0].strip() if lines else "Unknown Title"
        content = "".join(lines[1:]) if len(lines) > 1 else ""
        
        if query:
            content = highlight_keywords(content, query)
            title = highlight_keywords(title, query)

        return render_template_string(DOCUMENT_VIEW_TEMPLATE, title=title, content=content, doc_id=doc_id)
        
    except Exception as e:
        return f"SYSTEM_ERROR: {e}", 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)