import flask
from flask import Flask, Response, request, render_template, redirect, url_for
from flaskext.mysql import MySQL
import flask_login
import time
import numpy as np

#for image uploading
import os, base64

mysql = MySQL()
app = Flask(__name__)
app.secret_key = 'super secret string'  # Change this!

#These will need to be changed according to your creditionals
app.config['MYSQL_DATABASE_USER'] = 'cs460'
app.config['MYSQL_DATABASE_PASSWORD'] = 'cs460pass'
app.config['MYSQL_DATABASE_DB'] = 'cs460pa1'
app.config['MYSQL_DATABASE_HOST'] = 'localhost'
mysql.init_app(app)

#begin code used for login
login_manager = flask_login.LoginManager()
login_manager.init_app(app)

conn = mysql.connect()
cursor = conn.cursor()
cursor.execute("SELECT email from Users")
users = cursor.fetchall()

def getUserList():
	cursor = conn.cursor()
	cursor.execute("SELECT email from Users")
	return cursor.fetchall()

class User(flask_login.UserMixin):
	pass

@login_manager.user_loader
def user_loader(email):
	users = getUserList()
	if not(email) or email not in str(users):
		return
	user = User()
	user.id = email
	return user

@login_manager.request_loader
def request_loader(request):
	users = getUserList()
	email = request.form.get('email')
	if not(email) or email not in str(users):
		return
	user = User()
	user.id = email
	cursor = mysql.connect().cursor()
	cursor.execute("SELECT password FROM Users WHERE email = '{0}'".format(email))
	data = cursor.fetchall()
	pwd = str(data[0][0] )
	try:
		user.is_authenticated = request.form['password'] == pwd
	except:
		print("ok")
	# 	user.is_authenticated = False
	return user

'''
A new page looks like this:
@app.route('new_page_name')
def new_page_function():
	return new_page_html
'''

@app.route('/login', methods=['GET', 'POST'])
def login():
	if flask.request.method == 'GET':
		return '''
			   <form action='login' method='POST'>
				<input type='text' name='email' id='email' placeholder='email'></input>
				<input type='password' name='password' id='password' placeholder='password'></input>
				<input type='submit' name='submit'></input>
			   </form></br>
		   <a href='/'>Home</a>
			   '''
	#The request method is POST (page is recieving data)
	email = flask.request.form['email']
	cursor = conn.cursor()
	#check if email is registered
	if cursor.execute("SELECT password FROM Users WHERE email = '{0}'".format(email)):
		data = cursor.fetchall()
		pwd = str(data[0][0] )
		if flask.request.form['password'] == pwd:
			user = User()
			user.id = email
			flask_login.login_user(user) #okay login in user
			return flask.redirect(flask.url_for('protected')) #protected is a function defined in this file

	#information did not match
	return "<a href='/login'>Try again</a>\
			</br><a href='/register'>or make an account</a>"

@app.route('/logout')
def logout():
	flask_login.logout_user()
	return flask.redirect(flask.url_for('hello'))

@login_manager.unauthorized_handler
def unauthorized_handler():
	return render_template('unauth.html')

#you can specify specific methods (GET/POST) in function header instead of inside the functions as seen earlier
@app.route("/register", methods=['GET'])
def register():
	return render_template('register.html', supress='True')

@app.route("/register", methods=['POST'])
def register_user():
	try:
		email=request.form.get('email')
		password=request.form.get('password')
		fname=request.form.get('fname')
		lname=request.form.get('lname')
		birthd=request.form.get('birthd')
	except:
		print("couldn't find all tokens") #this prints to shell, end users will not see this (all print statements go to shell)
		return flask.redirect(flask.url_for('register'))
	cursor = conn.cursor()
	test =  isEmailUnique(email)
	if test:
		town=""
		try:
			town=request.form.get('town')
		except:
			print("couldn't find town")
		gender=""
		try:
			gender=request.form.get('gender')
		except:
			print("couldn't find town")
		print(cursor.execute("INSERT INTO Users (first_name, last_name, email, birth_date, hometown, gender, password) VALUES ('{0}', '{1}', '{2}', '{3}', '{4}', '{5}', '{6}')".format(fname, lname, email, birthd, town, gender, password)))
		conn.commit()
		#log user in
		user = User()
		user.id = email
		flask_login.login_user(user)
		return flask.redirect(flask.url_for('protected'))
	else:
		print("user already registered")
		return render_template('register.html', error="Error: user already exists", supress='True')

