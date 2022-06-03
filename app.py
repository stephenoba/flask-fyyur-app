# ----------------------------------------------------------------------------#
# Imports
# ----------------------------------------------------------------------------#

import os
import sys
from datetime import datetime
import dateutil.parser
import babel

from flask import Flask, render_template, request, flash, redirect, url_for, jsonify
from flask_moment import Moment
from sqlalchemy import and_
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import logging
from logging import Formatter, FileHandler
from flask_wtf import Form
from forms import *
# ----------------------------------------------------------------------------#
# App Config.
# ----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db = SQLAlchemy(app)

migrate = Migrate(app, db)

# ----------------------------------------------------------------------------#
# Models.
# ----------------------------------------------------------------------------#

# venue_genre = db.Table(
#   'venue_genre',
#   db.Column('genre_id', db.Integer, db.ForeignKey('genre.id'), primary_key=True),
#   db.Column('venue_id', db.Integer, db.ForeignKey('venue.id'), primary_key=True)
# )
#
# artiste_genre = db.Table(
#   'artiste_genre',
#   db.Column('genre_id', db.Integer, db.ForeignKey('genre.id'), primary_key=True),
#   db.Column('artist_id', db.Integer, db.ForeignKey('artist.id'), primary_key=True)
# )


class Venue(db.Model):
    __tablename__ = 'venue'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String())
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    address = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    genres = db.Column(db.String(120))
    # genres = db.relationship('Genre', secondary=venue_genre, lazy='subquery',
    #                          backref=db.backref('venues', lazy=True))
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    website_link = db.Column(db.String(120))
    seeking_talent = db.Column(
      db.Boolean, nullable=False, default=False)
    seeking_description = db.Column(db.Text)
    shows = db.relationship('Show', backref='venue', lazy=True)

    def __repr__(self):
        return f'<Venue {self.id} {self.name}>'


class Artist(db.Model):
    __tablename__ = 'artist'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String())
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    genres = db.Column(db.String(120))
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    website_link = db.Column(db.String(120))
    seeking_venue = db.Column(
        db.Boolean, nullable=False, default=False)
    seeking_description = db.Column(db.Text)
    shows = db.relationship('Show', backref='artist', lazy=True)

    def __repr__(self):
        return f'<Artist {self.id} {self.name}>'


class Show(db.Model):
    __tablename__ = 'show'

    id = db.Column(db.Integer, primary_key=True)
    venue_id = db.Column(
        db.Integer,
        db.ForeignKey('venue.id'),
        nullable=False
    )
    artist_id = db.Column(
        db.Integer,
        db.ForeignKey('artist.id'),
        nullable=False
    )
    start_time = db.Column(db.DateTime, nullable=False)

    def __repr__(self):
        return f'<Show {self.id} venue: {self.venue_id} artist: {self.artist_id}>'

# ----------------------------------------------------------------------------#
# Filters.
# ----------------------------------------------------------------------------#


def format_datetime(value, format='medium'):
    # date = dateutil.parser.parse(value)
    date = value
    if isinstance(value, str):
        date = dateutil.parser.parse(value)
    if format == 'full':
        format = "EEEE MMMM, d, y 'at' h:mma"
    elif format == 'medium':
        format = "EE MM, dd, y h:mma"
    return babel.dates.format_datetime(date, format, locale='en')


app.jinja_env.filters['datetime'] = format_datetime


# ----------------------------------
# Helpers
# ----------------------------------

def convert_list_to_csv(values):
    if not values:
        return ''

    if len(values) == 1:
        return values[0]

    return ','.join(values)


# ----------------------------------------------------------------------------#
# Controllers.
# ----------------------------------------------------------------------------#


@app.route('/')
def index():
    return render_template('pages/home.html')


