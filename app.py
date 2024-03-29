# Imports
import sys
import psycopg2
import psycopg2.extras
import re
import os
import imp
import urllib.request
import secrets
from flask_mail import Mail
from flask_mail import Message
from flask import Flask, render_template, request, session, redirect, url_for, flash, send_file
from werkzeug.utils import secure_filename
from paddleocr import PaddleOCR
from os.path import exists
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

UPLOAD_FOLDER = 'static/uploads/'

# secret key for flash messages
### [REMOVE THIS SECRET KEY FROM THIS FILE BEFORE UPLOADING TO GITHUB OTHERWISE THE SECRET KEY WILL BE MADE PUBLIC (i.e. app.secret_key ='']) ###
app.secret_key = '\x9f\xed\xb7\xb4bo\xc4\xb5\xcb\x00W\x0b'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# EMAIL DATA REMOVE BEFORE UPLOADING TO GITHUB
app.config['MAIL_SERVER']='smtp.gmail.com'
app.config['MAIL_PORT'] = 465
email_address = 'Comp490lab@gmail.com'
app.config['MAIL_USERNAME'] = email_address
app.config['MAIL_PASSWORD'] = 'Everyone123!'
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
mail = Mail(app)

#form:  {secret_key1 : id, secret_key2 : ...}
pass_recovery = {}
pass_recovery["123456"] = 1 #for testing

ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg'])

# Elephant SQL connection
### [REMOVE THIS POSTGRESQL WEBLINK FROM THIS FILE BEFORE UPLOADING TO GITHUB OTHERWISE DB ACCESS WILL BE MADE PUBLIC (i.e. POSTGRESQL_URI =""]) ###
POSTGRESQL_URI = "postgres://zvnmwduo:gjGsAHHJjKbCnQLSEmyS3H2VlnMk-ZIq@kashin.db.elephantsql.com/zvnmwduo"
connection = psycopg2.connect(POSTGRESQL_URI)

# Create users table
try:
	with connection:
		with connection.cursor() as cursor:
			cursor.execute("CREATE TABLE users (id SERIAL PRIMARY KEY, firstname VARCHAR (100) NOT NULL, lastname VARCHAR (100) NOT NULL, username VARCHAR (50) NOT NULL, password VARCHAR (255) NOT NULL, email VARCHAR (50) NOT NULL, securityq1 VARCHAR (50) NOT NULL, securityq2 VARCHAR (50) NOT NULL);")
except psycopg2.errors.DuplicateTable:
	pass

# Create posts table
try:
	with connection:
		with connection.cursor() as cursor:
			cursor.execute("CREATE TABLE posts (id SERIAL PRIMARY KEY, username VARCHAR (50) NOT NULL, content VARCHAR (1000) NOT NULL, imagename VARCHAR (100) NOT NULL);")
except psycopg2.errors.DuplicateTable:
	pass



### Web pages and Functions ###

# Check for allowed extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Read prescription label
def getPrescription():
	list = []

	ocr_model = PaddleOCR(lang='en')
	result = ocr_model.ocr(img_path)

	for res in result:
		list.append(res[1][0])

	return list

# Homepage
@app.route("/", methods=["GET", "POST"])
def home():
	# Connect to db
	cursor = connection.cursor(cursor_factory=psycopg2.extras.DictCursor)

	# Check if user is loggedin
	if 'loggedin' in session:

		# Display user's previous entries
		cursor.execute('SELECT * FROM posts WHERE username = %s', (session['username'],))
		posts = cursor.fetchall()

		# User is loggedin show them the home page
		return render_template('home.html', firstname=session['firstname'], posts=posts)
		
	# User is not loggedin redirect to login page
	return redirect(url_for('login'))



# Test file
@app.route("/displayResults", methods=["GET", "POST"])
def displayResults():
	return render_template('displayResults.html')



# Upload file
@app.route("/add", methods=["GET", "POST"])
def add():
	global img_path
	errorCheck = False

	# Connect to db
	cursor = connection.cursor(cursor_factory=psycopg2.extras.DictCursor)
 
	if 'file' not in request.files:
		flash('No file part')
		return redirect(request.url)
	file = request.files['file']

	if file.filename == '':
		flash('No image selected for uploading')
		return redirect(request.url)

	if file and allowed_file(file.filename):
		filename = secure_filename(file.filename)
		file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

	img_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
	print(img_path)

	# Translate picture to text
	try:
		list = getPrescription() # PaddleOCR function in functions.py

		# Convert list of text elements into a String
		string1 = ""
		for l in list:
			string1 += ("["+ l + "]  ")
		
		# Insert post content into db
		cursor.execute("INSERT INTO posts (username, content, imagename) VALUES (%s,%s,%s)", (session['username'], string1, filename))
		connection.commit()

		flash('Image successfully uploaded and displayed above.')
		return render_template('displayImage.html', filename=filename)
	except:
		flash("Error occured, no image found, please try again.")
		errorCheck = True

	return redirect(url_for('home'))



