from ics import Calendar, Event
from dotenv import load_dotenv
import os
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import uvicorn
from google.cloud.sql.connector import Connector


app = FastAPI()
load_dotenv()

connector = Connector()


def getconn():
    return connector.connect(
        os.getenv("INSTANCE_CONNECTION_NAME"),
        "pg8000",
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS"),
        db=os.getenv("DB_NAME"),
    )


# Create SQLAlchemy engine
engine = create_engine(
    "postgresql+pg8000://",
    creator=getconn
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def send_email(subject, recipient, body):
    sender_email = os.getenv('EMAIL_USER')
    password = os.getenv('EMAIL_PASS')

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    server = smtplib.SMTP(os.getenv('EMAIL_HOST'), int(os.getenv('EMAIL_PORT')))
    server.starttls()
    server.login(sender_email, password)
    server.sendmail(sender_email, recipient, msg.as_string())
    server.quit()


# Models
class BookingRequest(BaseModel):
    email: str
    phone: str
    date: str
    start_time: str
    duration: int


class AppointmentCancelRequest(BaseModel):
    id: str


# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/api/terminanfrage")
def book_appointment(request: BookingRequest, db=Depends(get_db)):
    query = text("""
        WITH new_booking AS (
            SELECT
                MAKE_TIMESTAMP(
                    SPLIT_PART(:date, '.', 3)::INT,
                    SPLIT_PART(:date, '.', 2)::INT,
                    SPLIT_PART(:date, '.', 1)::INT,
                    SPLIT_PART(:start_time, ':', 1)::INT,
                    SPLIT_PART(:start_time, ':', 2)::INT,
                    0
                ) AS start_time,
                MAKE_TIMESTAMP(
                    SPLIT_PART(:date, '.', 3)::INT,
                    SPLIT_PART(:date, '.', 2)::INT,
                    SPLIT_PART(:date, '.', 1)::INT,
                    SPLIT_PART(:start_time, ':', 1)::INT,
                    SPLIT_PART(:start_time, ':', 2)::INT,
                    0
                ) + (:duration * INTERVAL '1 minute') AS end_time
        )
        INSERT INTO "Appointment" (user_email, user_phone, start_time, end_time)
        SELECT :email, :phone, start_time, end_time FROM new_booking
        WHERE NOT EXISTS (
            SELECT 1 FROM "Appointment"
            WHERE tstzrange(start_time, end_time, '[]') &&
            tstzrange((SELECT start_time FROM new_booking), (SELECT end_time FROM new_booking), '[]')
        )
        RETURNING id;
    """)

    result = db.execute(query, {
        "date": request.date,
        "start_time": request.start_time,
        "duration": request.duration,
        "email": request.email,
        "phone": request.phone
    }).fetchone()

    db.commit()
    if not result:
        raise HTTPException(status_code=400, detail="Time slot already booked")
    # TODO send mail as well
    return {"id": result[0]}


@app.get("/api/booked-slots")
def get_booked_slots(db=Depends(get_db)):
    query = text("""
        SELECT 
            TO_CHAR(start_time, 'DD.MM.YYYY') AS date,
            TO_CHAR(start_time, 'HH24:MI') AS start_time,
            TO_CHAR(end_time, 'HH24:MI') AS end_time
        FROM "Appointment";
    """)
    slots = db.execute(query).fetchall()
    return slots


@app.delete("/api/terminabsage/{appointment_id}")
def cancel_appointment(appointment_id: str, db=Depends(get_db)):
    query = text('DELETE FROM "Appointment" WHERE id = :id RETURNING *;')
    result = db.execute(query, {"id": appointment_id}).fetchone()
    db.commit()

    if not result:
        raise HTTPException(status_code=404, detail="Appointment not found")

    send_email("Nancy Nails Termin Abgesagt", os.getenv('EMAIL_TO'), f"Termin mit ID {appointment_id} wurde abgesagt.")
    return {"message": "Appointment deleted successfully"}


@app.get("/api/health")
def health_check():
    return {"status": "ok"}



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


if __name__ == "__main__":
    port = int(os.getenv("PORT"))
    uvicorn.run(app, host="0.0.0.0", port=port)
