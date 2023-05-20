from flask import Flask, render_template, redirect, url_for, request
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired
from dotenv import load_dotenv
import requests
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///top-10-movies.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
Bootstrap(app)

load_dotenv('.env')
API_KEY = os.getenv('API_KEY')
MOVIE_DB_INFO_URL = os.getenv('MOVIE_DB_INFO_URL')
MOVIE_DB_SEARCH_URL = os.getenv('MOVIE_DB_SEARCH_URL')
MOVIE_IMG_URL = os.getenv('MOVIE_DB_IMG_URL')


class FindMovieForm(FlaskForm):
    movie_title = StringField('Movie Title', validators=[DataRequired()])
    submit = SubmitField('Add Movie')


class UpdateMovie(FlaskForm):
    new_rating = StringField('Your Rating Out of 10 e.g 7.5', validators=[DataRequired()])
    new_review = StringField('Your Review', validators=[DataRequired()])
    submit = SubmitField('Done')


class Movie(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), unique=True, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    description = db.Column(db.String(250), nullable=False)
    rating = db.Column(db.Float, nullable=False)
    ranking = db.Column(db.Integer, nullable=False, default=0)
    review = db.Column(db.String(250), nullable=False)
    img_url = db.Column(db.String(250), nullable=False)

    def __repr__(self):
        return f'<Movie {self.title}>'


@app.route("/")
def home():
    movies = db.session.query(Movie).all()
    return render_template("index.html", movies=movies)


@app.route("/add", methods=["GET", "POST"])
def add_movie():
    form = FindMovieForm()
    movie_title = form.movie_title.data
    if form.validate_on_submit():
        response = requests.get(url=MOVIE_DB_SEARCH_URL, params={"api_key": API_KEY, "query": movie_title})
        data = response.json()["results"]
        return render_template("select.html", options=data)
    return render_template("add.html", form=form)


@app.route("/find/<int:movie_id>", methods=['GET', 'POST'])
def find_movie(movie_id):
    movie_api_url = f"{MOVIE_DB_INFO_URL}/{movie_id}"

    response = requests.get(movie_api_url, params={"api_key": API_KEY, "language": "en-US"})
    data = response.json()

    new_movie = Movie(
        title=data["title"],
        year=data["release_date"].split("-")[0],
        img_url=f"{MOVIE_IMG_URL}{data['poster_path']}",
        description=data["overview"],
        rating=data["vote_average"],
        review=''
    )

    db.session.add(new_movie)
    db.session.commit()

    movies = Movie.query.order_by(Movie.rating.desc()).all()
    for i, movie in enumerate(movies):
        movie.ranking = i + 1 if movie.rating is not None else None
    db.session.commit()

    return redirect(url_for('home'))


@app.route('/edit/<int:movie_id>', methods=['GET', 'POST'])
def edit(movie_id):
    movie = Movie.query.get_or_404(movie_id)
    form = UpdateMovie()

    if request.method == 'POST':
        new_rating = request.form.get('new_rating')
        new_review = request.form.get('new_review')
        movie.rating = float(new_rating)
        movie.review = str(new_review)
        db.session.commit()

        movies = Movie.query.order_by(Movie.rating.desc()).all()
        for i, movie in enumerate(movies):
            movie.ranking = i + 1
        db.session.commit()

        return redirect(url_for('home'))

    return render_template('edit.html', movie=movie, form=form)


@app.route('/delete/<int:movie_id>')
def delete(movie_id):
    movie_to_delete = Movie.query.get_or_404(movie_id)
    db.session.delete(movie_to_delete)
    db.session.commit()
    return redirect(url_for('home'))


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000)
