"""
ClaimIQ — MySQL Database Setup Script
Run this ONCE to create the MySQL database before starting the server.
Usage: python scripts/setup_mysql.py
"""
import pymysql

DB_HOST = "localhost"
DB_PORT = 3306
DB_USER = "root"
DB_PASS = "root"
DB_NAME = "claimiq"

print("=" * 50)
print("  ClaimIQ — MySQL Database Setup")
print("=" * 50)

try:
    conn = pymysql.connect(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASS)
    cursor = conn.cursor()

    cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    print(f"  ✅ Database '{DB_NAME}' created (or already exists)")

    cursor.execute(f"SHOW DATABASES LIKE '{DB_NAME}'")
    result = cursor.fetchone()
    if result:
        print(f"  ✅ Verified: '{DB_NAME}' exists")
    else:
        print(f"  ❌ Failed to create database")

    cursor.close()
    conn.close()
    print("  ✅ MySQL setup complete!")
    print(f"\n  Connection URL: mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

except pymysql.err.OperationalError as e:
    print(f"\n  ❌ Cannot connect to MySQL: {e}")
    print("  \n  Make sure MySQL is running:")
    print("    • XAMPP: Start MySQL from XAMPP Control Panel")
    print("    • MySQL Server: net start mysql")
    print("    • WAMP: Start from system tray")

print("=" * 50)
