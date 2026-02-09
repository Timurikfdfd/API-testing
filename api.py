from fastapi import FastAPI, HTTPException, UploadFile, File, Header, status, Form, Depends
import uuid
import os
import base64
from pathlib import Path
from datetime import datetime
import uuid
from typing import List, Optional

app = FastAPI()

users = {
    "4c1b3391576925b36c1ce627f38ea92d112f1a6ba440352ef703b205": {
        "username": "admin",
        "password": "admin"
    }
}

pets = []

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


def check_key(key: str) -> bool:
    return key in users


def get_auth_key(auth_key: Optional[str] = Header(None, alias="auth-key")) -> str:
    if not auth_key or not check_key(auth_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid auth_key"
        )
    return auth_key


@app.get("/api/key", status_code=status.HTTP_200_OK)
def login_user(username: str, password: str):
    for key, value in users.items():
        if value["username"] == username and value["password"] == password:
            return {
                "key": key
            }
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid username or password"
    )


@app.get("/api/pets", status_code=status.HTTP_200_OK)
def get_pets(
        auth_key: str = Depends(get_auth_key),
        filter_type: Optional[str] = "my_pets"
):
    if filter_type == "my_pets":
        return [pet for pet in pets if pet["user_id"] == auth_key]
    return pets


@app.post("/api/create_pet_simple", status_code=status.HTTP_201_CREATED)
def create_simple_pet(
        animal_type: str,
        name: str,
        age: int,
        auth_key: str = Depends(get_auth_key)
):
    if not animal_type or not name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required fields: animal_type and name are required"
        )

    if age < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Age cannot be negative"
        )

    if age > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Age is unrealistic for a pet"
        )

    allowed_animal_types = ["dog", "cat", "bird", "fish", "rabbit", "hamster", "turtle", "parrot", "other"]
    if animal_type.lower() not in allowed_animal_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid animal type. Allowed types: {', '.join(allowed_animal_types)}"
        )

    if len(name.strip()) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Name must be at least 2 characters long"
        )

    if len(name.strip()) > 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Name cannot exceed 50 characters"
        )

    new_pet = {
        "pet_id": str(uuid.uuid4()),
        "user_id": auth_key,
        "animal_type": animal_type.lower(),
        "name": name.strip(),
        "age": age,
        "pet_photo": None,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }

    pets.append(new_pet)

    return new_pet


@app.post("/api/pets", status_code=status.HTTP_201_CREATED)
async def create_pet_with_photo(
        animal_type: str = Form(...),
        name: str = Form(...),
        age: int = Form(...),
        pet_photo: UploadFile = File(None),
        auth_key: str = Depends(get_auth_key)
):
    if not animal_type.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Animal type is required"
        )

    if not name.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Name is required"
        )

    if age < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Age cannot be negative"
        )

    if age > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Age is unrealistic for a pet"
        )

    allowed_animal_types = ["dog", "cat", "bird", "fish", "rabbit", "hamster", "turtle", "parrot", "other"]
    animal_type_clean = animal_type.strip().lower()

    if animal_type_clean not in allowed_animal_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid animal type. Allowed types: {', '.join(allowed_animal_types)}"
        )

    name_clean = name.strip()
    if len(name_clean) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Name must be at least 2 characters long"
        )

    if len(name_clean) > 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Name cannot exceed 50 characters"
        )

    for pet in pets:
        if pet["user_id"] == auth_key and pet["name"].lower() == name_clean.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You already have a pet with this name"
            )

    user_pet_count = sum(1 for pet in pets if pet["user_id"] == auth_key)
    if user_pet_count >= 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum number of pets (10) reached"
        )

    pet_photo = None
    if pet_photo and pet_photo.filename:
        allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp'}
        allowed_content_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/bmp']

        file_extension = Path(pet_photo.filename).suffix.lower()

        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file extension. Allowed: {', '.join(allowed_extensions)}"
            )

        if pet_photo.content_type not in allowed_content_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file type. Only images are allowed"
            )

        file_size = 0
        try:
            content = await pet_photo.read()
            file_size = len(content)

            if file_size > 5 * 1024 * 1024:  # 5MB
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="File too large. Maximum size is 5MB"
                )

            unique_filename = f"{uuid.uuid4().hex}{file_extension}"
            file_path = UPLOAD_DIR / unique_filename

            with open(file_path, "wb") as buffer:
                buffer.write(content)

            pet_photo = str(file_path)

            pet_photo.file.seek(0)

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error processing file: {str(e)}"
            )

    pet_id = str(uuid.uuid4())
    current_time = datetime.now().isoformat()

    new_pet = {
        "pet_id": pet_id,
        "user_id": auth_key,
        "animal_type": animal_type_clean,
        "name": name_clean,
        "age": age,
        "pet_photo": pet_photo,
        "created_at": current_time,
        "updated_at": current_time
    }

    pets.append(new_pet)

    response_data = {
        "pet_id": pet_id,
        "user_id": auth_key,
        "animal_type": animal_type_clean,
        "name": name_clean,
        "age": age,
        "pet_photo": pet_photo,
        "created_at": current_time,
    }

    return response_data


