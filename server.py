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
import re
from sqlalchemy import *
from sqlalchemy.pool import NullPool
from utility import User, Equal, Post, Response, Like, Contains, And, Or, Filter, Comment, GuessSetting
from flask import Flask, request, render_template, g, redirect, Response, url_for, flash, session
from flask.ext.login import LoginManager, UserMixin, login_required, login_user, current_user, logout_user


tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=tmpl_dir)

login_manager = LoginManager()
login_manager.init_app(app)

NUMBER_GUESSES = 3
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


def prepare_posts(user, posts):
    posts = posts[::-1]
    for post in posts:
        if hasattr(post, "tagged") and post.tagged == user.uni:
            post.display_guess = True
        else:
            post.display_guess = False
        post.comments = Comment.select([Equal("pid", post.pid)], [], g.conn)[::-1]
    return posts

@app.route('/', methods=["POST", "GET"])
def index():

    """
    User.create_table(g.conn)
    Post.create_table(g.conn)
    Comment.create_table(g.conn)
    GuessSetting.create_table(g.conn)
    Like.create_table(g.conn)
    """

    user = current_user
    posts = Post.get_all(g.conn, [("pid", Like, "pid"),
                                  ("pid", GuessSetting, "pid")])
    if posts:
        print(posts[0])
    posts = prepare_posts(user, posts)
    return render_template("main.html", **{"posts": posts})


@login_manager.user_loader
def load_user(email):
    user = None
    try:
        user = User.select([Equal("email", "'%s'" % email)], [], g.conn)[0]
    except BaseException as e:
        print e
    return user


@app.route('/login', methods=['GET', 'POST'])
def login():
    email = request.form["email"]
    password = request.form["password"]
    user = User.select([Equal("email", "'%s'" % email)], [], g.conn)[0]
    if (user and user.check_password(password)):
        user.authenticated = True
        login_user(user)
    return redirect("/")

@app.route('/comment', methods=['POST'])
def comment():
    pid = int(request.json.get("pid"))
    comment_body = request.json.get("comment_body")
    is_anonymous = request.json.get("is_anonymous", None) == "on"
    user = current_user

    if not type(user) == bool or not user.is_authenticated():
        print("not authenticated")
        is_anonymous = True

    poster = None
    if not is_anonymous:
        print("Not anonymous")
        poster = user.sid
    c = Comment(comment_body, poster, pid=pid)
    c.save(g.conn)
    return redirect("/")


@app.route('/like', methods=['get'])
def like():
    print("Like route")
    #Like.create_table(g.conn)
    pid = int(request.args.get("pid"))
    likes = Like.select([Equal("pid", pid)], [], g.conn)
    print(likes)
    if not likes:
        print "created like"
        like = Like(pid=pid, like_count=1)
        like.weak_save(g.conn, force_insert=True)
    else:
        print "updated like"
        like = likes[0]
        like.like_count += 1
        like.weak_save(g.conn)

    return redirect("/")


@app.route('/guess', methods=['POST'])
def guess():
    print("Guessing!")
    print(request.json)
    pid = int(request.json.get("pid"))
    guess = request.json.get("guess", None)
    post = Post.select([Equal("pid", pid)],
                                  [("pid", GuessSetting, "pid")], g.conn)[0]
    gs = GuessSetting.select([Equal("gsid", post.gsid)], [], g.conn)[0]
    user = current_user
    if not post.allow_guesses or not user.uni == post.tagged or gs.remaining < 1:
        print("access denied!")
        return redirect("/")
    gs.remaining -= 1

    print(guess)
    print(post.poster)
    if guess is not None and guess == post.poster:
        gs.matched = True
        print "MATCH!!!!! LOVE IS IN THE AIR"
    else:
        print "No match"
    gs.save(g.conn)
    return redirect("/")

@app.route('/search', methods=['POST'])
def search():
    text = request.json
    pid = request.form.get("post_id", "")
    contains = request.form.get("contains", "")
    tagged = request.form.get("tagged", "")
    filters = []
    search_text = contains if contains != "" else text
    if pid != "":
        pid_filter = Equal("pid", int(pid))
        filters.append(pid_filter)
    if search_text != "":
        filters.append(Contains("post_body", search_text))
    if tagged != "":
        filters.append(Contains("post_body", tagged))
    filters = Filter.and_reduce(filters)
    posts = Post.select(filters, [("pid", Like, "pid")], g.conn)

    posts = prepare_posts(current_user, posts)
    return render_template("main.html", **{"posts": posts})

@app.route('/own_posts', methods=['GET'])
@login_required
def own_posts():
    filters = []
    user = current_user
    filters.append(Equal("poster", user.sid))
    posts = Post.select(filters, [("pid", Like, "pid"),
                                  ("pid", GuessSetting, "pid")], g.conn)
    posts = prepare_posts(user, posts)
    return render_template("main.html", **{"posts": posts})

@app.route('/logout', methods=['GET'])
def logout():
    logout_user()
    return redirect("/")

@app.route('/faqs', methods=['GET'])
def faqs():
    return render_template("faqs.html")

@app.route('/post', methods=['POST'])
def post():
    post_body = request.form["post_body"]
    is_anonymous = request.form.get("is_anonymous", None) == "on"
    allow_guesses = request.form.get("allow_guesses", None) == "on"
    user = current_user

    if not user.is_authenticated():
        print("not authenticated")
        is_anonymous = True
        allow_guesses = False
    if is_anonymous:
        allow_guesses = False
    poster = tagged = None
    if not is_anonymous:
        print("Not anonymous")
        poster = user.sid
    m = re.search(r"@([^_\W]*)", post_body)
    if m and allow_guesses:
        tagged = m.group(1)
    guesses = NUMBER_GUESSES if allow_guesses else 0
    uni = user.uni if allow_guesses else None

    p = Post(post_body, False, poster, allow_guesses=allow_guesses)
    p.save(g.conn)
    like = Like(pid=p.pid, like_count=0)
    like.save(g.conn)
    gs = GuessSetting(p.pid, poster=uni, tagged=tagged, num_guesses=guesses,
                      remaining=guesses)
    gs.save(g.conn)
    return redirect("/")


@app.route('/register', methods=['POST'])
def register():
    print("starting registration")
    email = request.form["email"]
    uni = email.split("@")[0]
    first_name = request.form["first_name"]
    last_name = request.form["last_name"]
    raw_password = request.form["password"]
    user = User(first_name, last_name, email, uni)
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