def getUsersPhotos(uid):
	cursor = conn.cursor()
	cursor.execute("SELECT data, photo_id, caption, albums_id FROM Photos WHERE user_id = '{0}'".format(uid))
	return cursor.fetchall() #NOTE list of tuples, [(imgdata, pid), ...]

def getFiveMostTagged(uid):
	cursor = conn.cursor()
	cursor.execute("SELECT photo_id FROM Photos WHERE user_id = '{0}'".format(uid))
	photoIds = cursor.fetchall()  # NOTE list of tuples, [(imgdata, pid), ...]
	print(photoIds)
	tags = []
	for i,v in enumerate(photoIds):
		print(v)
		cursor.execute("SELECT tag_id FROM Tagged WHERE photo_id = '{0}'".format(v[0]))
		tag = cursor.fetchall()
		for ii,vv in enumerate(tag):
			tags.append(vv[0])

	recom = []
	alreadyAdded = []
	for i,v in enumerate(tags):
		added = False
		for ii, vv in enumerate(alreadyAdded):
			if vv == v:
				added = True
				break
		if added:
			continue
		count = 0
		for ii, vv in enumerate(tags):
			if vv == v:
				count += 1
		alreadyAdded.append(v)
		recom.append([v, count])
		recom.sort(key=lambda x: -x[1])
	fiveMost = []
	for i,v in enumerate(recom):
		fiveMost.append(v[0])
	return fiveMost

def getRecommendedPhotos(fiveMost, user_id):
	cursor = conn.cursor()
	cursor.execute("SELECT photo_id FROM Photos WHERE NOT user_id='{0}'".format(user_id))
	photos = cursor.fetchall()
	# [id, fiveMatch, totalTags]
	photoMatches = []
	for i, v in enumerate(photos):
		cursor.execute("SELECT tag_id FROM Tagged WHERE photo_id = '{0}'".format(v[0]))
		photoTags = cursor.fetchall()
		count = 0
		for ii, vv in enumerate(photoTags):
			for iii, vvv in enumerate(fiveMost):
				if vv[0] == vvv:
					count += 1
					break
		photoMatches.append([v[0], count, len(photoTags)])
	photoMatches.sort(key=lambda x: (-x[1],x[2]))
	return photoMatches

def getPhotoById(photo_id):
	cursor = conn.cursor()
	cursor.execute("SELECT data, photo_id, caption, albums_id FROM Photos WHERE photo_id = '{0}'".format(photo_id))
	return cursor.fetchall()  # NOTE list of tuples, [(imgdata, pid), ...]

def getUserIdFromEmail(email):
	cursor = conn.cursor()
	cursor.execute("SELECT user_id  FROM Users WHERE email = '{0}'".format(email))
	return cursor.fetchone()[0]

def isEmailUnique(email):
	#use this to check if a email has already been registered
	cursor = conn.cursor()
	if cursor.execute("SELECT email  FROM Users WHERE email = '{0}'".format(email)):
		#this means there are greater than zero entries with that email
		return False
	else:
		return True

def getUserAlbums(uid):
	cursor = conn.cursor()
	cursor.execute("SELECT albums_id, name, date FROM Albums WHERE user_id = '{0}'".format(uid))
	return cursor.fetchall() #NOTE list of tuples, [(imgdata, pid), ...]

def checkIfAlbumExists(uid, name):
	cursor = conn.cursor()
	if cursor.execute("SELECT albums_id FROM Albums WHERE name = '{0}' AND user_id = '{1}'".format(name, uid)):
		#this means there are greater than zero entries with that email
		return True
	else:
		return False

