import pathlib
import time

from fastapi import FastAPI, Depends, HTTPException, status, Path, Request, File, UploadFile
from sqlalchemy import text
from sqlalchemy.orm import Session

from db import get_db
from middlewares import CustomHeaderMiddleware
from models import User
# from models import Owner, Cat
from schemas import UserResponse, UserSchema

app = FastAPI()


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


app.add_middleware(CustomHeaderMiddleware)


@app.get("/")
def main_root():
    return {"message": "Application V0.0.1"}


@app.get("/users", response_model=list[UserResponse], tags=["users"])
async def get_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    return users


@app.get("/users/{users_id}", response_model=UserResponse, tags=["users"])
async def get_user_by_id(user_id: int = Path(ge=1), db: Session = Depends(get_db)):
    user = db.query(User).filter_by(id=user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="NOT FOUND")
    return user


@app.get("/users/{users_name}", response_model=UserResponse, tags=["users"])
async def get_user_by_name(user_name: str, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(name=user_name).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="NOT FOUND")
    return user


@app.post("/users", response_model=UserResponse, tags=["users"])
async def create_user(body: UserSchema, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(email=body.email).first()
    if user:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User is existing!")

    user = User(name=body.name, second_name=body.second_name, email=body.email, phone=body.phone, birth=body.birth,
                notes=body.notes)
    db.add(user)
    db.commit()
    return user


#
#
@app.put("/users/{user_id}", response_model=UserResponse, tags=["users"])
async def update_user(body: UserSchema, owner_id: int = Path(ge=1), db: Session = Depends(get_db)):
    user = db.query(User).filter_by(id=owner_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="NOT FOUND")

    user.email = body.email
    user.fullname = body.fullname
    user.phone = body.phone
    user.birth = body.birhday
    db.commit()
    return user


#
#
@app.delete("/users/{user_id}", response_model=UserResponse, tags=["users"])
async def delete_user(user_id: int = Path(ge=1), db: Session = Depends(get_db)):
    user = db.query(User).filter_by(id=user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="NOT FOUND")

    db.delete(user)
    db.commit()
    return user


@app.get("/api/healthchecker")
def healthchecker(db: Session = Depends(get_db)):
    try:
        # Make request
        result = db.execute(text("SELECT 1")).fetchone()
        if result is None:
            raise HTTPException(status_code=500, detail="Database is not configured correctly")
        return {"message": "Welcome to FastAPI!"}
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Error connecting to the database")

MAX_FILE_SIZE = 1_000_000


@app.post("/upload-file/")
async def create_upload_file(file: UploadFile = File()):
    pathlib.Path("uploads").mkdir(exist_ok=True)
    file_path = f"uploads/{file.filename}"

    file_size = 0
    with open(file_path, "wb") as f:
        while True:
            chunk = await file.read(1024)
            if not chunk:
                break
            file_size += len(chunk)
            if file_size > MAX_FILE_SIZE:
                f.close()
                pathlib.Path(file_path).unlink()
                raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                                    detail=f"File size is over the limit: {MAX_FILE_SIZE}")
            f.write(chunk)

    return {"file_path": file_path}
