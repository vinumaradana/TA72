from fastapi import FastAPI, HTTPException, Query, Depends, Request, Form, Response, Cookie
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import httpx
import mysql.connector
import os
from dotenv import load_dotenv
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
import hashlib
import uuid
from urllib.request import urlopen
import json

from .routers import auth, wardrobe, devices
from .dependencies import get_current_user
from .database import get_db_connection, create_tables, seed_database

# Load environment variables
load_dotenv()

app = FastAPI()

class TemperatureData(BaseModel):
    value: float
    unit: str
    mac_address: str

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include routers
app.include_router(auth.router)
app.include_router(wardrobe.router)
app.include_router(devices.router)

# Templates
templates = Jinja2Templates(directory="app/templates")

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

@app.on_event("startup")
def startup_event():
    """Runs at startup to seed the database."""
    create_tables()
    print("temperature database initialized")
    seed_database()

@app.get("/", response_class=HTMLResponse)
async def read_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

AITEXT_API_URL = "https://ece140-wi25-api.frosty-sky-f43d.workers.dev/api/v1/ai/complete"

def hash_password(password: str) -> str:
    """Hash a password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()

def get_current_user(session_id: str = Cookie(None)):
    """Retrieve the current user based on the session cookie."""
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Query the sessions table using the session_id cookie (stored in the 'id' column)
        cursor.execute("SELECT user_id FROM sessions WHERE id = %s", (session_id,))
        session = cursor.fetchone()
        if not session:
            raise HTTPException(status_code=401, detail="Session not found")
        
        user_id = session["user_id"]
        
        # Now retrieve the user record from the users table using the user_id
        cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        # Optionally, you can return the entire user object or just user_id
        return user

    finally:
        cursor.close()
        conn.close()


@app.post("/getairesponse")
async def getAIResponse(request: Request, prompt: str = Form(...)):
    user_id = await authenticate(request)
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)



    try:
        cursor.execute("SELECT email, PID FROM users WHERE id = %s", (user_id,))
        user_data = cursor.fetchone()
        if not user_data:
            raise HTTPException(status_code=404, detail="User not found")
        
        email = user_data["email"]
        PID = user_data["PID"]
        # Send request to external AI API
        async with httpx.AsyncClient() as client:
            response = await client.post(
                AITEXT_API_URL,
                headers={
                    "email": email,
                    "pid": PID,
                    "Content-Type": "application/json"
                },
                json={"prompt": prompt}  # Sending prompt as JSON body
            )

        # Handle response
        if response.status_code == 200:
            response_json = response.json()
            ai_response = response_json.get("result", {}).get("response", "No response found")
            return JSONResponse(content={"response": ai_response})
        else:
            return JSONResponse(
                content={"error": f"AI API error: {response.text}"},
                status_code=response.status_code
            )
    except httpx.ReadTimeout:
        return JSONResponse(status_code=504, content={"error": "AI response took too long."})
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print("Database Error:", error_details)  # Log full error details
        return JSONResponse(
            content={"error": f"Internal server error: {str(e)}"},
            status_code=500
        )



async def get_session(session_id: str) -> Optional[dict]:
    """Retrieve session from database."""
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT *
            FROM sessions
            WHERE id = %s
        """,
            (session_id,),
        )
        return cursor.fetchone()
    finally:
            cursor.close()
            connection.close()


async def authenticate(request: Request):
    session_id = request.cookies.get("session_id")
    if not session_id:
        return RedirectResponse(url="/login", status_code=302)

    conn = get_db_connection()
    if conn is None:
        raise HTTPException(status_code=401, detail="Unauthorized: No session ID provided")

    session = await get_session(session_id)
    if not session:
        return RedirectResponse(url="/login", status_code=302)

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM sessions WHERE id = %s", (session_id,))
        valid_session = cursor.fetchone()
        if not valid_session:
            return None
        user_id = valid_session[0]
        return user_id
    finally: 
        cursor.close()
        conn.close()

class SensorData(BaseModel):
    value: float
    unit: str
    timestamp: Optional[str] = None
    device_id: Optional[str] = None

