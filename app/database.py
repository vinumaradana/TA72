import os
import mysql.connector
import pandas as pd
from dotenv import load_dotenv


# Load environment variables
load_dotenv()


# MySQL Connection
db_config = {
   "host": os.getenv("MYSQL_HOST"),
   "user": os.getenv("MYSQL_USER"),
   "password": os.getenv("MYSQL_PASSWORD"),
   "database": os.getenv("MYSQL_DATABASE"),
}


def get_db_connection():
   """Creates a new database connection."""
   return mysql.connector.connect(**db_config)


def create_tables():
   """Creates all necessary tables if they don't exist."""
   conn = get_db_connection()
   cursor = conn.cursor()

   # Create users table
   cursor.execute('''
       CREATE TABLE IF NOT EXISTS users (
           id INT AUTO_INCREMENT PRIMARY KEY,
           name VARCHAR(255) NOT NULL,
           email VARCHAR(255) UNIQUE NOT NULL,
           hashed_password VARCHAR(255) NOT NULL,
           PID VARCHAR(10) NOT NULL,
           location VARCHAR(255)
       )
   ''')
   
   cursor.execute( 
      """
            CREATE TABLE IF NOT EXISTS sessions (
                id VARCHAR(36) PRIMARY KEY,
                user_id INT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

   # Create devices table
   cursor.execute('''
       CREATE TABLE IF NOT EXISTS devices (
           id INT AUTO_INCREMENT PRIMARY KEY,
           user_id INT NOT NULL,
           device_id VARCHAR(255) UNIQUE NOT NULL,
           FOREIGN KEY (user_id) REFERENCES users (id)
       )
   ''')

   # Create wardrobe table
   cursor.execute('''
       CREATE TABLE IF NOT EXISTS wardrobe (
           id INT AUTO_INCREMENT PRIMARY KEY,
           user_id INT NOT NULL,
           item_name VARCHAR(255) NOT NULL,
           item_type VARCHAR(255) NOT NULL,
           FOREIGN KEY (user_id) REFERENCES users (id)
       )
   ''')
   cursor.execute('''
       CREATE TABLE IF NOT EXISTS temperature (
           id INT AUTO_INCREMENT PRIMARY KEY,
           temperature FLOAT NOT NULL,
           units VARCHAR(255) NOT NULL,
           mac_address VARCHAR(255) NOT NULL
       )
   ''')
   print("temperature database initialized")

   # Create sensor tables
   for sensor_type in ["temperature", "humidity", "light"]:
       cursor.execute(f'''
           CREATE TABLE IF NOT EXISTS {sensor_type} (
               id INT AUTO_INCREMENT PRIMARY KEY,
               value FLOAT NOT NULL,
               unit VARCHAR(50) NOT NULL,
               timestamp DATETIME NOT NULL,
               device_id VARCHAR(255),
               FOREIGN KEY (device_id) REFERENCES devices (device_id)
           )
       ''')
       

   conn.commit()
   cursor.close()
   conn.close()


def seed_database():
   """Seeds the database with initial data if needed."""
   conn = get_db_connection()
   cursor = conn.cursor()

   # Check if we need to seed
   cursor.execute("SELECT COUNT(*) FROM users")
   if cursor.fetchone()[0] == 0:
       # Add a test user
       cursor.execute('''
           INSERT INTO users (name, email, hashed_password, location, PID)
           VALUES (%s, %s, %s, %s, %s)
       ''', ("Test User", "test@example.com", "test123", "Test Location", "A12345678"))
       conn.commit()

   cursor.close()
   conn.close()


if __name__ == "__main__":
   create_tables()
   seed_database()