@app.route("/display/<filename>")
def display_image(filename):
    return redirect(url_for('static', filename='uploads/' + filename), code=301)



# Function to delete posts
@app.route("/delete", methods=["GET", "POST"])
def delete():
	# Connect to db
	cursor = connection.cursor(cursor_factory=psycopg2.extras.DictCursor)

	# Get user entered from form ID number
	ID = request.form['ID']

	# Delete the post
#try:
	cursor.execute("SELECT * FROM posts WHERE id = %s", (ID,))
	post = cursor.fetchone()
	imagename = post['imagename']
	print(imagename)
	
	if(os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], imagename))):
		os.remove(os.path.join(app.config['UPLOAD_FOLDER'], imagename))
	cursor.execute("DELETE FROM posts WHERE id = %s", (ID,))
	connection.commit()
#except:
	flash("Please enter only only one ID number at a time. i.e. \"1\" or \"53\".")
	connection.rollback()

	return redirect(url_for('home'))



# Login page
@app.route("/login/", methods=["GET", "POST"])
def login():
	# Connect to db
	cursor = connection.cursor(cursor_factory=psycopg2.extras.DictCursor)

	# Display users databse table in terminal
	cursor.execute("SELECT * FROM users")
	myStatement = (cursor.fetchall())
	print("\n\n\n\n\n")
	print("\n\n\n".join(str(e) for e in myStatement).replace("(","").replace(")",""))
	print("\n\n\n\n\n")

	# Display posts databse table in terminal
	cursor.execute("SELECT * FROM posts")
	myStatement = (cursor.fetchall())
	print("\n\n\n\n\n")
	print("\n\n\n".join(str(e) for e in myStatement).replace("(","").replace(")",""))
	print("\n\n\n\n\n")

	# Check if "username" and "password" POST requests exist (user submitted form)
	if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
		username = request.form['username']
		password = request.form['password']
 
		# Check if account exists using MySQL
		cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
		# Fetch one record and return result
		account = cursor.fetchone()
 
		if account:
			password_rs = account['password']
			# If account exists in users table in db
			if check_password_hash(password_rs, password):
				# Create session data, we can access this data in other routes
				session['loggedin'] = True
				session['id'] = account['id']
				session['username'] = account['username']
				session['firstname'] = account['firstname']
				# Redirect to home page
				return redirect(url_for('home'))
			else:
				# Account doesnt exist or username/password incorrect
				flash("Either your account doesn't exist or you have entered the wrong username or password.")
		else:
			# Account doesnt exist or username/password incorrect
			flash("Either your account doesn't exist or you have entered the wrong username or password.")

	return render_template("login.html")



