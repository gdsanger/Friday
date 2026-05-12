"""
Manual Test Setup for Global Teams Feature

This script creates test data for manual testing of ISSUE-20 Global Teams.
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from django.contrib.auth import get_user_model
from apps.teams.models import Team, TeamMembership
from apps.projects.models import Project, ProjectUserMembership, ProjectTeamMembership
from apps.tasks.models import Task

User = get_user_model()

print("Setting up test data for Global Teams manual testing...")

# Create test users
print("\n1. Creating test users...")
staff_user, _ = User.objects.get_or_create(
    username='admin',
    defaults={
        'email': 'admin@test.com',
        'is_staff': True,
        'is_superuser': True
    }
)
if _:
    staff_user.set_password('admin')
    staff_user.save()
    print("   ✓ Created admin user (username: admin, password: admin)")
else:
    print("   ✓ Admin user already exists")

dev_user, _ = User.objects.get_or_create(
    username='dev',
    defaults={'email': 'dev@test.com'}
)
if _:
    dev_user.set_password('dev')
    dev_user.save()
    print("   ✓ Created dev user (username: dev, password: dev)")
else:
    print("   ✓ Dev user already exists")

support_user, _ = User.objects.get_or_create(
    username='support',
    defaults={'email': 'support@test.com'}
)
if _:
    support_user.set_password('support')
    support_user.save()
    print("   ✓ Created support user (username: support, password: support)")
else:
    print("   ✓ Support user already exists")

# Create teams
print("\n2. Creating teams...")
dev_team, _ = Team.objects.get_or_create(
    slug='development',
    defaults={
        'name': 'Development',
        'description': 'Regular development team',
        'color': '#3b82f6',
        'icon': 'code-slash',
        'is_global': False
    }
)
print(f"   ✓ Development team ({'created' if _ else 'exists'}) - is_global=False")

it_support_team, _ = Team.objects.get_or_create(
    slug='it-support',
    defaults={
        'name': 'IT Support',
        'description': 'Global IT support team - has access to all projects',
        'color': '#ef4444',
        'icon': 'tools',
        'is_global': True
    }
)
print(f"   ✓ IT Support team ({'created' if _ else 'exists'}) - is_global=True")

rz_hosting_team, _ = Team.objects.get_or_create(
    slug='rz-hosting',
    defaults={
        'name': 'RZ/Hosting',
        'description': 'Global hosting team - involved in every project',
        'color': '#8b5cf6',
        'icon': 'server',
        'is_global': True
    }
)
print(f"   ✓ RZ/Hosting team ({'created' if _ else 'exists'}) - is_global=True")

# Add users to teams
print("\n3. Adding users to teams...")
TeamMembership.objects.get_or_create(
    team=dev_team,
    user=dev_user,
    defaults={'role': 'member'}
)
print("   ✓ Added dev user to Development team")

TeamMembership.objects.get_or_create(
    team=it_support_team,
    user=support_user,
    defaults={'role': 'member'}
)
print("   ✓ Added support user to IT Support team (global)")

TeamMembership.objects.get_or_create(
    team=rz_hosting_team,
    user=support_user,
    defaults={'role': 'lead'}
)
print("   ✓ Added support user to RZ/Hosting team (global)")

# Create projects
print("\n4. Creating test projects...")
project1, _ = Project.objects.get_or_create(
    name='Website Redesign',
    defaults={
        'description': 'Complete redesign of company website',
        'status': 'active',
        'visibility': 'members',
        'owner': staff_user,
        'color': '#3b82f6'
    }
)
print(f"   ✓ Project 'Website Redesign' ({'created' if _ else 'exists'})")

project2, _ = Project.objects.get_or_create(
    name='Internal Tools',
    defaults={
        'description': 'Development of internal tooling',
        'status': 'active',
        'visibility': 'members',
        'owner': staff_user,
        'color': '#10b981'
    }
)
print(f"   ✓ Project 'Internal Tools' ({'created' if _ else 'exists'})")

# Add team members to projects (only non-global teams)
print("\n5. Assigning teams to projects...")
ProjectTeamMembership.objects.get_or_create(
    project=project1,
    team=dev_team,
    defaults={'role': 'contributor'}
)
print("   ✓ Added Development team to Website Redesign project")

ProjectUserMembership.objects.get_or_create(
    project=project1,
    user=staff_user,
    defaults={'role': 'manager'}
)
print("   ✓ Added admin as manager to Website Redesign project")

ProjectUserMembership.objects.get_or_create(
    project=project2,
    user=staff_user,
    defaults={'role': 'manager'}
)
print("   ✓ Added admin as manager to Internal Tools project")

# Create test tasks
print("\n6. Creating test tasks...")
task1, _ = Task.objects.get_or_create(
    title='Setup CI/CD pipeline',
    project=project1,
    defaults={
        'description': 'Configure GitHub Actions for automated testing',
        'status': 'backlog',
        'priority': 2,
        'created_by': staff_user
    }
)
if _:
    task1.assigned_to_team = it_support_team
    task1.save()
print(f"   ✓ Task 'Setup CI/CD pipeline' ({'created' if _ else 'exists'}) - assigned to IT Support (global team)")

task2, _ = Task.objects.get_or_create(
    title='Design homepage mockup',
    project=project1,
    defaults={
        'description': 'Create mockup for new homepage design',
        'status': 'todo',
        'priority': 3,
        'created_by': staff_user,
        'assigned_to_user': dev_user
    }
)
print(f"   ✓ Task 'Design homepage mockup' ({'created' if _ else 'exists'}) - assigned to dev user")

print("\n" + "="*70)
print("✅ Test data setup complete!")
print("="*70)
print("\nManual Testing Checklist:")
print("\n1. Login as 'support' user (password: support)")
print("   - Should see both projects (via global team membership)")
print("   - Check project detail pages show global teams separately")
print("\n2. Login as 'admin' user (password: admin)")
print("   - Create a new team and mark it as global")
print("   - Edit existing teams and toggle is_global")
print("   - Check team list shows globe icon for global teams")
print("\n3. Check task assignment:")
print("   - Open any task in Website Redesign project")
print("   - Global teams (IT Support, RZ/Hosting) should appear in team dropdown")
print("   - Non-global unassigned teams should NOT appear")
print("\n4. Check project members:")
print("   - Open Website Redesign project detail")
print("   - Check 'Global Teams (auto-included)' section shows IT Support and RZ/Hosting")
print("   - These teams should NOT have a remove button")
print("\n5. Test access control:")
print("   - Login as 'support' user")
print("   - Verify can view and work on tasks in both projects")
print("   - Verify has 'contributor' role in both projects")
print("\nServer command: python manage.py runserver")
print("Admin URL: http://localhost:8000/accounts/login/")