@app.get("/api/{sensor_type}/count")
async def get_sensor_count(sensor_type: str, user_id: str = Depends(get_current_user)):
    """Returns the number of rows for a given sensor type."""
    if sensor_type not in ["temperature", "humidity", "light"]:
        raise HTTPException(status_code=404, detail="Invalid sensor type")
    
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        query = f"""
            SELECT COUNT(*) FROM {sensor_type} s
            JOIN devices d ON s.device_id = d.device_id
            WHERE d.user_id = %s
        """
        cursor.execute(query, (user_id,))
        count = cursor.fetchone()[0]
        return count
    finally:
        cursor.close()
        conn.close()




async def get_session_id_by_user_id(user_id: int) -> Optional[str]:
    """
    Retrieve the session ID for a given user ID.
    
    Args:
        user_id: The user's ID.
    
    Returns:
        The session ID as a string if a session exists, otherwise None.
    """
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT id FROM sessions WHERE user_id = %s", (user_id,))
        result = cursor.fetchone()
        if result:
            return result.get("id")
        return None
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()

@app.get("/api/{sensor_type}")
async def get_all_sensor_data(
    sensor_type: str,
    user_id: str = Depends(get_current_user),
    order_by: Optional[str] = Query(None, alias="order-by"),
    start_date: Optional[str] = Query(None, alias="start-date"),
    end_date: Optional[str] = Query(None, alias="end-date")
):
    """Fetch sensor data with optional filtering and sorting."""
    if sensor_type not in ["temperature", "humidity", "light"]:
        raise HTTPException(status_code=404, detail="Invalid sensor type")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        query = f"""
            SELECT s.* FROM {sensor_type} s
            JOIN devices d ON s.device_id = d.device_id
            WHERE d.user_id = %s
        """
        params = [user_id]

        if start_date:
            query += " AND s.timestamp >= %s"
            params.append(start_date)

        if end_date:
            query += " AND s.timestamp <= %s"
            params.append(end_date)

        if order_by in ["value", "timestamp"]:
            query += f" ORDER BY s.{order_by} ASC"

        cursor.execute(query, params)
        data = cursor.fetchall()

        # Convert timestamp fields to the expected format
        for record in data:
            ts = record.get("timestamp")
            if ts and isinstance(ts, datetime):
                record["timestamp"] = ts.strftime("%Y-%m-%d %H:%M:%S")

        return data
    finally:
        cursor.close()
        conn.close()

async def delete_session(session_id: str) -> bool:
    """Delete a session from the database."""
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("DELETE FROM sessions WHERE id = %s", (session_id,))
        connection.commit()
        return True
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()



# Helper function to get current user's ID (can be used in other routes)
def get_current_user_id(response: Response) -> int:
    user_id = response.cookies.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return int(user_id)



@app.post("/signup")
def signup(
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    location: str = Form(...),
    PID: str = Form(...)

):
    conn = get_db_connection()
    cursor = conn.cursor()
    # Check if the email already exists
    cursor.execute('''
        SELECT id FROM users WHERE email = ?
    ''', (email,))
    existing_user = cursor.fetchone()
    
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Hash the password
    hashed_password = hash_password(password)
    
    # Insert the new user
    cursor.execute('''
        INSERT INTO users (name, email, hashed_password, location, PID)
        VALUES (?, ?, ?, ?, ?)
    ''', (name, email, hashed_password, location, PID))
    conn.commit()
    
    # After successful registration, redirect to login with success message
    return RedirectResponse(
        url="/login?message=Successfully+Registered!!!",
        status_code=303
    )

async def get_user_by_email(email: str) -> Optional[dict]:
    """Retrieve user from database by username."""
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        return cursor.fetchone()
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()

async def create_session(user_id: int, session_id: str) -> bool:
    """Create a new session in the database."""
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO sessions (id, user_id) VALUES (%s, %s)", (session_id, user_id)
        )
        connection.commit()
        return True
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()

