-- Create Bookings Table
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

-- Create Booking Services Table
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
