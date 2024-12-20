from flask import Flask, render_template, request, redirect, url_for, send_from_directory, abort, jsonify
from werkzeug.utils import secure_filename
import os
import PyPDF2
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.probability import FreqDist
import string
import docx
import requests
from bs4 import BeautifulSoup
import re
import logging
from logging.handlers import RotatingFileHandler

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
handler = RotatingFileHandler('app.log', maxBytes=10000, backupCount=1)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# Download necessary NLTK data
nltk.download('punkt', quiet=True)
nltk.download('stopwords', quiet=True)
nltk.download('averaged_perceptron_tagger', quiet=True)
nltk.download('maxent_ne_chunker', quiet=True)
nltk.download('words', quiet=True)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads/'
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'docx', 'txt'}
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max file size

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def extract_text(file_path):
    _, ext = os.path.splitext(file_path)
    if ext == '.pdf':
        return extract_text_from_pdf(file_path)
    elif ext == '.docx':
        return extract_text_from_docx(file_path)
    elif ext == '.txt':
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    else:
        return "Error: Unsupported file type."

def extract_text_from_pdf(file_path):
    with open(file_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
    return text

def extract_text_from_docx(file_path):
    doc = docx.Document(file_path)
    return " ".join([para.text for para in doc.paragraphs])

def simplify_text(text):
    text = text.translate(str.maketrans('', '', string.punctuation)).lower()
    stop_words = set(stopwords.words('english'))
    words = [word for word in text.split() if word not in stop_words]
    return ' '.join(words)

def generate_summary(text, num_sentences=3):
    simplified_text = simplify_text(text)
    sentences = sent_tokenize(text)
    words = word_tokenize(simplified_text)
    
    freq_dist = FreqDist(words)
    sentence_scores = {}
    
    for sentence in sentences:
        for word in word_tokenize(simplify_text(sentence)):
            if word in freq_dist:
                if sentence not in sentence_scores:
                    sentence_scores[sentence] = freq_dist[word]
                else:
                    sentence_scores[sentence] += freq_dist[word]
    
    summary_sentences = sorted(sentence_scores, key=sentence_scores.get, reverse=True)[:num_sentences]
    
    simple_summary = "Key points:\n\n"
    for i, sentence in enumerate(summary_sentences, 1):
        simple_summary += f"{i}. {sentence}\n"
    
    return simple_summary

def extract_entities(text):
    words = word_tokenize(text)
    tagged = nltk.pos_tag(words)
    entities = nltk.chunk.ne_chunk(tagged)
    
    person_names = []
    organizations = []
    locations = []
    
    for entity in entities:
        if isinstance(entity, nltk.Tree):
            if entity.label() == 'PERSON':
                person_names.append(' '.join([leaf[0] for leaf in entity.leaves()]))
            elif entity.label() == 'ORGANIZATION':
                organizations.append(' '.join([leaf[0] for leaf in entity.leaves()]))
            elif entity.label() == 'GPE':  # GeoPolitical Entity
                locations.append(' '.join([leaf[0] for leaf in entity.leaves()]))
    
    return {
        'people': list(set(person_names))[:5],
        'organizations': list(set(organizations))[:5],
        'locations': list(set(locations))[:5]
    }

def count_words(text):
    words = word_tokenize(text)
    return len(words)

def search_and_analyze(query):
    search_url = f"https://www.google.com/search?q={query}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    
    response = requests.get(search_url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    search_results = []
    for g in soup.find_all('div', class_='g'):
        anchor = g.find('a')
        if anchor:
            link = anchor['href']
            title = g.find('h3', class_='r')
            snippet = g.find('div', class_='s')
            if title and snippet:
                search_results.append({
                    'title': title.text,
                    'link': link,
                    'snippet': snippet.text
                })
    
    if not search_results:
        return {
            'summary': f"No results found for the query: '{query}'. This could be due to very specific or unusual search terms, or temporary issues with the search service. You may want to try rephrasing your question or breaking it down into smaller, more general parts.",
            'entities': {'people': [], 'organizations': [], 'locations': []},
            'results': []
        }
    
    combined_text = " ".join([result['snippet'] for result in search_results])
    summary = generate_summary(combined_text, num_sentences=5)
    entities = extract_entities(combined_text)
    
    return {
        'summary': summary,
        'entities': entities,
        'results': search_results[:3]  # Return top 3 search results
    }

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        logger.debug("POST request received at /")
        if 'files[]' not in request.files:
            logger.warning("No file part in the request")
            return jsonify({"error": "No file part"}), 400
        files = request.files.getlist('files[]')
        if not files or files[0].filename == '':
            logger.warning("No file selected")
            return jsonify({"error": "No file selected"}), 400
        if all(file and allowed_file(file.filename) for file in files):
            filenames = []
            for file in files:
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                filenames.append(filename)
            logger.info(f"Files uploaded: {filenames}")
            return jsonify({"message": "Files uploaded successfully", "filenames": filenames}), 200
        else:
            logger.warning("Invalid file type uploaded")
            return jsonify({"error": "Invalid file type"}), 400
    return render_template('upload.html')

@app.route('/analyze', methods=['POST'])
def analyze_files():
    data = request.json
    if not data or 'filenames' not in data:
        return jsonify({"error": "No filenames provided"}), 400
    
    filenames = data['filenames']
    logger.debug(f"Analyze request received for files: {filenames}")
    
    all_text = ""
    total_words = 0
    file_info = []

    for filename in filenames:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        logger.debug(f"Checking file path: {file_path}")
        if os.path.exists(file_path):
            logger.info(f"Processing file: {filename}")
            try:
                text = extract_text(file_path)
                all_text += text
                word_count = count_words(text)
                total_words += word_count
                file_info.append({'name': filename, 'word_count': word_count})
            except Exception as e:
                logger.error(f"Error processing file {filename}: {str(e)}")
                return jsonify({"error": f"Error processing file {filename}: {str(e)}"}), 500
        else:
            logger.error(f"File not found: {filename}")
            return jsonify({"error": f"File not found: {filename}"}), 404

    try:
        summary = generate_summary(all_text)
        entities = extract_entities(all_text)
    except Exception as e:
        logger.error(f"Error generating summary or extracting entities: {str(e)}")
        return jsonify({"error": "Error analyzing files. Please try again."}), 500

    return jsonify({
        "summary": summary,
        "entities": entities,
        "file_info": file_info,
        "total_words": total_words
    }), 200

@app.route('/ask_question', methods=['POST'])
def ask_question():
    data = request.json
    if not data or 'filenames' not in data or 'question' not in data or 'weight' not in data:
        return jsonify({"error": "Invalid request data"}), 400

    filenames = data['filenames']
    question = data['question']
    weight = data['weight']

    logger.debug(f"Question asked: {question}")
    logger.debug(f"Files to analyze: {filenames}")

    all_text = ""
    for filename in filenames:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(file_path):
            all_text += extract_text(file_path)
        else:
            logger.error(f"File not found: {filename}")
            return jsonify({"error": f"File not found: {filename}"}), 404

    summary = generate_summary(all_text)
    entities = extract_entities(all_text)

    if weight == 'summary':
        response = f"Based on the summary, here's a possible answer to your question:\n\n{summary}\n\nThis information is most relevant to your query: '{question}'"
    elif weight == 'entities':
        entity_info = f"People: {', '.join(entities['people'])}\nOrganizations: {', '.join(entities['organizations'])}\nLocations: {', '.join(entities['locations'])}"
        response = f"Considering the entities mentioned in the documents, here's relevant information for your question:\n\n{entity_info}\n\nThis information might help answer your query: '{question}'"
    else:  # weight == 'context'
        context = ' '.join(sent_tokenize(all_text)[:5])  # Use first 5 sentences as context
        response = f"Taking the broader context into account, here's a possible answer to your question:\n\n{context}\n\nThis context is most relevant to your query: '{question}'"

    web_analysis = search_and_analyze(question)

    return jsonify({
        "summary": summary,
        "entities": entities,
        "file_info": [{'name': filename, 'word_count': count_words(extract_text(os.path.join(app.config['UPLOAD_FOLDER'], filename)))} for filename in filenames],
        "total_words": sum(count_words(extract_text(os.path.join(app.config['UPLOAD_FOLDER'], filename))) for filename in filenames),
        "additional_info": response,
        "web_analysis": web_analysis
    }), 200

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    logger.debug(f"Request for uploaded file: {filename}")
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.errorhandler(404)
def not_found_error(error):
    logger.error(f"404 error: {error}")
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"500 error: {error}")
    return jsonify({"error": "Internal server error"}), 500

@app.route('/test_file/<filename>')
def test_file(filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(file_path):
        return jsonify({"message": f"File {filename} exists and is accessible."}), 200
    else:
        return jsonify({"error": f"File {filename} does not exist or is not accessible."}), 404

if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(host='0.0.0.0', port=5000, debug=True)

logger.info("Enhanced Research Analysis System is ready to run!")

