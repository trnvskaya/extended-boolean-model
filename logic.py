import os
import re
from bs4 import BeautifulSoup
from collections import defaultdict
from nltk.stem import PorterStemmer
from nltk.corpus import stopwords
import time
from functools import wraps
import math
import json



def benchmark(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        duration = end_time - start_time
        print(f'The method {func.__name__} lasted {duration:.3f} seconds')
        return result
    return wrapper


def export_threads(limit=5000):
    q = pd.read_csv('stackDB/Questions.csv', encoding='latin1', nrows=limit)
    a = pd.read_csv('stackDB/Answers.csv', encoding='latin1')
    t = pd.read_csv('stackDB/Tags.csv', encoding='latin1')

    output_dir = 'documents'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for _, q_row in q.iterrows():
        q_id = q_row['Id']
        
        tags = t[t['Id'] == q_id]['Tag'].fillna('').tolist()
        tags_str = " ".join([str(t) for t in tags])
        
        answers = a[a['ParentId'] == q_id]
        answers_text = ""
        for _, a_row in answers.iterrows():
            answers_text += "\n" + BeautifulSoup(str(a_row['Body']), "html.parser").get_text()
        
        q_body = BeautifulSoup(str(q_row['Body']), "html.parser").get_text()
        
        full_content = f"{q_row['Title']}\n{tags_str}\n{q_body}\n{answers_text}"

        with open(f'{output_dir}/{q_id}.txt', 'w', encoding='utf-8') as f:
            f.write(full_content)




class InvertedIndexer:
    def __init__(self, doc_dir):
        self.doc_dir = doc_dir
        self.stemmer = PorterStemmer()
        self.stop_words = set(stopwords.words('english'))
        self.index = defaultdict(dict)
        self.doc_list = []
        self.tech_exceptions = {
            'aws', 'sql', 'php', 'java', 'ruby', 'git', 'css', 'html', 'xml', 'json', 
            'dns', 'ssh', 'ssl', 'ajax', 'orm', 'wcf', 'wpf', 'tdd', 'ssis', 'vba', 
            'bash', 'f#', 'c#', 'c++', '.net', 'ios', 'xcode', 'svn', 'iis', 'maven', 
            'regex', 'asp.net', 'vb.net', 'nhibernate', 'linq', 'tsql', 'plsql', 
            'sqlite', 'postgresql', 'mysql', 'linux', 'unix', 'osx', 'ubuntu', 
            'windows', 'vista', 'azure', 'android', 'vmware', 'hyper-v', 'tcp', 
            'udp', 'dhcp', 'nfs', 'vps', 'smb', 'smtp', 'perl', 'lisp', 'ocaml', 
            'rake', 'msbuild', 'nunit', 'junit', 'rails', 'jquery', 'ec2', 's3', 
            'mongodb', 'redis', 'react', 'node', 'angular', 'docker'
        }

    def preprocess(self, text):
        tokens = re.findall(r'[a-z][a-z0-9#+.-]*', text.lower())
        
        processed_terms = []
        for t in tokens:
            if t in self.stop_words or len(t) <= 1:
                continue

            if t in self.tech_exceptions:
                processed_terms.append(t)
            else:
                processed_terms.append(self.stemmer.stem(t))
                
        return processed_terms
        

    @benchmark
    def build(self):
        self.doc_list = [f for f in os.listdir(self.doc_dir) if f.endswith('.txt')]
        N = len(self.doc_list)
        term_counts = defaultdict(lambda: defaultdict(int))

        # 1. Průchod: Počítání frekvencí
        for doc_name in self.doc_list:
            path = os.path.join(self.doc_dir, doc_name)
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
                terms = self.preprocess(content)
                for t in terms:
                    term_counts[t][doc_name] += 1

        # 2. Průchod: Výpočet syrových TF-IDF vah a nalezení maxima
        max_raw_weight = 0
        for term, docs_with_terms in term_counts.items():
            n_t = len(docs_with_terms)
            idf = math.log10(N / n_t) if n_t > 0 else 0

            for doc_name, count in docs_with_terms.items():
                tf_weight = 1 + math.log10(count)
                weight = tf_weight * idf
                self.index[term][doc_name] = weight
                if weight > max_raw_weight:
                    max_raw_weight = weight

        # 3. Krok: KRITICKÁ NORMALIZACE (Aby váhy byly 0 až 1)
        if max_raw_weight > 0:
            for term in self.index:
                for doc_name in self.index[term]:
                    self.index[term][doc_name] /= max_raw_weight

    def save(self, filename='index.json'):
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.index, f)            


