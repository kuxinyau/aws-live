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

                return render_template('LecturerHome.html', lecturer=lecturer, students=students)
            
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

        select_sql = "SELECT * FROM lecturer WHERE lectId = %s"
        cursor = db_conn.cursor()

        try:
            cursor.execute(select_sql, (lectId,))
            lecturer = cursor.fetchone()

            if lecturer:
                select_sql = "SELECT * FROM student WHERE supervisor = %s"

                cursor.execute(select_sql, (lecturer[0],))
                students = cursor.fetchall()
            
        except Exception as e:
            return str(e)

        finally:   
            cursor.close()

        return render_template('LecturerHome.html', lecturer=lecturer, students=students)
    
    else:
        return render_template('LecturerLogin.html')

@app.route("/lecStudentDetails", methods=['GET'])
def LecStudentDetails():
    if 'loginLecturer' in session and request.args.get('studentId') is not None and request.args.get('studentId') != '':
        lectId = session['loginLecturer']
        studId = request.args.get('studentId')

        select_sql = "SELECT * FROM student WHERE supervisor = %s AND studentID = %s"
        cursor = db_conn.cursor()

        try:
            cursor.execute(select_sql, (lectId,studId,))
            student = cursor.fetchone()

            if student:
                select_sql = "SELECT * FROM report WHERE student = %s"

                cursor.execute(select_sql, (studId,))
                reports = cursor.fetchall()

                return render_template('LecStudDetails.html', student=student, reports=reports)
            
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

@app.route("/fetchdata", methods=['POST'])
def GetEmp():
    lec_id = request.form['lec_id']
    select_sql = "SELECT * FROM lecturer WHERE lectId = %s"
    cursor = db_conn.cursor()

    try:
        cursor.execute(select_sql, (lec_id,))
        lecturer = cursor.fetchone()

        if not lecturer:
            return "Lecturer not found"

        lec_id = lecturer[0]
        passowrd = lecturer[1]
        name = lecturer[2]
        gender = lecturer[3]
        email = lecturer[4]
        expertis = lecturer[5]

        # Fetch the S3 image URL based on emp_id
        lec_image_file_name_in_s3 = "lec-id-" + str(lec_id) + "_image_file"
        s3 = boto3.client('s3')
        bucket_name = custombucket

        try:
            response = s3.generate_presigned_url('get_object',
                                                 Params={'Bucket': bucket_name,
                                                         'Key': lec_image_file_name_in_s3},
                                                 ExpiresIn=1000)  # Adjust the expiration time as needed

            # You can return the employee details along with the image URL
            lec_details = {
                "lec_id": lec_id,
                "passowrd": passowrd,
                "name": name,
                "gender": gender,
                "email": email,
                "expertis": expertis,
                "image_url": response
            }

            return render_template('GetLecOutput.html',image_url=response,id=lec_id ,psw=passowrd, name=name , email=email , expertise =expertis,gender=gender )

        except Exception as e:
            return str(e)

    except Exception as e:
        return str(e)

    finally:
        cursor.close()

@app.route("/editlec", methods=['POST'])
def UpdateEmp():
    lec_id = request.form['lec_id']
    password = request.form['password']
    name = request.form['name']
    gender = request.form['gender']
    email = request.form['email']
    expertise = request.form['expertise']
    lec_image_file = request.files['lec_image_file']

    update_sql = "UPDATE lecturer SET password=%s, name=%s, gender=%s, email=%s, expertise=%s WHERE lectId=%s"
    cursor = db_conn.cursor()     

    try:
        # Check if the employee exists
        check_sql = "SELECT * FROM lecturer WHERE lectId = %s"
        cursor.execute(check_sql, (lec_id,))
        existing_lecturer = cursor.fetchone()

        if not existing_lecturer:
            return "Lecturer not found"

        cursor.execute(update_sql, (password, name, gender, email, expertise,lec_id))
        db_conn.commit()
        lec_name = "" + name 

        if lec_image_file.filename != "":
            # Update image file in S3
            lec_image_file_name_in_s3 = "lec-id-" + str(lec_id) + "_image_file"
            s3 = boto3.resource('s3')

            try:
                print("Data updated in MySQL RDS... updating image in S3...")
                s3.Bucket(custombucket).put_object(Key=lec_image_file_name_in_s3, Body=lec_image_file)
                bucket_location = boto3.client('s3').get_bucket_location(Bucket=custombucket)
                s3_location = (bucket_location.get('LocationConstraint'))

                if s3_location is None:
                    s3_location = ''
                else:
                    s3_location = '-' + s3_location

                object_url = "https://s3{0}.amazonaws.com/{1}/{2}".format(
                    s3_location,
                    custombucket,
                    lec_image_file_name_in_s3)

            except Exception as e:
                return str(e)

    finally:
        cursor.close()

    print("all modifications done...")
    return render_template('UpdateEmpOutput.html', name=name)

