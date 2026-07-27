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


@pytest.mark.django_db
def test_second_facilitys_first_grn_dn_invoice_do_not_collide_with_first_facilitys():
    """
    Regression test. Document number sequences (GRN/DN/Invoice) are scoped
    per facility (libs.sequences.get_next_sequence_number), so a second
    facility's first document is numbered "...-000001" too - the same number
    as the first facility's first document. The model fields used to be
    globally unique=True, which meant the very first GRN, DN or Invoice ever
    created in a second facility raised a ValidationError on save because it
    collided with facility 1's document of the same number.

    This was invisible for a long time because production only ever had one
    facility. It surfaced when a test for an unrelated feature (the payments
    register) created a second facility to prove per-facility isolation and
    immediately hit the collision. Uniqueness is now scoped to
    (facility, number) instead of being global - see the Meta.unique_together
    on GRN, DeliveryNote and Invoice.
    """
    from datetime import date
    from decimal import Decimal
    from apps.parties.services import create_party
    from apps.inventory.services import create_commodity, create_grn
    from apps.delivery.services import create_delivery_note
    from apps.delivery.models import DeliveryNote
    from apps.invoicing.services import generate_invoices_for_uninvoiced_deliveries

    fac1 = create_facility(name="Facility One")
    fac2 = create_facility(name="Facility Two")

    def first_document_set(facility):
        party = create_party(facility_id=facility.id, name="Farmer", type="DEPOSITOR")
        commodity = create_commodity(facility_id=facility.id, name="Potato", unit="BAGS")
        grn = create_grn(
            facility_id=facility.id,
            party_id=party.id,
            receipt_date=date(2026, 7, 1),
            items=[{
                "commodity_id": commodity.id,
                "initial_qty": 50,
                "rent_rate_per_unit": Decimal('10.00'),
            }],
        )
        lot = grn.lots.first()
        dn = create_delivery_note(
            facility_id=facility.id,
            party_id=party.id,
            dispatch_date=date(2026, 7, 10),
            status=DeliveryNote.Status.POSTED,
            lines=[{"lot_id": lot.id, "qty": 10}],
        )
        invoice = generate_invoices_for_uninvoiced_deliveries(
            facility_id=facility.id, party_id=party.id
        )[0]
        return grn, dn, invoice

    grn1, dn1, inv1 = first_document_set(fac1)
    grn2, dn2, inv2 = first_document_set(fac2)

    # Both facilities' first documents get the same per-facility number...
    assert grn1.grn_number == grn2.grn_number == "GRN-000001"
    assert dn1.dn_number == dn2.dn_number == "DN-000001"
    assert inv1.invoice_number == inv2.invoice_number == "INV-000001"

    # ...and creating the second facility's set did not raise, and both rows
    # genuinely exist and belong to their own facility.
    assert grn1.facility_id == fac1.id and grn2.facility_id == fac2.id
    assert dn1.facility_id == fac1.id and dn2.facility_id == fac2.id
    assert inv1.facility_id == fac1.id and inv2.facility_id == fac2.id
