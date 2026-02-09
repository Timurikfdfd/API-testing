import pytest
import asyncio
import base64
from pathlib import Path
from io import BytesIO
from fastapi.testclient import TestClient
from api import app
import uuid

client = TestClient(app)

VALID_KEY = "4c1b3391576925b36c1ce627f38ea92d112f1a6ba440352ef703b205"
INVALID_KEY = "invalid_key_12345"
LONG_KEY = "x" * 300
EMPTY_KEY = ""
SPECIAL_CHARS_KEY = "!@#$%^&*()_+-=[]{}|;':\",./<>?"

created_pet_ids = []
created_user_data = []


class TestAPIAuthentication:
    """Тесты аутентификации"""

    def test_login_valid_credentials(self):
        """Тест 1: Вход с валидными учетными данными"""
        response = client.get("/api/key", params={
            "username": "admin",
            "password": "admin"
        })
        assert response.status_code == 200
        data = response.json()
        assert "key" in data

    def test_login_invalid_username(self):
        """Тест 2: Вход с неверным именем пользователя"""
        response = client.get("/api/key", params={
            "username": "wrong_user",
            "password": "admin"
        })
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
        assert "Invalid username or password" in data["detail"]

    def test_login_invalid_password(self):
        """Тест 3: Вход с неверным паролем"""
        response = client.get("/api/key", params={
            "username": "admin",
            "password": "wrong_password"
        })
        assert response.status_code == 401

    def test_login_empty_credentials(self):
        """Тест 4: Вход с пустыми учетными данными"""
        response = client.get("/api/key", params={
            "username": "",
            "password": ""
        })
        assert response.status_code == 401



class TestPetsAPI:
    """Тесты для работы с питомцами"""

    def test_get_pets_with_valid_key(self):
        """Тест 5: Получение списка питомцев с валидным ключом"""
        response = client.get(
            "/api/pets",
            headers={"auth-key": VALID_KEY}
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_pets_with_invalid_key(self):
        """Тест 6: Получение списка питомцев с неверным ключом"""
        response = client.get(
            "/api/pets",
            headers={"auth-key": INVALID_KEY}
        )
        assert response.status_code == 401

    def test_get_pets_without_key(self):
        """Тест 7: Получение списка питомцев без ключа"""
        response = client.get("/api/pets")
        assert response.status_code == 401

    def test_get_pets_filter_my_pets_empty(self):
        """Тест 8: Получение только своих питомцев (пока нет)"""
        response = client.get(
            "/api/pets",
            headers={"auth-key": VALID_KEY},
            params={"filter_type": "my_pets"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


    def test_create_pet_simple_valid(self):
        """Тест 9: Создание питомца (валидные данные)"""
        response = client.post(
            "/api/create_pet_simple",
            headers={"auth-key": VALID_KEY},
            params={
                "animal_type": "dog",
                "name": "Rex",
                "age": 3
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert "pet_id" in data
        assert data["name"] == "Rex"
        assert data["animal_type"] == "dog"
        assert data["age"] == 3
        global created_pet_ids
        created_pet_ids.append(data["pet_id"])

    def test_create_pet_simple_edge_age_min(self):
        """Тест 10: Создание питомца с минимальным возрастом (граничное значение)"""
        response = client.post(
            "/api/create_pet_simple",
            headers={"auth-key": VALID_KEY},
            params={
                "animal_type": "cat",
                "name": "Whiskers",
                "age": 0
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["age"] == 0
        created_pet_ids.append(data["pet_id"])

    def test_create_pet_simple_edge_age_max(self):
        """Тест 11: Создание питомца с максимальным возрастом (граничное значение)"""
        response = client.post(
            "/api/create_pet_simple",
            headers={"auth-key": VALID_KEY},
            params={
                "animal_type": "turtle",
                "name": "Shelly",
                "age": 100
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["age"] == 100
        created_pet_ids.append(data["pet_id"])

    def test_create_pet_simple_invalid_age_negative(self):
        """Тест 12: Создание питомца с отрицательным возрастом"""
        response = client.post(
            "/api/create_pet_simple",
            headers={"auth-key": VALID_KEY},
            params={
                "animal_type": "dog",
                "name": "Buddy",
                "age": -5
            }
        )
        assert response.status_code == 400

    def test_create_pet_simple_invalid_age_large(self):
        """Тест 13: Создание питомца с очень большим возрастом"""
        response = client.post(
            "/api/create_pet_simple",
            headers={"auth-key": VALID_KEY},
            params={
                "animal_type": "dog",
                "name": "Oldie",
                "age": 1000
            }
        )
        assert response.status_code == 400

    def test_create_pet_simple_empty_name(self):
        """Тест 14: Создание питомца с пустым именем"""
        response = client.post(
            "/api/create_pet_simple",
            headers={"auth-key": VALID_KEY},
            params={
                "animal_type": "bird",
                "name": "",
                "age": 2
            }
        )
        assert response.status_code == 400

    def test_create_pet_simple_long_name(self):
        """Тест 15: Создание питомца с очень длинным именем"""
        long_name = "A" * 1000
        response = client.post(
            "/api/create_pet_simple",
            headers={"auth-key": VALID_KEY},
            params={
                "animal_type": "rabbit",
                "name": long_name,
                "age": 1
            }
        )
        assert response.status_code == 400


    def test_get_pets_filter_my_pets_with_data(self):
        """Тест 16: Получение только своих питомцев (теперь есть данные)"""
        response = client.get(
            "/api/pets",
            headers={"auth-key": VALID_KEY},
            params={"filter_type": "my_pets"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_get_pets_filter_with_data(self):
        """Тест 17: Получение всех питомцев (теперь есть данные)"""
        response = client.get(
            "/api/pets",
                headers={"auth-key": VALID_KEY},
                params={"filter_type": None}
            )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_update_pet_valid(self):
        """Тест 18: Обновление информации о питомце"""
        if not created_pet_ids:
            pytest.skip("Нет созданных питомцев для теста")

        pet_id = created_pet_ids[0]
        response = client.put(
            f"/api/pets/{pet_id}",
            headers={"auth-key": VALID_KEY},
            params={"name": "UpdatedName", "age": 5}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "UpdatedName"
        assert data["age"] == 5

    def test_delete_pet_not_valid(self):
        """Тест 19: Удаление питомца"""
        if len(created_pet_ids) < 2:
            pytest.skip("Недостаточно питомцев для теста удаления")

        pet_id = created_pet_ids[1]
        response = client.delete(
            f"/api/pets/{pet_id}",
            headers={"auth-key": VALID_KEY}
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert data["message"] == "Pet deleted successfully"

        response = client.get(
            "/api/pets",
            headers={"auth-key": VALID_KEY}
        )
        all_pets = response.json()
        pet_ids = [pet["pet_id"] for pet in all_pets]
        assert pet_id not in pet_ids

    def test_delete_pet_valid(self):
        """Тест 20: Удаление питомца который не существует"""

        pet_id = str(uuid.uuid4())
        response = client.delete(
            f"/api/pets/{pet_id}",
            headers={"auth-key": VALID_KEY}
        )
        assert response.status_code == 404
        data = response.json()

# Фикстуры для настройки и очистки
@pytest.fixture(scope="session", autouse=True)
def cleanup_after_tests():
    """Очистка после всех тестов"""
    yield
    import shutil
    uploads_dir = Path("uploads")
    if uploads_dir.exists():
        shutil.rmtree(uploads_dir)
    uploads_dir.mkdir(exist_ok=True)


if __name__ == "__main__":
    pytest.main([
        "test_api.py",
        "-v",
        "--tb=short",
        "-x"
    ])