class BooleanSearch:
    def __init__(self, index_path = 'index.json'):
        if not os.path.exists(index_path):
            idx = InvertedIndexer('documents')
            idx.build()
            idx.save()

        with open(index_path, 'r', encoding = 'utf-8') as f:
            self.index = json.load(f)
        self.stemmer = PorterStemmer()
        self.all_docs = set()
        for doc_dict in self.index.values():
            self.all_docs.update(doc_dict.keys())  

    def get_postfix(self, query):
        priority = {'NOT': 3, 'AND': 2, 'OR': 1, '(': 0}
        stack, output = [], []
        
        tokens = re.findall(r'\(|\)|AND|OR|NOT|[a-zA-Z#+]+', query, re.IGNORECASE)
        
        for token in tokens:
            t_upper = token.upper()
            if t_upper == '(': 
                stack.append(token)
            elif t_upper == ')':
                while stack and stack[-1] != '(': 
                    output.append(stack.pop())
                if stack: stack.pop()
            elif t_upper in priority:
                # Priorita operátorů
                while stack and priority.get(stack[-1].upper(), 0) >= priority[t_upper]:
                    output.append(stack.pop())
                stack.append(t_upper)
            else:
                token_lower = token.lower()
                if token_lower in self.index:
                    output.append(token_lower)
                else:
                    output.append(self.stemmer.stem(token_lower))    
        
        while stack: 
            output.append(stack.pop())
        return output
    @benchmark
    def search(self, query, p=2):
        postfix = self.get_postfix(query)
        results = {}

        for doc_id in self.all_docs:
            stack = []
            for token in postfix:
                if token == 'AND':
                    w2 = stack.pop() if stack else 0
                    w1 = stack.pop() if stack else 0
                    if w1 == 0 or w2 == 0:
                        stack.append(0.0)
                    else:
                        base = max(0, ((1-w1)**p + (1-w2)**p) / 2)
                        score = 1 - (base**(1/p))
                        stack.append(score)
                elif token == 'OR':
                    w2 = stack.pop() if stack else 0
                    w1 = stack.pop() if stack else 0
                    base = max(0, (w1**p + w2**p) / 2)
                    score = (base**(1/p))
                    stack.append(score)
                elif token == 'NOT':
                    w1 = stack.pop() if stack else 0
                    stack.append(1 - w1)
                else:
                    val = self.index.get(token, {}).get(doc_id, 0)
                    stack.append(val)
            
            if stack:
                final_relevance = stack.pop()
                if final_relevance > 0.05: 
                    results[doc_id] = round(final_relevance, 4)

        return sorted(results.items(), key=lambda x: x[1], reverse=True)
    

@benchmark
def sequential_search(doc_dir, term):
    results = []

    term_stemmed = PorterStemmer().stem(term.lower())

    for filename in os.listdir(doc_dir):
        if filename.endswith('.txt'):
            with open(os.path.join(doc_dir, filename), 'r', encoding='utf-8') as f:
                if term_stemmed in f.read().lower():
                    results.append(filename)
    return results                


if __name__ == "__main__":
    engine = InvertedIndexer('documents')
    engine.build()
    engine.save()
    
    searcher = BooleanSearch('index.json')
