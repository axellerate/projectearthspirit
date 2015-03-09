import os
import re
import random
import hashlib
import urllib2
import hmac
from google.appengine.api import urlfetch
from google.appengine.api import users
from string import letters
from google.appengine.ext import blobstore
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
import datetime
import webapp2
import jinja2
from google.appengine.ext import db
from HTMLParser import HTMLParser

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
                               autoescape = True)

secret = 'ID,fmkf458FDHhfJIJ9j%^%hY77RRF76gb.2'

def make_secure_val(val):
    return '%s|%s' % (val, hmac.new(secret, val).hexdigest())

def check_secure_val(secure_val):
    val = secure_val.split('|')[0]
    if secure_val == make_secure_val(val):
        return val

def render_str(template, **params):
    t = jinja_env.get_template(template)
    return t.render(params)

class MainHandler(webapp2.RequestHandler):
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

    def render_str(self, template, **params):
        return render_str(template, **params)

    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))

    def set_secure_cookie(self, name, val):
        cookie_val = make_secure_val(val)
        self.response.headers.add_header(
            'Set-Cookie',
            '%s=%s; Path=/' % (name, cookie_val))

    def read_secure_cookie(self, name):
        cookie_val = self.request.cookies.get(name)
        return cookie_val and check_secure_val(cookie_val)

    def login(self, user):
        self.set_secure_cookie('user_id', str(user.key().id()))

    def logout(self):
        self.response.headers.add_header('Set-Cookie', 'user_id=; Path=/')

    def initialize(self, *a, **kw):
        webapp2.RequestHandler.initialize(self, *a, **kw)
        uid = self.read_secure_cookie('user_id')
        self.user = uid and User.by_id(int(uid))


class MainPage(MainHandler):
    def get(self):
	if self.user:
            self.render('index.html', username = self.user.name)
        else:
            self.render('index.html')

    def post(self):
	username = self.request.get('username').lower()
        password = self.request.get('password')

        u = User.login(username, password)
        if u:
            self.login(u)
            self.redirect('/')
        else:
            msg = 'Invalid username or password.'
            self.render('index.html', error = msg)	


# user stuff
def make_salt(length = 5):
    return ''.join(random.choice(letters) for x in xrange(length))

def make_pw_hash(name, pw, salt = None):
    if not salt:
        salt = make_salt()
    h = hashlib.sha256(name + pw + salt).hexdigest()
    return '%s,%s' % (salt, h)

def valid_pw(name, password, h):
    salt = h.split(',')[0]
    return h == make_pw_hash(name, password, salt)

def users_key(group = 'default'):
    return db.Key.from_path('users', group)

class User(db.Model):
    email = db.StringProperty(required = True) 
    firstName = db.StringProperty(required = True)
    lastName = db.StringProperty(required = True)
    pw_hash = db.StringProperty(required = True)
    created = db.DateTimeProperty(auto_now_add = True)
    country = db.StringProperty(required = True)
    provenceState = db.StringProperty()
    cityTown = db.StringProperty()

  
  
    @classmethod
    def by_id(cls, uid):
        return User.get_by_id(uid, parent = users_key())

    @classmethod
    def by_name(cls, name):
        u = User.all().filter('name =', name).get()
        return u
    
    @classmethod
    def by_email(cls, email):
        e = User.all().filter('email =', email).get()
        return e

    @classmethod
    def register(cls, name, pw, email = None, country = None, month = None, day = None, year = None):
        pw_hash = make_pw_hash(name, pw)
        return User(parent = users_key(),
                    name = name,
                    pw_hash = pw_hash,
                    email = email,
                    country = country,
                    month = month,
                    day = day,
                    year = year)
	

    @classmethod
    def login(cls, name, pw):
        u = cls.by_name(name)
        if u and valid_pw(name, pw, u.pw_hash):
        	return u

class Cars(db.Model):
    make = db.StringProperty(required = True)
    model = db.StringProperty(required = True)
    mileage = db.StringProperty(required = True)

class UserCars(db.Model):
    user = db.ReferenceProperty(User)
    car = db.ReferenceProperty(Cars)

    @classmethod
    def by_user(cls, user):
        u = UserCars.all().filter('user =', user).get()
        return u

    @classmethod
    def by_cars(cls, car):
        u = UserCars.all().filter('car =', car).get()
        return u

