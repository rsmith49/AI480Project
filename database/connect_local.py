import mysql.connector
import os.path
import json

default_config = {'user': 'root',
    'password': '',
    'host':'0.0.0.0',
    'port': 8889,
    'database': 'MLBDaily'
}

AWS_CFG_FILE = "aws_db_connection.txt"

class Connection:

    def __init__(self):
        self.cnx = None
        self.cursor = None

    def close(self):
        self.cursor.close()
        self.cnx.close()

    def connect(self):
        #Check for our local MySQL config file; if it exists, read the config object from there.
        #otherwise, use the default_config object.
        if (os.path.isfile(AWS_CFG_FILE)):
            cfg_file = open(AWS_CFG_FILE, 'r')
            aws_config = json.load(cfg_file)
            print ("found AWS config object in " + AWS_CFG_FILE)
            self.cnx = mysql.connector.connect(**aws_config)
        else:
            self.cnx = mysql.connector.connect(**default_config)

        self.cursor = self.cnx.cursor()

    def query(self, query):
        res = []
        try:
            self.cursor.execute(query)
            for data in self.cursor:
                res.append(data)
        except mysql.connector.ProgrammingError as err:
            print(err)
            print(query)
            res = False

        return res

    def execute(self, query):
        try:
            self.cursor.execute(query)
            self.cursor.commit()
        except mysql.connector.ProgrammingError as err:
            print(err)
            return False

        return True

if __name__ == '__main__':
    conn = Connection()
    conn.connect()
    count_result = conn.query("SELECT COUNT(*) FROM active_players")
    print(count_result)