
import sqlite3

def get_connection():
    conn = sqlite3.connect("crm.db")
    cursor = conn.cursor()
    return (conn, cursor) 

