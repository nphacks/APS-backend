from datetime import datetime
from typing import List
from db_conn.tidb.db import get_connection
from models.tidb.user_project import UserProjectCreate, UserProjectUpdate, UserProjectResponse
from .update_project import check_permission

def add_user_to_project(project_id: str, requesting_user_id: str, user_data: UserProjectCreate) -> UserProjectResponse:
    """Add a user to a project (requires owner or admin role)"""
    
    # Check permissions
    if not check_permission(project_id, requesting_user_id, ['owner', 'admin']):
        raise PermissionError("Only owners and admins can add users to projects")
    
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        added_at = datetime.utcnow()
        
        # Check if user exists
        cursor.execute("SELECT id, username, email FROM users WHERE id = %s", (user_data.user_id,))
        user = cursor.fetchone()
        if not user:
            raise ValueError("User not found")
        
        # Check if user is already in project
        cursor.execute(
            "SELECT role FROM user_projects WHERE user_id = %s AND project_id = %s",
            (user_data.user_id, project_id)
        )
        if cursor.fetchone():
            raise ValueError("User is already in this project")
        
        # Add user to project
        cursor.execute(
            "INSERT INTO user_projects (user_id, project_id, role, added_at) VALUES (%s, %s, %s, %s)",
            (user_data.user_id, project_id, user_data.role, added_at)
        )
        
        conn.commit()
        
        return UserProjectResponse(
            user_id=user['id'],
            username=user['username'],
            email=user['email'],
            role=user_data.role,
            added_at=added_at
        )
        
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()
        conn.close()

def get_project_users(project_id: str, requesting_user_id: str) -> List[UserProjectResponse]:
    """Get all users in a project"""
    
    # Check if requesting user has access to this project
    if not check_permission(project_id, requesting_user_id, ['owner', 'admin', 'editor', 'commentator', 'viewer']):
        raise PermissionError("You don't have access to this project")
    
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        query = """
            SELECT u.id as user_id, u.username, u.email, up.role, up.added_at
            FROM user_projects up
            INNER JOIN users u ON up.user_id = u.id
            WHERE up.project_id = %s
            ORDER BY up.added_at ASC
        """
        cursor.execute(query, (project_id,))
        users = cursor.fetchall()
        
        return [UserProjectResponse(**user) for user in users]
        
    finally:
        cursor.close()
        conn.close()

def update_user_role(project_id: str, requesting_user_id: str, target_user_id: str, role_data: UserProjectUpdate) -> UserProjectResponse:
    """Update a user's role in a project (requires owner or admin role)"""
    
    # Check permissions
    if not check_permission(project_id, requesting_user_id, ['owner', 'admin']):
        raise PermissionError("Only owners and admins can update user roles")
    
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Check if target user is in project
        cursor.execute(
            "SELECT role FROM user_projects WHERE user_id = %s AND project_id = %s",
            (target_user_id, project_id)
        )
        if not cursor.fetchone():
            raise ValueError("User is not in this project")
        
        # Prevent changing owner role (only one owner allowed)
        cursor.execute(
            "SELECT role FROM user_projects WHERE user_id = %s AND project_id = %s",
            (target_user_id, project_id)
        )
        current_role = cursor.fetchone()['role']
        if current_role == 'owner':
            raise PermissionError("Cannot change owner role")
        
        # Update role
        cursor.execute(
            "UPDATE user_projects SET role = %s WHERE user_id = %s AND project_id = %s",
            (role_data.role, target_user_id, project_id)
        )
        
        # Get user info
        cursor.execute(
            """
            SELECT u.id as user_id, u.username, u.email, up.role, up.added_at
            FROM user_projects up
            INNER JOIN users u ON up.user_id = u.id
            WHERE up.user_id = %s AND up.project_id = %s
            """,
            (target_user_id, project_id)
        )
        user = cursor.fetchone()
        
        conn.commit()
        
        return UserProjectResponse(**user)
        
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()
        conn.close()

def remove_user_from_project(project_id: str, requesting_user_id: str, target_user_id: str) -> bool:
    """Remove a user from a project (requires owner or admin role)"""
    
    # Check permissions
    if not check_permission(project_id, requesting_user_id, ['owner', 'admin']):
        raise PermissionError("Only owners and admins can remove users from projects")
    
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Check if target user is owner
        cursor.execute(
            "SELECT role FROM user_projects WHERE user_id = %s AND project_id = %s",
            (target_user_id, project_id)
        )
        result = cursor.fetchone()
        if result and result['role'] == 'owner':
            raise PermissionError("Cannot remove project owner")
        
        # Remove user
        cursor.execute(
            "DELETE FROM user_projects WHERE user_id = %s AND project_id = %s",
            (target_user_id, project_id)
        )
        
        conn.commit()
        
        return cursor.rowcount > 0
        
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()
        conn.close()
