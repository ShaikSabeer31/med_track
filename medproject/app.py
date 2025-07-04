from dotenv import load_dotenv
load_dotenv()
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import boto3
import uuid

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# --- AWS DynamoDB Setup ---
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')  # replace with your AWS region
users_table = dynamodb.Table('Users')
appointments_table = dynamodb.Table('Appointments')
diagnoses_table = dynamodb.Table('Diagnoses')

# --- Dummy User Class (used for Flask-Login) ---
class User(UserMixin):
    def __init__(self, username, role):
        self.id = username
        self.username = username
        self.role = role

# --- Flask-Login Manager Setup ---
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    response = users_table.get_item(Key={'username': user_id})
    user_data = response.get('Item')
    if user_data:
        return User(user_data['username'], user_data.get('role'))
    return None

# --- Routes ---
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password_input = request.form['password']
        response = users_table.get_item(Key={'username': username})
        user_data = response.get('Item')
        if user_data and check_password_hash(user_data['password'], password_input):
            user = User(username, user_data.get('role'))
            login_user(user)
            return redirect(url_for('dashboard'))
        flash("Invalid credentials", "danger")
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']

        # Check if user exists
        response = users_table.get_item(Key={'username': username})
        if 'Item' in response:
            flash("Username already exists", "danger")
            return redirect(url_for('register'))

        hashed_pw = generate_password_hash(password)
        users_table.put_item(Item={
            'username': username,
            'password': hashed_pw,
            'role': role
        })
        flash("Registered successfully!", "success")
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template("dashboard.html")

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/book', methods=['GET', 'POST'])
@login_required
def book():
    if request.method == 'POST':
        doctor = request.form['doctor']
        date = request.form['date']
        time = request.form['time']
        appt_id = str(uuid.uuid4())
        appointments_table.put_item(Item={
            'id': appt_id,
            'user_id': current_user.id,
            'doctor': doctor,
            'date': date,
            'time': time
        })
        flash("Appointment booked!", "success")
        return redirect(url_for('appointments'))
    return render_template('book.html')

@app.route('/appointments')
@login_required
def appointments():
    if current_user.role == 'patient':
        response = appointments_table.scan()
        all_appointments = response.get('Items', [])
        my_appointments = [a for a in all_appointments if a['user_id'] == current_user.id]
        return render_template("appointments.html", appointments=my_appointments, role='patient')
    elif current_user.role == 'doctor':
        response = appointments_table.scan()
        all_appointments = response.get('Items', [])
        my_appointments = [a for a in all_appointments if a['doctor'] == current_user.id]
        return render_template("appointments.html", appointments=my_appointments, role='doctor')
    else:
        return render_template("appointments.html", appointments=[], role='guest')

@app.route('/diagnosis', methods=['GET', 'POST'])
@login_required
def diagnosis():
    if current_user.role != 'patient':
        flash("Only patients can submit diagnoses.", "warning")
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        diag_id = str(uuid.uuid4())
        symptoms = request.form['symptoms']
        diagnoses_table.put_item(Item={
            'id': diag_id,
            'user_id': current_user.id,
            'symptoms': symptoms,
            'status': 'Pending'
        })
        flash("Diagnosis submitted!", "success")
        return redirect(url_for('view_diagnosis'))
    return render_template("diagnosis.html")

@app.route('/view_diagnosis')
@login_required
def view_diagnosis():
    response = diagnoses_table.scan()
    all_diagnoses = response.get('Items', [])
    my_diagnoses = [d for d in all_diagnoses if d['user_id'] == current_user.id]
    return render_template("view_diagnosis.html", diagnoses=my_diagnoses)

@app.route('/manage_diagnosis', methods=['GET', 'POST'])
@login_required
def manage_diagnosis():
    if current_user.role != 'doctor':
        flash("Only doctors can manage diagnoses.", "danger")
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        diag_id = request.form['diag_id']
        new_status = request.form['status']
        diagnoses_table.update_item(
            Key={'id': diag_id},
            UpdateExpression="SET #s = :status",
            ExpressionAttributeNames={'#s': 'status'},
            ExpressionAttributeValues={':status': new_status}
        )
        flash("Diagnosis updated.", "success")

    response = diagnoses_table.scan()
    all_diagnoses = response.get('Items', [])
    return render_template("manage_diagnosis.html", diagnoses=all_diagnoses)

# --- Run App ---
if __name__ == '__main__':
    app.run(debug=True)
