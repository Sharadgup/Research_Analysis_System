from flask import Flask, render_template, request, redirect, url_for
from werkzeug.utils import secure_filename
import os
import PyPDF2
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.probability import FreqDist
import string
import docx

# Download necessary NLTK data
nltk.download('punkt')
nltk.download('stopwords')
nltk.download('averaged_perceptron_tagger')
nltk.download('maxent_ne_chunker')
nltk.download('words')

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads/'
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'docx', 'txt'}

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
        simple_summary += f"{i}. {' '.join(sentence.split()[:15])}...\n"
    
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

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'files[]' not in request.files:
            return redirect(request.url)
        files = request.files.getlist('files[]')
        if not files or files[0].filename == '':
            return redirect(request.url)
        if all(file and allowed_file(file.filename) for file in files):
            filenames = []
            for file in files:
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                filenames.append(filename)
            return redirect(url_for('analyze_files', filenames=','.join(filenames)))
    return render_template('upload.html')

@app.route('/analyze/<filenames>')
def analyze_files(filenames):
    file_list = filenames.split(',')
    all_text = ""
    total_words = 0
    file_info = []

    for filename in file_list:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        text = extract_text(file_path)
        all_text += text
        word_count = count_words(text)
        total_words += word_count
        file_info.append({'name': filename, 'word_count': word_count})

    summary = generate_summary(all_text)
    entities = extract_entities(all_text)

    return render_template('result.html', 
                           summary=summary, 
                           entities=entities, 
                           file_info=file_info, 
                           total_words=total_words)

if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(debug=True)

print("Enhanced Research Analysis System is ready to run!")

