import pytest
from django.core.exceptions import ValidationError
from apps.facilities.models import Facility
from apps.parties.models import Party
from apps.parties.services import create_party, update_party

@pytest.fixture
def alternate_facility(db):
    facility, _ = Facility.objects.get_or_create(
        code="FAC-02",
        defaults={"name": "Other Facility"}
    )
    return facility

@pytest.mark.django_db
def test_create_party_success(default_facility):
    party = create_party(
        facility_id=default_facility.id,
        name="Test Depositor",
        type="DEPOSITOR",
        phone="1234567890",
        email="test@example.com",
        address="123 Storage Lane"
    )
    
    assert party.name == "Test Depositor"
    assert party.code == "PRT-000001"
    assert party.type == "DEPOSITOR"
    assert party.facility == default_facility
    assert party.is_active is True
    
    # Verify simple history record is created
    assert party.history.count() == 1
    assert party.history.first().history_type == "+"

@pytest.mark.django_db
def test_create_party_sequence_advances(default_facility):
    party1 = create_party(
        facility_id=default_facility.id,
        name="Depositor 1",
        type="DEPOSITOR"
    )
    party2 = create_party(
        facility_id=default_facility.id,
        name="Depositor 2",
        type="DEPOSITOR"
    )
    
    assert party1.code == "PRT-000001"
    assert party2.code == "PRT-000002"
    assert party1.code != party2.code

@pytest.mark.django_db
def test_create_party_sanitisation(default_facility):
    party = create_party(
        facility_id=default_facility.id,
        name="  jai   prakash ",
        type="DEPOSITOR",
        gstin="  27aabcc1408h1zc ",
        email=" Foo@BAR.com ",
        phone=" +91 (987) 654-3210 ",
        address="  123   Main  St "
    )
    
    assert party.name == "Jai Prakash"
    assert party.gstin == "27AABCC1408H1ZC"
    assert party.email == "foo@bar.com"
    assert party.phone == "+91 987 654 3210"
    assert party.address == "123 Main St"

@pytest.mark.django_db
def test_create_party_invalid_facility():
    with pytest.raises(ValidationError) as context:
        create_party(
            facility_id=9999,
            name="Test Depositor",
            type="DEPOSITOR"
        )
    assert "Facility with ID 9999 does not exist." in str(context.value)

@pytest.mark.django_db
def test_create_party_invalid_type(default_facility):
    with pytest.raises(ValidationError) as context:
        create_party(
            facility_id=default_facility.id,
            name="Test Depositor",
            type="INVALID_TYPE"
        )
    assert "Invalid party type" in str(context.value)

@pytest.mark.django_db
def test_update_party_success(default_facility):
    party = create_party(
        facility_id=default_facility.id,
        name="Test Depositor",
        type="DEPOSITOR"
    )
    
    updated_party = update_party(
        party_id=party.id,
        name="Updated Depositor",
        phone="9876543210",
        is_active=False
    )
    
    assert updated_party.name == "Updated Depositor"
    assert updated_party.phone == "9876543210"
    assert updated_party.is_active is False
    assert updated_party.type == "DEPOSITOR"
    assert updated_party.code == "PRT-000001"
    
    # Verify history record shows the update
    assert party.history.count() == 2
    latest_history = party.history.order_by('-history_date').first()
    assert latest_history.history_type == "~"
    assert latest_history.name == "Updated Depositor"
