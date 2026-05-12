from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from ORCEP.models import BarangayStaff

class Command(BaseCommand):
    help = 'Create initial barangay staff users'

    def handle(self, *args, **options):
        staff_users = [
            {
                'username': 'barangay.admin',
                'email': 'admin@barangaypoblacion.com',
                'password': 'admin123',
                'first_name': 'Barangay',
                'last_name': 'Admin',
                'position': 'secretary'
            },
            {
                'username': 'barangay.captain',
                'email': 'captain@barangaypoblacion.com',
                'password': 'captain123',
                'first_name': 'Juan',
                'last_name': 'Dela Cruz',
                'position': 'captain'
            }
        ]

        for staff_data in staff_users:
            user, created = User.objects.get_or_create(
                username=staff_data['username'],
                defaults={
                    'email': staff_data['email'],
                    'first_name': staff_data['first_name'],
                    'last_name': staff_data['last_name'],
                    'is_staff': True
                }
            )
            
            if created:
                user.set_password(staff_data['password'])
                user.save()
                self.stdout.write(
                    self.style.SUCCESS(f'Created user: {staff_data["username"]}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'User already exists: {staff_data["username"]}')
                )

            # Create BarangayStaff profile
            staff, staff_created = BarangayStaff.objects.get_or_create(
                user=user,
                defaults={'position': staff_data['position']}
            )
            
            if staff_created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created staff profile for: {user.get_full_name()}')
                )