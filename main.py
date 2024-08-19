import datetime
import json
import os
import re
import uuid

import psycopg2
import redis
import requests
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, Response
from redis import Redis
from starlette.responses import RedirectResponse

r: Redis = redis.Redis(
  ssl=os.getenv("REDIS_SSL"),
  host=os.getenv("REDIS_HOST"),
  port=os.getenv("REDIS_PORT"),
  password=os.getenv("REDIS_PASSWORD"),
)

countries = {}

app = FastAPI(
    title="BlinkLink",
    description=(
        "API RESTful para acortar URLs.\n\n"
        "### Pasos para usarla:\n\n"
        "1. **Haz deploy en Render**:\n"
        "   - Clona el repositorio desde [GitHub](https://github.com/pyoneerC/urlshortener).\n"
        "   - En Render, crea un nuevo servicio y selecciona este repositorio.\n\n"
        "2. **Configura el Comando de Inicio**:\n"
        "   - En el campo 'Comando de inicio' de tu servicio en Render, ingresa:\n"
        "     ```\n"
        "     uvicorn main:app --host 0.0.0.0 --port $PORT\n"
        "     ```\n\n"
        "3. **Agrega las Variables de Entorno**:\n"
        "   - En la sección de variables de entorno en Render, agrega las siguientes variables:\n\n"
        "   - **API_KEY**: Tu API key de [ipgeolocation.io](https://ipgeolocation.io).\n\n"
        "   - **PostgreSQL**:\n"
        "     ```\n"
        "     DATABASE_URL=<tu_database_url>\n"
        "     PGGSSENCMODE=disable\n"
        "     ```\n\n"
        "   - **Redis**:\n"
        "     ```\n"
        "     REDIS_HOST=<tu_redis_host>\n"
        "     REDIS_PASSWORD=<tu_redis_password>\n"
        "     REDIS_PORT=6379\n"
        "     REDIS_SSL=true\n"
        "     ```\n\n"
        "   - **ADMIN_PASSWORD**: Una contraseña para crear usuarios administradores.\n\n"
        "4. **Accede a tu servicio**:\n"
        "   - Una vez configurado, accede a la URL de tu servicio en Render y comienza a usar la API RESTful de BlinkLink!\n"
    ),
    version="2.0.0",
    openapi_tags=[
        {"name": "shorten", "description": "Operaciones CRUD para acortar URLs"},
        {"name": "users", "description": "Operaciones CRUD para usuarios"}
    ],
    contact={
        "name": "Max Comperatore",
        "url": "https://maxcomperatore.com",
        "email": "maxcomperatore@gmail.com"
    },
    license_info={
        "name": "Licencia MIT",
        "url": "https://opensource.org/licenses/MIT"
    }
)

def get_db_connection():
    return psycopg2.connect(os.getenv("DATABASE_URL"))

@app.post("/shorten", summary="Crea un nuevo enlace corto", tags=["shorten"], description="Crea un nuevo enlace corto a partir de una URL dada.", response_model=dict)
async def create_short_url(url: str):
    try:
        response = requests.get(url, timeout=5)
        if response.status_code < 200 or response.status_code >= 400:
            raise HTTPException(status_code=404, detail="Invalid URL")

        code = uuid.uuid4().hex[:6]
        created_at = datetime.datetime.now()
        expiration_date = created_at + datetime.timedelta(days=69)

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM urls WHERE short_code = %s", (code,))
        existing_url = cursor.fetchone()
        if existing_url:
            cursor.close()
            conn.close()

            return JSONResponse(
                status_code=409,
                content={
                    "error": "Conflict",
                    "message": f"Short code already exists!",
                    "short_code": code
                }
            )

        cursor.execute(
            "INSERT INTO urls (short_code, original_url, created_at, last_updated_at, expiration_date, access_count) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (code, url, created_at, created_at, expiration_date, 0)
        )
        conn.commit()
        cursor.close()
        conn.close()

        return {
            "short_code": code,
            "original_url": url,
            "created_at": created_at.strftime("%Y-%m-%d %H:%M:%S %p"),
            "last_updated_at": created_at.strftime("%Y-%m-%d %H:%M:%S %p"),
            "expiration_date": expiration_date.strftime("%Y-%m-%d %H:%M:%S %p"),
            "access_count": 0
        }

    except requests.exceptions.RequestException:
        raise HTTPException(status_code=404, detail="An error occurred while validating the URL, please try again later (or try putting 'http://' or 'https://' in front of the URL)")
    except psycopg2.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

