from flask import Flask, render_template, request, redirect, session
import sqlite3
import csv

app = Flask(__name__)
app.secret_key = "schoolportal123"

DB = "school.db"


# ================= DATABASE =================

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS students(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        admission TEXT UNIQUE,
        year_birth TEXT,
        class_name TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS teachers(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        username TEXT UNIQUE,
        password TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS fees(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        admission TEXT,
        total_fee INTEGER,
        amount_paid INTEGER
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS attendance(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_admission TEXT,
        date TEXT,
        status TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS results(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        admission TEXT,
        subject TEXT,
        marks INTEGER
    )
    """)

    conn.commit()
    conn.close()


init_db()


# ================= HOME =================

@app.route('/')
def home():
    return render_template('home.html')


# ================= LOGOUT =================

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


# ================= ADMIN =================
@app.route('/admin', methods=['GET', 'POST'])
def admin():

    message = ""

    if request.method == 'POST':

        username = request.form['username']
        password = request.form['password']

        if username == "admin" and password == "admin12":
            session['admin'] = True
            message = "Login Successful"
            return redirect('/admin_dashboard')
        else:
            message = "Wrong Username or Password"

    return render_template(
        'admin_login.html',
        message=message
    )


@app.route('/admin_dashboard')
def admin_dashboard():

    if 'admin' not in session:
        return redirect('/admin')

    conn = sqlite3.connect(DB)

    students = conn.execute("SELECT * FROM students").fetchall()
    teachers = conn.execute("SELECT * FROM teachers").fetchall()

    conn.close()

    return render_template('admin_dashboard.html',
                           students=students,
                           teachers=teachers)


# ================= STUDENTS =================

@app.route('/add_student', methods=['GET', 'POST'])
def add_student():

    if 'admin' not in session:
        return redirect('/admin')

    if request.method == 'POST':

        conn = sqlite3.connect(DB)
        conn.execute("""
        INSERT INTO students(name, admission, year_birth, class_name)
        VALUES (?,?,?,?)
        """, (
            request.form['name'],
            request.form['admission'],
            request.form['year_birth'],
            request.form['class_name']
        ))
        conn.commit()
        conn.close()

        return redirect('/admin_dashboard')

    return render_template('add_student.html')


@app.route('/edit_student/<int:id>', methods=['GET', 'POST'])
def edit_student(id):

    if 'admin' not in session:
        return redirect('/admin')

    conn = sqlite3.connect(DB)

    if request.method == 'POST':

        conn.execute("""
        UPDATE students
        SET name=?, admission=?, year_birth=?, class_name=?
        WHERE id=?
        """, (
            request.form['name'],
            request.form['admission'],
            request.form['year_birth'],
            request.form['class_name'],
            id
        ))

        conn.commit()
        conn.close()

        return redirect('/admin_dashboard')

    student = conn.execute("SELECT * FROM students WHERE id=?", (id,)).fetchone()
    conn.close()

    return render_template('edit_student.html', student=student)


@app.route('/delete_student/<int:id>')
def delete_student(id):

    if 'admin' not in session:
        return redirect('/admin')

    conn = sqlite3.connect(DB)
    conn.execute("DELETE FROM students WHERE id=?", (id,))
    conn.commit()
    conn.close()

    return redirect('/admin_dashboard')


# ================= TEACHERS =================

@app.route('/add_teacher', methods=['GET', 'POST'])
def add_teacher():

    if 'admin' not in session:
        return redirect('/admin')

    if request.method == 'POST':

        conn = sqlite3.connect(DB)
        conn.execute("""
        INSERT INTO teachers(name, username, password)
        VALUES (?,?,?)
        """, (
            request.form['name'],
            request.form['username'],
            request.form['password']
        ))
        conn.commit()
        conn.close()

        return redirect('/admin_dashboard')

    return render_template('add_teacher.html')


@app.route('/delete_teacher/<int:id>')
def delete_teacher(id):

    if 'admin' not in session:
        return redirect('/admin')

    conn = sqlite3.connect(DB)
    conn.execute("DELETE FROM teachers WHERE id=?", (id,))
    conn.commit()
    conn.close()

    return redirect('/admin_dashboard')


# ================= TEACHER =================

@app.route('/teacher', methods=['GET', 'POST'])
def teacher():

    message = ""

    if request.method == 'POST':

        conn = sqlite3.connect(DB)

        t = conn.execute("""
        SELECT * FROM teachers
        WHERE username=? AND password=?
        """, (
            request.form['username'],
            request.form['password']
        )).fetchone()

        conn.close()

        if t:
            session['teacher'] = t[0]
            return redirect('/teacher_dashboard')
        else:
            message = "Wrong Username or Password"

    return render_template(
        'teacher_login.html',
        message=message
    )

@app.route('/teacher_dashboard')
def teacher_dashboard():

    if 'teacher' not in session:
        return redirect('/teacher')

    return render_template('teacher_dashboard.html')


# ================= ATTENDANCE =================

@app.route('/attendance')
def attendance():

    if 'teacher' not in session:
        return redirect('/teacher')

    conn = sqlite3.connect(DB)
    students = conn.execute("SELECT * FROM students").fetchall()
    conn.close()

    return render_template('attendance.html', students=students)


@app.route('/save_attendance', methods=['POST'])
def save_attendance():

    if 'teacher' not in session:
        return redirect('/teacher')

    conn = sqlite3.connect(DB)

    students = conn.execute("SELECT * FROM students").fetchall()

    for s in students:

        status = request.form.get(f"attendance_{s[2]}", "Absent")

        conn.execute("""
        INSERT INTO attendance(student_admission, date, status)
        VALUES (?,?,?)
        """, (s[2], request.form['date'], status))

    conn.commit()
    conn.close()

    return redirect('/teacher_dashboard')


# ================= RESULTS =================

@app.route('/upload_results', methods=['GET', 'POST'])
def upload_results():

    if 'teacher' not in session:
        return redirect('/teacher')

    if request.method == 'POST':

        file = request.files['csvfile']

        data = csv.reader(
            file.stream.read().decode('utf-8').splitlines()
        )

        headers = next(data)

        conn = sqlite3.connect(DB)

        for row in data:

            admission = row[0]

            for i in range(1, len(headers)):

                subject = headers[i]
                marks = row[i]

                if marks.strip() != "":

                    conn.execute(
                        """
                        INSERT INTO results
                        (admission, subject, marks)
                        VALUES (?, ?, ?)
                        """,
                        (admission, subject, marks)
                    )

        conn.commit()
        conn.close()

        return "Results Uploaded Successfully"

    return render_template('upload_results.html')


# ================= STUDENT =================

@app.route('/student', methods=['GET', 'POST'])
def student():

    message = ""

    if request.method == 'POST':

        admission = request.form['admission']
        year_birth = request.form['year_birth']

        conn = sqlite3.connect(DB)

        student = conn.execute("""
        SELECT * FROM students
        WHERE admission=? AND year_birth=?
        """, (admission, year_birth)).fetchone()

        if student:

            results = conn.execute("""
            SELECT subject, marks
            FROM results
            WHERE admission=?
            """, (admission,)).fetchall()

            fee = conn.execute("""
            SELECT total_fee, amount_paid
            FROM fees
            WHERE admission=?
            """, (admission,)).fetchone()

            total = sum(int(r[1]) for r in results) if results else 0
            mean = round(total / len(results), 2) if results else 0
            balance = (fee[0] - fee[1]) if fee else 0

            conn.close()

            return render_template(
                'student_result.html',
                student=student,
                results=results,
                total_marks=total,
                mean_score=mean,
                fee=fee,
                balance=balance
            )

        conn.close()

    return render_template('student_login.html')

# ================= RESULTS SUMMARY =================

@app.route('/results')
def results_summary():

    if 'admin' not in session:
        return redirect('/admin')

    conn = sqlite3.connect(DB)
    results = conn.execute("SELECT * FROM results").fetchall()
    conn.close()

    return render_template(
        'results.html',
        results=results
    )


# ================= FEES =================

@app.route('/fees')
def fees():

    if 'admin' not in session:
        return redirect('/admin')

    conn = sqlite3.connect(DB)
    fees_data = conn.execute("SELECT * FROM fees").fetchall()
    conn.close()

    return render_template(
        'fees.html',
        fees_data=fees_data
    )


@app.route('/add_fee', methods=['GET', 'POST'])
def add_fee():

    if 'admin' not in session:
        return redirect('/admin')

    if request.method == 'POST':

        conn = sqlite3.connect(DB)

        conn.execute(
            """
            INSERT INTO fees
            (admission, total_fee, amount_paid)
            VALUES (?, ?, ?)
            """,
            (
                request.form['admission'],
                request.form['total_fee'],
                request.form['amount_paid']
            )
        )

        conn.commit()
        conn.close()

        return redirect('/fees')

    return render_template('add_fee.html')


# ================= ATTENDANCE RECORDS =================

@app.route('/attendance_records')
def attendance_records():

    if 'admin' not in session:
        return redirect('/admin')

    conn = sqlite3.connect(DB)

    records = conn.execute(
        "SELECT * FROM attendance ORDER BY id DESC"
    ).fetchall()

    conn.close()

    return render_template(
        'attendance_records.html',
        records=records
    )

@app.route('/change_password', methods=['GET', 'POST'])
def change_password():

    if 'teacher' not in session:
        return redirect('/teacher')

    message = ""

    if request.method == 'POST':

        old_password = request.form['old_password']
        new_password = request.form['new_password']

        conn = sqlite3.connect(DB)

        teacher = conn.execute(
            """
            SELECT * FROM teachers
            WHERE id=? AND password=?
            """,
            (session['teacher'], old_password)
        ).fetchone()

        if teacher:

            conn.execute(
                """
                UPDATE teachers
                SET password=?
                WHERE id=?
                """,
                (new_password, session['teacher'])
            )

            conn.commit()
            message = "Password Changed Successfully"

        else:
            message = "Old Password Is Incorrect"

        conn.close()

    return render_template(
        'change_password.html',
        message=message
    )
@app.route('/search_student', methods=['GET', 'POST'])
def search_student():

    if 'admin' not in session:
        return redirect('/admin')

    students = []

    if request.method == 'POST':

        keyword = request.form['keyword']

        conn = sqlite3.connect(DB)

        students = conn.execute(
            """
            SELECT * FROM students
            WHERE name LIKE ?
            OR admission LIKE ?
            """,
            ('%' + keyword + '%',
             '%' + keyword + '%')
        ).fetchall()

        conn.close()

    return render_template(
        'search_student.html',
        students=students
    )

@app.route('/manage_students')
def manage_students():

    if 'admin' not in session:
        return redirect('/admin')

    conn = sqlite3.connect(DB)
    students = conn.execute("SELECT * FROM students").fetchall()
    conn.close()

    return render_template(
        'manage_students.html',
        students=students
    )


@app.route('/manage_teachers')
def manage_teachers():

    if 'admin' not in session:
        return redirect('/admin')

    conn = sqlite3.connect(DB)
    teachers = conn.execute("SELECT * FROM teachers").fetchall()
    conn.close()

    return render_template(
        'manage_teachers.html',
        teachers=teachers
    )


@app.route('/print_reports')
def print_reports():

    if 'admin' not in session:
        return redirect('/admin')

    return render_template('print_reports.html')


@app.route('/performance_analysis')
def performance_analysis():

    if 'admin' not in session:
        return redirect('/admin')

    conn = sqlite3.connect(DB)

    results = conn.execute(
        "SELECT subject, AVG(marks) FROM results GROUP BY subject"
    ).fetchall()

    conn.close()

    return render_template(
        'performance_analysis.html',
        results=results
    )
# ================= RUN =================

if __name__ == '__main__':
    app.run(debug=True)