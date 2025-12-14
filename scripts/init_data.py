import asyncio
import random
from sqlpilot.database.mysql import MySQLAdapter
from sqlpilot.core.config import settings

async def init_data():
    print(f"Connecting to database at {settings.shadow_database.mysql.host}:{settings.shadow_database.mysql.port}...")
    db = MySQLAdapter(settings.shadow_database.mysql)
    await db.connect()
    
    try:
        print("Creating tables...")
        # Create users
        await db.execute_query("DROP TABLE IF EXISTS users")
        await db.execute_query("""
            CREATE TABLE users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50),
                email VARCHAR(100),
                status VARCHAR(20) DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create orders
        await db.execute_query("DROP TABLE IF EXISTS orders")
        await db.execute_query("""
            CREATE TABLE orders (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT,
                amount DECIMAL(10, 2),
                status VARCHAR(20) DEFAULT 'completed',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_user_id (user_id)
            )
        """)
        
        print("Inserting data...")
        # Insert 1000 users
        users_batch = []
        for i in range(1, 1001):
            users_batch.append(f"('user{i}', 'user{i}@example.com', 'active')")
        
        # Split into chunks of 100 for insertion
        chunk_size = 100
        for i in range(0, len(users_batch), chunk_size):
            chunk = users_batch[i:i + chunk_size]
            await db.execute_query(f"INSERT INTO users (username, email, status) VALUES {','.join(chunk)}")
            
        # Insert 5000 orders
        orders_batch = []
        for i in range(1, 5001):
            uid = random.randint(1, 1000)
            amt = random.uniform(10.0, 500.0)
            orders_batch.append(f"({uid}, {amt:.2f})")
            
        for i in range(0, len(orders_batch), chunk_size):
            chunk = orders_batch[i:i + chunk_size]
            await db.execute_query(f"INSERT INTO orders (user_id, amount) VALUES {','.join(chunk)}")
        
        print(f"Initialized 1000 users and 5000 orders.")
        
    except Exception as e:
        print(f"Error initializing data: {e}")
    finally:
        await db.close()

if __name__ == "__main__":
    asyncio.run(init_data())
