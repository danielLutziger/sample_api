from fastapi import FastAPI, HTTPException, Request
from ics import Calendar, Event
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import os
from dotenv import load_dotenv
from google.cloud.sql.connector import Connector
import sqlalchemy

app = FastAPI()
load_dotenv()

connector = Connector()

def getconn():
    return connector.connect(
        os.getenv('INSTANCE_CONNECTION_NAME'),
        "pg8000",
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASS'),
        db=os.getenv('DB_NAME')
    )

engine = sqlalchemy.create_engine(
    "postgresql+pg8000://",
    creator=getconn
)

with engine.connect() as connection:
    result = connection.execute("SELECT NOW();")
    print("Current Timestamp:", result.fetchone())

@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}

def generate_ics_file(booking_details, services, total_duration, total_price):
    c = Calendar()
    e = Event()

    date_parts = booking_details['date'].split(".")[::-1]
    year, month, day = map(int, date_parts)
    hour, minute = map(int, booking_details['time'].split(":"))

    e.begin = f"{year}-{month:02d}-{day:02d}T{hour:02d}:{minute:02d}:00"
    e.duration = {
        'hours': total_duration // 60,
        'minutes': total_duration % 60
    }
    e.name = f"Booking: {', '.join([s['title'] for s in services])}"
    servs = ', '.join([f"{s['title']} ({s['duration']} Minuten)" for s in services])
    e.description = (
        f"Buchung für {booking_details['firstname']} {booking_details['lastname']}\n"
        f"E-Mail: {booking_details['email']}\n"
        f"Telefon: {booking_details['phone']}\n"
        f"Datum: {booking_details['date']}, Zeit: {booking_details['time']}\n"
        f"Services: {servs}\n"
        f"Ungefährer Preis: CHF {total_price}\n"
        "Stornierung: Bis spätestens 2 Tage vorher telefonisch möglich."
    )
    e.location = "Kirchgasse 3, 9500 Wil, Schweiz"
    e.status = "CONFIRMED"

    c.events.add(e)
    return str(c)

@app.post('/api/terminanfrage')
async def handle_booking_request(request: Request):
    data = await request.json()

    if not data.get('agbChecked'):
        raise HTTPException(status_code=400, detail='AGBs must be accepted to proceed with the booking.')

    booking_details = data
    services = data['services']
    total_duration = sum(service['duration'] for service in services)
    total_price = sum(service['price'] for service in services)

    query_res = book_appointment(
        data['email'], data['phone'], data['dateInfo']['date'], data['dateInfo']['startTime'], data['dateInfo']['duration']
    )

    if query_res.get('error') == "Time slot already booked":
        raise HTTPException(status_code=400, detail='Termin überschneidet einen gebuchten Block. Wählen Sie einen anderen Zeitpunkt')

    try:
        ics_content = generate_ics_file(booking_details, services, total_duration, total_price)

        send_email(
            subject='Neuer Nancy Nails Termin',
            recipient=os.getenv('EMAIL_TO'),
            body=f"""
            Neue Anfrage nach einem Termin: {data['firstname']} {data['lastname']}.
            Kontakt Details: Email - {data['email']}, Phone - {data['phone']}.
            Termin ID: {query_res['id']}
            Datum: {data['date']}, Zeit: {data['time']}
            Folgende Services wurden gebucht: {', '.join([s['title'] for s in services])}
            Bemerkung des Kunden: {data.get('bemerkung', '')}
            """,
            attachment_content=ics_content,
            attachment_name='appointment.ics'
        )

        send_email(
            subject='Nancy Nails Termin Gebucht',
            recipient=data['email'],
            body=f"""
            Termin wurde erfolgreich gebucht. Termin ID: {query_res['id']}
            Datum: {data['date']}, Zeit: {data['time']}
            Folgende Services wurden gebucht: {', '.join([s['title'] for s in services])}
            """
        )

        return query_res
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Failed to send email: {str(e)}')

def send_email(subject, recipient, body, attachment_content=None, attachment_name=None):
    sender_email = os.getenv('EMAIL_USER')
    password = os.getenv('EMAIL_PASSWORD')

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    if attachment_content and attachment_name:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(attachment_content.encode('utf-8'))
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename={attachment_name}')
        msg.attach(part)

    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(sender_email, password)
    text = msg.as_string()
    server.sendmail(sender_email, recipient, text)
    server.quit()

def book_appointment(email, phone, date, start_time, duration):
    # Placeholder function for booking logic
    return {'id': '12345'}


def setup():
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            # create the table
            connection.execute(
                sqlalchemy.text("CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, name TEXT, email TEXT);")
            )
            # insert into table
            connection.execute(
                sqlalchemy.text("INSERT INTO users (name, email) VALUES (:name, :email)"),
                {"name": "Alice", "email": "alice@example.com"}
            )
            # fetch all
            result = connection.execute(sqlalchemy.text("SELECT * FROM users;"))
            print(result.fetchall())

            # commit
            transaction.commit()

        except Exception as e:
            transaction.rollback()
            print("Error:", e)