def checkIfFriends(uid1, uid2):
	cursor = conn.cursor()
	if cursor.execute("SELECT * FROM Friends WHERE user_id1 = '{0}' AND user_id2 = '{1}'".format(uid1, uid2)):
		# this means there are greater than zero entries with that email
		return True
	else:
		return False

def getComments(photoId):
	cursor = conn.cursor()
	cursor.execute("SELECT comment_id, user_id, photo_id, text, date FROM Comments WHERE photo_id='{0}'".format(photoId))
	return cursor.fetchall()

def getUserName(user_id):
	cursor = conn.cursor()
	cursor.execute("SELECT first_name, last_name FROM Users WHERE user_id='{0}'".format(user_id))
	return cursor.fetchall()

def imageAuthorId(photo_id):
	cursor = conn.cursor()
	cursor.execute("SELECT user_id FROM Photos WHERE photo_id='{0}'".format(photo_id))
	return cursor.fetchall()

def getPhotoLikes(photo_id):
	cursor = conn.cursor()
	cursor.execute("SELECT user_id FROM Likes WHERE photo_id='{0}'".format(photo_id))
	likes = cursor.fetchall()
	if likes:
		return likes
	else:
		return []

def getAllTags():
	cursor = conn.cursor()
	cursor.execute("SELECT * FROM Tags WHERE true")
	return cursor.fetchall()

def getMostRecentPhotoId():
	cursor = conn.cursor()
	cursor.execute("SELECT MAX(photo_id) FROM Photos WHERE true")
	return cursor.fetchall()

# [tag_id, name]
def getPhotoTagNames(photo_id):
	cursor = conn.cursor()
	cursor.execute("SELECT tag_id FROM Tagged WHERE photo_id='{0}'".format(photo_id))
	tags = cursor.fetchall()
	tagNames = []
	for i,v in enumerate(tags):
		cursor = conn.cursor()
		cursor.execute("SELECT * FROM Tags WHERE tag_id='{0}'".format(v[0]))
		tagNames.append(cursor.fetchall())
	return tagNames

# [tag_id, name, count]
def getAllTagsWithCountSorted():
	cursor = conn.cursor()
	cursor.execute("SELECT tag_id, name FROM Tags WHERE true")
	tags = cursor.fetchall()
	tagCount = []
	if tags:
		for i,v in enumerate(tags):
			print(v)
			cursor.execute("SELECT COUNT(*) FROM Tagged WHERE tag_id = '{0}'".format(v[0]))
			count = cursor.fetchall()
			print(count)
			tagCount.append([v[0], v[1], count[0][0]])
		tagCount.sort(key=lambda x: -x[2])
	return tagCount

def getPhotosWithTags(tagList):
	nameQuery = ""
	for i in range(len(tagList)):
		if i < len(tagList)-1:
			nameQuery += "name = '"+str(tagList[i])+"' OR "
		else:
			nameQuery += "name = '" + str(tagList[i]) + "'"
	cursor = conn.cursor()
	cursor.execute("SELECT tag_id FROM Tags WHERE "+nameQuery)
	idList = cursor.fetchall()
	tagIdList = []
	for i, v in enumerate(idList):
		tagIdList.append(v[0])
	print(tagIdList)

	orQuery = ""
	for i in range(len(tagIdList)):
		if i < len(tagIdList)-1:
			orQuery += "tag_id = "+str(tagIdList[i])+" OR "
		else:
			orQuery += "tag_id = " + str(tagIdList[i])
	sqlQuery = '''SELECT * FROM
		((SELECT data, photo_id, caption, albums_id, user_id FROM Photos) as T3 inner join
			(select photo_id, count(photo_id) from
				(select * from Tagged where {0})
					as T group by photo_id having count(*)={1}
			) as T2 on T2.photo_id = T3.photo_id
		)'''.format(orQuery, str(len(tagIdList)))
	print(sqlQuery)
	cursor.execute(sqlQuery)
	return cursor.fetchall()

