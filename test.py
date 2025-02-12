from dotenv import load_dotenv
from google.cloud.sql.connector import Connector
import sqlalchemy
import os

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
    result = connection.execute(sqlalchemy.text("SELECT NOW();"))
    print("Current Timestamp:", result.fetchone())

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

if __name__ == "__main__":
    setup()