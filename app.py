from  __future__  import print_function
import pyrebase
from flask import *
from datetime import datetime
import pickle
import os.path
import googleapiclient.discovery
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

app = Flask(__name__)

config = {
    "apiKey": "AIzaSyDQkaQjhaa0ueRT_D-1vVtXMbX8xtqPwBI",
    "authDomain": "covid-19-isolation-tracker.firebaseapp.com",
    "databaseURL": "https://covid-19-isolation-tracker.firebaseio.com",
    "projectId": "covid-19-isolation-tracker",
    "storageBucket": "covid-19-isolation-tracker.appspot.com",
    "messagingSenderId": "435855688991",
    "appId": "1:435855688991:web:17bcb9b15f945d4cc11c2a",
    "measurementId": "G-JBSNN6Z8DV"
}

firebase = pyrebase.initialize_app(config)

auth = firebase.auth()
db = firebase.database()

@app.route('/', methods = ['GET', 'POST'])
def public():
    loggedin=None
    if session != {}:
        loggedin=True
        uid = session['uid']
        data = db.child("users").child(uid).get().val()
        startDate = datetime.strptime(data["startDate"], '%Y-%m-%d-%H:%M:%S')
        today = datetime.now()
        days = abs((today - startDate).days)
        daysLeft = 14 - days
        today = today.strftime('%Y-%m-%d')
        return render_template("tracker.html", data=data, daysLeft=daysLeft, today=today)
    return render_template('index.html', loggedin=loggedin)

#--------------register
@app.route('/register')
def register():
    return render_template('register.html')

@app.route('/registration', methods=['GET', 'POST'])
def enter_user():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['Pass']
        try:
            #create new user
            user = auth.create_user_with_email_and_password(email, password)
            uid = user['localId']
            today = datetime.now()
            today = today.strftime("%Y-%m-%d-%H:%M:%S")
            #set up db item for user with key=uid
            data = {
                "email": email,
                "startDate": today
            }
            db.child("users").child(uid).set(data)
            moreData = {
                "temperature": 37.0,
                "cough": 0,
                "headache": 0,
                "fatigue": 0,
                "other": None
            }
            db.child("users").child(uid).child(14).set(moreData)
            return render_template('index_login.html')
        except:
            return render_template('register.html')


#--------login
@app.route('/login')
def login():
    return render_template('index_login.html')

@app.route('/loginAuth', methods=['GET', 'POST'])
def loginAuth():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['Pass']
        try:
            #user sign in
            user = auth.sign_in_with_email_and_password(email,password)
            #get user data from db
            uid = user['localId']
            #save session
            session['uid'] = uid
            #get days
            generalData = db.child("users").child(uid).get().val()
            startDate = datetime.strptime(generalData["startDate"], '%Y-%m-%d-%H:%M:%S')
            today = datetime.now()
            days = abs((today - startDate).days)
            daysLeft = 14 - days
            today = today.strftime('%Y-%m-%d')
            #get latest data
            data = db.child("users").child(uid).child(daysLeft).get().val()
            if not data:
                data = db.child("users").child(uid).child(daysLeft+1).get().val()
            return render_template("tracker.html", data=data, daysLeft=daysLeft, today=today)
        except:
            return render_template('index_login.html')


#-----------------update
@app.route('/checklist', methods=['GET','POST'])
def checklist():
    if request.method == 'POST':
        temperature = request.form['temperature']
        cough = request.form.get('cough', 0)
        headache = request.form.get('headache', 0)
        fatigue = request.form.get('fatigue', 0)
        print(cough, headache, fatigue)
        try:
            uid = session['uid']
            #get days
            generalData = db.child("users").child(uid).get().val()
            startDate = datetime.strptime(generalData["startDate"], '%Y-%m-%d-%H:%M:%S')
            today = datetime.now()
            days = abs((today - startDate).days)
            daysLeft = 14 - days
            today = today.strftime('%Y-%m-%d')
            #get old data
            #skip
            #get new data
            newData = {
                "temperature": temperature,
                "cough": cough,
                "headache": headache,
                "fatigue": fatigue
            }
            if db.child("users").child(uid).child(daysLeft).get():
                db.child("users").child(uid).child(daysLeft).update(newData)
            else:
                db.child("users").child(uid).child(daysLeft).set(newData)
            return render_template("tracker.html", data=newData, daysLeft=daysLeft, today=today)
        except:
            return render_template("tracker.html", data="error", daysLeft="error", today="error")

@app.route('/logout', methods=['GET','POST'])
def logout():
    #logout the user
    session.pop("uid", None)
    return render_template('index.html')


@app.route('/dashboard', methods=['GET','POST'])
def cal():
    creds = None
    SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with  open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
    'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            # with open('token.pickle', 'wb') as token: # can't write files in Google App Engine so comment out or delete
            # pickle.dump(creds, token)
    service = googleapiclient.discovery.build('calendar', 'v3', credentials=creds)
    # Call the Calendar API
    now = datetime.datetime.utcnow().isoformat() +  'Z'  # 'Z' indicates UTC time
    print('Getting the upcoming 10 events')
    events_result = service.events().list(calendarId='find your cal id from google and paste it here', timeMin=now, maxResults=10, singleEvents=True, orderBy='startTime').execute()
    events = events_result.get('items', [])
    if not events:
        print('No upcoming events found.')
    # for event in events:
    # start = event['start'].get('dateTime', event['start'].get('date'))
    # print(start, event['summary'])
    event_list = [event["summary"] for event in events]

    return render_template('dashboard.html', events = events_list)


#secret key
app.secret_key = b'_5askq478eqrbkhdfs]/'

if __name__ =='__main__':
    app.run(debug=True)