def getCommentsByUserSort(comment):
	cursor = conn.cursor()
	cursor.execute("select user_id, count(user_id) from Comments where text='{0}' group by user_id;".format(comment))
	commentCount = np.asarray(cursor.fetchall()).tolist()
	users = []
	if commentCount:
		commentCount.sort(key=lambda x: -x[1])
		for i,v in enumerate(commentCount):
			name = getUserName(v[0])
			users.append([name[0][0], name[0][1],v[0], v[1]])
	return users

def measureContribution(user_id):
	cursor = conn.cursor()
	cursor.execute("select count(*) from Photos where user_id='{0}'".format(user_id))
	photos_posted = cursor.fetchall()[0][0]
	cursor.execute("select count(*) from Comments where user_id='{0}'".format(user_id))
	comments_posted = cursor.fetchall()[0][0]
	return photos_posted+comments_posted

def getUsersByContributions():
	measureContribution(3)
	cursor = conn.cursor()
	cursor.execute("SELECT user_id FROM Users");
	allUsers = cursor.fetchall()
	contributions = []
	for i,v in enumerate(allUsers):
		name = getUserName(v[0])
		contributions.append([name[0][0], name[0][1], v[0], measureContribution(v[0])])
		contributions.sort(key=lambda x: -x[3])
	return contributions

def getFriends(uid):
	cursor = conn.cursor()
	cursor.execute("SELECT user_id2 FROM Friends WHERE user_id1='{0}'".format(uid));
	x = cursor.fetchall()
	if x:
		return x
	return []

def getFriendOfFriend(uid):
	myFriends = getFriends(uid)
	allFriends = []
	for i,v in enumerate(myFriends):
		friendOfFriend = getFriends(v[0])
		for ii,vv in enumerate(friendOfFriend):
			ok = True

			# remove users who are already friends
			for iii, vvv in enumerate(myFriends):
				if vvv[0] == vv[0]:
					ok = False
					break
			# remove yourself
			if vv[0] == uid:
				ok = False

			if ok:
				allFriends.append(vv[0])
	recom = []
	alreadyAdded = []
	for i,v in enumerate(allFriends):
		added = False
		for ii, vv in enumerate(alreadyAdded):
			if vv == v:
				added = True
				break
		if added:
			continue
		count = 0
		for ii, vv in enumerate(allFriends):
			if vv == v:
				count += 1
		name = getUserName(v)
		alreadyAdded.append(v)
		recom.append([name[0][0], name[0][1], v, count])
		recom.sort(key=lambda x: -x[3])
	return recom
#end login code

@app.route('/profile')
@flask_login.login_required
def protected():
	user_id = getUserIdFromEmail(flask_login.current_user.id)
	recom = getRecommendedPhotos(getFiveMostTagged(user_id), user_id)[:10]
	photos = []
	for i,v in enumerate(recom):
		photos.append(getPhotoById(v[0]))
	cursor = conn.cursor()
	cursor.execute(
		"SELECT first_name, last_name, birth_date, hometown, gender, user_id FROM Users WHERE user_id='{0}'".format(
			user_id))
	data = cursor.fetchall()
	cursor.execute(
		"SELECT user_id2 FROM Friends WHERE user_id1='{0}'".format(user_id))
	friends = cursor.fetchall()
	friend_list = []
	for i,v in enumerate(friends):
		cursor = conn.cursor()
		cursor.execute("SELECT first_name, last_name, user_id FROM Users WHERE user_id='{0}'".format(v[0]))
		friend_list.append(cursor.fetchall())
	# print(friends, len(friends), friend_list)
	recom = getFriendOfFriend(user_id)
	return render_template('profile.html', photos=photos, base64=base64, recommendations=recom, name=flask_login.current_user.id, friend_list=friend_list, data=data, message="Here's your profile")

#begin photo uploading code
# photos uploaded using base64 encoding so they can be directly embeded in HTML
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])
def allowed_file(filename):
	return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

