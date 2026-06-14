#!/usr/bin/env python
"""Admin user management script.

Usage:
    python manage_admins.py create <username> <password>
    python manage_admins.py list
    python manage_admins.py delete <username>
    python manage_admins.py set-password <username> <new_password>
"""
import sys
from app.db.base import SessionLocal
from app.models.models import Admin
from app.core.security import hash_password, verify_password


def create_admin(username: str, password: str):
    """Create a new admin user."""
    db = SessionLocal()
    try:
        existing = db.query(Admin).filter(Admin.username == username).first()
        if existing:
            print(f"❌ Admin '{username}' already exists")
            return False

        admin = Admin(
            username=username,
            password_hash=hash_password(password),
            is_active=True,
        )
        db.add(admin)
        db.commit()
        print(f"✅ Admin '{username}' created successfully")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def list_admins():
    """List all admin users."""
    db = SessionLocal()
    try:
        admins = db.query(Admin).all()
        if not admins:
            print("No admins found")
            return

        print("\n📋 Admin Users:")
        print("─" * 50)
        for admin in admins:
            status = "✓ Active" if admin.is_active else "✗ Inactive"
            print(f"  {admin.id:2d} | {admin.username:20s} | {status} | Created: {admin.created_at}")
        print("─" * 50)
    finally:
        db.close()


def delete_admin(username: str):
    """Delete an admin user."""
    db = SessionLocal()
    try:
        admin = db.query(Admin).filter(Admin.username == username).first()
        if not admin:
            print(f"❌ Admin '{username}' not found")
            return False

        db.delete(admin)
        db.commit()
        print(f"✅ Admin '{username}' deleted")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def set_password(username: str, new_password: str):
    """Change admin password."""
    db = SessionLocal()
    try:
        admin = db.query(Admin).filter(Admin.username == username).first()
        if not admin:
            print(f"❌ Admin '{username}' not found")
            return False

        admin.password_hash = hash_password(new_password)
        db.commit()
        print(f"✅ Password for '{username}' updated")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1]

    if command == "create" and len(sys.argv) == 4:
        create_admin(sys.argv[2], sys.argv[3])
    elif command == "list":
        list_admins()
    elif command == "delete" and len(sys.argv) == 3:
        delete_admin(sys.argv[2])
    elif command == "set-password" and len(sys.argv) == 4:
        set_password(sys.argv[2], sys.argv[3])
    else:
        print(__doc__)
        sys.exit(1)
