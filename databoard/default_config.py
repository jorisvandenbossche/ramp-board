import os


class Config(object):
    # FLASK GENERAL CONFIG PARAMETERS
    SECRET_KEY = os.getenv('DATABOARD_SECRET_KEY', 'abcdefghijkl')
    # abs max upload file size, to throw 413, before saving it
    WTF_CSRF_ENABLED = True
    LOG_FILENAME = None  # if None, output to screen
    MAX_CONTENT_LENGTH = 1024 * 1024 * 1024
    DEBUG = False
    TESTING = False

    # FLASK MAIL CONFIG PARAMETERS
    MAIL_SERVER = os.getenv('DATABOARD_MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = os.getenv('DATABOARD_MAIL_PORT', 587)
    MAIL_USERNAME = os.getenv('DATABOARD_MAIL_USERNAME', 'user')
    MAIL_PASSWORD = os.getenv('DATABOARD_MAIL_PASSWORD', 'password')
    MAIL_DEFAULT_SENDER = (
        os.getenv('DATABOARD_MAIL_SENDER_ALIAS', 'RAMP admin'),
        os.getenv('DATABOARD_MAIL_SENDER', 'rampmailer@gmail.com')
    )
    MAIL_RECIPIENTS = []
    MAIL_USE_TLS = False
    MAIL_USE_SSL = True
    MAIL_DEBUG = False


class DBConfig(object):
    DATABASE_URI = 'sqlite:///:memory:'
    DATABASE_QUERY_TIMEOUT = 0.5  # slow database query threshold (in seconds)

    SQLALCHEMY_TRACK_MODIFICATIONS = True
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABOARD_DB_URL', 'sqlite:///databoard.db')
    SQLALCHEMY_MIGRATE_REPO = os.getenv(
        'DATABOARD_DB_MIGRATE_REPO', 'sqlite:///databoard.db/db_repository')
    SQLALCHEMY_RECORD_QUERIES = (
        True if os.getenv('DATABOARD_DB_PERF', 0) else False
    )


class RampConfig(object):
    RAMP_ADMIN_MAILS = os.getenv('DATABOARD_ADMIN_MAILS', [])

    RAMP_KITS_DIR = 'ramp-kits'
    RAMP_DATA_DIR = 'ramp-data'
    RAMP_SUBMISSIONS_DIR = 'submissions'
    RAMP_SANDBOX_DIR = 'starting_kit'
    
    RAMP_SCORETYPES_MODULE = 'databoard.specific.score_types'

    RAMP_SERVER_PORT = 8080
    # make it False if parallel training is not working
    # is_parallelize
    RAMP_PARALLELIZE = bool(os.getenv('DATABOARD_PARALLELIZE', 1))

######################################################################


class ProductionConfig(Config):
    DATABASE_URI = 'mysql://user@localhost/foo'
    DEPLOYMENT_PATH = os.getenv(
        'DATABOARD_DEPLOYMENT_PATH', '/tmp/databoard')


class DevelopmentConfig(Config):
    DEBUG = True
    MAIL_DEBUG = True
    DEPLOYMENT_PATH = os.getenv(
        'DATABOARD_DEPLOYMENT_PATH_TEST', '/tmp/databoard-test')


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABOARD_DB_URL_TEST')
    DEPLOYMENT_PATH = os.getenv(
        'DATABOARD_DEPLOYMENT_PATH_TEST', '/tmp/databoard-test')
