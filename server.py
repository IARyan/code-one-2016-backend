import cPickle as pickle
from flask import Flask, request
from flask_restful import Resource, Api
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS, cross_origin
from firebase import firebase
from twilio.rest import TwilioRestClient
from chore_state import Chore_Status_Stack


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///server.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
CORS(app)
api = Api(app)

# Find these values at https://twilio.com/user/account
account_sid = "AC30fdadaeaa4a59de8529d33da2ae313b"
auth_token = "cb872711044f3a0befd6b80f7faad80a"
client = TwilioRestClient(account_sid, auth_token)



#Table to handle the self-referencing many-to-many relationship for the User class:
#First column holds the user who is a parent, the second the user is the child.
user_to_user = db.Table('user_to_user',
    db.Column("parent_id", db.Integer, db.ForeignKey("user.id"), primary_key=True),
    db.Column("child_id", db.Integer, db.ForeignKey("user.id"), primary_key=True)
)


user_to_chores = db.Table('user_to_chores', db.Model.metadata,
    db.Column("user_id", db.Integer, db.ForeignKey("user.id")),
    db.Column("chore_id", db.Integer, db.ForeignKey("chore.id"))
)

class User(db.Model):
  __tablename__ = 'user'
  id = db.Column(db.Integer, primary_key=True)
  #parent_id = db.Column(db.Integer,db.ForeignKey('user.id'))
  username = db.Column(db.String(250), unique=True)
  password = db.Column(db.String(250))
  is_child = db.Column(db.Integer)
  user_stage =  db.Column(db.Integer)
  full_name = db.Column(db.String(250))
  children = db.relationship("User",
                    secondary=user_to_user,
                    primaryjoin=id==user_to_user.c.parent_id,
                    secondaryjoin=id==user_to_user.c.child_id,
                    backref="parents"
  )
  chores = db.relationship("Chore", secondary=user_to_chores)
  

  def __init__(self, username, password, is_child, user_stage, full_name, children, chores):
    self.username = username
    self.password = password
    self.is_child = is_child
    self.user_stage = user_stage
    self.full_name = full_name
    self.children = children
    self.chores = chores

class Chore(db.Model):
  __tablename__ = 'chore'
  id = db.Column(db.Integer, primary_key=True)
  #parent_id = db.Column(db.Integer,db.ForeignKey('user.id'))
  title = db.Column(db.String(250), unique=True)
  description = db.Column(db.Text)
  salary = db.Column(db.Float)
  image_path = db.Column(db.Text)
  status = db.Column(db.String(250))

  def __init__(self, title, description, salary, image_path, status):
    self.title = title
    self.description = description
    self.salary = salary
    self.image_path = image_path
    self.status = status

# Check login credentials
class Login(Resource):
    def _seralize_user(self, user):
      parents = []
      children = []
      out_parents = []
      out_children = []

      # If the user is a child get its parents. Else get the parents children
      # This will need to be improved inorder to scale
      if user.is_child:
        active_user = {"username": user.username, "isChild": user.is_child, "fullName": user.full_name}
        for parent in user.parents:
          for child in parent.children:
            if child not in children:
              children.append(child)
          if parent not in parents:
            parents.append(parent)
      else:
        active_user = {"username": user.username, "isChild": user.is_child, "userStage": user.user_stage, "fullName": user.full_name}
        for child in user.children:
          for parent in child.parents:
            if parent not in parents:
              parents.append(parent)
          if child not in children:
            children.append(child)

      # Now we have the list of children and parents
      for parent in parents:
        out_parents.append({"username": parent.username, "isChild": parent.is_child, "fullName": parent.full_name})

      for child in children:
        out_children.append({"username": child.username, "isChild": child.is_child, "userStage": child.user_stage, "fullName": child.full_name})

      # Return the array of parents and children
      return {"active_user": active_user, "parents": out_parents, "children": out_children}

    def post(self):
      # Receive the login data
      login_data = request.get_json()
      # Pull out json data
      json_username =(login_data["username"]).lower()
      json_password = login_data["password"]

      # Look for user in the database
      user = User.query.filter_by(username=json_username).first()
      if user:
        if user.password == json_password:
          return self._seralize_user(user)
      return {"status":"Login Failed :'("}

