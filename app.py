from flask import *
import sqlite3
import os
import hashlib
from sim import Calculator

app = Flask(__name__)
cal = Calculator()
PROJECT_ROOT = app.root_path
DATABASE = os.path.join(PROJECT_ROOT, 'projects.db')  # The database file for this project
UPLOAD_FOLDER = os.path.join(PROJECT_ROOT, 'static/images')  # Folder that the images of words is saved in
app.secret_key = "mHrli-#iuP{y):K"  # Hash key


def get_db(query, args=(), fetch_type="all"):
    con = sqlite3.connect(DATABASE)
    cur = con.cursor()
    cur.execute(query, args)
    if fetch_type == "one":
        data = cur.fetchone()
    else:
        data = cur.fetchall()
    con.close()

    return data


def exec_db(query, args=()):
    con = sqlite3.connect(DATABASE)
    cur = con.cursor()
    cur.execute(query, args)
    con.commit()
    con.close()


@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        standard_id = request.form['standard']
        question_id = get_db("""SELECT questions.id FROM questions
                INNER JOIN standards ON questions.standard=standards.id 
                WHERE standards.id=? ORDER BY questions.id""", 
                (standard_id, ), fetch_type="one")[0]
        return redirect(url_for('question', question_id=question_id))
    else:
        subjects = get_db("SELECT * FROM subjects")
        standards = get_db("SELECT * FROM standards")
        return render_template("home.html", subjects=subjects, standards=standards)


@app.route('/question/<question_id>')
def question(question_id):
    question = list(get_db("""SELECT * FROM questions WHERE questions.id=?""", 
                (question_id, ), fetch_type="one"))
    
    session['question'] = question
    return render_template("question.html", question=question)


@app.route('/test', methods=['GET', 'POST'])
def test():
    if request.method == 'POST':
        text = request.form['text']
        answer = session["question"][3]
        db_answers = get_db("SELECT answer FROM questions WHERE id!=? LIMIT 10", (session["question"][0], ))
        list_answers = [item[0] for item in db_answers]
        text_sim = round(cal.cossim(text, answer, list_answers) * 100, 2)

        if "user" in session:
            db_statement = "INSERT INTO queries (user, question, response, score) VALUES (?, ?, ?, ?)"
            exec_db(db_statement, (session['user'], session['question'][0], text, text_sim, ))
        
        response = {
            "success": True, 
            "html": 
                """
                <div class="card">
                    <div class="card-body">
                        <h5>Your Answer</h5>
                        <small>""" + text.replace('\n', '<br>') + "</small>" + 
                """
                        <hr>
                        <h5>Model Answer</h5>
                        <small>""" + answer.replace('\n', '<br>') + "</small>" + 
                """
                        <hr>
                        <h5>Indicative Grade</h5>
                        <b>""" + str(text_sim) + "% | " + convert(text_sim) + "</b><hr>"
                """
                        <div class="row">
                            <div class="col-6"><button type="button" class="btn btn-block btn-warning" onclick="javascript:ResetForm()">Redo</button></div>
                            <div class="col-6"><button type="button" class="btn btn-block btn-primary" onclick="javascript:ChangeForm()">Next Question</button></div>
                        </div>
                    </div>
                </div>
                """
        }
        return response
    else:   
        if 'question' not in session:
            return redirect(url_for('home'))
        
        question = get_db("""SELECT * FROM questions
                INNER JOIN standards ON questions.standard=standards.id 
                WHERE questions.id>? AND standards.id=?
                ORDER BY questions.id LIMIT 1""", 
                (session["question"][0], session["question"][1], ), fetch_type="one")
        
        session["question"] = question
        response = {
            "success": True, 
            "question": question, 
        }

        return response


@app.route('/profile')
def profile():
    queries = get_db("""SELECT questions.standard, subjects.subject, standards.level,
                     standards.name, COUNT(DISTINCT queries.question)
                FROM queries
                INNER JOIN questions ON queries.question=questions.id
                INNER JOIN standards ON questions.standard=standards.id
                INNER JOIN subjects ON standards.subject=subjects.id
                WHERE queries.user=? GROUP BY questions.standard""", 
                (session["user"], ))
    
    return render_template("profile.html", queries=queries)


@app.route('/standard/<standard_id>/<fetch_type>')
def standard(standard_id, fetch_type):
    questions_list = get_db("""SELECT questions.id FROM questions
            WHERE questions.standard=?""", 
            (standard_id, ))

    html = """<ul class="list-group">"""
    for i, question in enumerate(questions_list, start=1):
        if fetch_type == "question":
            html += ("""
                <a href="/question/{}"><li class="list-group-item text-center">
                    Question {}
                </li></a>""".format(question[0], str(i)))
        else:
            num = get_db("""SELECT COUNT(*)
                FROM queries
                WHERE queries.question=? AND queries.user=?""", 
                (question[0], session["user"]), fetch_type="one")[0]
            html += ("""
                <a href="/detail/{}"><li class="list-group-item d-flex justify-content-between align-items-center">
                    Question {}
                    <span class="badge badge-{} badge-pill">{} Response(s)</span>
                </li></a>""".format(question[0], str(i), ("primary" if num > 0 else "warning"), num))
    
    html += """</ul> """

    response = {
        "success": True, 
        "html": html,
    }
    return response
    