#  Venues
#  ----------------------------------------------------------------
def venue_serializer(venue):
    shows_query = db.session.query(Show).select_from(
        Venue).join(Show, Venue.id == Show.venue_id).filter(Show.venue_id == venue.id)
    past_shows_query = shows_query.filter(Show.start_time < datetime.now())
    upcoming_shows_query = shows_query.filter(Show.start_time >= datetime.now())
    
    data = {
        'id': venue.id,
        'name': venue.name,
        "genres": venue.genres,
        "address": venue.address,
        "city": venue.city,
        "state": venue.state,
        "phone": venue.phone,
        "website": venue.website_link,
        "facebook_link": venue.facebook_link,
        "seeking_talent": venue.seeking_talent,
        "seeking_description": venue.seeking_description,
        "image_link": venue.image_link,
        'past_shows': [show_serializer(show) for show in past_shows_query.all()],
        'upcoming_shows': [show_serializer(show) for show in upcoming_shows_query.all()],
        "past_shows_count": past_shows_query.count(),
        "upcoming_shows_count": upcoming_shows_query.count()
    }
    return data


def venue_list_serializer(data):
    new_data = []

    for venue in data:
        new_data.append(
            venue_serializer(venue)
        )
    return new_data


def venues_serializer():
    data = []
    states_query = db.session.query(Venue.state.distinct().label("state"))

    for state_row in states_query.all():
        cities_query = db.session.query(Venue.city).filter(Venue.state == state_row.state).distinct()
        for city_row in cities_query.all():
            entry = dict()
            entry['city'] = city_row.city
            entry['state'] = state_row.state
            entry['venues'] = venue_list_serializer(
                Venue.query.filter(
                    and_(
                        Venue.state == state_row.state,
                        Venue.city == city_row.city
                    )
                )
            )
            data.append(entry)
    return data


@app.route('/venues')
def venues():
    data = venues_serializer()
    return render_template('pages/venues.html', areas=data)


def search_serializer(search_term, content_type=Venue):
    response = {
        "count": 0,
        "data": []
    }

    if search_term:
        search_query = f"%{search_term}%"
        _query = content_type.query.filter(content_type.name.ilike(search_query))
        if content_type == Venue:
            response = {
                "count": _query.count(),
                "data": [venue_serializer(venue) for venue in _query.all()]
            }
        if content_type == Artist:
            response = {
                "count": _query.count(),
                "data": [artist_serializer(artist) for artist in _query.all()]
            }
    return response


@app.route('/venues/search', methods=['POST'])
def search_venues():
    # implement search on artists with partial string search. Ensure it is case-insensitive.
    # seach for Hop should return "The Musical Hop".
    # search for "Music" should return "The Musical Hop" and "Park Square Live Music & Coffee"
    search_term = request.form.get('search_term', '')
    response = search_serializer(search_term)
    return render_template(
        'pages/search_venues.html',
        results=response, search_term=search_term)


@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
    # shows the venue page with the given venue_id
    data = venue_serializer(Venue.query.get_or_404(venue_id))
    return render_template('pages/show_venue.html', venue=data)

#  Create Venue
#  ----------------------------------------------------------------


@app.route('/venues/create', methods=['GET'])
def create_venue_form():
    form = VenueForm()
    return render_template('forms/new_venue.html', form=form)


@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
    form = VenueForm(request.form)
    data = form.data.copy()
    _ = data.pop('csrf_token')
    venue_id = None
    genres = data.pop('genres')
    error = False
    try:
        genres = convert_list_to_csv(genres)
        venue = Venue(**data, genres=genres)
        db.session.add(venue)
        db.session.commit()
        venue_id = venue.id
    except Exception as e:
        db.session.rollback()
        error = True
        print(e)
    finally:
        db.session.close()
        if not error:
            flash(
                f'Venue {form.name.data} was successfully listed!',
                category='success-message'
            )
            return redirect(url_for('show_venue', venue_id=venue_id))
        else:
            flash(
                f'An Error occurred while creating Venue {form.name.data}',
                category='error-message'
            )

    # e.g., flash('An error occurred. Venue ' + data.name + ' could not be listed.')
    # see: http://flask.pocoo.org/docs/1.0/patterns/flashing/
    return render_template('pages/home.html')


