import sqlite3 as sql
import hashlib
from random import randint
from cryptography.fernet import Fernet

from MyLibs import configure

database = configure.database
password = configure.password


def encrypt(message, key):
    return (Fernet(key).encrypt(message.encode())).decode()

def decrypt(token, key):
    try:
        return (Fernet(key).decrypt(token.encode())).decode()
    except:
        return "None"

def create_new_room():
    con = sql.connect(database)
    cur = con.cursor()
    cur.execute("INSERT INTO rooms DEFAULT VALUES")
    con.commit()
    cur.execute("SELECT room_id FROM rooms ORDER BY room_id DESC LIMIT 1")
    room_id = str(cur.fetchall()[0][0])
    con.close()
    return( encrypt(room_id, password) )

def create_new_user(username, room_id_crypt):
    con = sql.connect(database)
    cur = con.cursor()
    room_id =  decrypt(room_id_crypt, password)
    cur.execute("INSERT INTO users(user_name, room_id) values('" + username + "', '" + room_id + "')")
    con.commit()
    cur.execute("SELECT user_id FROM users ORDER BY user_id DESC LIMIT 1")
    user_id = str(cur.fetchall()[0][0])
    cur.execute("SELECT member_id FROM rooms WHERE room_id='" + room_id + "'")
    member_id = cur.fetchall()[0]
    if member_id[0] != "-1":
        member_id = str(member_id[0]) + "," + str(user_id)
    else:
        member_id = user_id
    cur.execute("UPDATE rooms SET member_id='" + member_id + "' WHERE room_id='" + room_id + "'")
    con.commit()
    cur.execute("SELECT activeuser_id FROM rooms WHERE room_id='" + room_id + "'")
    activeuser_id = cur.fetchall()[0][0]
    if activeuser_id == -1 :
         cur.execute("UPDATE rooms SET activeuser_id='" + user_id + "' WHERE room_id='" + room_id + "'")
         con.commit()
    con.close()
    return( user_id , room_id)
    
def check_session(user_id, room_id):
    con = sql.connect(database)
    cur = con.cursor()
    cur.execute("SELECT member_id FROM rooms WHERE room_id='" + room_id + "'")
    member_id = cur.fetchall()
    con.close()
    if member_id == []:
        return(False)
    else:
        member_id = member_id[0][0]
        members = member_id.split(",")
        if user_id in members:
            return(True)
        else:
            return(False)

def check_room_exists(room_id_crypt):
    try:
        room_id = decrypt(room_id_crypt, password)
    except:
            return False
    con = sql.connect(database)
    cur = con.cursor()
    cur.execute("SELECT room_id FROM rooms WHERE room_id='" + room_id + "'")

    test = cur.fetchall()
    con.close()
    if test == []:
        return False
    else:
        test = test[0][0]
        return(test != None)

def get_members(room_id):
    con = sql.connect(database)
    cur = con.cursor()
    cur.execute("SELECT member_id FROM rooms WHERE room_id='" + room_id + "'")
    member_id = cur.fetchall()[0][0]
    cur.execute("SELECT user_name, user_id FROM users WHERE user_id IN (" + str(member_id) + ")")
    members = cur.fetchall()
    con.close()
    return(members)# [(username, userid)]

def get_user_by_id(user_id):
    con = sql.connect(database)
    cur = con.cursor()
    cur.execute("SELECT user_name FROM users WHERE user_id='" + str(user_id) + "'")
    user_name = cur.fetchall()
    if user_name == []:
        user_name = (None, None)
    else:
        user_name = user_name[0][0]
        
    con.close()
    return(user_name)# username

def get_active_user(room_id):
    con = sql.connect(database)
    cur = con.cursor()
    cur.execute("SELECT activeuser_id FROM rooms WHERE room_id='" + room_id + "'")
    activeuser_id = cur.fetchall()
    if activeuser_id:
        activeuser_id = activeuser_id[0][0]
        return((activeuser_id, get_user_by_id(activeuser_id))) # (userid, username)
    else:
        return((0, False))

def check_active_player(user_id, room_id):
    return int(get_active_user(room_id)[0]) == int(user_id)