@app.route('/detail/<question_id>')
def detail(question_id):
    question = get_db("""SELECT questions.*, standards.number FROM questions
            INNER JOIN standards ON questions.standard=standards.id 
            WHERE questions.id=?""", 
            (question_id, ), fetch_type="one")
    queries = get_db("""SELECT queries.id,
                queries.response, queries.score
                FROM queries
                WHERE queries.question=? AND queries.user=?""", 
                (question_id, session["user"]))
    return render_template("detail.html", queries=queries, question=question)


@app.route('/add/question', methods=['POST', 'GET'])
def add_question():
    if request.method == 'POST':
        standard = int(request.form['standard'])
        question = request.form['question'].strip()
        answer = request.form['answer'].strip()
        source = request.form['source']

        db_statement = "INSERT INTO questions (standard, question, answer, source) VALUES (?, ?, ?, ?)"
        exec_db(db_statement, (standard, question, answer, source))

        question_id = get_db("SELECT id FROM questions ORDER BY ID DESC LIMIT 1", fetch_type="one")[0]

        image = request.files['image']
        if image:
            file_name, file_extension = os.path.splitext(image.filename)
            image_name = "question{}{}".format(question_id, file_extension)
            image.save(os.path.join(UPLOAD_FOLDER, image_name))

            exec_db("UPDATE questions SET image=? WHERE id=?;", (image_name, question_id))

        return "<h3>Your process was successful.</h3>"
    else:
        standards = get_db("""SELECT id, number, name FROM standards ORDER BY number""")
        return render_template("AddQuestion.html", standards=standards)


@app.route('/signup', methods=['POST', 'GET'])
def signup():
    if request.method == 'POST':
        # Below code collects all the information of the user
        firstname = request.form['firstname'].strip().title()
        lastname = request.form['lastname'].strip().title()
        username = request.form['username'].strip()
        email = request.form['email'].strip().lower()
        password = request.form['password']
        print(request.form)

        con = sqlite3.connect(DATABASE)
        cur = con.cursor()

        uerror = False
        eerror = False

        # Check is username is taken
        cur.execute("SELECT id FROM users WHERE username=?", (username,))
        exist_user = cur.fetchone()
        if exist_user is not None:
            uerror = True

        # Check if email is used
        cur.execute("SELECT id FROM users WHERE email=?", (email,))
        exist_email = cur.fetchone()
        if exist_email is not None:
            eerror = True

        if uerror or eerror:
            return render_template("signup.html", uerror=uerror, eerror=eerror)

        query = "INSERT INTO users (firstname, lastname, username, email, password) VALUES (?, ?, ?, ?, ?)"
        # I have used hashlib because it is easier to use and builtin in Python
        hashed_password = hashlib.sha256(password.encode("utf-8")).hexdigest()
        try:
            cur.execute(query, (firstname, lastname, username, email, hashed_password))
            con.commit()
        except:
            return "<h3>Your process was unsuccessful. Please refresh to page and try again</h3>"

        # Find the ID of the new added user and saves it into session
        cur.execute("SELECT id FROM users WHERE username=?", (username,))
        user = cur.fetchone()
        session['user'] = user[0]
        con.close()

        return redirect(url_for('home'))

    else:
        return render_template("signup.html")


@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == "POST":
        username = request.form['username'].strip()
        password = request.form['password']
        print(request.form)
        query = "SELECT id, password FROM users WHERE username=?"
        user = get_db(query, (username, ), "one")

        if user is None:  # Check if the username is correct
            return render_template("login.html", uerror=True)
        elif hashlib.sha256(password.encode("utf-8")).hexdigest() != user[1]:  # Check if the password is correct
            return render_template("login.html", perror=True)

        # Saves the ID and the role to the session
        session['user'] = user[0]

        return redirect(url_for('home'))
    
    else:
        return render_template("login.html")


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))


@app.template_filter('cut')
def cut(text):
    if len(text) < 100:
        return text
    else:
        return text[:100] + "..."
    

@app.template_filter('convert')
def convert(score):
    score = int(score)
    if score < 20:
        return "Not Achieved"
    elif score < 40:
        return "Achieved"
    elif score < 60:
        return "Merit"
    else:
        return "Excellence"


if __name__ == '__main__':
    app.run() 

