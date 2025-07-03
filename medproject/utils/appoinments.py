# utils/appointments.py

appointments = []

def book_appointment(patient_username, doctor_name, date, time):
    appointment = {
        'patient': patient_username,
        'doctor': doctor_name,
        'date': date,
        'time': time
    }
    appointments.append(appointment)
    return appointment

def get_user_appointments(username):
    return [appt for appt in appointments if appt['patient'] == username]



