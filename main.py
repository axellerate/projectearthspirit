import os
import random
import hashlib
from google.appengine.ext import blobstore
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
import datetime
import webapp2
import jinja2
from google.appengine.ext import endpoints
from google.appengine.ext import ndb
from protorpc import messages
from protorpc import message_types
from protorpc import remote

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
                               autoescape = True)

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



#Database#

class Country(ndb.Model):
    name = ndb.StringProperty(required = True)
    created = ndb.DateTimeProperty(auto_now_add = True)
    edited = ndb.DateTimeProperty(auto_now = True)

class Users(ndb.Model):
    email = ndb.StringProperty(required = True)
    pw_hash = ndb.StringProperty(required = True)
    firstName = ndb.StringProperty(required = True)
    lastName = ndb.StringProperty(required = True)
    country = ndb.KeyProperty(kind = Country)
    created = ndb.DateTimeProperty(auto_now_add = True)
    edited = ndb.DateTimeProperty(auto_now = True)

class Cars(ndb.Model):
    carId = ndb.IntegerProperty(required = True)
    make = ndb.StringProperty(required = True)
    model = ndb.StringProperty(required = True)
    year = ndb.IntegerProperty(required = True)
    created = ndb.DateTimeProperty(auto_now_add = True)
    edited = ndb.DateTimeProperty(auto_now = True)

class UserCars(ndb.Model):
    user = ndb.KeyProperty(kind = Users)
    car = ndb.KeyProperty(kind = Cars)

class UserFuel(ndb.Model):
    user = ndb.KeyProperty(kind = Users)
    litres = ndb.FloatProperty(required = True)

class CarEmissions(ndb.Model):
    car = ndb.KeyProperty(kind = Cars)
    grams = ndb.IntegerProperty(required = True)


#API Methods#


#User's API#


class UserInfo(messages.Message):
    email = messages.StringField(1, required = True)
    firstName = messages.StringField(2)
    lastName = messages.StringField(3)



class CreateUser(messages.Message):
    email = messages.StringField(1, required = True)
    firstName = messages.StringField(2, required = True)
    lastName = messages.StringField(3, required = True)
    pw_hash = messages.StringField(4, required = True)


class AddCar(messages.Message):
    user = messages.IntegerField(1, required = True)
    car = messages.IntegerField(2, required = True)


@endpoints.api(name = 'users', version = 'v1',
               description = 'Fetch and Create User Data')
class UserApi(remote.Service):

    @endpoints.method(UserInfo, UserInfo,
                        name = 'user.getUser',
                        path = 'getuser',
                        http_method = 'GET')
    def getUser(self, request):
        user_query = Users.query(Users.email == request.email)
        for i in user_query:
            user = UserInfo(email = i.email, firstName = i.firstName,
                            lastName = i.lastName)
        return user

    @endpoints.method(CreateUser, CreateUser,
                        name = 'user.create',
                        path = 'createuser',
                        http_method = 'POST')
    def createUser(self, request):
        Users(email = request.email, firstName = request.firstName,
              lastName = request.lastName, pw_hash = request.pw_hash).put()
        return request

    @endpoints.method(AddCar, message_types.VoidMessage,
                        name = 'user.addCar',
                        path = 'addCar',
                        http_method = 'POST')
    def addCarToUser(self, request):
        user = Users.get_by_id(request.user)
        car = Cars.get_by_id(request.car)
        UserCars(car = car.key, user = user.key).put()
        return message_types.VoidMessage()




#Car's API#

class GetCar(messages.Message):
    carId = messages.IntegerField(1)



class CreateCar(messages.Message):
    make = messages.StringField(1)
    model = messages.StringField(2)
    year = messages.IntegerField(3)
    carId = messages.IntegerField(4)

class AllCarsList(messages.Message):
    cars = messages.MessageField(CreateCar, 1, repeated = True)

@endpoints.api(name = 'cars', version = 'v1',
               description = 'Fetch and Create Car Data')
class CarsApi(remote.Service):

    @endpoints.method(CreateCar, CreateCar,
                        name = 'car.add',
                        path = 'addcar',
                        http_method = 'POST')
    def createCar(self, request):
        Cars(make = request.make, model = request.model, year = request.year, carId = int(request.carId)).put()
        return request

    @endpoints.method(message_types.VoidMessage, AllCarsList,
                        name = 'car.allcars',
                        path = 'allcars',
                        http_method = 'GET')
    def allCars(self, request):
        all_cars = []
        cars = Cars.query()
        for i in cars:
            all_cars.append(CreateCar(make = i.make, model = i.model, year = i.year, carId = i.carId))
        return AllCarsList(cars = all_cars)


    @endpoints.method(GetCar, CreateCar,
                        name = 'car.getCar',
                        path = 'getcar',
                        http_method = 'GET')
    def getCar(self, request):
        car_query = Cars.query(Cars.carId == request.carId)
        for i in car_query:
            car = CreateCar(make = i.make, model = i.model,
                            year = i.year, carId = i.carId)
        return car



application = endpoints.api_server([UserApi, CarsApi])

app = webapp2.WSGIApplication([('/', MainPage)],
                              debug=True)