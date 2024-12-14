from flask import Flask, render_template, redirect, url_for, request
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired
from flask_sqlalchemy import SQLAlchemy
from flask_bootstrap import Bootstrap
from flask_wtf import FlaskForm
from dotenv import load_dotenv
import requests
import os

app = Flask(__name__)
load_dotenv(".env")

app.config.update(
    SECRET_KEY=os.getenv("SECRET_KEY"),
    SQLALCHEMY_DATABASE_URI="sqlite:///top-10-movies.db",
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    WTF_CSRF_SECRET_KEY=os.getenv("WTF_CSRF_SECRET_KEY"),
)

db = SQLAlchemy(app)
Bootstrap(app)

API_KEY = os.getenv("API_KEY", "")
MOVIE_DB_INFO_URL = os.getenv("MOVIE_DB_INFO_URL", "https://api.themoviedb.org/3/movie")
MOVIE_DB_SEARCH_URL = os.getenv(
    "MOVIE_DB_SEARCH_URL", "https://api.themoviedb.org/3/search/movie"
)
MOVIE_IMG_URL = os.getenv("MOVIE_DB_IMG_URL", "https://image.tmdb.org/t/p/w500")


class FindMovieForm(FlaskForm):
    movie_title = StringField("Movie Title", validators=[DataRequired()])
    submit = SubmitField("Add Movie")


class UpdateMovie(FlaskForm):
    new_rating = StringField(
        "Your Rating Out of 10 e.g 7.5", validators=[DataRequired()]
    )
    new_review = StringField("Your Review", validators=[DataRequired()])
    submit = SubmitField("Done")


class Movie(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), unique=True, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    description = db.Column(db.String(500), nullable=False)
    rating = db.Column(db.Float, nullable=False)
    ranking = db.Column(db.Integer, nullable=False, default=0)
    review = db.Column(db.String(500), nullable=False)
    img_url = db.Column(db.String(250), nullable=False)

    def __repr__(self):
        return f"<Movie {self.title}>"


def update_movie_rankings():
    """Update the rankings of all movies based on their ratings."""
    try:
        movies = Movie.query.order_by(Movie.rating.desc(), Movie.title).all()
        for i, movie in enumerate(movies):
            movie.ranking = i + 1
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Error updating rankings: {e}")


@app.route("/")
def home():
    """Display all movies ordered by their ranking."""
    movies = Movie.query.order_by(Movie.ranking).all()
    return render_template("index.html", movies=movies)


@app.route("/add", methods=["GET", "POST"])
def add_movie():
    """Handle movie search and addition."""
    form = FindMovieForm()
    if form.validate_on_submit():
        try:
            response = requests.get(
                url=MOVIE_DB_SEARCH_URL,
                params={"api_key": API_KEY, "query": form.movie_title.data},
            )
            response.raise_for_status()
            data = response.json()["results"]
            return render_template("select.html", options=data)
        except requests.RequestException as e:
            print(f"API request error: {e}")
            return render_template(
                "add.html", form=form, error="Failed to fetch movies. Please try again."
            )
    return render_template("add.html", form=form)


@app.route("/find/<int:movie_id>", methods=["GET", "POST"])
def find_movie(movie_id):
    """Fetch movie details from API and add to database."""
    try:
        response = requests.get(
            f"{MOVIE_DB_INFO_URL}/{movie_id}",
            params={"api_key": API_KEY, "language": "en-US"},
        )
        response.raise_for_status()
        data = response.json()

        new_movie = Movie(
            title=data["title"],
            year=int(data["release_date"].split("-")[0]),
            img_url=(
                f"{MOVIE_IMG_URL}{data['poster_path']}" if data["poster_path"] else ""
            ),
            description=data["overview"],
            rating=data["vote_average"],
            review="",
        )

        db.session.add(new_movie)
        db.session.commit()
        update_movie_rankings()
        return redirect(url_for("home"))
    except Exception as e:
        print(f"Error adding movie: {e}")
        db.session.rollback()
        return redirect(url_for("add"))


@app.route("/edit/<int:movie_id>", methods=["GET", "POST"])
def edit(movie_id):
    """Edit movie rating and review."""
    try:
        movie = Movie.query.get_or_404(movie_id)
        form = UpdateMovie()

        if form.validate_on_submit():
            movie.rating = float(form.new_rating.data)
            movie.review = form.new_review.data
            db.session.commit()
            update_movie_rankings()
            return redirect(url_for("home"))

        form.new_rating.data = str(movie.rating)
        form.new_review.data = movie.review
        return render_template("edit.html", movie=movie, form=form)
    except Exception as e:
        print(f"Error editing movie: {e}")
        db.session.rollback()
        return redirect(url_for("home"))


@app.route("/delete/<int:movie_id>")
def delete(movie_id):
    """Delete a movie from the database."""
    try:
        movie_to_delete = Movie.query.get_or_404(movie_id)
        db.session.delete(movie_to_delete)
        db.session.commit()
        update_movie_rankings()
    except Exception as e:
        print(f"Error deleting movie: {e}")
        db.session.rollback()
    return redirect(url_for("home"))


@app.errorhandler(404)
def page_not_found(e):
    """Handle 404 errors."""
    return render_template("404.html"), 404


@app.errorhandler(500)
def internal_server_error(e):
    """Handle 500 errors."""
    return render_template("500.html"), 500


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=False, host="0.0.0.0", port=8000)
