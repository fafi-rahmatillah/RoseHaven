from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse


class AdministratorAccessTests(TestCase):
    def setUp(self):
        group, _ = Group.objects.get_or_create(name='Administrator')
        self.admin = User.objects.create_user('adminuser', password='StrongPass123!')
        self.admin.groups.add(group)

    def test_admin_pages(self):
        self.client.login(username='adminuser', password='StrongPass123!')
        for name in ['administrator:dashboard', 'administrator:room_list', 'administrator:room_type_list', 'administrator:facility_list', 'administrator:customer_list', 'administrator:reservation_list', 'administrator:payment_list', 'administrator:receptionist_list', 'administrator:reports', 'administrator:settings']:
            self.assertEqual(self.client.get(reverse(name)).status_code, 200)