# Check login credentials
class Get_All_Chores(Resource):
  def get(self):
    chores = Chore.query.all()
    chores_array = []
    for chore in chores:
      chores_array.append({"title":chore.title, "description": chore.description, "salary": chore.salary, "image_path": chore.image_path, "status": chore.status}) 
    return {"chores": chores_array}

# Get all possible user chores
class Get_User_Chores(Resource):
  def get(self, username):
     # Look for user in the database
      user = User.query.filter_by(username=username).first()
      chores_array = []
      if user:
         for chore in user.chores:
          chores_array.append({"title":chore.title, "description": chore.description, "salary": chore.salary, "image_path": chore.image_path, "status": chore.status}) 
      return {"chores": chores_array}

# Update Account 
class Update_Acount(Resource):
  def post(self):
    # Receive the login data
    post_data = request.get_json()
    username = post_data["username"]
    value = post_data["value"]
    try:
      account = "/account/{0}".format(username)
      funds = {"balance": float(value)}
      # Look for user in the database
      fb_connect = firebase.FirebaseApplication('https://popping-fire-3662.firebaseio.com', None)
      result = fb_connect.patch(account, funds, {'print': 'pretty'}, {'X_FANCY_HEADER': 'VERY FANCY'})
      return {"status": "Success", "Message": "Firebase updated success"}
    except:
     return {"status": "Error", "Message": "Firebase updated failure"}

# Update Account 
class Update_Stage(Resource):
  def post(self):
    post_data = request.get_json()
    username = post_data["username"]
    stage = post_data["stage"]
    user = User.query.filter_by(username=username).first()
    try:
      if user:
        if user.is_child:
          user.user_stage = int(stage)
          db.session.commit()
          return {"status": "Success", "Message": "User stage updated"}
        else:
           return {"status": "Error", "Message": "User is not a child"}
    except:
      print "Error updating firebase :("
    return {"status": "Error", "Message": "Failure updating user child stage"}
    
# Update Account 
class Assign_Chore(Resource):
  def post(self):
    post_data = request.get_json()
    username = post_data["username"]
    title = post_data["title"]
    user = User.query.filter_by(username=username).first()
    chore = Chore.query.filter_by(title=title).first()
    if user and chore:
        user.chores.append(chore)
        db.session.commit()
        return {"status": "Success", "Message": "User stage updated"}
    else:
      return {"status": "Error", "Message": "Failure adding chore to user"}

# Update Account 
class Create_Chore(Resource):
  def post(self):
    post_data = request.get_json()
    title = post_data["title"]
    description = post_data["description"]
    salary = post_data["salary"]
    image_path = post_data["image_path"]
    try:
      chore = Chore(title=title, description=description, salary=salary, image_path=image_path, status="not-completed")
      db.session.add(chore)
      db.session.commit()
      return {"status": "Success", "Message": "Create chore updated"}
    except:
      return {"status": "Error", "Message": "Failure creating new chore"}

class Update_Chore_Status(Resource):
  def post(self):
    post_data = request.get_json()
    username = post_data["username"]
    title = post_data["title"]
    status = post_data["status"]
    user = User.query.filter_by(username=username).first()
    if user:
      for chore in user.chores:
        if chore.title == title:
          chore.status = status
          db.session.commit()
          body_message =" %s has requsted payment for completing the chore: %s.\n Would you like to Accept or Deny? Please reply Accept or Deny." % (username.title(), title)
          message = client.messages.create(to="+14026304979", from_="+14027693538 ", body=body_message)
          account = "/chores/{0}".format(username)
          chore_fb = {chore.title: chore.status}
          fb_connect = firebase.FirebaseApplication('https://popping-fire-3662.firebaseio.com', None)
          result = fb_connect.patch(account, chore_fb, {'print': 'pretty'}, {'X_FANCY_HEADER': 'VERY FANCY'})

          # Save and update the chore status
          with open('chore_state.p', 'rb') as pickle_file:
            status_stack = pickle.load(pickle_file)

          status_stack.push(username=username, title=title, status=status)

          with open('chore_state.p', 'wb') as pickle_file:
            pickle.dump(status_stack, pickle_file)

          # Establish a secure session with gmail's outgoing SMTP server using your gmail account
          return {"status": "Success", "Message": "User chore status updated"}
    return {"status": "Error", "Message": "Failure changing chore status"}

