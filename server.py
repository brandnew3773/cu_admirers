#!/usr/bin/env python2.7

"""
Columbia W4111 Intro to databases
Example webserver

To run locally

    python server.py

Go to http://localhost:8111 in your browser


A debugger such as "pdb" may be helpful for debugging.
Read about it online.

eugene wu 2015
"""

import os
from sqlalchemy import *
from sqlalchemy.pool import NullPool
from utility import User, Equal, Post
from flask import Flask, request, render_template, g, redirect, Response, url_for, flash, session
from flask.ext.login import LoginManager, UserMixin, login_required, login_user, current_user, logout_user


tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=tmpl_dir)

login_manager = LoginManager()
login_manager.init_app(app)


#class User(UserMixin):
#    # proxy for a database of users

#    def __init__(self, username, password):
#        self.id = username
#        self.password = password

#    @classmethod
#    def get(cls, email):
#        return User.select([Equal("email", email)])




#
# The following uses the sqlite3 database test.db -- you can use this for debugging purposes
# However for the project you will need to connect to your Part 2 database in order to use the
# data
#
# XXX: The URI should be in the format of:
#
#     postgresql://USER:PASSWORD@w4111db1.cloudapp.net:5432/proj1part2
#
# For example, if you had username ewu2493, password foobar, then the following line would be:
#
#     DATABASEURI = "postgresql://ewu2493:foobar@w4111db1.cloudapp.net:5432/proj1part2"
#
DATABASEURI = "sqlite:///test.db"


#
# This line creates a database engine that knows how to connect to the URI above
#
engine = create_engine(DATABASEURI)
#conn = engine.connect()

#
# START SQLITE SETUP CODE
#
# after these statements run, you should see a file test.db in your webserver/ directory
# this is a sqlite database that you can query like psql typing in the shell command line:
#
#     sqlite3 test.db
#
# The following sqlite3 commands may be useful:
#
#     .tables               -- will list the tables in the database
#     .schema <tablename>   -- print CREATE TABLE statement for table
#
# The setup code should be deleted once you switch to using the Part 2 postgresql database
#



@app.before_request
def before_request():
    """
    This function is run at the beginning of every web request
    (every time you enter an address in the web browser).
    We use it to setup a database connection that can be used throughout the request

    The variable g is globally accessible
    """
    try:
        g.conn = engine.connect()
    except:
        print "uh oh, problem connecting to database"
        import traceback; traceback.print_exc()
        g.conn = None

@app.teardown_request
def teardown_request(exception):
    """
    At the end of the web request, this makes sure to close the database connection.
    If you don't the database could run out of memory!
    """
    try:
        g.conn.close()
    except Exception as e:
        pass


#
# @app.route is a decorator around index() that means:
#   run index() whenever the user tries to access the "/" path using a POST or GET request
#
# If you wanted the user to go to e.g., localhost:8111/foobar/ with POST or GET then you could use
#
#       @app.route("/foobar/", methods=["POST", "GET"])
#
# PROTIP: (the trailing / in the path is important)
#
# see for routing: http://flask.pocoo.org/docs/0.10/quickstart/#routing
# see for decorators: http://simeonfranklin.com/blog/2012/jul/1/python-decorators-in-12-steps/
#
@app.route('/', methods=["POST", "GET"])
def index():
    """
    request is a special object that Flask provides to access web request information:

    request.method:   "GET" or "POST"
    request.form:     if the browser submitted a form, this contains the data in the form
    request.args:     dictionary of URL arguments e.g., {a:1, b:2} for http://localhost?a=1&b=2

    See its API: http://flask.pocoo.org/docs/0.10/api/#incoming-request-data
    """
    posts = Post.get_all(g.conn)
    print(posts[0])
    return render_template("index.html", **{"posts": posts})




@login_manager.user_loader
def load_user(email):
    user = None
    try:
        user = User.select([Equal("email", "'%s'" % email)], g.conn)[0]
    except BaseException as e:
        print e
    return user


# @login_manager.request_loader
# def load_user(request):
#     token = request.headers.get('Authorization')
#     if token is None:
#         token = request.args.get('token')
#
#     if token is not None:
#         username,password = token.split(":") # naive token
#         user_entry = User.get(username)
#         if (user_entry is not None):
#             user = User(user_entry[0],user_entry[1])
#             if (user.password == password):
#                 return user
#     return None


@app.route('/login', methods=['GET', 'POST'])
def login():
    # Here we use a class of some kind to represent and validate our
    # client-side form data. For example, WTForms is a library that will
    # handle this for us, and we use a custom LoginForm to validate.
    #form = LoginForm()
    print "login"
    if request.method == "POST":
        print "post"
        email = request.form["email"]
        password = request.form["password"]
        print email
        user = User.select([Equal("email", "'%s'" % email)], g.conn)[0]
        print user.password
        if (user and user.check_password(password)):
            print "correct login"
            user.authenticated = True
            login_user(user)
    else:
        flash('Username or password incorrect')

    return redirect("/")

@app.route('/comment', methods=['POST'])
def comment():
    pass

@app.route('/like', methods=['POST'])
def like():
    pass

@app.route('/guess', methods=['POST'])
def guess():
    pass

@app.route('/search', methods=['POST'])
def search():
    pass

@app.route('/logout', methods=['GET'])
def logout():
    logout_user()
    return redirect("/")


@app.route('/post', methods=['POST'])
def post():
    Post.create_table(g.conn, True)
    print request.form
    post_body = request.form["post_body"]
    is_anonymous = request.form.get("is_anonymous", None) == "on"
    print("is anonymous")
    allow_guesses = request.form.get("allow_guesses", None) == "on"
    user = current_user
    print user
    if not user.is_authenticated():
        print("not authenticated")
        is_anonymous = True
        allow_guesses = False
    poster = None
    if not is_anonymous:
        print("Not anonymous")
        poster = user.sid
    p = Post(post_body, False, poster, 1, allow_guesses=allow_guesses)
    p.save(g.conn)
    return redirect("/")


@app.route('/register', methods=['POST'])
def register():
    print("starting register")
    email = request.form["email"]
    first_name = request.form["first_name"]
    last_name = request.form["last_name"]
    raw_password = request.form["password"]
    user = User(first_name, last_name, email)
    print("created user")
    user.set_password(raw_password)
    user.save(g.conn)
    print("Saving user")
    return redirect("/")



if __name__ == "__main__":
    import click

    @click.command()
    @click.option('--debug', is_flag=True)
    @click.option('--threaded', is_flag=True)
    @click.argument('HOST', default='0.0.0.0')
    @click.argument('PORT', default=8111, type=int)
    def run(debug, threaded, host, port):
        """
        This function handles command line parameters.
        Run the server using

            python server.py

        Show the help text using

            python server.py --help

        """
        app.secret_key = 'super secret key'
        #app.config['SESSION_TYPE'] = 'filesystem'

        #session.init_app(app)

        #sess = Session()
        #sess.init_app(app)
        debug=True
        HOST, PORT = host, port
        print "running on %s:%d" % (HOST, PORT)
        app.run(host=HOST, port=PORT, debug=debug, threaded=threaded)

    run()
