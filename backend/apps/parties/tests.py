from django.test import TestCase
from django.core.exceptions import ValidationError
from apps.facilities.models import Facility
from apps.parties.models import Party
from apps.parties.services import create_party, update_party

class PartyServiceTestCase(TestCase):
    def setUp(self):
        # Fetch or create default facility seeded by migrations
        self.facility, _ = Facility.objects.get_or_create(
            code="FAC-01",
            defaults={"name": "Default Facility"}
        )
        # Create an alternative facility for testing cross-facility constraints
        self.other_facility, _ = Facility.objects.get_or_create(
            code="FAC-02",
            defaults={"name": "Other Facility"}
        )

    def test_create_party_success(self):
        party = create_party(
            facility_id=self.facility.id,
            name="Test Depositor",
            code="DEP001",
            type="DEPOSITOR",
            phone="1234567890",
            email="test@example.com",
            address="123 Storage Lane"
        )
        
        self.assertEqual(party.name, "Test Depositor")
        self.assertEqual(party.code, "DEP001")
        self.assertEqual(party.type, "DEPOSITOR")
        self.assertEqual(party.facility, self.facility)
        self.assertTrue(party.is_active)
        
        # Verify simple history record is created
        self.assertEqual(party.history.count(), 1)
        self.assertEqual(party.history.first().history_type, "+") # "+" represents creation

    def test_create_party_invalid_facility(self):
        with self.assertRaises(ValidationError) as context:
            create_party(
                facility_id=9999,
                name="Test Depositor",
                code="DEP001",
                type="DEPOSITOR"
            )
        self.assertIn("Facility with ID 9999 does not exist.", str(context.exception))

    def test_create_party_invalid_type(self):
        with self.assertRaises(ValidationError) as context:
            create_party(
                facility_id=self.facility.id,
                name="Test Depositor",
                code="DEP001",
                type="INVALID_TYPE"
            )
        self.assertIn("Invalid party type", str(context.exception))

    def test_create_party_unique_constraint(self):
        # Create first party
        create_party(
            facility_id=self.facility.id,
            name="Test Depositor 1",
            code="DEP001",
            type="DEPOSITOR"
        )
        
        # Creating another party with same code in same facility should fail
        with self.assertRaises(ValidationError):
            create_party(
                facility_id=self.facility.id,
                name="Test Depositor 2",
                code="DEP001",
                type="DEPOSITOR"
            )

        # Creating another party with same code in DIFFERENT facility should succeed
        party_other = create_party(
            facility_id=self.other_facility.id,
            name="Test Depositor 2",
            code="DEP001",
            type="DEPOSITOR"
        )
        self.assertEqual(party_other.facility, self.other_facility)

    def test_update_party_success(self):
        party = create_party(
            facility_id=self.facility.id,
            name="Test Depositor",
            code="DEP001",
            type="DEPOSITOR"
        )
        
        updated_party = update_party(
            party_id=party.id,
            name="Updated Depositor",
            phone="9876543210",
            is_active=False
        )
        
        self.assertEqual(updated_party.name, "Updated Depositor")
        self.assertEqual(updated_party.phone, "9876543210")
        self.assertFalse(updated_party.is_active)
        # Type and code should remain unchanged
        self.assertEqual(updated_party.type, "DEPOSITOR")
        self.assertEqual(updated_party.code, "DEP001")
        
        # Verify history record shows the update
        self.assertEqual(party.history.count(), 2)
        latest_history = party.history.order_by('-history_date').first()
        self.assertEqual(latest_history.history_type, "~") # "~" represents update
        self.assertEqual(latest_history.name, "Updated Depositor")
