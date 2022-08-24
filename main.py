import sys
from abc import ABC
from time import sleep

import schedule
from flask import Flask
from flask_admin import Admin, AdminIndexView
from flask_admin.babel import gettext
from flask_admin.contrib.sqla import ModelView
from flask_admin.model import BaseModelView
from flask_admin.model.filters import BaseFilter
from flask_security import UserMixin, RoleMixin, SQLAlchemyUserDatastore, Security, login_required, current_user
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///shop.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.config['FLASK_ADMIN_SWATCH'] = 'cerulean'
app.config['FLASK_ENV'] = 'development'
app.config['SECRET_KEY'] = 'asdzxcrfwef'

app.config['SECURITY_PASSWORD_SALT'] = 'salt'
app.config['SECURITY_PASSWORD_HASH'] = 'bcrypt'
db = SQLAlchemy(app)


# ограничиваем доступ к админке пользователям без прав
class AdminView(ModelView):
    def is_accessible(self):
        return current_user.has_role('admin')

    def inaccessible_callback(self, name, **kwargs):
        return redirect('/login')


# не даем получить доступ к админке без авторизации
class HomeAdminView(AdminIndexView):
    def is_accessible(self):
        return current_user.has_role('admin')

    def inaccessible_callback(self, name, **kwargs):
        return redirect('/login')


# инициализируем админку
admin = Admin(app, name='Старая Почта', template_mode='bootstrap3',
              endpoint='admin', index_view=HomeAdminView(name='Home'))


# класс модели для каталога
class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    price = db.Column(db.Float, nullable=False)
    mass = db.Column(db.Float, nullable=False)

    country = db.Column(db.String(250), nullable=False)
    city = db.Column(db.String(250), nullable=False)
    street = db.Column(db.String(250), nullable=False)

    def __repr__(self):
        return f'Название {self.title}'


class MyBaseFilter(BaseFilter, ABC):

    def __init__(self, column, country, street=None, city=None):
        super(MyBaseFilter, self).__init__(country, street, city)

        self.column = column


class MyEqualFilter(MyBaseFilter):
    def apply(self, query, value):
        return query.filter(self.column == value)

    def operation(self):
        return gettext('equals')

    def validate(self, value):
        return True

    def clean(self, value):
        return value


class MyDbModel(BaseModelView):
    def scaffold_filters(self, country):
        attr = getattr(self.model, Item.country)

        if isinstance(attr, Item.country):
            return [MyEqualFilter(country, country)]


# делаем чтобы был доступ с админки
admin.add_view(AdminView(Item, db.session))
# определяем роли для пользователей
roles_users = db.Table('roles_users',
                       db.Column('user_id', db.Integer(), db.ForeignKey('user.id')),
                       db.Column('role_id', db.Integer(), db.ForeignKey('role.id'))

                       )


# класс модели с пользователями
class User(db.Model, UserMixin):
    id = db.Column(db.Integer(), primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(250))
    active = db.Column(db.Boolean())
    roles = db.relationship('Role', secondary=roles_users, backref=db.backref('users', lazy='dynamic'))


# класс модели с ролями пользователей
class Role(db.Model, RoleMixin):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(100), unique=True)
    description = db.Column(db.String(255), )


# инициализируем роли и пользователей
user_datastore = SQLAlchemyUserDatastore(db, User, Role)
security = Security(app, user_datastore)


# шаблон главной страницы
@app.route('/')
def index():
    items = Item.query.order_by(Item.price).all()
    return render_template('index.html', data=items)


# удаление записи из базы через кноку на главной странице
@app.route('/<int:id>/del')
@login_required
def post_del(id):
    post = Item.query.get_or_404(id)
    try:
        db.session.delete(post)
        db.session.commit()
        return redirect('/')
    except:
        return 'Хьюстон, У нас проблемы'


# шаблон создания записи в базе
@app.route('/create', methods=['POST', 'GET'])
@login_required
def create():
    if request.method == 'POST':
        title = request.form['title']
        price = request.form['price']
        mass = request.form['mass']

        country = request.form['country']
        city = request.form['city']
        street = request.form['street']

        item = Item(
            title=title,
            price=price,
            mass=mass,
            country=country,
            city=city,
            street=street
        )
        try:
            db.session.add(item)
            db.session.commit()
            return redirect('/')
        except:
            return 'Хьюстон, У нас проблемы'
    else:
        return render_template('create.html')


from flask import request, render_template, redirect
from celery import Celery

"""# Celery configuration
app.config['CELERY_BROKER_URL'] = 'redis://localhost/0'
app.config['CELERY_RESULT_BACKEND'] = 'redis://localhost:5000/'"""

# Initialize Celery
celery = Celery()
# celery.conf.update(app.config)


@celery.task
def loger_task():
    logger.addFilter(NoParsingFilter())
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
    (logger.info(msg='Current time ' + str(datetime.datetime.now())))


import logging
import datetime

logger = logging.getLogger("logger")


class NoParsingFilter(logging.Filter):
    def filter(self, record):
        return not record.getMessage().startswith('parsing')


@celery.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(60.0, loger_task(), name='add every 60')


if __name__ == '__main__':
    app.run(debug=True)