@app.route('/upload', methods=['GET', 'POST'])
@flask_login.login_required
def upload_file():
	if request.method == 'POST':
		uid = getUserIdFromEmail(flask_login.current_user.id)
		imgfile = request.files['photo']
		caption = request.form.get('caption')
		album = request.form.get('albumId')
		tags = request.form.get('uploadTags')
		photo_data =imgfile.read()
		cursor = conn.cursor()
		cursor.execute('''INSERT INTO Photos (data, user_id, caption, albums_id) VALUES (%s, %s, %s, %s )''' ,(photo_data,uid, caption, album))
		conn.commit()
		if(tags):
			tags = tags.split(",")
			if tags[0] != "":
				photo_id = getMostRecentPhotoId()[0][0]
				for i,v in enumerate(tags):
					cursor = conn.cursor()
					cursor.execute('''INSERT INTO Tagged (photo_id, tag_id) VALUES (%s, %s)''',
								   (photo_id, v))
					conn.commit()
		return flask.redirect(flask.url_for('protected'))
	#The method is GET so we return a  HTML form to upload the a photo.
	else:
		return flask.redirect(flask.url_for('hello'))
#end photo uploading code

@app.route('/album', methods=['GET', 'POST'])
@flask_login.login_required
def manage_albums():
	if request.method == 'POST':
		type = request.form.get('type')
		if str(type) == "1":
			uid = getUserIdFromEmail(flask_login.current_user.id)
			albumName = request.form.get('albumName')
			if checkIfAlbumExists(uid, albumName):
				return flask.redirect(flask.url_for('manage_albums'))
			date = time.strftime('%Y-%m-%d')
			cursor = conn.cursor()
			cursor.execute('''INSERT INTO Albums (name, user_id, date) VALUES (%s, %s, %s )''' ,(albumName,uid, date))
			conn.commit()
			return flask.redirect('/album?id='+str(uid))
		elif str(type) == "2":
			uid = getUserIdFromEmail(flask_login.current_user.id)
			tagName = request.form.get('tagName')
			cursor = conn.cursor()
			cursor.execute('''INSERT INTO Tags (name) VALUES (%s)''', (tagName))
			conn.commit()
			return flask.redirect('/album?id=' + str(uid))
		uid = getUserIdFromEmail(flask_login.current_user.id)
		return flask.redirect('/album?id=' + str(uid))
	#The method is GET so we return a  HTML form to upload the a photo.
	else:
		myid = "-1"
		if flask_login.current_user.is_authenticated:
			myid = str(getUserIdFromEmail(flask_login.current_user.id))
		uid = request.args.get('id')
		author = getUserName(uid)
		albums = getUserAlbums(uid)
		return render_template('albums.html', tags=getAllTags(), author=[author, uid], albums=albums, user=flask_login.current_user, myid=myid, photos=getUsersPhotos(uid), base64=base64, len=len(albums))

@app.route('/search', methods=['GET', 'POST'])
def search():
	if request.method == 'GET':
		return render_template('search.html')
	else:
		fname = request.form.get('firstName')
		lname = request.form.get('lastName')
		print(fname, lname, fname=="", lname=="", "here")
		if fname == "" and lname == "":
			cursor = conn.cursor()
			cursor.execute("SELECT first_name, last_name, user_id FROM Users WHERE true")
			return render_template('search.html', users=cursor.fetchall())
		elif fname == "":
			cursor = conn.cursor()
			cursor.execute("SELECT first_name, last_name, user_id FROM Users WHERE last_name = '{0}'".format(lname))
			return render_template('search.html', users=cursor.fetchall())
		elif lname == "":
			cursor = conn.cursor()
			cursor.execute("SELECT first_name, last_name, user_id FROM Users WHERE first_name = '{0}'".format(fname))
			return render_template('search.html', users=cursor.fetchall())
		else:
			cursor = conn.cursor()
			cursor.execute("SELECT first_name, last_name, user_id FROM Users WHERE first_name = '{0}' AND last_name = '{1}'".format(fname, lname))
			return render_template('search.html', users=cursor.fetchall())
		return render_template('search.html')

@app.route('/tagsearch', methods=['GET', 'POST'])
def tagsearch():
	if request.method == 'GET':
		return render_template('tagsearch.html')
	if request.method == 'POST':
		tags = request.form.get('tag')
		if tags:
			query = tags.split(" ")
			print(query)
			photos = getPhotosWithTags(query)
			return render_template('tagsearch.html', photos=photos, len=len(photos), base64=base64)
		return render_template('tagsearch.html')


