import paho.mqtt.client as mqtt
import psycopg2
import json
import time

def is_valid_message(topic):
    # Skip system topics which cause massive unnecessary writes
    if topic.startswith("$SYS/"):
        return False
    return True

# Connect to PostgreSQL with connection pooling
conn = psycopg2.connect(
    "dbname=mqtt_db user=emqx password=emqx host=localhost",
    connect_timeout=5,
    options="-c statement_timeout=5000"
)
conn.set_session(autocommit=False)

# Create table if needed
cur = conn.cursor()
cur.execute("""
CREATE TABLE IF NOT EXISTS mqtt_messages (
    id SERIAL PRIMARY KEY,
    topic TEXT NOT NULL,
    payload JSONB,
    qos INTEGER,
    retain BOOLEAN,
    arrived_at TIMESTAMPTZ DEFAULT NOW()
)
""")
conn.commit()

def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))
    client.subscribe("#", qos=1)  # Use QoS 1 for reliability

def on_message(client, userdata, msg):
    # Skip system topics (critical for performance)
    if not is_valid_message(msg.topic):
        return
        
    try:
        # Try to parse as JSON, fallback to string
        try:
            payload = json.loads(msg.payload.decode('utf-8'))
        except:
            payload = {"value": msg.payload.decode('utf-8', 'ignore')}
        
        # Batch-friendly insertion (protect against overload)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO mqtt_messages (topic, payload, qos, retain) VALUES (%s, %s, %s, %s)",
            (msg.topic, json.dumps(payload), msg.qos, msg.retain)
        )
        conn.commit()
    except Exception as e:
        print(f"Database error: {e}")
        conn.rollback()
        # Don't ack the message so it can be redelivered

# Configure client with proper keepalive and clean session
client = mqtt.Client(client_id="postgres-sink", clean_session=False)
client.max_inflight_messages_set(100)  # Control message flow
client.on_connect = on_connect
client.on_message = on_message

# Reconnection logic
while True:
    try:
        client.connect("localhost", 1883, 60)
        client.loop_forever()
    except Exception as e:
        print(f"Connection failed: {e}. Retrying in 5 seconds...")
        time.sleep(5)