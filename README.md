## Widgera – Structured LLM Responses from Text + Images

This project lets a user:

- **Register / log in**
- **Upload an image** (stored in S3-compatible storage – MinIO)
- **Define a dynamic response structure** (any number of fields, each `string` or `number`)
- **Send a prompt + optional image to an LLM**, and
- **Display a structured JSON response** that matches the defined fields.

It includes optional optimizations:

- **Per-user image deduplication** by content hash – the same image file is never uploaded twice for one user.
- **Cross-user query caching** – identical `(prompt + field structure + image)` requests reuse the same cached LLM response.

Everything runs with a **single command**:

```bash
docker compose up --build
```

and exposes:

- **Frontend (React)**: `http://localhost:5173`
- **Backend (FastAPI)**: `http://localhost:8000`
- **MinIO Console (optional)**: `http://localhost:9001`

---

## 1. Architecture Overview

- **Frontend**: React + Vite + TypeScript (folder `frontend`)
  - Login / registration screen
  - Main app: prompt input, dynamic field builder, image upload, structured JSON result
  - Talks to backend via `VITE_API_BASE_URL` (default `http://localhost:8000`)

- **Backend**: FastAPI (folder `backend`)
  - **Authentication**
    - `/auth/register` – username, password, confirm password
    - `/auth/login` – returns JWT access token
  - **Image Handling**
    - `/api/upload-image` – uploads to MinIO, per-user dedup by content hash
  - **LLM Structured Output**
    - `/api/structured-query` – accepts prompt + field structure (+ optional image reference)
    - Calls OpenAI `gpt-4o-mini` with a **JSON Schema** response format
    - Returns `{"result": {...}, "cached": boolean}`
  - **Caching**
    - Uses Postgres table `query_cache` keyed by a hash of `(prompt, fields, image_hash)`

- **Storage & Infrastructure**
  - **Postgres** – user accounts, images, cache
  - **MinIO** – S3-compatible object storage for images
  - **Docker Compose** – runs everything together

---

## 2. Prerequisites

On your Windows machine (or any OS), make sure you have:

- **Docker Desktop** installed and running
  - Download from the official Docker website and follow installation wizard
- An **OpenAI API key**
  - Create an account, generate a key, and keep it ready (it will be placed into `.env`)

No local Python or Node installation is required if you use Docker.

---

## 3. Environment Configuration

> The repository does **not** include a real `.env` file for security reasons.  
> You must create one in the **project root** (`Widgera/.env`) before running Docker.

1. In the root folder (same level as `docker-compose.yml`), create a new file named `.env`.

2. Paste the following template and fill in your own `OPENAI_API_KEY` (you can keep the other defaults if you like):

```bash
OPENAI_API_KEY=sk-your-openai-api-key-here

# Postgres
POSTGRES_USER=widgera
POSTGRES_PASSWORD=widgera_password
POSTGRES_DB=widgera

# MinIO (S3-compatible storage)
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin
MINIO_BUCKET_NAME=widgera-images

# JWT
JWT_SECRET_KEY=change_this_in_production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60

# Frontend
VITE_API_BASE_URL=http://localhost:8000
```

3. Save the file as `.env`.

Docker Compose will automatically load this file for both the backend and frontend containers.

---

## 4. Running the Application with Docker

From the **project root** (folder containing `docker-compose.yml`):

1. Open a terminal (PowerShell is fine) and `cd` into the project:

```powershell
cd C:\Users\sabak\OneDrive\Documents\Widgera
```

2. Build and start all services:

```powershell
docker compose up --build
```

The first run will:

- Download Docker images for Postgres, MinIO, Node, and Python
- Install Python dependencies for the backend
- Install Node dependencies for the frontend
- Start all containers (db, minio, backend, frontend)

3. When startup finishes, you should see logs from:

- Postgres
- MinIO
- FastAPI backend (`Uvicorn running on 0.0.0.0:8000`)
- Vite dev server (`http://0.0.0.0:5173`)

4. Open your browser:

- **Main app**: `http://localhost:5173`
- (Optional) **API docs**: `http://localhost:8000/docs`
- (Optional) **Health check**: `http://localhost:8000/health`
- (Optional) **MinIO console**: `http://localhost:9001`  
  Login with `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD` from `.env`.

5. To stop everything:

```powershell
Ctrl+C  # in the terminal running docker compose
docker compose down
```

---

## 5. Frontend – Usage Walkthrough

Once `http://localhost:5173` is open:

### 5.1 Register or Login

- You’ll see a **card** with tabs:
  - **Login**
  - **Register**
- For a new user:
  - Switch to **Register**
  - Enter:
    - **Username**
    - **Password**
    - **Confirm Password**
  - Click **Create Account**
  - On success, the UI will switch back to **Login**; log in with your new credentials.

On successful login:

- A JWT access token is stored in `localStorage` (`authToken`)
- The UI switches to the **main interface**

### 5.2 Main Interface

The main screen has:

- **Header**
  - App title, subtitle
  - **Logout** button
- **Left card** – Prompt, image, and response structure
- **Right card** – Structured JSON output

Steps:

1. **Prompt**
   - Enter a prompt, e.g.
     - `"Who invented the Turing machine? Return full name and birth year. Also return the number printed on the runner's shirt in the attached photo."`

2. **Image (optional)**
   - Click the file input and select an image file.
   - When you submit, the frontend calls `/api/upload-image`; the backend:
     - Computes a **SHA-256 hash** of its content
     - Checks if this user has already uploaded an image with the same hash
       - If yes: **reuses the existing record and object key**
       - If no: uploads the file to MinIO and stores metadata in Postgres

