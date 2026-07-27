import pytest
from apps.facilities.services import create_facility, update_facility
from apps.facilities.models import Facility

@pytest.mark.django_db
def test_create_facility_success():
    facility = create_facility(name="Test Facility", address="Some address")
    assert facility.name == "Test Facility"
    assert facility.code == "FAC-000001"
    assert facility.address == "Some address"
    assert Facility.objects.filter(code="FAC-000001").exists()

@pytest.mark.django_db
def test_create_facility_sequence_advances():
    f1 = create_facility(name="Facility 1")
    f2 = create_facility(name="Facility 2")
    assert f1.code == "FAC-000001"
    assert f2.code == "FAC-000002"
    assert f1.code != f2.code

@pytest.mark.django_db
def test_update_facility_success():
    facility = create_facility(name="Old Name")
    updated = update_facility(facility_id=facility.id, name="New Name", address="New Address")
    assert updated.name == "New Name"
    assert updated.address == "New Address"
    assert updated.code == "FAC-000001"
