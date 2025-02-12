from ics import Calendar, Event
from dotenv import load_dotenv
import os
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import uvicorn
from google.cloud.sql.connector import Connector
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
import uuid

app = FastAPI()
load_dotenv()

origins = [
    "http://localhost:5173",  # running locally
    "https://yourfrontend.com"  # deployed URL
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


def create_bookings_table():
    with engine.connect() as connection:
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS bookings (
                id SERIAL PRIMARY KEY,
                booking_hash TEXT UNIQUE NOT NULL,
                user_email TEXT NOT NULL,
                user_phone TEXT NOT NULL,
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP NOT NULL,
                firstname TEXT NOT NULL,
                lastname TEXT NOT NULL,
                agbChecked BOOLEAN NOT NULL,
                bemerkung TEXT
            );
        """))
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS booking_services (
                id SERIAL PRIMARY KEY,
                booking_id INT NOT NULL REFERENCES bookings(id) ON DELETE CASCADE,
                service_id TEXT NOT NULL,
                title TEXT NOT NULL,
                price FLOAT NOT NULL,
                duration INT,
                description TEXT,
                image TEXT,
                reduction TEXT
            );
        """))
        connection.commit()

create_bookings_table()


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
class Service(BaseModel):
    id: str
    title: str
    price: float
    duration: Optional[int]
    description: Optional[str]
    image: Optional[str]
    images: Optional[List[str]]
    reduction: Optional[str]
    extras: Optional[str] = None

class DateInfo(BaseModel):
    date: str
    startTime: str
    endTime: Optional[str]
    duration: Optional[int]

class BookingRequest(BaseModel):
    email: str
    phone: str
    date: str
    time: str
    firstname: str
    lastname: str
    agbChecked: bool
    bemerkung: Optional[str]
    emailError: bool
    phoneError: bool
    dateInfo: DateInfo
    services: List[Service]


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
    duration = sum(service.duration for service in request.services if service.duration)

    # Parse start_time and calculate end_time in Python
    start_time = datetime.strptime(f"{request.date} {request.time}", "%d.%m.%Y %H:%M")
    end_time = start_time + timedelta(minutes=duration)
    booking_hash = str(uuid.uuid4())

    # Check for overlapping bookings
    overlap_query = text("""
        SELECT 1 FROM bookings 
        WHERE start_time < :end_time AND end_time > :start_time
    """)
    overlap = db.execute(overlap_query, {
        "start_time": start_time,
        "end_time": end_time
    }).fetchone()

    if overlap:
        raise HTTPException(status_code=400, detail="Time slot is overlapping with another booking. Book another time")

    # Insert the booking
    query = text("""
        INSERT INTO bookings (booking_hash, user_email, user_phone, start_time, end_time, firstname, lastname, agbChecked, bemerkung)
        VALUES (:booking_hash, :email, :phone, :start_time, :end_time, :firstname, :lastname, :agbChecked, :bemerkung)
        RETURNING id;
    """)

    result = db.execute(query, {
        "booking_hash": booking_hash,
        "email": request.email,
        "phone": request.phone,
        "start_time": start_time,
        "end_time": end_time,
        "firstname": request.firstname,
        "lastname": request.lastname,
        "agbChecked": request.agbChecked,
        "bemerkung": request.bemerkung
    }).fetchone()
    db.commit()

    if not result:
        raise HTTPException(status_code=400, detail="Failed to book appointment")

    booking_id = result[0]
    for service in request.services:
        db.execute(text("""
            INSERT INTO booking_services (booking_id, service_id, title, price, duration, description, image, reduction)
            VALUES (:booking_id, :service_id, :title, :price, :duration, :description, :image, :reduction)
        """), {
            "booking_id": booking_id,
            "service_id": service.id,
            "title": service.title,
            "price": service.price,
            "duration": service.duration,
            "description": service.description,
            "image": service.image,
            "reduction": service.reduction
        })
    db.commit()

    return {"id": booking_hash}


@app.get("/api/booked-slots")
def get_booked_slots(db=Depends(get_db)):
    query = text("""
        SELECT 
            TO_CHAR(start_time, 'DD.MM.YYYY') AS date,
            TO_CHAR(start_time, 'HH24:MI') AS start_time,
            TO_CHAR(end_time, 'HH24:MI') AS end_time
        FROM bookings;
    """)
    slots = db.execute(query).fetchall()
    return [{"date": slot.date, "startTime": slot.start_time, "endTime": slot.end_time} for slot in slots]


@app.delete("/api/terminabsage/{booking_hash}")
def cancel_appointment(booking_hash: str, db=Depends(get_db)):
    query = text("DELETE FROM bookings WHERE booking_hash = :booking_hash RETURNING *;")
    result = db.execute(query, {"booking_hash": booking_hash}).fetchone()
    db.commit()

    if not result:
        raise HTTPException(status_code=404, detail="Appointment not found")

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
