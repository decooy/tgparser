import psycopg2
import psycopg2.extras


class database:
    def __init__(self):
        self.postgre_connection = psycopg2.connect(dbname='postgres', user='postgres', password='1q2w3e123qwe',
                                                   host='localhost', port='5432')
        self.cursor = self.postgre_connection.cursor()
        self.cursor.execute("""CREATE TABLE IF NOT EXISTS parsed_chats(
                   id TEXT,
                   title TEXT,
                   access_hash TEXT,
                   username TEXT,
                   participants_count INT
                   );
                """)
        self.postgre_connection.commit()

        self.cursor.execute("""CREATE TABLE IF NOT EXISTS users(
                           id TEXT,
                           access_hash TEXT,
                           first_name TEXT,
                           last_name TEXT,
                           username TEXT,
                           phone TEXT,
                           chat TEXT
                           );
                        """)
        self.postgre_connection.commit()

        self.cursor.execute("""CREATE TABLE IF NOT EXISTS account(
                                   first_name TEXT,
                                   number TEXT
                                   );
                                """)
        self.postgre_connection.commit()

    def add_parsed_chat(self, id, title, access_hash, username, participants_count):
        if participants_count is None:
            participants_count = -1
        self.cursor.execute(f"""INSERT INTO parsed_chats(id, title, access_hash, username, participants_count) 
        VALUES('{id}', '{title}', '{access_hash}', '{username}', '{participants_count}')""")
        self.postgre_connection.commit()

    def get_parsed_chats(self):
        self.cursor.execute("""SELECT * FROM parsed_chats""")
        return self.cursor.fetchall()

    def delete_parsed_chat(self, id):
        self.cursor.execute(f"""DELETE FROM parsed_chats WHERE id='{id}'""")
        self.postgre_connection.commit()

    def get_channel_by_id(self, id):
        self.cursor.execute(f"""SELECT * FROM parsed_chats WHERE id='{id}'""")
        return self.cursor.fetchall()[0]

    def add_parsed_user(self, user, chat):
        self.cursor.execute(f"""INSERT INTO users(id, access_hash, first_name, last_name, username, phone, chat) VALUES(
        '{user.id}', '{user.access_hash}', '{str(user.first_name).replace("'", "")}',
         '{str(user.last_name).replace("'", "")}', '{user.username}', '{user.phone}', '{chat[0]}')""")
        self.postgre_connection.commit()

    def get_accounts_count(self):
        self.cursor.execute(F"""SELECT count(*) FROM users;""")
        return self.cursor.fetchone()[0]

    def get_chats_count(self):
        self.cursor.execute(F"""SELECT count(*) FROM parsed_chats;""")
        return self.cursor.fetchone()[0]

    def get_all_accounts(self):
        self.cursor.execute(f"""SELECT * FROM users""")
        return self.cursor.fetchall()

    def delete_user(self, id):
        self.cursor.execute(f"""DELETE FROM users WHERE id='{id}'""")
        self.postgre_connection.commit()

    def clear_base(self):
        self.cursor.execute(f"""DELETE FROM users""")
        self.postgre_connection.commit()
        self.cursor.execute(f"""DELETE FROM parsed_chats""")
        self.postgre_connection.commit()