@app.get("/shorten/{short_code}", summary="Obtiene información de un enlace corto", tags=["shorten"], description="Obtiene información detallada de un enlace corto a partir de su código.", response_model=dict)
async def get_url_info(short_code: str):
    cached_url = r.get(short_code)
    if cached_url:
        return json.loads(cached_url)

    try:
        conn, cursor, result = await connect_to_db_and_check_validity(short_code)

        result = {
            "short_code": result[1],
            "original_url": result[2],
            "created_at": result[3].strftime("%Y-%m-%d %H:%M:%S %p"),
            "last_updated_at": result[4].strftime("%Y-%m-%d %H:%M:%S %p"),
            "expiration_date": result[5].strftime("%Y-%m-%d %H:%M:%S %p"),
            "access_count": result[6]
        }

        r.setex(short_code, 180, json.dumps(result))

        return result

    except psycopg2.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

@app.put("/shorten", summary="Actualiza un enlace corto", tags=["shorten"], description="Actualiza la URL original de un enlace corto.", response_model=dict)
async def update_short_url(short_code: str, url: str):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM urls WHERE short_code = %s", (short_code,))
        result = cursor.fetchone()

        if result is None:
            raise HTTPException(status_code=404, detail="Short code not found")

        expiration_date = result[5]
        if expiration_date < datetime.datetime.now():
            await delete_short_url(short_code)
            raise HTTPException(status_code=404, detail="Short code has expired")

        if url == result[2]:
            raise HTTPException(status_code=409, detail=f"New URL is the same as the current URL: {url}")

        if not url.startswith("http://") and not url.startswith("https://"):
            raise HTTPException(status_code=404, detail="Invalid URL, please include 'http://' or 'https://' in front of the URL")

        last_updated_at = datetime.datetime.now()

        cursor.execute(
            "UPDATE urls SET original_url = %s, last_updated_at = %s, access_count = 0 WHERE short_code = %s",
            (url, last_updated_at, short_code)
        )
        conn.commit()

        cursor.execute("SELECT * FROM urls WHERE short_code = %s", (short_code,))
        updated_result = cursor.fetchone()

        cursor.close()
        conn.close()

        return {
            "short_code": updated_result[1],
            "original_url": updated_result[2],
            "created_at": updated_result[3].strftime("%Y-%m-%d %H:%M:%S %p"),
            "last_updated_at": updated_result[4].strftime("%Y-%m-%d %H:%M:%S %p"),
            "expiration_date": updated_result[5].strftime("%Y-%m-%d %H:%M:%S %p"),
            "access_count": updated_result[6]
        }

    except psycopg2.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

@app.delete("/shorten/{short_code}", summary="Elimina un enlace corto", tags=["shorten"], description="Elimina un enlace corto a partir de su código.", response_model=dict)
async def delete_short_url(short_code: str):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM urls WHERE short_code = %s", (short_code,))
        result = cursor.fetchone()

        if result is None:
            cursor.close()
            conn.close()
            raise HTTPException(status_code=404, detail="Short code not found")

        cursor.execute("DELETE FROM urls WHERE short_code = %s", (short_code,))
        conn.commit()

        cursor.close()
        conn.close()

        return Response(status_code=204)

    except psycopg2.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")