@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
    try:
        venue = Venue.query.get(venue_id)
        db.session.delete(venue)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        sys.stdout.write(e)
    finally:
        db.session.close()
    return jsonify({'success': True})


#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():
    data = db.session.query(Artist).all()
    return render_template('pages/artists.html', artists=data)


@app.route('/artists/search', methods=['POST'])
def search_artists():
    # implement search on artists with partial string search. Ensure it is case-insensitive.
    # seach for "A" should return "Guns N Petals", "Matt Quevado", and "The Wild Sax Band".
    # search for "band" should return "The Wild Sax Band".
    search_term = request.form.get('search_term', '')
    response = search_serializer(search_term, content_type=Artist)
    return render_template(
        'pages/search_artists.html',
        results=response,
        search_term=search_term)


def artist_serializer(artist):
    shows_query = db.session.query(Show).select_from(
        Artist).join(Show, Artist.id == Show.artist_id).filter(Show.artist_id == artist.id)
    past_shows_query = shows_query.filter(Show.start_time < datetime.now())
    upcoming_shows_query = shows_query.filter(Show.start_time >= datetime.now())

    data = {
        'id': artist.id,
        'name': artist.name,
        "genres": artist.genres,
        "city": artist.city,
        "state": artist.state,
        "phone": artist.phone,
        "website": artist.website_link,
        "facebook_link": artist.facebook_link,
        "seeking_venue": artist.seeking_venue,
        "seeking_description": artist.seeking_description,
        "image_link": artist.image_link,
        'past_shows': [show_serializer(show) for show in past_shows_query.all()],
        'upcoming_shows': [show_serializer(show) for show in upcoming_shows_query.all()],
        "past_shows_count": past_shows_query.count(),
        "upcoming_shows_count": upcoming_shows_query.count()
    }
    return data


@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
    # shows the artist page with the given artist_id
    data = artist_serializer(Artist.query.get_or_404(artist_id))
    return render_template('pages/show_artist.html', artist=data)


#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
    form = ArtistForm()
    artist = Artist.query.get_or_404(artist_id)

    form.name.data = artist.name
    form.city.data = artist.city
    form.genres.data = artist.genres
    form.address.data = artist.address
    form.state.data = artist.state
    form.phone.data = artist.phone
    form.website_link.data = artist.website_link
    form.facebook_link.data = artist.facebook_link
    form.seeking_venue.data = artist.seeking_venue
    form.seeking_description.data = artist.seeking_description
    form.image_link.data = artist.image_link
    return render_template('forms/edit_artist.html', form=form, artist=artist)


@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
    # artist record with ID <artist_id> using the new attributes
    form = ArtistForm(request.form)
    data = form.data.copy()
    _ = data.pop('csrf_token')
    artist = Artist.query.get_or_404(artist_id)
    genres = data.pop('genres')
    error = False
    try:
        genres = convert_list_to_csv(genres)
        artist.name = form.name.data
        artist.city = form.city.data
        artist.state = form.state.data
        artist.phone = form.phone.data
        artist.genres = genres
        artist.address = form.address.data
        artist.seeking_talent = form.seeking_venue.data
        artist.seeking_description = form.seeking_description.data
        artist.facebook_link = form.facebook_link.data
        artist.website_link = form.website_link.data
        artist.image_link = form.image_link.data

        db.session.commit()
    except Exception as e:
        db.session.rollback()
        error = True
        print(e)
    finally:
        db.session.close()
        if not error:
            flash(
                f'Artist {form.name.data} was updated updated!',
                category='success-message'
            )
            return redirect(url_for('show_artist', artist_id=artist_id))
        else:
            flash(
                f'An Error occurred while updating Venue {form.name.data}',
                category='error-message'
            )
    return redirect(url_for('show_artist', artist_id=artist_id))


@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
    form = VenueForm()
    venue = Venue.query.get_or_404(venue_id)

    form.name.data = venue.name
    form.city.data = venue.city
    form.genres.data = venue.genres
    form.address.data = venue.address
    form.state.data = venue.state
    form.phone.data = venue.phone
    form.website_link.data = venue.website_link
    form.facebook_link.data = venue.facebook_link
    form.seeking_talent.data = venue.seeking_talent
    form.seeking_description.data = venue.seeking_description
    form.image_link.data = venue.image_link
    return render_template('forms/edit_venue.html', form=form, venue=venue)


