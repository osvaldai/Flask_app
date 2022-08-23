# Importing flask module in the project is mandatory
# An object of Flask class is our WSGI application.
from flask import Flask, render_template, request, redirect
from flask_sqlalchemy import SQLAlchemy

# Flask constructor takes the name of
# current module (__name__) as argument.
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://shop.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


class Item(db.Model):
    id = db.Column(db.Integer, primery_key=True)
    title = db.Column(db.String(150), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    mass = db.Column(db.Integer, nullable=False)

    country = db.Column(db.String(250), nullable=False)
    city = db.Column(db.String(250), nullable=False)
    street = db.Column(db.String(250), nullable=False)

    def __repr__(self):
        return f'Название {self.title}'


@app.route('/')
def index():
    items = Item.qvery.order_by(Item.price).all()
    return render_template('index.html', data=items)


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/create', methods=['POST', 'GET'])
def about():
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


if __name__ == '__main__':
    app.run(debug=True)