@app.get("/", summary="Redirige a la URL original", tags=["shorten"], description="Redirige a la URL original a partir de un enlace corto.", response_class=RedirectResponse)
async def redirect_to_url(short_code: str):
    try:
        conn, cursor, result = await connect_to_db_and_check_validity(short_code)

        cursor.execute("UPDATE urls SET access_count = %s WHERE short_code = %s", (result[6] + 1, short_code))
        conn.commit()

        url = 'https://api.ipgeolocation.io/ipgeo?apiKey=' + os.getenv("API_KEY")
        response = requests.get(url)
        data = response.json()

        country_name = data['country_name']
        state_prov = data['state_prov']
        ip = data['ip']
        latitude = data['latitude']
        longitude = data['longitude']

        if country_name in countries:
            countries[country_name] += 1
        else:
            countries[country_name] = 1

        if state_prov in countries:
            countries[state_prov] += 1
        else:
            countries[state_prov] = 1

        cursor.execute(
            """
            UPDATE urls
            SET locations_where_accessed = array_append(locations_where_accessed, %s),
                ip_addresses = array_append(ip_addresses, %s),
                latitude = %s,
                longitude = %s
            WHERE short_code = %s
            """,
            (f"{country_name}, {state_prov}", ip, latitude, longitude, short_code)
        )
        conn.commit()

        cursor.close()
        conn.close()

        return RedirectResponse(url=result[2])

    except psycopg2.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    except:
        raise HTTPException(status_code=404, detail="Short code not found")


async def connect_to_db_and_check_validity(short_code):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM urls WHERE short_code = %s", (short_code,))
    result = cursor.fetchone()
    if not result:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Short code not found")
    expiration_date = result[5]
    if expiration_date < datetime.datetime.now():
        cursor.close()
        conn.close()
        await delete_short_url(short_code)
        raise HTTPException(status_code=404, detail="Short code has expired")
    return conn, cursor, result


@app.get("/ping", summary="Verifica que el servicio esté en línea", description="Verifica que el servicio esté en línea y funcionando correctamente.", response_model=dict)
async def health_check():
    return JSONResponse(status_code=200, content={"status": "ok"})

@app.post("/login", summary="Inicia sesión", tags=["users"], description="Inicia sesión en el sistema.", response_model=dict)
async def login(email: str, password: str):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = %s AND password = %s",
                          (email, password))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        if user:
            return JSONResponse(status_code=200, content={"message": "Login successful"})
        else:
            raise HTTPException(status_code=401, detail="Invalid credentials")
    except psycopg2.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

@app.post("/register", summary="Registra un nuevo usuario", tags=["users"], description="Registra un nuevo usuario en el sistema.", response_model=dict)
async def register(email: str, password: str):
    try:
        email_regex = r"[^@]+@[^@]+\.[^@]+"
        if not re.match(email_regex, email):
            raise HTTPException(status_code=400, detail="Invalid email format")

        password_regex = r"^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]{8,}$"
        if not re.match(password_regex, password):
            raise HTTPException(status_code=400, detail="Password must be at least 8 characters long and contain at least one letter and one number")

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()

        if user:
            cursor.close()
            conn.close()
            raise HTTPException(status_code=409, detail="User already exists, please try again with a different email")

        if password == os.getenv("ADMIN_PASSWORD"):
            role = "admin"
        else:
            role = "user"

        cursor.execute("INSERT INTO users (email, password, created_at, role) VALUES (%s, %s, %s, %s)",
                       (email, password, datetime.datetime.now(), role))
        conn.commit()
        cursor.close()
        conn.close()
        return JSONResponse(status_code=201, content={"message": "User created"})
    except psycopg2.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")


@app.delete("/delete", summary="Elimina un usuario", tags=["users"], description="Elimina un usuario del sistema.", response_model=dict)
async def delete_user(email: str, password: str):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE email = %s AND password = %s", (email, password))
        user = cursor.fetchone()

        if user is None:
            cursor.close()
            conn.close()
            raise HTTPException(status_code=404, detail="User not found")

        cursor.execute("DELETE FROM users WHERE email = %s AND password = %s", (email, password))
        conn.commit()
        cursor.close()
        conn.close()
        return Response(status_code=204)

    except psycopg2.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")