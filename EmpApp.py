from flask import Flask, render_template, session, request
from pymysql import connections
import os
import boto3
from config import *

app = Flask(__name__)
app.secret_key = "CC"

bucket = custombucket
region = customregion

db_conn = connections.Connection(
    host=customhost,
    port=3306,
    user=customuser,
    password=custompass,
    db=customdb

)
output = {}
table = 'employee'


@app.route("/", methods=['GET', 'POST'])
def home():
    return render_template('home.html')


@app.route("/about", methods=['POST'])
def about():
    return render_template('www.tarc.edu.my')


@app.route("/addemp", methods=['POST'])
def AddEmp():
    emp_id = request.form['emp_id']
    first_name = request.form['first_name']
    last_name = request.form['last_name']
    pri_skill = request.form['pri_skill']
    location = request.form['location']
    emp_image_file = request.files['emp_image_file']

    insert_sql = "INSERT INTO employee VALUES (%s, %s, %s, %s, %s)"
    cursor = db_conn.cursor()

    if emp_image_file.filename == "":
        return "Please select a file"

    try:

        cursor.execute(insert_sql, (emp_id, first_name, last_name, pri_skill, location))
        db_conn.commit()
        emp_name = "" + first_name + " " + last_name
        # Uplaod image file in S3 #
        emp_image_file_name_in_s3 = "emp-id-" + str(emp_id) + "_image_file"
        s3 = boto3.resource('s3')

        try:
            print("Data inserted in MySQL RDS... uploading image to S3...")
            s3.Bucket(custombucket).put_object(Key=emp_image_file_name_in_s3, Body=emp_image_file)
            bucket_location = boto3.client('s3').get_bucket_location(Bucket=custombucket)
            s3_location = (bucket_location['LocationConstraint'])

            if s3_location is None:
                s3_location = ''
            else:
                s3_location = '-' + s3_location

            object_url = "https://s3{0}.amazonaws.com/{1}/{2}".format(
                s3_location,
                custombucket,
                emp_image_file_name_in_s3)

        except Exception as e:
            return str(e)

    finally:
        cursor.close()

    print("all modification done...")
    return render_template('AddEmpOutput.html', name=emp_name)

@app.route("/leclogin")
def LecLoginPage():
    return render_template('LecturerLogin.html')

@app.route("/loginlec", methods=['GET','POST'])
def LoginLec():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        select_sql = "SELECT * FROM lecturer WHERE email = %s AND password = %s"
        cursor = db_conn.cursor()

        try:
            cursor.execute(select_sql, (email,password,))
            lecturer = cursor.fetchone()

            if lecturer:
                session['loginLecturer'] = lecturer[0]
                select_sql = "SELECT * FROM student WHERE supervisor = %s"

                cursor.execute(select_sql, (lecturer[0],))
                students = cursor.fetchall()

                return render_template('LecturerHome.html', lecturer=lecturer, name=lecturer[2], gender=lecturer[3], email=lecturer[4], expertise=lecturer[5], students=students)
            
        except Exception as e:
            return str(e)

        finally:   
            cursor.close()
        
    return render_template('LecturerLogin.html', msg="Access Denied : Invalid email or password")

@app.route("/logoutlec")
def LogoutLec():
    if 'loginLecturer' in session:
        session.pop('loginLecturer', None)
    return render_template('home.html')

@app.route("/lecHome")
def LecHome():
    if 'loginLecturer' in session:
        lectId = session['loginLecturer']
        return render_template('LecturerHome.html', lectId = lectId)
    else:
        return render_template('LecturerLogin.html')

@app.route("/lecStudentDetails", methods=['GET'])
def LecStudentDetails():
    if 'loginLecturer' in session & request.args.get('studentId') is not None & request.args.get('studentId') != '':
        lectId = session['loginLecturer']
        studId = request.args.get('studentId')

        select_sql = "SELECT * FROM students WHERE lecturer = %s AND studentID = %s"
        cursor = db_conn.cursor()

        try:
            cursor.execute(select_sql, (lectId,studId,))
            student = cursor.fetchone()

            if student:
                select_sql = "SELECT * FROM report WHERE supervisor = %s AND student = %s"

                cursor.execute(select_sql, (lectId, studId,))
                reports = cursor.fetchall()

                return render_template('LecStudDetails.html', student=student, count=reports.count, reports=reports)
            
        except Exception as e:
            return str(e)

        finally:   
            cursor.close()

    return render_template('/lecHome')

@app.route("/updateReportStatus", methods=['POST'])
def LecUpdateReportStatus():
    if request.method == 'POST':
        if request.form['submit'] == 'approve':
            status = 'Approved'
        elif request.form['submit'] == 'reject':
            status = 'Rejected'
    
    return render_template('LecStudDetails.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)

