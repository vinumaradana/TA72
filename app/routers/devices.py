from fastapi import APIRouter, HTTPException, Form, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from ..database import get_db_connection
from typing import Optional

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

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
        print(user_id)
        return user_id
    finally: 
        cursor.close()
        conn.close()

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
            FROM sessions s
            WHERE s.id = %s
        """,
            (session_id,),
        )
        return cursor.fetchone()
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()



@router.get("/profile", response_class=HTMLResponse)
async def get_profile_page(request: Request):
    user_id = authenticate(request)
    print(user_id)
    if user_id is None:
        return RedirectResponse(url="login", status_code = 302)
    return templates.TemplateResponse("profile.html", {"request": request})

@router.post("/register-device")
async def register_device(
    request: Request,
    mac_address: str = Form(...),
):
    user_id = await authenticate(request)
    if user_id is None:
        return RedirectResponse(url="login", status_code=302)
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO devices (user_id, device_id)
            VALUES (%s, %s)
        """, (user_id, mac_address))
        conn.commit()
        return {"message": "Device registered successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        cursor.close()
        conn.close()


@router.delete("/delete-device/{mac_address}")
async def delete_device(
    request: Request,
    mac_address: str,
):
    user_id = authenticate(request)
    print(user_id)
    if user_id is None:
        return RedirectResponse(url="login", status_code = 302)
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # First verify the device belongs to the user
        cursor.execute('''
            SELECT mac_address FROM devices 
            WHERE user_id = %s AND mac_address = %s
        ''', (user_id, mac_address))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Device not found or not authorized")

        cursor.execute('''
            DELETE FROM devices 
            WHERE user_id = %s AND mac_address = %s
        ''', (user_id, mac_address))
        conn.commit()
        return {"message": "Device deleted successfully"}
    finally:
        cursor.close()
        conn.close() 