@app.route("/commentsearch", methods=['GET', 'POST'])
def commentsearch():
	if request.method == 'GET':
		return render_template('commentsearch.html')
	if request.method == 'POST':
		comment = request.form.get('comment')
		if comment:
			users = getCommentsByUserSort(comment)
			print(users)
			return render_template('commentsearch.html', users=users)
		return render_template('commentsearch.html')

#default page
@app.route("/", methods=['GET'])
def hello():
	contributions = getUsersByContributions()
	cursor.execute("SELECT data, photo_id, caption, albums_id, user_id FROM Photos WHERE true")
	photos = cursor.fetchall()
	authors = []
	for i,v in enumerate(photos):
		author = getUserName(v[4])
		likes = getPhotoLikes(v[1])
		authors.append([author, v[1], v[2], len(likes), v[0], v[4]])
	return render_template('hello.html', contributions=contributions[:10], tags=getAllTagsWithCountSorted(), photos=authors, base64=base64, user=flask_login.current_user)

#default page
@app.route("/photo", methods=['GET', 'POST'])
def photo():
	if request.method == 'GET':
		photoid = request.args.get('id')
		if photoid:
			cursor = conn.cursor()
			cursor.execute("SELECT data, photo_id, caption, albums_id, user_id FROM Photos WHERE photo_id='{0}'".format(photoid))
			data=cursor.fetchall()
			if data:
				author = getUserName(data[0][4])
				comments = getComments(photoid)
				authors = []
				for i, v in enumerate(comments):
					authors.append([v, getUserName(v[1])])
				likes = getPhotoLikes(photoid)
				isLiked = False
				if flask_login.current_user.is_authenticated:
					userId = getUserIdFromEmail(flask_login.current_user.id)
					for i,v in enumerate(likes):
						if userId == v[0]:
							isLiked = True
							break
				return render_template('photo.html', tags=getPhotoTagNames(photoid), author=[data[0][4], author], likes=len(likes), isLiked=isLiked, photos=data, base64=base64, comments=authors, user=flask_login.current_user)
			else:
				return flask.redirect(flask.url_for('hello'))
		else:
			return flask.redirect(flask.url_for('hello'))
	else:
		print("hello")
		photoid = request.form.get('photoId')
		if photoid:
			type = request.form.get('type')
			print(photoid, type)
			if str(type) == "1":
				print(photoid)
				userId = getUserIdFromEmail(flask_login.current_user.id)
				if userId == imageAuthorId(str(photoid))[0][0]:
					return flask.redirect("/photo?id="+str(photoid))
				cursor = conn.cursor()
				print(photoid)
				cursor.execute('''INSERT INTO Comments (user_id, photo_id, text, date) VALUES (%s, %s, %s, %s )''',
							   (userId, photoid, request.form.get('comment'), time.strftime('%Y-%m-%d')))
				conn.commit()
			elif str(type) == "2":
				userId = getUserIdFromEmail(flask_login.current_user.id)
				likes = getPhotoLikes(photoid)
				isLiked = False
				for i,v in enumerate(likes):
					if userId == v[0]:
						isLiked = True
						break
				if not isLiked:
					cursor = conn.cursor()
					cursor.execute('''INSERT INTO Likes (user_id, photo_id) VALUES (%s, %s)''',
								   (userId, photoid))
					conn.commit()
			elif str(type) == "3":
				userId = getUserIdFromEmail(flask_login.current_user.id)
				likes = getPhotoLikes(photoid)
				isLiked = False
				for i,v in enumerate(likes):
					if userId == v[0]:
						isLiked = True
						break
				if isLiked:
					cursor = conn.cursor()
					cursor.execute('''DELETE FROM Likes WHERE (user_id, photo_id) = (%s, %s)''',
								   (userId, photoid))
					conn.commit()
			return flask.redirect("/photo?id="+str(photoid))
		return flask.redirect("/photo?id="+str(photoid))

