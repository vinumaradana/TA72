from fastapi import APIRouter, Request, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from ..database import get_db_connection
from ..dependencies import get_current_user

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/wardrobe", response_class=HTMLResponse)
async def get_wardrobe_page(request: Request, user_id: str = Depends(get_current_user)):
    return templates.TemplateResponse("wardrobe.html", {"request": request})

@router.get("/api/wardrobe")
async def get_wardrobe_items(user_id: str = Depends(get_current_user)):
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
    item_name: str = Form(...),
    item_type: str = Form(...),
    user_id: str = Depends(get_current_user)
):
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
async def delete_item(item_id: int, user_id: str = Depends(get_current_user)):
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