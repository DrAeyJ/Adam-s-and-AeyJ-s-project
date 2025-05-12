import datetime

from sqlalchemy import Column, Integer, String, DATETIME
from db_session import SqlAlchemyBase


class User(SqlAlchemyBase):
    __tablename__ = 'users'  # имя таблицы в базе

    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, nullable=False)
    name = Column(String, default=f'User-{id}')
    type = Column(String, default='Unregistered', nullable=False)
    questions_made_count = Column(Integer, default=0)
    questions_moderated_count = Column(Integer, default=0)
    questions_answered_count = Column(Integer, default=0)
    suspended_until = Column(DATETIME, default=datetime.datetime(year=1, month=1, day=1))

    def __repr__(self):
        return f"<User(name='{self.name}', tg_id={self.telegram_id})>"


class Questions(SqlAlchemyBase):
    __tablename__ = 'questions'

    id = Column(Integer, primary_key=True)
    author_tg_id = Column(Integer)
    content = Column(String)

    answers_count = Column(Integer, nullable=False, default=2)
    answer_1 = Column(String)
    answer_2 = Column(String)
    answer_3 = Column(String, nullable=True)
    answer_4 = Column(String, nullable=True)

    answer_1_count = Column(Integer, default=0)
    answer_2_count = Column(Integer, default=0)
    answer_3_count = Column(Integer, nullable=True)
    answer_4_count = Column(Integer, nullable=True)

    likes_count = Column(Integer, default=0)
    dislikes_count = Column(Integer, default=0)
    reports_count = Column(Integer, default=0)

    def __repr__(self):
        return f'<Question(id={self.id}, content={self.content})>'