class Update_Chore_Status_Complete(Resource):
  def post(self):
    post_data = request.get_json()
    username = post_data["username"]
    title = post_data["title"]
    status = post_data["status"]
    user = User.query.filter_by(username=username).first()
    if user:
      for chore in user.chores:
        if chore.title == title:
          chore.status = status
          db.session.commit()
          account = "/chores/{0}".format(username)
          chore_fb = {chore.title: chore.status}
          fb_connect = firebase.FirebaseApplication('https://popping-fire-3662.firebaseio.com', None)
          result = fb_connect.patch(account, chore_fb, {'print': 'pretty'}, {'X_FANCY_HEADER': 'VERY FANCY'})
          
          p_account = '/account/adam/balance'
          c_account = '/account/%s/balance' % (user.username)

          parent_account_bal = fb_connect.get(p_account, None, {'print': 'pretty'}, {'X_FANCY_HEADER': 'VERY FANCY'})
          child_account_bal = fb_connect.get(c_account, None, {'print': 'pretty'}, {'X_FANCY_HEADER': 'VERY FANCY'})

          account = "/account/{0}".format(user.username)
          account_fb = {"balance": child_account_bal + chore.salary}
          fb_connect = firebase.FirebaseApplication('https://popping-fire-3662.firebaseio.com', None)
          result = fb_connect.patch(account, account_fb, {'print': 'pretty'}, {'X_FANCY_HEADER': 'VERY FANCY'})

          account = "/account/{0}".format("adam")
          account_fb = {"balance": parent_account_bal - chore.salary}
          fb_connect = firebase.FirebaseApplication('https://popping-fire-3662.firebaseio.com', None)
          result = fb_connect.patch(account, account_fb, {'print': 'pretty'}, {'X_FANCY_HEADER': 'VERY FANCY'})
          # Establish a secure session with gmail's outgoing SMTP server using your gmail account
          return {"status": "Success", "Message": "User chore status updated"}
    return {"status": "Error", "Message": "Failure changing chore status"}

# Check login credentials
class Status(Resource):
    def _seralize_user(self, user):
      parents = []
      children = []
      out_parents = []
      out_children = []

      # If the user is a child get its parents. Else get the parents children
      # This will need to be improved inorder to scale
      if user.is_child:
        active_user = {"username": user.username, "isChild": user.is_child, "fullName": user.full_name}
        for parent in user.parents:
          for child in parent.children:
            if child not in children:
              children.append(child)
          if parent not in parents:
            parents.append(parent)
      else:
        active_user = {"username": user.username, "isChild": user.is_child, "userStage": user.user_stage, "fullName": user.full_name}
        for child in user.children:
          for parent in child.parents:
            if parent not in parents:
              parents.append(parent)
          if child not in children:
            children.append(child)

      # Now we have the list of children and parents
      for parent in parents:
        out_parents.append({"username": parent.username, "isChild": parent.is_child, "fullName": parent.full_name})

      for child in children:
        out_children.append({"username": child.username, "isChild": child.is_child, "userStage": child.user_stage, "fullName": child.full_name})

      # Return the array of parents and children
      return {"active_user": active_user, "parents": out_parents, "children": out_children}

    def post(self):
      # Receive the login data
      login_data = request.get_json()
      # Pull out json data
      json_username =(login_data["username"]).lower()
      # Look for user in the database
      user = User.query.filter_by(username=json_username).first()
      if user:
        return self._seralize_user(user)
      return {"status":"Login Failed :'("}

api.add_resource(Login, '/login')
api.add_resource(Get_All_Chores, '/chores')
api.add_resource(Get_User_Chores, '/chores/<string:username>')
api.add_resource(Update_Acount, '/update/account')
api.add_resource(Update_Stage, '/update/stage')
api.add_resource(Assign_Chore, '/assign/chore')
api.add_resource(Create_Chore, '/create/chore')
api.add_resource(Update_Chore_Status, '/update/chore/status')
api.add_resource(Update_Chore_Status_Complete, '/update/chore/status/complete')
api.add_resource(Status, '/refresh')
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)