def change_active_user(user_id, room_id):
    members = get_members(room_id)
    activeuser_id = int(user_id)
    for i in range(len(members)):

        if members[i][1] == activeuser_id:

            if len(members) == 1:
                break
            elif len(members) == i + 1:
                activeuser_id = members[0][1]
                break
            else:

                activeuser_id = members[i+1][1] 
                break

    con = sql.connect(database)
    cur = con.cursor() 
    cur.execute("UPDATE rooms SET activeuser_id='" + str(activeuser_id) + "' WHERE room_id='" + room_id + "'")
    con.commit()
    con.close()
    return((activeuser_id, get_user_by_id(activeuser_id)))


def get_actual_question(room_id):
    con = sql.connect(database)
    cur = con.cursor() 
    cur.execute("SELECT actual_question FROM rooms WHERE room_id='" + str(room_id) + "'")
    question_id = cur.fetchall()[0][0]
    cur.execute("SELECT question FROM questions WHERE question_id='" + str(question_id) + "'")
    question = cur.fetchall()[0][0]
    con.close()
    return(question)

def get_new_question(room_id):
    con = sql.connect(database)
    cur = con.cursor() 
    cur.execute("SELECT passed_questions FROM rooms WHERE room_id='" + str(room_id) + "'")
    passed_questions = cur.fetchall()[0][0]
    cur.execute("SELECT question_id, question FROM questions WHERE question_id NOT IN (" + str(passed_questions) + ")")
    possible_questions = cur.fetchall()
    if not len(possible_questions) == 0:
        question_pos = randint(0, len(possible_questions) - 1)
        question = possible_questions[question_pos]
        cur.execute("UPDATE rooms SET passed_questions='" + str(passed_questions) + "," + str(question[0]) + "' WHERE room_id='" + room_id + "'")
        con.commit()
        cur.execute("UPDATE rooms SET actual_question='" + str(question[0]) + "' WHERE room_id='" + str(room_id) + "'")
        con.commit()
        question = question[1]
    else:
        cur.execute("UPDATE rooms SET passed_questions='1' WHERE room_id='" + str(room_id) + "'")
        con.commit()
        cur.execute("UPDATE rooms SET actual_question='1' WHERE room_id='" + str(room_id) + "'")
        con.commit()
        question = get_actual_question(room_id)
    
    con.close()
    return(str(question))

def update_active(user_id, room_id, only_update=False):
    con = sql.connect(database)
    cur = con.cursor() 
    cur.execute("UPDATE users SET timestamp = CURRENT_TIMESTAMP WHERE user_id = " + str(user_id))#
    con.commit()
    con.close()
    if only_update == False:
        remove_timeouted_user(user_id, room_id)
    return("True")

def check_user_exists(user_id):
    con = sql.connect(database)
    cur = con.cursor()
    cur.execute("SELECT user_id FROM users WHERE user_id='" + str(user_id) + "'")
    user_id = cur.fetchall()
    if user_id == [] or user_id == False or user_id == [()]:
        return(False)
    else:
        return(True)
    
def remove_timeouted_user(user_id, room_id):
    con = sql.connect(database)
    cur = con.cursor()
    cur.execute("DELETE FROM users WHERE timestamp <= strftime('%Y-%m-%d %H:%M:%S','now','-22 seconds')")
    con.commit()
    
    
    
    cur.execute("SELECT member_id FROM rooms WHERE room_id='" + str(room_id) + "'")
    member_ids = cur.fetchall()[0][0]
    active_member_ids = []
    for member_id in member_ids.split(','):
        if check_user_exists(member_id):
            active_member_ids.append(member_id)
    
    active_member_str = ""
    for member in active_member_ids:
        active_member_str += str(member) + ","
        
    active_member_str = active_member_str[:-1]
    
    cur.execute("UPDATE rooms SET member_id='" + str(active_member_str) + "' WHERE room_id='" + str(room_id) + "'")
    con.commit()
    

    active_user = get_active_user(room_id)[0]
    if not check_user_exists(active_user):
        print("change active")
        cur.execute("UPDATE rooms SET activeuser_id ='" + str(user_id) + "' WHERE room_id='" + str(room_id) + "'")
        con.commit()
    
    con.close()
        
    # delete empty room
    