class TransportationDistance(db.Model):
    user = db.ReferenceProperty(User)
    distance = db.FloatProperty(required = True)
    created = db.DateTimeProperty(auto_now_add = True)

    @classmethod
    def by_user(cls, user):
        u = TransportationDistance.all().filter('user =', user).get()
        return u

class TransportationCarbon(db.Model):
    user = db.ReferenceProperty(User)
    amount = db.FloatProperty(required = True)
    created = db.DateTimeProperty(auto_now_add = True)

    @classmethod
    def by_user(cls, user):
        u = TransportationCarbon.all().filter('user =', user).get()
        return u

class TransportationMethane(db.Model):
    user = db.ReferenceProperty(User)
    amount = db.FloatProperty(required = True)
    created = db.DateTimeProperty(auto_now_add = True)

    @classmethod
    def by_user(cls, user):
        u = TransportationMethane.all().filter('user =', user).get()
        return u

##Regular Expressions

USER_RE = re.compile(r"^[a-zA-Z0-9_-]{3,20}$")
def valid_username(username):
    return username and USER_RE.match(username)

PASSWORD_RE = re.compile(r"^.{3,20}$")
def valid_password(password):
    return password and PASSWORD_RE.match(password)

EMAIL_RE = re.compile(r"^[\S]+@[\S]+\.[\S]+$")
def valid_email(email):
    return email and EMAIL_RE.match(email)

class SignUp(MainHandler):
    def get(self):
        self.render("register.html")

    def post(self):
        have_error = False
        self.email = self.request.get('email')
        self.password = self.request.get('password')
        self.verify_password = self.request.get('verify_password')
        self.first_name = self.request.get('first_name')
        self.last_name = self.request.get('last_name')
        self.country = self.request.get('country')
        self.stateProvence = self.request.get('stateProvence')
        self.cityTown = self.request.get('cityTown')

        params = dict(verify_email = self.verify_email, username = self.username, email = self.email,  verify_password = self.verify_password, country = self.country, month = self.month, day = self.day, year = self.year)

        if not valid_username(self.username):
            params['username_error'] = "Invalid username (or blank)."
            have_error = True

        if not valid_password(self.password):
            params['password_error'] = "That wasn't a valid password."
            have_error = True
            
        elif self.password != self.verify_password:
            params['password_verify_error'] = "Your passwords didn't match."
            have_error = True

        if not self.country:
            params['country_error'] = "Country required."
            have_error = True

        if not valid_email(self.email):
            params['error_email'] = "That's not a valid email."
            have_error = True

        elif self.email != self.verify_email:
            params['error_verify_email'] = "That's not a valid email."
            have_error = True
            
        if not self.month:
            params['error_birthday'] = "A birth day is required."
            have_error = True
            
        if not self.day:
            params['error_birthday'] = "A birth day is required."
            have_error = True

        if not self.year:
            params['error_birthday'] = "A birth day is required."
            have_error = True
            
        if have_error:
            self.render('register.html', **params)
        else:
            self.done()

    def done(self, *a, **kw):
        raise NotImplementedError
            

class Register(SignUp):

    def get(self):
        if self.user:
            self.redirect('/')
        else:
            self.render('register.html')
    
    def done(self):
        #make sure the user doesn't already exist
        e = User.by_email(self.email.lower())
        u = User.by_name(self.username.lower())
        if u and e:
            msg = 'That user already exists.'
            msg1 = 'That email is already in use.'
            self.render('register.html', error_username = msg, error_email = msg1)
        elif u:
            msg = 'That user already exists.'
            self.render('register.html', error_username = msg)
        elif e:
            msg1 = 'That email is already in use.'
            self.render('register.html', error_email = msg1)
        else:
            u = User.register(self.username.lower(), self.password, self.email.lower(), self.country, self.month, self.day, self.year)
            u.put()

            self.login(u)
            self.redirect('/')
	
        

class Login(MainHandler):
    def get(self):
        self.render('index.html')

    def post(self):
        username = self.request.get('username').lower()
        password = self.request.get('password')

        u = User.login(username, password)
        if u:
            self.login(u)
            self.redirect('/news_page')
        else:
            msg = 'Invalid login. Please try again.'
            self.render('index.html', error = msg)

class Logout(MainHandler):
    def get(self):
        self.logout()
        self.redirect('/')



app = webapp2.WSGIApplication([('/', MainPage),
                               ('/logout', Logout),
                               ('/register', Register),
                               ('/login', Login)],
                              debug=True)