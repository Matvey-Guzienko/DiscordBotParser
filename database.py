import sqlite3


class Database:
    def __init__(self, database: str):
        self.db = sqlite3.connect(database)
        self.cur = self.db.cursor()

        self.cur.execute(
            """
            CREATE TABLE IF NOT EXISTS parse_channels (
                post_channel_id BIGINT NOT NULL,
                parse_channel_id BIGINT NOT NULL,
                UNIQUE(post_channel_id, parse_channel_id) ON CONFLICT REPLACE
            )
        """
        )
        self.db.commit()

        self.cur.execute(
            """
            CREATE TABLE IF NOT EXISTS parsed_messages (
                parsed_message_channel_id BIGINT NOT NULL,
                target_message_id BIGINT NOT NULL,
                parsed_message_id BIGINT NOT NULL,
                UNIQUE(target_message_id, parsed_message_id) ON CONFLICT REPLACE
            )
        """
        )
        self.db.commit()

    def close(self):
        self.db.close()

    def add_parse_channel(self, post_channel_id: int, parse_channel_id: int):
        self.cur.execute(
            "INSERT INTO parse_channels VALUES (?, ?)",
            (post_channel_id, parse_channel_id),
        )
        self.db.commit()

    def remove_parse_channel(self, post_channel_id: int, parse_channel_id: int):
        self.cur.execute(
            "DELETE FROM parse_channels WHERE post_channel_id = ? AND parse_channel_id = ?",
            (post_channel_id, parse_channel_id),
        )
        self.db.commit()

    def get_post_channel_ids(self, parse_channel_id: int) -> list[tuple[int]]:
        self.cur.execute(
            "SELECT post_channel_id FROM parse_channels WHERE parse_channel_id = ?",
            (parse_channel_id,),
        )
        return self.cur.fetchall()

    def drop_all_parse_channels(self):
        self.cur.execute("DELETE FROM parse_channels")
        self.db.commit()

    def get_all_parse_channels(self) -> list[tuple[int, int]]:
        self.cur.execute("SELECT * FROM parse_channels")
        return self.cur.fetchall()

    def add_parsed_message(
        self,
        parsed_message_channel_id: int,
        target_message_id: int,
        parsed_message_id: int,
    ):
        self.cur.execute(
            "INSERT INTO parsed_messages VALUES (?, ?, ?)",
            (parsed_message_channel_id, target_message_id, parsed_message_id),
        )
        self.db.commit()

    def get_parsed_messages(self, target_message_id: int) -> list[tuple[int]]:
        self.cur.execute(
            "SELECT parsed_message_channel_id, parsed_message_id FROM parsed_messages WHERE target_message_id = ?",
            (target_message_id,),
        )
        return self.cur.fetchall()
