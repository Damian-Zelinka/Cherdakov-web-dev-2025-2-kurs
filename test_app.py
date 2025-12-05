# test_app.py
import pytest
from app import app as flask_app, db
from models import User, Role, Product
from flask import session

@pytest.fixture
def app():
    flask_app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False,
        "SECRET_KEY": "testsecret",
    })
    with flask_app.app_context():
        db.create_all()
        # Create roles
        if Role.query.count() == 0:
            db.session.add_all([
                Role(name="Администратор"),
                Role(name="Пользователь")
            ])
            db.session.commit()
        yield flask_app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def init_users(app):
    with app.app_context():
        # Create admin user
        admin = User(
            login="admin",
            full_name="Admin User",
            email="admin@test.com",
            role_id=1
        )
        admin.set_password("Admin123!")
        # Create regular user
        user = User(
            login="user",
            full_name="Normal User",
            email="user@test.com",
            role_id=2
        )
        user.set_password("User123!")
        db.session.add_all([admin, user])
        db.session.commit()
        return {"admin": admin, "user": user}

@pytest.fixture
def init_products(app):
    with app.app_context():
        products = [
            Product(name="Test Product 1", category="Cat1", price=10.0, bee_coin=1),
            Product(name="Test Product 2", category="Cat2", price=20.0, bee_coin=2),
        ]
        db.session.add_all(products)
        db.session.commit()
        return products

def login(client, login, password):
    return client.post(
        "/login",
        data={"login": login, "password": password},
        follow_redirects=True
    )

def logout(client):
    return client.get("/logout", follow_redirects=True)

def register(client, login, password, confirm_password, full_name, email):
    return client.post(
        "/register",
        data={
            "login": login,
            "password": password,
            "confirm_password": confirm_password,
            "full_name": full_name,
            "email": email,
        },
        follow_redirects=True
    )

# ---------------- TESTS ---------------- #

def test_registration(client):
    # Successful registration
    response = register(
        client, "newuser", "Password1!", "Password1!", "New User", "newuser@test.com"
    )
    assert "Регистрация прошла успешно" in response.data.decode("utf-8")

    # Duplicate login
    response = register(
        client, "newuser", "Password1!", "Password1!", "New User", "newuser2@test.com"
    )
    assert "Логин уже занят" in response.data.decode("utf-8")

    # Duplicate email
    response = register(
        client, "anotheruser", "Password1!", "Password1!", "New User", "newuser@test.com"
    )
    assert "Email уже используется" in response.data.decode("utf-8")

    # Invalid password
    response = register(
        client, "badpass", "short", "short", "Bad Pass", "bad@test.com"
    )
    assert "Минимум 8 символов" in response.data.decode("utf-8")


def test_login_logout(client, init_users):
    # Successful login
    response = login(client, "user", "User123!")
    assert "user" in response.data.decode("utf-8")

    # Logout
    response = logout(client)
    assert "Login" in response.data.decode("utf-8")

    # Wrong credentials
    response = login(client, "user", "WrongPass")
    assert "Неверный логин или пароль" in response.data.decode("utf-8")


def test_change_password(client, init_users):
    login(client, "user", "User123!")
    # Successful password change
    response = client.post(
        "/change_password",
        data={
            "old_password": "User123!",
            "new_password": "NewPass123!",
            "confirm_password": "NewPass123!",
        },
        follow_redirects=True,
    )
    assert "Пароль успешно изменен" in response.data.decode("utf-8")

    # Wrong current password
    response = client.post(
        "/change_password",
        data={
            "old_password": "WrongOld",
            "new_password": "NewPass123!",
            "confirm_password": "NewPass123!",
        },
        follow_redirects=True,
    )
    assert "Неверный текущий пароль" in response.data.decode("utf-8")

    # Password mismatch
    response = client.post(
        "/change_password",
        data={
            "old_password": "NewPass123!",
            "new_password": "AnotherPass123!",
            "confirm_password": "Mismatch123!",
        },
        follow_redirects=True,
    )
    assert "Пароли не совпадают" in response.data.decode("utf-8")


def test_add_to_cart_and_checkout(client, init_users, init_products):
    login(client, "user", "User123!")
    # Add first product to cart
    response = client.get(f"/add_to_cart/{init_products[0].id}", follow_redirects=True)
    assert "added to your cart" in response.data.decode("utf-8")

    # Checkout
    response = client.post(
        "/checkout", data={"beecoin_to_use": "0"}, follow_redirects=True
    )
    assert "Order placed successfully" in response.data.decode("utf-8")

    # Check BeeCoins updated
    with flask_app.app_context():
        user = User.query.filter_by(login="user").first()
        assert user.bee_coins > 0


def test_admin_access(client, init_users):
    # Regular user cannot access admin
    login(client, "user", "User123!")
    response = client.get("/admin/dashboard", follow_redirects=True)
    assert "Доступ запрещён" in response.data.decode("utf-8")
    logout(client)

    # Admin can access
    login(client, "admin", "Admin123!")
    response = client.get("/admin/dashboard")
    assert response.status_code == 200
    html = response.data.decode("utf-8")
    assert "dashboard" in html or "Admin" in html
