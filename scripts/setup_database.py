"""
Database setup script for Multi-Agent Customer Service System
Creates the SQLite database with Customers and Tickets tables
"""

import sqlite3
import os
from datetime import datetime

import os
# Database path in project root
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
DB_PATH = os.path.join(PROJECT_ROOT, "customer_service.db")

def setup_database():
    """Initialize the database with required tables"""
    # Remove existing database if it exists (for fresh start)
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create Customers table
    cursor.execute("""
        CREATE TABLE customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create Tickets table
    cursor.execute("""
        CREATE TABLE tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            issue TEXT NOT NULL,
            status TEXT DEFAULT 'open',
            priority TEXT DEFAULT 'medium',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        )
    """)
    
    # Insert sample data
    sample_customers = [
        (1, "Alice Johnson", "alice@example.com", "555-0101", "active"),
        (2, "Bob Smith", "bob@example.com", "555-0102", "active"),
        (3, "Charlie Brown", "charlie@example.com", "555-0103", "active"),
        (4, "Diana Prince", "diana@example.com", "555-0104", "active"),
        (5, "Eve Davis", "eve@example.com", "555-0105", "active"),
        (12345, "Premium Customer", "premium@example.com", "555-9999", "active"),
    ]
    
    for customer in sample_customers:
        cursor.execute("""
            INSERT INTO customers (id, name, email, phone, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (*customer, datetime.now(), datetime.now()))
    
    # Insert sample tickets
    sample_tickets = [
        (1, "Account access issue", "open", "medium"),
        (1, "Password reset", "resolved", "low"),
        (2, "Billing inquiry", "open", "high"),
        (12345, "Premium account upgrade", "in_progress", "high"),
        (3, "Product inquiry", "resolved", "low"),
    ]
    
    for ticket in sample_tickets:
        cursor.execute("""
            INSERT INTO tickets (customer_id, issue, status, priority, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (*ticket, datetime.now()))
    
    conn.commit()
    conn.close()
    print(f"Database '{DB_PATH}' created successfully with sample data!")

def reset_database():
    """Reset the database to initial state"""
    setup_database()
    print("Database reset complete!")

if __name__ == "__main__":
    setup_database()