3. **Response Structure**
   - You can:
     - Edit field names
     - Change type (`string` / `number`)
     - Add more fields via **+ Add Field**
     - Remove fields via the `✕` button

4. Click **Submit**
   - The frontend:
     - Ensures the image (if present) is uploaded and has an `image_id`
     - Sends:
       - `prompt`
       - `fields` array
       - optional `image_id`
       - Bearer token in `Authorization` header
     - To `POST /api/structured-query`

5. **View Results**
   - The right panel shows:
     - A small **“Loaded from cache…” badge** if the result was cached
     - The **JSON** that matches your defined fields

---

## 6. Backend – Important Endpoints & Behavior

### 6.1 Authentication

- **POST `/auth/register`**
  - Body: JSON
    - `username` – string
    - `password` – string
    - `password_confirm` – string
  - Validates:
    - Passwords match
    - Username is unique
  - Creates `users` row; hashes password with `bcrypt`.

- **POST `/auth/login`**
  - Body: `application/x-www-form-urlencoded`
    - `username`
    - `password`
  - On success:
    - Returns `{ "access_token": "<JWT>", "token_type": "bearer" }`
  - The frontend uses this token for all authenticated requests.

### 6.2 Image Upload & Deduplication

- **POST `/api/upload-image`**
  - Auth: **required** (`Authorization: Bearer <token>`)
  - Body: multipart form, `file` field
  - Process:
    1. Read file bytes
    2. Compute SHA-256 hash
    3. Check Postgres table `images` for `(user_id, content_hash)`
       - If exists → return existing `image_id` without uploading
       - If not → upload bytes to MinIO bucket, create DB row
  - Response:
    - `image_id` – used by `/api/structured-query`

### 6.3 Structured LLM Query + Caching

- **POST `/api/structured-query`**
  - Auth: **required**
  - Body:
    - `prompt` – text
    - `fields` – array of `{ name: string, type: "string" | "number" }`
    - `image_id` – optional UUID (returned from `/api/upload-image`)
  - Internal flow:
    1. If `image_id` is provided:
       - Fetch metadata from `images` table (and verify owner)
       - Download bytes from MinIO
       - Use the stored `content_hash` as `image_hash` for caching
    2. Build a **cache key** from:
       - `prompt`
       - `fields` (serialized array)
       - `image_hash` (or `null`)
       - Hash this payload with SHA-256
    3. Check `query_cache` table for the computed `cache_key`
       - If hit → return `{"result": cached_json, "cached": true}`
    4. If miss:
       - Build a **JSON Schema** enforcing your fields and types
       - Call OpenAI `gpt-4o-mini` with:
         - Messages containing the prompt and optional image (inline base64)
         - `response_format` of type `json_schema`
       - Parse the JSON response
       - Insert cache row (with `cache_key` and response JSON)
       - Return `{"result": parsed_json, "cached": false}`

---

## 7. Local Development Without Docker (Optional)

If you prefer to run backend and frontend directly on your machine:

### 7.1 Backend

1. Install Python 3.11+
2. Create and activate a virtual environment
3. Install requirements:

```bash
cd backend
pip install -r requirements.txt
```

4. Ensure Postgres + MinIO are running and that your environment variables match the values in `.env`.

5. Start the FastAPI server:

```bash
uvicorn app.main:app --reload
```

Backend will listen on `http://localhost:8000`.

### 7.2 Frontend

1. Install Node.js 18+ (or 20+ recommended)
2. Install dependencies:

```bash
cd frontend
npm install
```

3. Create `frontend/.env` with:

```bash
VITE_API_BASE_URL=http://localhost:8000
```

4. Run Vite dev server:

```bash
npm run dev
```

Visit `http://localhost:5173`.

---

## 8. Notes on Caching & Optimization

- **Query Caching**
  - Implemented in `query_cache` table (see backend code).
  - The key is a SHA-256 hash of:
    - prompt text
    - field structure (+ order)
    - image hash (or `null` if no image)
  - This means:
    - Any user who sends the same logical query (including the same image bytes) benefits from the cached answer.

- **Image Deduplication (Per User)**
  - The `images` table includes a unique constraint on `(user_id, content_hash)`.
  - This prevents multiple uploads of the same file for the same user.
  - The MinIO object is only created once per unique `(user_id, content_hash)` pair.

If you wanted, you could extend this to:

- Global image dedup across all users
- TTL-based cache invalidation
- Redis or another in-memory store instead of Postgres for cache

---

## 9. Where to Look in the Code

- **Backend**
  - `backend/app/main.py` – FastAPI app factory and router registration
  - `backend/app/models.py` – SQLAlchemy models (`User`, `Image`, `QueryCache`)
  - `backend/app/routes_auth.py` – registration & login endpoints
  - `backend/app/routes_llm.py` – image upload, structured query, caching logic
  - `backend/app/storage.py` – MinIO integration & hashing helpers
  - `backend/app/auth.py` – password hashing, JWT token generation, current user dependency

- **Frontend**
  - `frontend/src/App.tsx` – entire UI (auth + main app)
  - `frontend/src/api.ts` – minimal API client for the backend
  - `frontend/src/styles.css` – modern interface styling

---

## 10. Summary

- **One-command deployment** via `docker compose up --build`
- **JWT auth**, **image upload to MinIO**, and **LLM structured JSON output** using OpenAI
- **Dynamic field builder** lets the user define any structured response shape
- **Caching and deduplication** are fully implemented while keeping the code readable and documented

If you’d like, you can extend this project with:

- A dedicated “history” view of previous queries
- Support for additional field types (booleans, arrays, nested objects)
- Alternative LLM providers or LangChain-based orchestration