@app.post("/login")
async def login(
    email: str = Form(...),
    password: str = Form(...),
    response: Response = None
):
    try:
        # Hash the password for comparison
        hashed_password = hash_password(password)
        conn = get_db_connection()
        cursor = conn.cursor()
        user = await get_user_by_email(email)
        username = user["username"]
        print(username)
        if not user or user["password"] != password:
        # You could redirect back to login with an error message or display an error page.
            return HTMLResponse(content="Invalid username or password", status_code=401)
        # Check if user exists and password matches
        cursor.execute('''
            SELECT id, email FROM users WHERE email = ? AND hashed_password = ?
        ''', (email, hashed_password))
        user = cursor.fetchone()
        session_id = str(uuid.uuid4())
        await create_session(username, session_id)
        response = RedirectResponse(url=f"/dashboard", status_code=302)
        response.set_cookie(key="session_id", value=session_id, httponly=True, max_age = 3600)
        return response
        

        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/{sensor_type}")
async def insert_sensor_data(
    sensor_type: str,
    data: SensorData,
    user_id: str = Depends(get_current_user)
    
):
    """Insert new sensor data."""
    if sensor_type not in ["temperature", "humidity", "light"]:
        raise HTTPException(status_code=404, detail="Invalid sensor type")

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Verify device belongs to user
        cursor.execute('''
            SELECT device_id FROM devices 
            WHERE user_id = %s AND device_id = %s
        ''', (user_id, data.device_id))
        if not cursor.fetchone():
            raise HTTPException(status_code=403, detail="Device not authorized")

        timestamp = data.timestamp if data.timestamp else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        query = f"""
            INSERT INTO {sensor_type} (value, unit, timestamp, device_id)
            VALUES (%s, %s, %s, %s)
        """
        cursor.execute(query, (data.value, data.unit, timestamp, data.device_id))
        conn.commit()
        return {"id": cursor.lastrowid}
    finally:
        cursor.close()
        conn.close()

@app.get("/api/{sensor_type}/{id}")
async def get_sensor_data(
    sensor_type: str,
    id: int,
    user_id: str = Depends(get_current_user)
):
    """Get a specific sensor reading by ID."""
    if sensor_type not in ["temperature", "humidity", "light"]:
        raise HTTPException(status_code=404, detail="Invalid sensor type")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        query = f"""
            SELECT s.* FROM {sensor_type} s
            JOIN devices d ON s.device_id = d.device_id
            WHERE s.id = %s AND d.user_id = %s
        """
        cursor.execute(query, (id, user_id))
        data = cursor.fetchone()

        if not data:
            raise HTTPException(status_code=404, detail="Data not found")

        return data
    finally:
        cursor.close()
        conn.close()

@app.put("/api/{sensor_type}/{id}")
async def update_sensor_data(
    sensor_type: str,
    id: int,
    data: SensorData,
    user_id: str = Depends(get_current_user)
):
    """Update an existing sensor reading."""
    if sensor_type not in ["temperature", "humidity", "light"]:
        raise HTTPException(status_code=404, detail="Invalid sensor type")

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Verify device belongs to user
        cursor.execute('''
            SELECT device_id FROM devices 
            WHERE user_id = %s AND device_id = %s
        ''', (user_id, data.device_id))
        if not cursor.fetchone():
            raise HTTPException(status_code=403, detail="Device not authorized")

        updates = []
        params = []

        if data.value is not None:
            updates.append("value = %s")
            params.append(data.value)
        if data.unit:
            updates.append("unit = %s")
            params.append(data.unit)
        if data.timestamp:
            updates.append("timestamp = %s")
            params.append(data.timestamp)

        if not updates:
            raise HTTPException(status_code=400, detail="No fields to update")

        params.extend([id, user_id])
        query = f"""
            UPDATE {sensor_type} s
            JOIN devices d ON s.device_id = d.device_id
            SET {', '.join(updates)}
            WHERE s.id = %s AND d.user_id = %s
        """
        cursor.execute(query, params)
        conn.commit()

        return {"message": "Updated successfully"}
    finally:
        cursor.close()
        conn.close()

