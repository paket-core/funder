"""funder tests"""
import util.logger
import db
util.logger.setup()

LOGGER = util.logger.logging.getLogger('pkt.funder.test')


def init_db():
    """Clear table and refill them with new data"""
    assert db.DB_NAME.startswith('test'), \
        "refusing to clear a db with a name that does not start with 'test' ({})".format(db.DB_NAME)
    LOGGER.info('clearing database')
    db.util.db.clear_tables(db.SQL_CONNECTION, db.DB_NAME)
    try:
        LOGGER.info('creating tables...')
        db.init_db()
    except db.util.db.mysql.connector.ProgrammingError:
        LOGGER.info('tables already exists')
    db.util.db.clear_tables(db.SQL_CONNECTION, db.DB_NAME)
