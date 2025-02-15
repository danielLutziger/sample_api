from ics import Calendar, Event
from dotenv import load_dotenv
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta, timezone
import uuid
from supabase import create_client, Client

app = FastAPI()
load_dotenv()

origins = [
    "http://localhost:5173",  # running locally
    "https://storage.googleapis.com", # deployed URL
    "https://just-aloe.oa.r.appspot.com" # deployed URL
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

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


class Question(BaseModel):
    firstname: str
    email: str
    phone: str
    bemerkung: str


class AppointmentCancelRequest(BaseModel):
    id: str


def generate_ics_file(booking_details: BookingRequest, services: List[Service], total_duration: int,
                      total_price: float, booking_hash: uuid):
    c = Calendar()
    e = Event()

    date_parts = booking_details.date.split(".")[::-1]
    year, month, day = map(int, date_parts)
    hour, minute = map(int, booking_details.time.split(":"))

    start_time = datetime(year, month, day, hour, minute, tzinfo=timezone.utc) - timedelta(hours=1)

    e.begin = start_time.strftime("%Y-%m-%dT%H:%M:%S")
    e.duration = {
        'hours': total_duration // 60,
        'minutes': total_duration % 60
    }
    e.name = f"Booking: {', '.join([s.title for s in services])}"
    servs = ', '.join([f"{s.title} ({s.duration} Minuten)" for s in services])
    e.description = (
        f"Termin ID: {booking_hash}\n"
        f"Buchung für {booking_details.firstname} {booking_details.lastname}\n"
        f"E-Mail: {booking_details.email}\n"
        f"Telefon: {booking_details.phone}\n"
        f"Datum: {booking_details.date}, Zeit: {booking_details.time}\n"
        f"Services: {servs}\n"
        f"Ungefährer Preis: CHF {total_price}\n"
        "Stornierung: Bis spätestens 2 Tage vorher telefonisch möglich: +41 79 968 11 84"
    )
    e.location = "Kirchgasse 3, 9500 Wil, Schweiz"
    e.status = "CONFIRMED"

    c.events.add(e)
    return str(c)


def send_email(subject, recipient, body, ics_content=None):
    sender_email = os.getenv('EMAIL_USER')
    password = os.getenv('EMAIL_PASS')

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    if ics_content:
        ics_attachment = MIMEBase('text', 'calendar')
        ics_attachment.set_payload(ics_content)
        encoders.encode_base64(ics_attachment)
        ics_attachment.add_header('Content-Disposition', 'attachment', filename="appointment.ics")
        msg.attach(ics_attachment)

    server = smtplib.SMTP(os.getenv('EMAIL_HOST'), int(os.getenv('EMAIL_PORT')))
    server.starttls()
    server.login(sender_email, password)
    server.sendmail(sender_email, recipient, msg.as_string())
    server.quit()


@app.post("/api/terminanfrage")
def book_appointment(request: BookingRequest):
    duration = sum(service.duration for service in request.services if service.duration)

    # Parse start_time and calculate end_time in Python
    start_time = datetime.strptime(f"{request.date} {request.time}", "%d.%m.%Y %H:%M")
    end_time = start_time + timedelta(minutes=duration)
    booking_hash = str(uuid.uuid4())

    # Check for overlapping bookings
    overlap_query = supabase.table("bookings") \
        .select("*") \
        .filter("start_time", "lt", end_time.isoformat()) \
        .filter("end_time", "gt", start_time.isoformat()) \
        .execute()

    if overlap_query.data:
        raise HTTPException(status_code=400, detail="Time slot is overlapping with another booking. Book another time")

    # Insert the booking
    response = supabase.table("bookings").insert({
        "booking_hash": booking_hash,
        "user_email": request.email,
        "user_phone": request.phone,
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "firstname": request.firstname,
        "lastname": request.lastname,
        "agbchecked": request.agbChecked,
        "bemerkung": request.bemerkung
    }).execute()

    if not response.data:
        raise HTTPException(status_code=400, detail="Failed to book appointment")

    booking_id = response.data[0]['id']
    total_price = 0
    for service in request.services:
        supabase.table("booking_services").insert({
            "booking_id": booking_id,
            "service_id": service.id,
            "title": service.title,
            "price": service.price,
            "duration": service.duration,
            "description": service.description,
            "image": service.image,
            "reduction": service.reduction
        }).execute()
        total_price += service.price

    try:
        body = "Ihr Termin wurde erfolgreich gebucht. Bitte finden Sie die Buchungsdetails in der angehängten .ics Datei."
        ics = generate_ics_file(booking_details=request, services=request.services,
                                total_duration=request.dateInfo.duration, total_price=total_price,
                                booking_hash=booking_hash)
        send_email("Termin erfolgreich gebucht", os.getenv("EMAIL_TO"), body, ics)
        send_email("Termin erfolgreich gebucht", request.email, body, ics)
        return {"id": booking_hash}
    except:
        print("Mail sending went wrong. Probably wrong email from user.")
        return {"id": booking_hash}


@app.get("/api/booked-slots")
def get_booked_slots():
    query = supabase.table("bookings").select("start_time, end_time").execute()

    # Convert stored timestamps into "DD.MM.YYYY" format
    booked_slots = []
    for slot in query.data:
        start_dt = datetime.fromisoformat(slot["start_time"])  # Convert from ISO
        end_dt = datetime.fromisoformat(slot["end_time"])

        booked_slots.append({
            "date": start_dt.strftime("%d.%m.%Y"),  # Format as "31.01.2025"
            "startTime": start_dt.strftime("%H:%M"),  # Format as "12:00"
            "endTime": end_dt.strftime("%H:%M")  # Format as "13:30"
        })

    return booked_slots

@app.delete("/api/terminabsage/{booking_hash}")
def cancel_appointment(booking_hash: str):
    result = supabase.table("bookings").delete().eq("booking_hash", booking_hash).execute()
    if not result:
        raise HTTPException(status_code=404, detail="Termin nicht gefunden")

    body = (
        f"Buchung für {result[6]} {result[7]} vom {result[4].strftime('%d.%m.%Y')}, {result[4].strftime('%H:%M')} erfolgreich abgesagt."
    )

    send_email("Termin erfolgreich abgesagt", os.getenv("EMAIL_TO"), body)
    send_email("Termin erfolgreich abgesagt", result[2], body)
    return {"message": "Appointment deleted successfully"}

@app.post("/api/anliegen_melden")
def anliegen_mitteilen(request: Question):
    print(request)
    body = (
        f"Anliegen von {request.firstname} \n"
        f"Email: {request.email} \n"
        f"Telefon-Nr: {request.phone} \n"
        f"Anliegen: {request.bemerkung}"
    )
    send_email(f"Anliegen von {request.firstname}", os.getenv("EMAIL_TO"), body)
    return {"message": "Successfully sent question"}


@app.get("/api/health")
def health_check():
    return {"status": "ok"}


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)