#!/usr/bin/env python3
"""
MQTT to PostgreSQL bridge using current best practices.

Key improvements:
- Uses MQTTv5 as default with MQTTv3 fallback
- Implements safe UPSERT to prevent duplicates
- Proper connection management and error handling
- Enhanced logging instead of print statements
"""

import logging
import paho.mqtt.client as mqtt
import psycopg2
import psycopg2.extras
import json
import time
import hashlib
import os
from typing import Dict, Any, Optional

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("mqtt-to-psql")

# Configuration - consider moving to environment variables in production
DB_CONFIG = {
    "dbname": os.getenv("DB_NAME", "mqtt_db"),
    "user": os.getenv("DB_USER", "emqx"),
    "password": os.getenv("DB_PASSWORD", "emqx"),
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
    "connect_timeout": 5,
    "options": "-c statement_timeout=5000"
}

MQTT_CONFIG = {
    "host": os.getenv("MQTT_HOST", "localhost"),
    "port": int(os.getenv("MQTT_PORT", "1883")),
    "client_id": os.getenv("MQTT_CLIENT_ID", "postgres-sink"),
    "keepalive": 60,
    "max_inflight": 100,
    "mqtt_versions": [mqtt.MQTTv5, mqtt.MQTTv311]  # Try v5 first, then v3
}

class DatabaseConnection:
    """Context manager for safe database connections with proper cleanup."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.conn = None
        self.cur = None
        
    def __enter__(self):
        try:
            self.conn = psycopg2.connect(**self.config)
            self.conn.set_session(autocommit=False)
            self.cur = self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            return self
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.cur:
            self.cur.close()
        if self.conn:
            if exc_type is None:
                self.conn.commit()
            else:
                self.conn.rollback()
            self.conn.close()

def init_database():
    """Initialize database schema with appropriate constraints for UPSERT."""
    with DatabaseConnection(DB_CONFIG) as db:
        # Create table with proper indexing and constraints
        db.cur.execute("""
            CREATE TABLE IF NOT EXISTS mqtt_messages (
                id SERIAL PRIMARY KEY,
                topic TEXT NOT NULL,
                payload JSONB,
                qos INTEGER NOT NULL,
                retain BOOLEAN NOT NULL,
                arrived_at TIMESTAMPTZ DEFAULT NOW(),
                message_hash TEXT NOT NULL UNIQUE
            )
        """)
        
        # Create index for faster topic queries
        db.cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_mqtt_messages_topic ON mqtt_messages(topic)
        """)
        
        logger.info("Database schema initialized")

def generate_message_hash(topic: str, payload: Any) -> str:
    """Generate a unique hash for deduplication."""
    payload_str = json.dumps(payload, sort_keys=True) if isinstance(payload, dict) else str(payload)
    hash_input = f"{topic}|{payload_str}"
    return hashlib.sha256(hash_input.encode()).hexdigest()

def is_valid_message(topic: str) -> bool:
    """Skip system topics which cause massive unnecessary writes."""
    if topic.startswith("$SYS/"):
        return False
    return True

def on_connect(client: mqtt.Client, userdata: Any, flags: Dict, reason_code: Any, properties: Optional[Any] = None) -> None:
    """
    Connection callback handler for MQTT.
    Uses the MQTTv5 signature with fallback capabilities for MQTTv3.
    """
    logger.info(f"Connected with result code {reason_code}")
    
    # Subscribe using MQTTv5 subscription options for better control
    try:
        # For MQTTv5 we can use more advanced subscribing
        if hasattr(mqtt, 'SubscribeOptions'):
            opts = mqtt.SubscribeOptions(qos=1)
            client.subscribe([("#", opts)])
        else:
            # Fallback for MQTTv3
            client.subscribe("#", qos=1)
        logger.info("Subscribed to all topics with QoS 1")
    except Exception as e:
        logger.error(f"Subscription failed: {e}")

def on_message(client: mqtt.Client, userdata: Any, msg: mqtt.MqttMessage) -> None:
    """Process incoming MQTT messages and store in PostgreSQL."""
    # Skip system topics (critical for performance)
    if not is_valid_message(msg.topic):
        return
    
    # Parse payload - try JSON first, fallback to string
    try:
        payload = json.loads(msg.payload.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError):
        payload = {"value": msg.payload.decode('utf-8', 'replace')}
    
    # Generate hash for deduplication
    message_hash = generate_message_hash(msg.topic, payload)
    
    # Database insertion with UPSERT
    with DatabaseConnection(DB_CONFIG) as db:
        try:
            # Using UPSERT to prevent duplicates based on message_hash
            db.cur.execute("""
                INSERT INTO mqtt_messages (topic, payload, qos, retain, message_hash)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (message_hash)
                DO UPDATE SET 
                    arrived_at = EXCLUDED.arrived_at,
                    qos = EXCLUDED.qos,
                    retain = EXCLUDED.retain
                RETURNING id
            """, (
                msg.topic,
                json.dumps(payload),
                msg.qos,
                msg.retain,
                message_hash
            ))
            
            result = db.cur.fetchone()
            if result:
                logger.debug(f"Message processed (ID: {result['id']})")
        except Exception as e:
            logger.error(f"Database operation failed: {e}")
            raise  # Will trigger rollback in the context manager

def create_mqtt_client() -> mqtt.Client:
    """Create and configure an MQTT client with proper protocol versioning."""
    client = None
    
    for version in MQTT_CONFIG["mqtt_versions"]:
        try:
            logger.info(f"Trying to connect with MQTT version: {'v5' if version == mqtt.MQTTv5 else 'v3'}")
            client = mqtt.Client(
                client_id=MQTT_CONFIG["client_id"],
                protocol=version,
                clean_session=False,
                reconnect_on_failure=True
            )
            
            # Configure network settings
            client.max_inflight_messages_set(MQTT_CONFIG["max_inflight"])
            client.connect(
                MQTT_CONFIG["host"],
                MQTT_CONFIG["port"],
                MQTT_CONFIG["keepalive"]
            )
            return client
        except Exception as e:
            logger.warning(f"MQTT {version} connection failed: {e}")
    
    if not client:
        raise ConnectionError("Failed to establish MQTT connection with any supported protocol version")
    
    return client

def main():
    """Main application entry point with reconnection logic."""
    init_database()
    
    while True:
        try:
            client = create_mqtt_client()
            client.on_connect = on_connect
            client.on_message = on_message
            
            # Start network loop in separate thread
            client.loop_start()
            logger.info("MQTT client started successfully")
            
            # Keep main thread alive
            while True:
                time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("Shutting down by user request...")
            break
        except Exception as e:
            logger.error(f"Unexpected error: {e}. Reconnecting in 5 seconds...")
            time.sleep(5)

if __name__ == "__main__":
    main()