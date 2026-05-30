#!/usr/bin/env python3
"""
Script to promote a user to admin role
Usage: python scripts/make_admin.py <username_or_email>
"""

import sys
from app.database import get_db

def make_admin(identifier):
    """Make a user admin by username or email"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Try to find by email first, then by username
        cursor.execute("SELECT id, username, email, role FROM users WHERE email = ? OR username = ?", 
                      (identifier, identifier))
        user = cursor.fetchone()
        
        if not user:
            print(f"❌ User '{identifier}' not found")
            print("\nAvailable users:")
            cursor.execute("SELECT id, username, email, role FROM users ORDER BY id DESC")
            for row in cursor.fetchall():
                print(f"  ID: {row[0]}, Username: {row[1]}, Email: {row[2]}, Role: {row[3]}")
            return False
        
        user_id, username, email, current_role = user
        
        if current_role == "admin":
            print(f"⚠️  User '{username}' ({email}) is already an admin")
            return True
        
        # Update role to admin
        cursor.execute("UPDATE users SET role = 'admin' WHERE id = ?", (user_id,))
        conn.commit()
        
        print(f"✅ User '{username}' ({email}) has been promoted to admin!")
        return True

def list_users():
    """List all users"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, email, role FROM users ORDER BY id DESC")
        users = cursor.fetchall()
        
        if not users:
            print("No users found in database")
            return
        
        print("\n" + "="*70)
        print(f"{'ID':<5} {'Username':<20} {'Email':<30} {'Role':<10}")
        print("="*70)
        for row in users:
            user_id, username, email, role = row
            print(f"{user_id:<5} {username:<20} {email:<30} {role:<10}")
        print("="*70 + "\n")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        identifier = sys.argv[1]
        make_admin(identifier)
    else:
        print("Usage: python make_admin.py <username_or_email>")
        print("\nExample: python make_admin.py john@example.com")
        print("Example: python make_admin.py john_doe\n")
        list_users()
