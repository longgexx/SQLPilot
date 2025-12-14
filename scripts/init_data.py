import asyncio
import random
import time
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
                INDEX idx_user_id (user_id),
                INDEX idx_created_at (created_at) 
            )
        """)
        
        # NOTE: Added index on created_at to support the README optimization example
        
        print("Generating data...")
        
        # 1. Insert Users (10,000)
        USER_COUNT = 10000
        BATCH_SIZE = 2000
        print(f"Inserting {USER_COUNT} users...")
        
        users_batch = []
        for i in range(1, USER_COUNT + 1):
            users_batch.append(f"('user{i}', 'user{i}@example.com', 'active')")
            
            if len(users_batch) >= BATCH_SIZE:
                 await db.execute_query(f"INSERT INTO users (username, email, status) VALUES {','.join(users_batch)}")
                 users_batch = []
                 print(f"Inserted {i} users...")
                 
        if users_batch:
            await db.execute_query(f"INSERT INTO users (username, email, status) VALUES {','.join(users_batch)}")

        # 2. Insert Orders (1,000,000)
        ORDER_COUNT = 1000000
        BATCH_SIZE = 5000
        print(f"Inserting {ORDER_COUNT} orders...")
        
        orders_batch = []
        start_time = time.time()
        
        for i in range(1, ORDER_COUNT + 1):
            uid = random.randint(1, USER_COUNT)
            amt = round(random.uniform(10.0, 500.0), 2)
            # Generate random dates in 2023
            month = random.randint(1, 12)
            day = random.randint(1, 28)
            hour = random.randint(0, 23)
            ts = f"2023-{month:02d}-{day:02d} {hour:02d}:00:00"
            
            orders_batch.append(f"({uid}, {amt}, '{ts}')")
            
            if len(orders_batch) >= BATCH_SIZE:
                values = ",".join(orders_batch)
                await db.execute_query(f"INSERT INTO orders (user_id, amount, created_at) VALUES {values}")
                orders_batch = []
                
                if i % 100000 == 0:
                    elapsed = time.time() - start_time
                    rate = i / elapsed
                    print(f"Inserted {i} orders... ({rate:.0f} rows/sec)")

        if orders_batch:
            values = ",".join(orders_batch)
            await db.execute_query(f"INSERT INTO orders (user_id, amount, created_at) VALUES {values}")
        
        print(f"Successfully initialized {USER_COUNT} users and {ORDER_COUNT} orders.")
        
    except Exception as e:
        print(f"Error initializing data: {e}")
    finally:
        await db.close()

if __name__ == "__main__":
    asyncio.run(init_data())
