import psycopg2
from datetime import datetime


class DBLogger:
    def __init__(self):
        self.conn = psycopg2.connect(
            dbname="defaultdb",
            user="avnadmin",
            password="AVNS_Es-E-izeKfjJkDmNly7",
            host="pg-ff24d4c-ringo-6580.i.aivencloud.com",
            port=13103,
            sslmode="require"
        )
        self.conn.autocommit = True
        self.cur = self.conn.cursor()

        self._create_table()

    def _create_table(self):
        self.cur.execute("""
        CREATE TABLE IF NOT EXISTS public.simulation_logs (
            id SERIAL PRIMARY KEY,
            run_id TEXT,
            step INT,
            timestamp TIMESTAMP,
            vehicle_count INT,
            avg_congestion FLOAT
        );
        """)

    def log(self, run_id, step, vehicle_count, avg_congestion):
        self.cur.execute("""
        INSERT INTO public.simulation_logs (run_id, step, timestamp, vehicle_count, avg_congestion)
        VALUES (%s, %s, %s, %s, %s);
        """, (
            run_id,
            step,
            datetime.utcnow(),
            vehicle_count,
            avg_congestion
        ))

    def close(self):
        self.cur.close()
        self.conn.close()