import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:furry@localhost/bee_pro'
SQLALCHEMY_TRACK_MODIFICATIONS = False
SECRET_KEY = '/RiXnoGXTLXVyfanm2XgKA=='