@app.route("/displayStudent" ,methods=['GET','POST'])
def GetStudent():
    
    action=request.form['action']
    id=request.form['lec_id']

    if action == 'drop':
        select_sql = f"SELECT * FROM student WHERE supervisor LIKE '%{id}%'"
        cursor = db_conn.cursor()

    if action =='pickUp':
        select_sql = f"SELECT * FROM student WHERE supervisor IS NULL"
        cursor = db_conn.cursor()

    try:
        cursor.execute(select_sql)
        students = cursor.fetchall()  # Fetch all students
               
        student_list = []

        for student in students:
            student_id = student[0]
            name = student[1]
            gender = student[4]
            email = student[6]
            level = student[7]
            programme = student[8]
            cohort = student[10]

            # Fetch the S3 image URL based on student_id
            stu_image_file_name_in_s3 = "stu-id-" + str(student_id) + "_image_file"
            s3 = boto3.client('s3')
            bucket_name = custombucket

            try:
                response = s3.generate_presigned_url('get_object',
                                                     Params={'Bucket': bucket_name,
                                                             'Key': stu_image_file_name_in_s3},
                                                     ExpiresIn=1000)  # Adjust the expiration time as needed

                # Create a dictionary for each student with their details and image URL
                student_data = {
                    "student_id": student_id,
                    "name": name,
                    "gender": gender,
                    "email": email,
                    "level": level,
                    "programme": programme,
                    "cohort": cohort,
                }

                # Append the student's dictionary to the student_list
                student_list.append(student_data)
                

            except Exception as e:
                return str(e)       
         
        if action == 'drop':
         return render_template('DropStudent.html', student_list=student_list,id=id)

        if action =='pickUp': 
         return render_template('PickUpStudent.html', student_list=student_list)

    except Exception as e:
        return str(e)

    finally:
        cursor.close()


@app.route("/pickUp" ,methods=['GET','POST'])
def PickStudent():
    selected_student_ids = request.form.getlist('selected_students[]')
    #selected_student_name = request.form.getlist('selected_studentsNames[]')
    lec_id = request.form['lec_id']
    #student_id = request.form['student_id']
    #name = request.form['name']
    #gender = request.form['gender']
    #email = request.form['email']
    #level = request.form['level']
    #programme = request.form['programme']
    #cohort = request.files['cohort']
    

    update_sql = "UPDATE student SET supervisor=%s WHERE studentId=%s"
    cursor = db_conn.cursor()    

    try:
        # Check if the employee exists
        for student_id in selected_student_ids:
            update_sql = "UPDATE student SET supervisor=%s WHERE studentId=%s"
            cursor = db_conn.cursor()    
            cursor.execute(update_sql, (lec_id,student_id))
            db_conn.commit()                    

    finally:
        cursor.close()
    
    return render_template('PickedUpOutput.html', student_list=selected_student_ids)

@app.route("/drop" ,methods=['GET','POST'])
def DropStudent():
    selected_student_ids = request.form.getlist('selected_students[]')
    selected_student_name = request.form.getlist('selected_students[]')
    #student_id = request.form['student_id']
    #name = request.form['name']
    #gender = request.form['gender']
    #email = request.form['email']
    #level = request.form['level']
    #programme = request.form['programme']
    #cohort = request.files['cohort']
    
    update_sql = "UPDATE student SET supervisor='' WHERE studentId=%s"
    cursor = db_conn.cursor()    
    try:       
        for student_id in selected_student_ids:
            update_sql = "UPDATE student SET supervisor = NULL WHERE studentId=%s"
            cursor = db_conn.cursor()    
            cursor.execute(update_sql, (student_id))
            db_conn.commit()                    

    finally:
        cursor.close()
    
    return render_template('DropOutput.html', student_list=selected_student_name)

