import sqlite3
import unittest
import pytest
from alchemical import Alchemical


class TestCore(unittest.TestCase):
    def test_read_write(self):
        db = Alchemical('sqlite://')

        class User(db.Model):
            id = db.Column(db.Integer, primary_key=True)
            name = db.Column(db.String(128))

        db.create_all()
        assert db.metadata == db.Model.metadata

        with db.begin() as session:
            for name in ['mary', 'joe', 'susan']:
                session.add(User(name=name))

        with db.Session() as session:
            all = session.execute(db.select(User)).scalars().all()
        assert len(all) == 3

        db.drop_all()
        db.create_all()

        with db.Session() as session:
            all = session.execute(db.select(User)).scalars().all()
        assert len(all) == 0

    def test_binds(self):
        db = Alchemical()
        db.initialize(
            'sqlite://', binds={'one': 'sqlite://', 'two': 'sqlite://'})

        class User(db.Model):
            __tablename__ = 'users'
            id = db.Column(db.Integer, primary_key=True)
            name = db.Column(db.String(128))

        class User1(db.Model):
            __tablename__ = 'users'
            __bind_key__ = 'one'
            id = db.Column(db.Integer, primary_key=True)
            name = db.Column(db.String(128))

        class User2(db.Model):
            __bind_key__ = 'two'
            id = db.Column(db.Integer, primary_key=True)
            name = db.Column(db.String(128))
            addresses = db.relationship('Address', back_populates='user')

        class Address(db.Model):
            __bind_key__ = 'two'
            id = db.Column(db.Integer, primary_key=True)
            name = db.Column(db.String(128))
            user_id = db.Column(db.Integer, db.ForeignKey('user2.id'))
            user = db.relationship('User2', back_populates='addresses')

        db.create_all()
        assert db.bind_names() == ['one', 'two']
        assert db.metadata.tables.keys() == {'users', 'user2', 'address'}

        with db.begin() as session:
            user = User(name='main')
            user1 = User1(name='one')
            user2 = User2(name='two')
            user3 = User2(name='three')
            address1 = Address(name='address1')
            address2 = Address(name='address2')
            address1.user = user3
            address2.user = user3
            session.add_all([user, user1, user2, user3, address1, address2])

        conn = db.get_engine().pool.connect()
        cur = conn.cursor()
        cur.execute('select * from users;')
        assert cur.fetchall() == [(1, 'main')]
        conn.close()

        conn = db.get_engine(bind='one').pool.connect()
        cur = conn.cursor()
        cur.execute('select * from users;')
        assert cur.fetchall() == [(1, 'one')]
        conn.close()

        conn = db.get_engine(bind='two').pool.connect()
        cur = conn.cursor()
        cur.execute('select * from user2;')
        assert cur.fetchall() == [(1, 'two'), (2, 'three')]

        cur.execute('select * from address;')
        assert cur.fetchall() == [(1, 'address1', 2), (2, 'address2', 2)]
        conn.close()

        db.drop_all()

        conn = db.get_engine().pool.connect()
        cur = conn.cursor()
        with pytest.raises(sqlite3.OperationalError):
            cur.execute('select * from users;')
        conn.close()

        conn = db.get_engine(bind='one').pool.connect()
        cur = conn.cursor()
        with pytest.raises(sqlite3.OperationalError):
            cur.execute('select * from users;')
        conn.close()

        conn = db.get_engine(bind='two').pool.connect()
        cur = conn.cursor()
        with pytest.raises(sqlite3.OperationalError):
            cur.execute('select * from user2;')
        conn.close()