@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
    # venue record with ID <venue_id> using the new attributes
    form = VenueForm(request.form)
    data = form.data.copy()
    _ = data.pop('csrf_token')
    venue = Venue.query.get_or_404(venue_id)
    genres = data.pop('genres')
    error = False
    try:
        genres = convert_list_to_csv(genres)
        venue.name = form.name.data
        venue.city = form.city.data
        venue.state = form.state.data
        venue.phone = form.phone.data
        venue.genres = genres
        venue.address = form.address.data
        venue.seeking_talent = form.seeking_talent.data
        venue.seeking_description = form.seeking_description.data
        venue.facebook_link = form.facebook_link.data
        venue.website_link = form.website_link.data
        venue.image_link = form.image_link.data

        db.session.commit()
    except Exception as e:
        db.session.rollback()
        error = True
        print(e)
    finally:
        db.session.close()
        if not error:
            flash(
                f'Venue {form.name.data} was successfully updated!',
                category='success-message'
            )
            return redirect(url_for('show_venue', venue_id=venue_id))
        else:
            flash(
                f'An Error occurred while updating Venue {form.name.data}',
                category='error-message'
            )
    return redirect(url_for('show_venue', venue_id=venue_id))


#  Create Artist
#  ----------------------------------------------------------------

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
    form = ArtistForm()
    return render_template('forms/new_artist.html', form=form)


@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
    # called upon submitting the new artist listing form
    form = ArtistForm(request.form)
    data = form.data.copy()
    _ = data.pop('csrf_token')
    artist_id = None
    genres = data.pop('genres')
    error = False
    try:
        genres = convert_list_to_csv(genres)
        artist = Artist(**data, genres=genres)
        db.session.add(artist)
        db.session.commit()
        artist_id = artist.id
    except Exception as e:
        db.session.rollback()
        error = True
        sys.stdout.write(e)
    finally:
        db.session.close()
        if not error:
            flash(
                f'Artist {form.name.data} was successfully listed!',
                category='success-message'
            )
            return redirect(url_for('show_artist', artist_id=artist_id))
        else:
            flash(
                f'An Error occurred while creating Artist {form.name.data}',
                category='error-message'
            )

    # on successful db insert, flash success
    return render_template('pages/home.html')


#  Shows
#  ----------------------------------------------------------------
def show_serializer(show):
    data = {
        'venue_id': show.venue_id,
        'venue_name': show.venue.name,
        'artist_id': show.artist_id,
        'artist_name': show.artist.name,
        'artist_image': show.artist.image_link,
        'start_time': show.start_time,
        'venue_image': show.venue.image_link
    }
    return data
    
 
@app.route('/shows')
def shows():
    # displays list of shows at /shows
    shows_query = db.session.query(Show)
    data = [show_serializer(show) for show in shows_query.all()]
    return render_template('pages/shows.html', shows=data)


@app.route('/shows/create')
def create_shows():
    # renders form. do not touch.
    form = ShowForm()
    return render_template('forms/new_show.html', form=form)


@app.route('/shows/create', methods=['POST'])
def create_show_submission():
    # called to create new shows in the db, upon submitting new show listing form
    form = ShowForm(request.form)
    data = form.data.copy()
    _ = data.pop('csrf_token')
    error = False
    try:
        show = Show(**data)
        db.session.add(show)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        error = True
        sys.stdout.write(f'{e}')
    finally:
        db.session.close()
        if not error:
            flash(
                'Show was successfully listed!',
                category='success-message'
            )
            return redirect(url_for('shows'))
        else:
            flash(
                'An Error occurred while creating Show',
                category='error-message'
            )

    return render_template('pages/home.html')


@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404


@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

# ----------------------------------------------------------------------------#
# Launch.
# ----------------------------------------------------------------------------#


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
