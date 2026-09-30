import pytest
from app import create_app
from database import db
from database.models import User


@pytest.fixture
def client():
    app = create_app('testing')
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            yield client
            db.session.remove()
            db.drop_all()


def test_password_hashing():
    u = User(username='testuser', email='test@panopticon.ai', full_name='Test User')
    u.set_password('Secret@123')
    assert u.password_hash is not None
    assert u.check_password('Secret@123') is True
    assert u.check_password('WrongPassword') is False


def test_user_registration(client):
    res = client.post('/register', data={
        'full_name': 'Registration Test',
        'username': 'regtest',
        'email': 'regtest@panopticon.ai',
        'password': 'Password@123',
        'confirm_password': 'Password@123',
        'role': 'student'
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b'Account created successfully' in res.data


def test_user_duplicate_registration(client):
    client.post('/register', data={
        'full_name': 'Original User',
        'username': 'duptest',
        'email': 'dup@panopticon.ai',
        'password': 'Password@123',
        'confirm_password': 'Password@123',
        'role': 'student'
    })
    # Try registering again with duplicate email
    res = client.post('/register', data={
        'full_name': 'Duplicate User',
        'username': 'duptest2',
        'email': 'dup@panopticon.ai',
        'password': 'Password@123',
        'confirm_password': 'Password@123',
        'role': 'student'
    }, follow_redirects=True)
    assert b'Email already registered' in res.data


def test_login_and_logout(client):
    # Register user
    client.post('/register', data={
        'full_name': 'Login Tester',
        'username': 'logintester',
        'email': 'login@panopticon.ai',
        'password': 'SecretPassword123',
        'confirm_password': 'SecretPassword123',
        'role': 'student'
    })

    # Test bad password
    bad_res = client.post('/login', data={
        'identifier': 'login@panopticon.ai',
        'password': 'WrongPassword'
    }, follow_redirects=True)
    assert b'Invalid username/email or password' in bad_res.data

    # Test good login
    good_res = client.post('/login', data={
        'identifier': 'login@panopticon.ai',
        'password': 'SecretPassword123'
    }, follow_redirects=True)
    assert b'Welcome back, Login Tester!' in good_res.data

    # Test logout
    logout_res = client.get('/logout', follow_redirects=True)
    assert b'signed out' in logout_res.data


def test_admin_access_control(client):
    # Register regular student
    client.post('/register', data={
        'full_name': 'Student Access',
        'username': 'studentacc',
        'email': 'studentacc@panopticon.ai',
        'password': 'Password123',
        'confirm_password': 'Password123',
        'role': 'student'
    })
    client.post('/login', data={'identifier': 'studentacc@panopticon.ai', 'password': 'Password123'})

    # Student trying to visit admin dashboard should be blocked
    res = client.get('/admin/dashboard', follow_redirects=True)
    assert b'Access denied: Administrator privileges required' in res.data
