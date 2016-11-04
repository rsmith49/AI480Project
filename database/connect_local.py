import mysql.connector

config = {'user': 'root',
    'password': '',
    'host':'0.0.0.0',
    'port': 8889,
    'database': 'MLBDaily'
}

class Connection:

    def __init__(self):
        self.cnx = None
        self.cursor = None

    def close(self):
        self.cursor.close()
        self.cnx.close()

    def connect(self):
        self.cnx = mysql.connector.connect(**config)
        self.cursor = self.cnx.cursor()

    def query(self, query):
        res = []
        try:
            self.cursor.execute(query)
            for data in self.cursor:
                res.append(data)
        except mysql.connector.ProgrammingError as err:
            print(err)
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