@app.route("/photos", methods=['GET'])
def photos():
	if request.method == 'GET':
		userid = request.args.get('user')
		tagid = request.args.get('tag')
		if tagid:
			if userid:
				cursor = conn.cursor()
				cursor.execute(
					"SELECT data, Photos.photo_id, caption, albums_id, user_id FROM (Photos INNER JOIN Tagged ON Photos.photo_id = Tagged.photo_id) WHERE tag_id='{0}' AND Photos.user_id='{1}'".format(
						tagid, userid))
				data = cursor.fetchall()
				authors = []
				for i, v in enumerate(data):
					authors.append([v[4], getUserName(v[4])])
				return render_template('photos.html', authors=authors, len=len(data), photos=data, base64=base64,
									   user=flask_login.current_user)
			else:
				cursor = conn.cursor()
				cursor.execute(
					"SELECT data, Photos.photo_id, caption, albums_id, user_id FROM (Photos INNER JOIN Tagged ON Photos.photo_id = Tagged.photo_id) WHERE tag_id='{0}'".format(tagid))
				data = cursor.fetchall()
				authors = []
				for i, v in enumerate(data):
					authors.append([v[4], getUserName(v[4])])
				return render_template('photos.html', authors=authors, len=len(data), photos=data, base64=base64,
									   user=flask_login.current_user)
		elif userid:
			cursor = conn.cursor()
			cursor.execute("SELECT data, photo_id, caption, albums_id, user_id FROM Photos WHERE user_id='{0}'".format(userid))
			data=cursor.fetchall()
			authors = []
			for i,v in enumerate(data):
				authors.append([v[4], getUserName(v[4])])
			return render_template('photos.html', authors=authors, len=len(data), photos=data, base64=base64, user=flask_login.current_user)
		else:
			return flask.redirect(flask.url_for('hello'))


#default page
@app.route("/user", methods=['GET', 'POST'])
def user():
	if request.method == 'GET':
		user_id = request.args.get('id')
		if user_id:
			isFriends = False
			if flask_login.current_user.is_authenticated:
				isFriends = checkIfFriends(user_id, getUserIdFromEmail(flask_login.current_user.id))
				if str(getUserIdFromEmail(flask_login.current_user.id)) == str(user_id):
					return flask.redirect(flask.url_for('protected'))
			cursor = conn.cursor()
			cursor.execute("SELECT first_name, last_name, birth_date, hometown, gender, user_id FROM Users WHERE user_id='{0}'".format(user_id))
			data=cursor.fetchall()
			if data:
				return render_template('user.html', isFriends=isFriends, data=data, user=flask_login.current_user)
			else:
				return flask.redirect(flask.url_for('hello'))
		else:
			return flask.redirect(flask.url_for('hello'))
	else:
		user1 = getUserIdFromEmail(request.form.get('user1'))
		user2 = request.form.get('user2')
		type = request.form.get('type')
		if str(type) == "2":
			if checkIfFriends(user1, user2):
				return flask.redirect(flask.url_for('protected'))
			else:
				cursor = conn.cursor()
				cursor.execute('''INSERT INTO Friends (user_id1, user_id2) VALUES (%s, %s)''', (user1, user2))
				cursor.execute('''INSERT INTO Friends (user_id1, user_id2) VALUES (%s, %s)''', (user2, user1))
				conn.commit()
				return flask.redirect(flask.url_for('protected'))
		elif str(type) == "1":
			print("here", checkIfFriends(user1, user2))
			if checkIfFriends(user1, user2):
				cursor = conn.cursor()
				cursor.execute('''DELETE FROM Friends WHERE (user_id1, user_id2) = (%s, %s)''', (user1, user2))
				cursor.execute('''DELETE FROM Friends WHERE (user_id1, user_id2) = (%s, %s)''', (user2, user1))
				conn.commit()
				return flask.redirect(flask.url_for('protected'))
			else:
				return flask.redirect(flask.url_for('protected'))
		return flask.redirect(flask.url_for('hello'))
