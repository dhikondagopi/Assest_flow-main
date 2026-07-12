"""
Management command: seed_demo_data
Run: python manage.py seed_demo_data
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
import datetime


class Command(BaseCommand):
    help = "Seeds AssetFlow with rich demo data"

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write("🌱  Seeding AssetFlow demo data …")

        from django.contrib.auth import get_user_model
        from apps.org.models import Department, AssetCategory, EmployeeProfile
        from apps.assets.models import Asset
        from apps.allocations.models import Allocation, TransferRequest
        from apps.bookings.models import Booking
        from apps.maintenance.models import MaintenanceRequest
        from apps.notifications.utils import create_notification
        from apps.notifications.models import Notification

        User = get_user_model()
        today = timezone.now().date()
        now   = timezone.now()

        # ── 1. Departments — 3-level hierarchy ────────────────────────────────
        corp, _ = Department.objects.get_or_create(
            code="CORP",
            defaults={"name": "Corporate", "description": "Top-level corporate entity"},
        )
        it_dept, _ = Department.objects.get_or_create(
            code="IT",
            defaults={"name": "Information Technology", "description": "IT department", "parent": corp},
        )
        it_infra, _ = Department.objects.get_or_create(
            code="IT-INF",
            defaults={"name": "IT Infrastructure", "description": "Servers, networking, hardware", "parent": it_dept},
        )
        it_sec, _ = Department.objects.get_or_create(
            code="IT-SEC",
            defaults={"name": "IT Security", "description": "Cybersecurity team", "parent": it_dept},
        )
        ops_dept, _ = Department.objects.get_or_create(
            code="OPS",
            defaults={"name": "Operations", "description": "Operations", "parent": corp},
        )
        hr_dept, _ = Department.objects.get_or_create(
            code="HR",
            defaults={"name": "Human Resources", "description": "HR", "parent": corp},
        )
        self.stdout.write("  ✓  6 departments (3-level: Corporate → IT → IT Infrastructure/Security)")

        # ── 2. Users ──────────────────────────────────────────────────────────
        def make_user(email, first, last, role, password="Password@123"):
            u, created = User.objects.get_or_create(
                email=email,
                defaults={"first_name": first, "last_name": last, "role": role},
            )
            if created:
                u.set_password(password)
                u.save()
            return u

        admin1 = make_user("admin@assetflow.com",    "Alice",  "Admin",    User.Role.ADMIN)
        admin2 = make_user("admin2@assetflow.com",   "Bob",    "Boss",     User.Role.ADMIN)
        mgr1   = make_user("manager1@assetflow.com", "Carlos", "Manager",  User.Role.ASSET_MANAGER)
        mgr2   = make_user("manager2@assetflow.com", "Diana",  "Asset",    User.Role.ASSET_MANAGER)
        dh1    = make_user("depthead1@assetflow.com","Eve",    "Head",     User.Role.DEPARTMENT_HEAD)
        dh2    = make_user("depthead2@assetflow.com","Frank",  "Lead",     User.Role.DEPARTMENT_HEAD)
        emp1   = make_user("emp1@assetflow.com",     "Grace",  "Employee", User.Role.EMPLOYEE)
        emp2   = make_user("emp2@assetflow.com",     "Hank",   "Smith",    User.Role.EMPLOYEE)
        emp3   = make_user("emp3@assetflow.com",     "Ivy",    "Jones",    User.Role.EMPLOYEE)
        emp4   = make_user("emp4@assetflow.com",     "Jack",   "Brown",    User.Role.EMPLOYEE)
        emp5   = make_user("emp5@assetflow.com",     "Karen",  "White",    User.Role.EMPLOYEE)
        emp6   = make_user("emp6@assetflow.com",     "Leo",    "Black",    User.Role.EMPLOYEE)
        self.stdout.write("  ✓  12 users")

        # ── 3. Profiles ───────────────────────────────────────────────────────
        def make_profile(user, dept, emp_num, title=""):
            p, _ = EmployeeProfile.objects.get_or_create(
                user=user,
                defaults={"department": dept, "employee_number": emp_num, "title": title},
            )
            return p

        p_admin1 = make_profile(admin1, corp,    "EMP-001", "IT Operations Director")
        p_admin2 = make_profile(admin2, corp,    "EMP-002", "IT Director")
        p_mgr1   = make_profile(mgr1,   it_dept, "EMP-003", "Asset Program Manager")
        p_mgr2   = make_profile(mgr2,   ops_dept,"EMP-004", "Asset Manager")
        p_dh1    = make_profile(dh1,    it_infra,"EMP-005", "Head of IT Infrastructure")
        p_dh2    = make_profile(dh2,    hr_dept, "EMP-006", "Head of HR")
        p_emp1   = make_profile(emp1,   it_dept, "EMP-007", "Senior Software Engineer")
        p_emp2   = make_profile(emp2,   it_dept, "EMP-008", "Software Engineer")
        p_emp3   = make_profile(emp3,   ops_dept,"EMP-009", "Operations Analyst")
        p_emp4   = make_profile(emp4,   ops_dept,"EMP-010", "Operations Coordinator")
        p_emp5   = make_profile(emp5,   hr_dept, "EMP-011", "HR Specialist")
        p_emp6   = make_profile(emp6,   it_sec,  "EMP-012", "Security Analyst")

        corp.head    = dh1; corp.save()
        it_dept.head = dh1; it_dept.save()
        hr_dept.head = dh2; hr_dept.save()
        self.stdout.write("  ✓  12 employee profiles")

        # ── 4. Asset Categories ───────────────────────────────────────────────
        cat_laptop, _ = AssetCategory.objects.get_or_create(name="Laptop",      defaults={"extra_fields": [{"name":"ram_gb","type":"integer","required":True}]})
        cat_monitor,_ = AssetCategory.objects.get_or_create(name="Monitor",     defaults={"extra_fields": [{"name":"size_inch","type":"number","required":False}]})
        cat_vehicle,_ = AssetCategory.objects.get_or_create(name="Vehicle",     defaults={"extra_fields": [{"name":"plate_number","type":"string","required":True}]})
        cat_phone,  _ = AssetCategory.objects.get_or_create(name="Mobile Phone",defaults={"extra_fields": [{"name":"imei","type":"string","required":True}]})
        cat_room,   _ = AssetCategory.objects.get_or_create(name="Meeting Room",defaults={"extra_fields": [{"name":"capacity","type":"integer","required":True}]})
        self.stdout.write("  ✓  5 asset categories")

        # ── 5. Assets (20) ────────────────────────────────────────────────────
        def make_asset(name, category, status=Asset.Status.AVAILABLE, **kwargs):
            a, _ = Asset.objects.get_or_create(name=name, defaults={"category": category, "status": status, **kwargs})
            return a

        laptops  = [make_asset(f"Dell Latitude {5000+i}", cat_laptop, serial_number=f"DELL-{1000+i}", location="IT Store") for i in range(1, 8)]
        monitors = [make_asset(f"Dell 24\" Monitor {i}",  cat_monitor, serial_number=f"MON-{200+i}",  location="IT Store") for i in range(1, 5)]
        vehicles = [
            make_asset("Toyota Corolla 2022", cat_vehicle, serial_number="VH-001", location="Parking Bay A"),
            make_asset("Honda CR-V 2023",     cat_vehicle, serial_number="VH-002", location="Parking Bay B"),
        ]
        phones = [
            make_asset("iPhone 14 Pro",      cat_phone, serial_number="IPH-001"),
            make_asset("Samsung Galaxy S23", cat_phone, serial_number="SGS-001"),
        ]
        rooms = [
            make_asset("Conference Room A", cat_room, location="Floor 2", extra_data={"capacity": 10}),
            make_asset("Conference Room B", cat_room, location="Floor 3", extra_data={"capacity": 20}),
            make_asset("Board Room",        cat_room, location="Floor 5", extra_data={"capacity": 30}),
        ]

        Asset.objects.filter(pk=laptops[5].pk).update(status=Asset.Status.LOST)
        Asset.objects.filter(pk=phones[0].pk).update(status=Asset.Status.LOST)
        Asset.objects.filter(pk=monitors[0].pk).update(status=Asset.Status.UNDER_MAINTENANCE)
        Asset.objects.filter(pk=vehicles[1].pk).update(status=Asset.Status.UNDER_MAINTENANCE)

        for a in laptops + monitors + vehicles + phones + rooms:
            a.refresh_from_db()

        self.stdout.write("  ✓  20 assets")

        # ── 6. Allocations — including one with rich history (4+ events) ─────
        def make_alloc(asset, profile, by, due=None, notes=""):
            Asset.objects.filter(pk=asset.pk).update(status=Asset.Status.ALLOCATED)
            a, _ = Allocation.objects.get_or_create(
                asset=asset, employee=profile, status=Allocation.Status.ACTIVE,
                defaults={"allocated_by": by, "due_date": due, "notes": notes},
            )
            return a

        alloc1 = make_alloc(laptops[0], p_emp1, mgr1, due=today + datetime.timedelta(days=30), notes="Primary work laptop")
        alloc2 = make_alloc(laptops[1], p_emp2, mgr1, due=today + datetime.timedelta(days=15))
        alloc3 = make_alloc(laptops[2], p_emp3, mgr1, due=today - datetime.timedelta(days=10), notes="OVERDUE — please return")

        # Rich history asset: laptops[3] has been allocated → returned → reallocated → maintenance
        hist_asset = laptops[3]
        hist_alloc_old, _ = Allocation.objects.get_or_create(
            asset=hist_asset, employee=p_emp4, status=Allocation.Status.RETURNED,
            defaults={
                "allocated_by": mgr1,
                "due_date":     today - datetime.timedelta(days=60),
                "notes":        "First allocation — returned on schedule",
            },
        )
        if not hist_alloc_old.returned_at:
            hist_alloc_old.returned_at = now - datetime.timedelta(days=50)
            hist_alloc_old.save(update_fields=["returned_at"])

        # Second allocation on same asset (closed by transfer)
        hist_alloc2, _ = Allocation.objects.get_or_create(
            asset=hist_asset, employee=p_emp5, status=Allocation.Status.CLOSED,
            defaults={"allocated_by": mgr1, "notes": "Closed via transfer"},
        )
        # Current active allocation on the rich history asset
        Asset.objects.filter(pk=hist_asset.pk).update(status=Asset.Status.ALLOCATED)
        hist_alloc_cur, _ = Allocation.objects.get_or_create(
            asset=hist_asset, employee=p_emp6, status=Allocation.Status.ACTIVE,
            defaults={"allocated_by": mgr1, "due_date": today + datetime.timedelta(days=20)},
        )
        self.stdout.write("  ✓  allocations (3 active incl. 1 overdue + 1 rich-history asset)")

        # ── 7. Bookings ────────────────────────────────────────────────────────
        room_a = rooms[0]
        base_dt = now.replace(hour=9, minute=0, second=0, microsecond=0) + datetime.timedelta(days=1)

        def make_booking(asset, user, start, end, purpose=""):
            b, _ = Booking.objects.get_or_create(
                asset=asset, booked_by=user, start_time=start,
                defaults={"end_time": end, "purpose": purpose, "status": Booking.Status.CONFIRMED},
            )
            return b

        make_booking(room_a, emp1, base_dt,                                   base_dt + datetime.timedelta(hours=2), "Sprint planning")
        make_booking(room_a, emp2, base_dt + datetime.timedelta(hours=2),     base_dt + datetime.timedelta(hours=4), "Team retrospective")
        self.stdout.write("  ✓  2 bookings (back-to-back; 3rd would conflict)")

        # ── 8. Maintenance — 2 requests + history entries on rich-history asset
        maint1, _ = MaintenanceRequest.objects.get_or_create(
            asset=monitors[0], requested_by=emp1,
            defaults={"description": "Screen flickering badly", "priority": MaintenanceRequest.Priority.HIGH, "status": MaintenanceRequest.Status.APPROVED},
        )
        maint2, _ = MaintenanceRequest.objects.get_or_create(
            asset=vehicles[1], requested_by=emp3,
            defaults={"description": "Engine oil change required", "priority": MaintenanceRequest.Priority.MEDIUM,
                      "status": MaintenanceRequest.Status.IN_PROGRESS, "assigned_to": mgr1,
                      "scheduled_date": today + datetime.timedelta(days=3)},
        )
        # Resolved maintenance on rich-history asset (completes the timeline)
        maint_hist, _ = MaintenanceRequest.objects.get_or_create(
            asset=hist_asset, requested_by=emp4,
            defaults={
                "description": "Battery drain — replaced battery module under warranty.",
                "priority": MaintenanceRequest.Priority.HIGH,
                "status": MaintenanceRequest.Status.RESOLVED,
                "assigned_to": mgr1,
            },
        )
        self.stdout.write("  ✓  3 maintenance requests (APPROVED + IN_PROGRESS + RESOLVED on history asset)")

        # ── 9. Notifications — 5 unread + 5 read across different types ───────
        # Clear old seed notifications to stay idempotent
        Notification.objects.filter(
            recipient__in=[emp1, emp2, emp3, emp4, emp5, emp6, mgr1, admin1],
            verb__in=["ASSET_ALLOCATED","ASSET_RETURNED","TRANSFER_APPROVED","TRANSFER_PENDING",
                      "BOOKING_CONFIRMED","MAINTENANCE_APPROVED","MAINTENANCE_RESOLVED",
                      "MAINTENANCE_REJECTED","OVERDUE_RETURN"],
        ).delete()

        def notif(recipient, verb, msg, target, read=False):
            n = Notification.objects.create(
                recipient=recipient, verb=verb, message=msg,
                target_id=str(target), is_read=read,
            )
            return n

        # 5 UNREAD
        notif(emp1,  "ASSET_ALLOCATED",     f"Asset {laptops[0].asset_tag} has been allocated to you.",                str(alloc1.id))
        notif(emp3,  "OVERDUE_RETURN",      f"Asset {laptops[2].asset_tag} is 10 days overdue — please return.",       str(alloc3.id))
        notif(emp1,  "MAINTENANCE_APPROVED",f"Your maintenance request for {monitors[0].asset_tag} was approved.",     str(maint1.id))
        notif(mgr1,  "TRANSFER_PENDING",    "A new transfer request is awaiting your approval.",                       "")
        notif(emp4,  "BOOKING_CONFIRMED",   f"Conference Room A booking tomorrow 09:00–11:00 confirmed.",              "")

        # 5 READ
        notif(emp2,  "ASSET_ALLOCATED",     f"Asset {laptops[1].asset_tag} has been allocated to you.",                str(alloc2.id),  read=True)
        notif(emp4,  "ASSET_ALLOCATED",     f"Asset {hist_asset.asset_tag} has been allocated to you.",                str(hist_alloc_cur.id), read=True)
        notif(emp4,  "MAINTENANCE_RESOLVED",f"Maintenance on {hist_asset.asset_tag} has been resolved.",               str(maint_hist.id), read=True)
        notif(emp5,  "TRANSFER_APPROVED",   f"Transfer of {hist_asset.asset_tag} was approved.",                       "", read=True)
        notif(admin1,"MAINTENANCE_APPROVED",f"Maintenance for {monitors[0].asset_tag} is approved and underway.",      str(maint1.id), read=True)

        self.stdout.write("  ✓  10 notifications (5 unread + 5 read across all types)")

        self.stdout.write(self.style.SUCCESS(
            "\n✅  Demo data seeded!\n"
            "   Admin:    admin@assetflow.com / Password@123\n"
            "   Manager:  manager1@assetflow.com / Password@123\n"
            "   Employee: emp1@assetflow.com / Password@123"
        ))
