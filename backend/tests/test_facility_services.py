import pytest
from apps.facilities.services import create_facility, update_facility
from apps.facilities.models import Facility
from django.core.exceptions import ValidationError

@pytest.mark.django_db
def test_create_facility_success():
    facility = create_facility(name="Test Facility", code="TST-01", address="Some address")
    assert facility.name == "Test Facility"
    assert facility.code == "TST-01"
    assert facility.address == "Some address"
    assert Facility.objects.filter(code="TST-01").exists()

@pytest.mark.django_db
def test_create_facility_duplicate_code():
    create_facility(name="Facility 1", code="DUP-01")
    with pytest.raises(ValidationError):
        create_facility(name="Facility 2", code="DUP-01")

@pytest.mark.django_db
def test_update_facility_success():
    facility = create_facility(name="Old Name", code="OLD-01")
    updated = update_facility(facility_id=facility.id, name="New Name", address="New Address")
    assert updated.name == "New Name"
    assert updated.address == "New Address"
    assert updated.code == "OLD-01"