@app.delete("/api/pets/{pet_id}", status_code=status.HTTP_200_OK)
def delete_pet(
        pet_id: str,
        auth_key: str = Depends(get_auth_key)
):
    for i, pet in enumerate(pets):
        if pet["pet_id"] == pet_id:
            if pet["user_id"] != auth_key:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You don't have permission to delete this pet"
                )

            deleted_pet = pets.pop(i)
            return {
                "message": "Pet deleted successfully",
                "deleted_pet": deleted_pet
            }
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Pet not found"
    )


@app.put("/api/pets/{pet_id}", status_code=status.HTTP_200_OK)
def update_pet(
        pet_id: str,
        name: Optional[str] = None,
        age: Optional[int] = None,
        animal_type: Optional[str] = None,
        auth_key: str = Depends(get_auth_key)
):
    for pet in pets:
        if pet["pet_id"] == pet_id:
            if pet["user_id"] != auth_key:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Permission denied"
                )

            if name is not None:
                pet["name"] = name
            if age is not None:
                pet["age"] = age
            if animal_type is not None:
                pet["animal_type"] = animal_type

            return pet

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Pet not found"
    )


@app.post("/api/pets/set_photo/{pet_id}", status_code=status.HTTP_200_OK)
async def set_photo(
        pet_id: str,
        pet_photo: UploadFile = File(...),
        auth_key: str = Depends(get_auth_key)
):
    pet_found = None
    for pet in pets:
        if pet["pet_id"] == pet_id:
            pet_found = pet
            break

    if not pet_found:
        raise HTTPException(
            status_code=404,
            detail="Pet not found"
        )

    if pet_found["user_id"] != auth_key:
        raise HTTPException(
            status_code=403,
            detail="Permission denied"
        )

    allowed_content_types = ['image/jpeg', 'image/jpg', 'image/png']
    allowed_extensions = {'.jpg', '.jpeg', '.png'}

    file_extension = Path(pet_photo.filename).suffix.lower()

    if (pet_photo.content_type not in allowed_content_types or
            file_extension not in allowed_extensions):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Only JPG, JPEG or PNG formats are allowed"
        )

    max_size = 10 * 1024 * 1024

    content = await pet_photo.read()

    if len(content) > max_size:
        raise HTTPException(
            status_code=400,
            detail="File too large. Maximum size is 10MB"
        )

    try:

        unique_filename = f"{pet_id}_{uuid.uuid4().hex}{file_extension}"
        file_path = UPLOAD_DIR / unique_filename

        with open(file_path, "wb") as buffer:
            buffer.write(content)

        mime_type = "image/jpeg" if file_extension in ['.jpg', '.jpeg'] else "image/png"
        base64_encoded = base64.b64encode(content).decode('utf-8')
        data_url = f"data:{mime_type};base64,{base64_encoded}"

        pet_found["pet_photo"] = data_url

        if "updated_at" not in pet_found:
            pet_found["created_at"] = datetime.now().timestamp()

        return {
            "id": pet_found.get("pet_id", pet_id),
            "name": pet_found.get("name", ""),
            "animal_type": pet_found.get("animal_type", ""),
            "age": pet_found.get("age", 0),
            "pet_photo": data_url,
            "user_id": pet_found.get("user_id", auth_key),
            "created_at": pet_found.get("created_at", datetime.now().timestamp())
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing file: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)