# @app.get("/get_devices")
# async def get_devices():
#     try:
        

    
#     except mysql.connector.Error as e:
#         import traceback
#         print("Database Error:", traceback.format_exc())
#         raise HTTPException(status_code=500, detail=f"Database error: {e}")
    
@app.get("/get_temp/{mac_address}")
async def get_temp(mac_address: str):
    try:
        conn = get_db_connection()
        # Using a dictionary cursor so that we get results as dicts.
        cursor = conn.cursor(dictionary=True)
        sql = "SELECT id, temperature, units, mac_address FROM temperature WHERE mac_address = %s"
        cursor.execute(sql, (mac_address,))
        records = cursor.fetchall()
        if not records:
            raise HTTPException(status_code=404, detail="No temperature data found for the given MAC address.")
        return {"data": records}
    except mysql.connector.Error as e:
        import traceback
        print("Database Error:", traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

@app.post("/add_temp")
async def add_temp(data: TemperatureData):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Access the fields from the model
        temp = str(data.value)
        print(temp + " " + data.unit + " " + data.mac_address)
        sql = "INSERT INTO temperature (temperature, units, mac_address) VALUES (%s, %s, %s)"
        values = (str(data.value), data.unit, data.mac_address)
        cursor.execute(sql, values)
        conn.commit() 
        return {"message": "Temperature data added successfully."}
    except mysql.connector.Error as e:
        import traceback
        print("Database Error:", traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

@app.delete("/api/{sensor_type}/{id}")
async def delete_sensor_data(
    sensor_type: str,
    id: int,
    user_id: str = Depends(get_current_user)
):
    """Delete a sensor reading."""
    if sensor_type not in ["temperature", "humidity", "light"]:
        raise HTTPException(status_code=404, detail="Invalid sensor type")

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        query = f"""
            DELETE s FROM {sensor_type} s
            JOIN devices d ON s.device_id = d.device_id
            WHERE s.id = %s AND d.user_id = %s
        """
        cursor.execute(query, (id, user_id))
        conn.commit()

        return {"message": "Deleted successfully"}
    finally:
        cursor.close()
        conn.close()

# Weather App
def get_loc(city: str):
    url = f"https://nominatim.openstreetmap.org/search?q={city.replace(' ', '%20')}&format=json"
    response = urlopen(url).read().decode()
    data = json.loads(response)
    if data:
        lat = data[0]['lat']
        lon = data[0]['lon']
        return lat, lon
    return None, None

from urllib.request import urlopen
import json

def get_weather(lat: str, lon: str):
    url = f"https://api.weather.gov/points/{lat},{lon}"
    response = urlopen(url)
    if response.getcode() != 200:
        return {"error": "Could not fetch weather data."}
    
    # Read and decode the response
    response_text = response.read().decode()
    data = json.loads(response_text)
    
    if "properties" in data:
        forecast_url = data["properties"]["forecast"]
        forecast_response = urlopen(forecast_url)
        if forecast_response.getcode() != 200:
            return {"error": "Could not fetch forecast data."}
        forecast_text = forecast_response.read().decode()
        forecast_data = json.loads(forecast_text)
        return forecast_data["properties"]["periods"][0]
    return None


@app.get("/weather", response_class=HTMLResponse)
async def home():
    with open("Weather/weather.html") as html:
        return HTMLResponse(content=html.read())

@app.post("/weather")
async def weather(city: str = Form(...)):
    if not city.strip():  
        return {"error": "City name cannot be empty"}  
    
    lat, lon = get_loc(city)
    if not lat or not lon:
        return {"error": "City not found"}
    
    if lat and lon:
        weather_data = get_weather(lat, lon)

        if not weather_data:
            return {"error": "Weather data unavailable"}
        
        if weather_data:
            return {
                "location": city,
                "condition": weather_data["shortForecast"],
                "temperature": f"{weather_data['temperature']}°{weather_data['temperatureUnit']}"
                }
    return {"error": "Data not found"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app="app.main:app", host="0.0.0.0", port=6543, reload=True)