@app.route("/filterStudent" ,methods=['GET','POST'])
def FilterStudent():
    
    level= request.form['search-level']
    programme=request.form['search-programme']
    cohort=request.form['search-cohort']

    select_sql = "SELECT * FROM student WHERE supervisor IS NULL"
    cursor = db_conn.cursor()

    if level !='All':
          select_sql += f" AND level LIKE '%{level}%'"
    if programme:
          select_sql += f" AND programme LIKE '%{programme}%'"
    if level:
          select_sql += f" AND cohort LIKE '%{cohort}%'"

    try:
        cursor.execute(select_sql)
        students = cursor.fetchall()  # Fetch all students



        stu = []
        student_list = []

        for student in students:
            student_id = student[0]
            name = student[1]
            gender = student[4]
            email = student[6]
            level = student[7]
            programme = student[8]
            cohort = student[10]

            # Fetch the S3 image URL based on student_id
            stu_image_file_name_in_s3 = "stu-id-" + str(student_id) + "_image_file"
            s3 = boto3.client('s3')
            bucket_name = custombucket

            try:
                response = s3.generate_presigned_url('get_object',
                                                     Params={'Bucket': bucket_name,
                                                             'Key': stu_image_file_name_in_s3},
                                                     ExpiresIn=1000)  # Adjust the expiration time as needed

                # Create a dictionary for each student with their details and image URL
                student_data = {
                    "student_id": student_id,
                    "name": name,
                    "gender": gender,
                    "email": email,
                    "level": level,
                    "programme": programme,
                    "cohort": cohort,
                }

                # Append the student's dictionary to the student_list
                student_list.append(student_data)
                

            except Exception as e:
                return str(e)       
         
        return render_template('PickUpStudent.html', student_list=student_list)

    except Exception as e:
        return str(e)

    finally:
        cursor.close()

@app.route("/filterPickedStudent" ,methods=['GET','POST'])
def FilterPickedStudent():
    

    level= request.form['search-level']
    programme=request.form['search-programme']
    cohort=request.form['search-cohort']
    id=request.form['lec_id']

    select_sql = f"SELECT * FROM student WHERE supervisor = '{id}'"
    cursor = db_conn.cursor()

    if level != 'All':
          select_sql += f" AND level LIKE '%{level}%'"
    if programme:
          select_sql += f" AND programme LIKE '%{programme}%'"
    if level:
          select_sql += f" AND cohort LIKE '%{cohort}%'"

    try:
        cursor.execute(select_sql)
        students = cursor.fetchall()  # Fetch all students


        stu = []
        student_list = []

        for student in students:
            student_id = student[0]
            name = student[1]
            gender = student[4]
            email = student[6]
            level = student[7]
            programme = student[8]
            cohort = student[10]

            # Fetch the S3 image URL based on student_id
            stu_image_file_name_in_s3 = "stu-id-" + str(student_id) + "_image_file"
            s3 = boto3.client('s3')
            bucket_name = custombucket

            try:
                response = s3.generate_presigned_url('get_object',
                                                     Params={'Bucket': bucket_name,
                                                             'Key': stu_image_file_name_in_s3},
                                                     ExpiresIn=1000)  # Adjust the expiration time as needed

                # Create a dictionary for each student with their details and image URL
                student_data = {
                    "student_id": student_id,
                    "name": name,
                    "gender": gender,
                    "email": email,
                    "level": level,
                    "programme": programme,
                    "cohort": cohort,
                }

                # Append the student's dictionary to the student_list
                student_list.append(student_data)
                

            except Exception as e:
                return str(e)       
         
        return render_template('DropStudent.html', student_list=student_list)

    except Exception as e:
        return str(e)

    finally:
        cursor.close()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)

