from fastapi import APIRouter, HTTPException, Response, Form, Request, Depends, Cookie
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse, FileResponse
from fastapi.templating import Jinja2Templates
from ..database import get_db_connection
from ..dependencies import hash_password
import os
import uuid
import hashlib
from typing import Optional

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@router.get("/signup", response_class=HTMLResponse)
async def signup_page(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})

@router.post("/signup")
async def signup(
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    location: str = Form(...),
    PID: str = Form(...)
):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Check if email exists
        cursor.execute('SELECT id FROM users WHERE email = %s', (email,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Email already registered")

        # Hash password and insert user
        hashed_password = hash_password(password)
        
        cursor.execute('''
            INSERT INTO users (name, email, hashed_password, location, PID)
            VALUES (%s, %s, %s, %s, %s)
        ''', (name, email, hashed_password, location, PID))
        conn.commit()

        return RedirectResponse(
            url="/login",
            status_code=303
        )
    except Exception as e:
        import traceback
        print("Database Error:", traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    finally:
        cursor.close()
        conn.close()

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

@router.get("/user_info")
async def getuserInformation(request: Request):
    from datetime import datetime
    session_id = request.cookies.get("session_id")
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        # Use the correct column name: sessions.id instead of session_id
        cursor.execute(
            '''
            SELECT user_id FROM sessions WHERE id = %s
            ''', (session_id,)
        )
        user_id_row = cursor.fetchone()
        if not user_id_row: 
            raise HTTPException(status_code=404, detail="user not found")
        # Extract the user_id (assuming it's the first element in the tuple)
        user_id = user_id_row[0]
        
        cursor.execute(
            "SELECT * FROM users WHERE id = %s", (user_id,)
        )
        user = cursor.fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="user not found")
        
        # Construct user_data (adjust indexes based on your table schema)
        user_data = {
            "id": user[0],
            "username": user[1],
            "email": user[2],
            "PID": user[4],
            "Location": user[5]
        }
        return JSONResponse(content=user_data)
    except Exception as e:
        import traceback
        print("Database Error:", traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    finally:
        cursor.close()
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

@router.post("/login")
async def login(
    email: str = Form(...),
    password: str = Form(...),
    response: Response = None
):
    try:
        # Hash the provided password for comparison
        hashed_password = hash_password(password)
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Retrieve user by email
        user = await get_user_by_email(email)
        if not user:
            # User not found: return an error response
            return HTMLResponse(content="Invalid username or password", status_code=401)
        
        # Retrieve necessary fields from the found user
        username = user["email"]  # or user["username"] if applicable
        user_id = user["id"]
        print(username)
        print(hashed_password)
        
        # Ensure you're comparing the right field: update 'password' to 'hashed_password' if needed
        if user.get("hashed_password") != hashed_password:
            return HTMLResponse(content="Invalid username or password", status_code=401)
        
        # Optionally, you can perform a SELECT query to double-check (not strictly necessary here)
        cursor.execute(
            "SELECT id, email FROM users WHERE email = %s AND hashed_password = %s",
            (email, hashed_password)
        )
        user_record = cursor.fetchone()
        if not user_record:
            return HTMLResponse(content="Invalid username or password", status_code=401)
        
        # Create a new session for the user
        session_id = str(uuid.uuid4())
        await create_session(user_id, session_id)
        response = RedirectResponse(url="/dashboard", status_code=302)
        response.set_cookie(key="session_id", value=session_id, httponly=True, max_age=3600)
        return response

    except Exception as e:
        import traceback
        print("Database Error:", traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    finally:
        cursor.close()
        conn.close()


def hash_password(password: str) -> str:
    """Hash a password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()
@router.get("/dashboard", response_class=HTMLResponse)
async def read_dashboard(request: Request):
    session_id = request.cookies.get("session_id")
    if not session_id:
        return RedirectResponse(url="/login", status_code=302)
    # Get the directory of the current file (e.g., /code/app/routers)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Go up one level to /code/app and then join dashboard.html
    dashboard_path = os.path.join(current_dir, "../templates", "dashboard.html")
    
    if not os.path.exists(dashboard_path):
        raise HTTPException(status_code=500, detail="Dashboard not found.")
    
    return FileResponse(dashboard_path)

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

@router.post("/logout")
async def logout(request: Request):
    session_id = request.cookies.get("session_id")
    response = RedirectResponse(url="/login", status_code=302)
    if session_id:
        await delete_session(session_id)
        # Delete the session cookie
        response.delete_cookie("session_id")
    return response
