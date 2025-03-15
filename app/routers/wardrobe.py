from fastapi import APIRouter, Request, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from ..database import get_db_connection, get_session

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
        return user_id
    finally: 
        cursor.close()
        conn.close()



@router.get("/wardrobe")

async def get_wardrobe_page(request: Request):
    user_id = await authenticate(request)
    if user_id is None:
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse("wardrobe.html", {"request": request})

@router.get("/api/wardrobe")
async def get_wardrobe_items(request: Request):
    session_id = request.cookies.get("session_id")
    if not session_id:
        return RedirectResponse(url="/login", status_code=302)
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute('''
            SELECT id, item_name, item_type 
            FROM wardrobe 
            WHERE user_id = %s
        ''', (user_id,))
        items = cursor.fetchall()
        return items
    finally:
        cursor.close()
        conn.close()

@router.post("/add-item")
async def add_item(
    request: Request,
    item_name: str = Form(...),
    item_type: str = Form(...),
):
    session_id = request.cookies.get("session_id")
    if not session_id:
        return RedirectResponse(url="/login", status_code=302)
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            INSERT INTO wardrobe (item_name, item_type, user_id)
            VALUES (%s, %s, %s)
        ''', (item_name, item_type, user_id))
        conn.commit()
        return {"message": "Item added successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()

@router.delete("/delete-item/{item_id}")
async def delete_item(request: Request, item_id: int):
    session_id = request.cookies.get("session_id")
    if not session_id:
        return RedirectResponse(url="/login", status_code=302)
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            DELETE FROM wardrobe 
            WHERE id = %s AND user_id = %s
        ''', (item_id, user_id))
        conn.commit()
        return {"message": "Item deleted successfully"}
    finally:
        cursor.close()
        conn.close() 
