from flask import Flask, render_template, request, redirect
from flask_admin import Admin, AdminIndexView
from flask_admin.contrib.sqla import ModelView
from flask_sqlalchemy import SQLAlchemy
from flask_security import UserMixin, RoleMixin, SQLAlchemyUserDatastore, Security, login_required, current_user
from celery import Celery

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///shop.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.config['FLASK_ADMIN_SWATCH'] = 'cerulean'
app.config['FLASK_ENV'] = 'development'
app.config['SECRET_KEY'] = 'asdzxcrfwef'

app.config['SECURITY_PASSWORD_SALT'] = 'salt'
app.config['SECURITY_PASSWORD_HASH'] = 'bcrypt'


db = SQLAlchemy(app)


def make_celery(app):
    celery = Celery(app.import_name)
    celery.conf.update(app.config["CELERY_CONFIG"])
    celery.autodiscover_tasks()
    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery


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
    price = db.Column(db.Integer, nullable=False)
    mass = db.Column(db.Integer, nullable=False)

    country = db.Column(db.String(250), nullable=False)
    city = db.Column(db.String(250), nullable=False)
    street = db.Column(db.String(250), nullable=False)

    def __repr__(self):
        return f'Название {self.title}'


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


celery = make_celery(app)
from logging import info


@celery.task()
def add_together(info):
    return print(info)


if __name__ == '__main__':
   app.run(debug=True)