# Register page
@app.route("/register", methods=["GET", "POST"])
def register():
	# Connect to db
	cursor = connection.cursor(cursor_factory=psycopg2.extras.DictCursor)

	sent = False
 
	# Check if all fields POST requests exist (user submitted form)
	if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'password2' in request.form and 'email' in request.form  and 'firstname' in request.form  and 'lastname' in request.form  and 'securityq1' in request.form  and 'securityq2' in request.form:
		# Create variables for easy access
		firstname = request.form['firstname']
		lastname = request.form['lastname']
		username = request.form['username']
		password = request.form['password']
		password2 = request.form['password2']
		email = request.form['email']
		securityq1 = request.form['securityq1']
		securityq2 = request.form['securityq2']
    
		_hashed_password = generate_password_hash(password)
 
		# Check if account exists using MySQL
		cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
		account = cursor.fetchone()
		# If account exists show error and validation checks
		if account:
			flash('Account already exists!')
		elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
			flash('Invalid email address!')
		elif not re.match(r'[A-Za-z0-9]+', username):
			flash('Username must contain only characters and numbers!')
		elif not re.match(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*#?&])[A-Za-z\d@$!#%*?&]{8,18}$', password):
			flash('Password must contain one uppercase letter, one lowercase letter, one number, one special character(@, $, !, %, *, #, ?, &), and must be 8-18 characters long.')
		elif password != password2:
			flash('Passwords do not match.')
		elif not username or not password or not email:
			flash('Please fill out the form!')
		else:
			# Account doesnt exist and the form data is valid, now insert new account into users table
			cursor.execute("INSERT INTO users (firstname, lastname, username, password, email, securityq1, securityq2) VALUES (%s,%s,%s,%s,%s,%s,%s)", (firstname, lastname, username, _hashed_password, email, securityq1, securityq2))
			connection.commit()
			sent = True
			flash('You have successfully registered!')
	elif request.method == 'POST':
		# Form is empty... (no POST data)
		flash('Please fill out the form!')
	# Show registration form with message (if any)
	return render_template('register.html', sent=sent)



@app.route('/logout')
def logout():
    # Remove session data, this will log the user out
   session.pop('loggedin', None)
   session.pop('id', None)
   session.pop('username', None)
   # Redirect to login page
   return redirect(url_for('login'))



#Forgot Password
@app.route("/forgotpassword", methods=["GET", "POST"])
def forgotpassword():
	global email_address
	global pass_recovery
	# Connect to db
	cursor = connection.cursor(cursor_factory=psycopg2.extras.DictCursor)

	# Check if "username" and "password" POST requests exist (user submitted form)
	if request.method == 'POST' and 'email' in request.form:
		email = request.form['email']
		
 
		# Check if account exists using MySQL
		cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
		# Fetch one record and return result
		account = cursor.fetchone()
 
		if account:
			user_id = account['id']
			username = account['username']
			new_key = secrets.token_hex(16)
			pass_recovery[new_key] = user_id

			msg = Message('Password Recovery - PB Scanner', sender =   email_address, recipients = [email])
			msg.body = "Hey " + username + ", you requested a password reset. Enter the following link to reset your password:\n http://127.0.0.1:5000/resetpassword?k="+new_key
			mail.send(msg)
			flash("Recovery email sent. Check your mailbox, don't forget to check in the spam folder!")
			
		else:
			# Account doesnt exist or username/password incorrect
			flash("No account associated with that email.")

	return render_template("forgotpassword.html")



#Forgot Username
@app.route("/forgotusername", methods=["GET", "POST"])
def forgotusername():
	global email_address
	# Connect to db
	cursor = connection.cursor(cursor_factory=psycopg2.extras.DictCursor)

	# Check if "username" and "password" POST requests exist (user submitted form)
	if request.method == 'POST' and 'email' in request.form:
		email = request.form['email']
		
 
		# Check if account exists using MySQL
		cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
		# Fetch one record and return result
		account = cursor.fetchone()
 
		if account:
			username = account['username']
			msg = Message('Username Recovery - PB Scanner', sender =   email_address, recipients = [email])
			msg.body = "Hey there, you requested a username recovery. Your username is " + username
			mail.send(msg)
			flash("Recovery email sent. Check your mailbox, don't forget to check in the spam folder!")
			
		else:
			# Account doesnt exist or username/password incorrect
			flash("No account associated with that email.")

	return render_template("forgotusername.html")



#Reset Password
@app.route("/resetpassword", methods=["GET", "POST"])
def resetpassword():
	global pass_recovery
	# Connect to db
	cursor = connection.cursor(cursor_factory=psycopg2.extras.DictCursor)

	

	# Check if "username" and "password" POST requests exist (user submitted form)
	if request.method == 'POST' and 'new_password' in request.form and 'new_password2' in request.form and 'secret_key' in request.form:
		pass1 = request.form['new_password']
		pass2 = request.form['new_password2']
		secret_key = request.form['secret_key']
		if secret_key is None or secret_key not in pass_recovery:
			return "",400

		user_id = pass_recovery[secret_key]
		
		if pass1 != pass2:
			flash('Passwords do not match.')

		elif not re.match(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*#?&])[A-Za-z\d@$!#%*?&]{8,18}$', pass1):
			flash('Password must contain one uppercase letter, one lowercase letter, one number, one special character(@, $, !, %, *, #, ?, &), and must be 8-18 characters long.')
		else:
			_hashed_password = generate_password_hash(pass1)
			# Check if account exists using MySQL
			cursor.execute('UPDATE users SET password = %s WHERE id = %s', (_hashed_password,user_id))
			connection.commit()
			pass_recovery.pop(secret_key)
			flash('You have successfully reset your password!')

	else:
		secret_key = request.args.get('k',type = str)	
		if secret_key is None or secret_key not in pass_recovery:
			return "",400

		user_id = pass_recovery[secret_key]
		

	return render_template("resetpassword.html",skey = secret_key)



# Main
if __name__ == '__main__':
	app.run()

