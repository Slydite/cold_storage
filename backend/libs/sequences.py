from django.db import transaction

# Sequence helper stub
# We will define the Sequence model later in one of our apps.
# This utility will use select_for_update() on that model to generate safe sequence numbers.

def get_next_sequence_number(sequence_type: str) -> str:
    """
    Generate the next sequence number for a given type (e.g. 'GRN', 'DN', 'INV')
    using select_for_update() on the Sequence model.
    """
    # Placeholder implementation
    raise NotImplementedError("Sequence model and generator not implemented yet.")
