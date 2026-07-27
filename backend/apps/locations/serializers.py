from rest_framework import serializers
from .models import Chamber, Floor, Block


class ChamberOutputSerializer(serializers.ModelSerializer):
    facility_id = serializers.IntegerField(source='facility.id', read_only=True)

    class Meta:
        model = Chamber
        fields = [
            'id',
            'facility_id',
            'name',
            'code',
            'sort_order',
            'is_active',
            'created_at',
            'updated_at'
        ]


class ChamberInputSerializer(serializers.Serializer):
    facility_id = serializers.IntegerField()
    name = serializers.CharField(max_length=50)
    sort_order = serializers.IntegerField(default=0, required=False)
    is_active = serializers.BooleanField(default=True, required=False)


class ChamberUpdateInputSerializer(serializers.Serializer):
    facility_id = serializers.IntegerField(required=False)
    name = serializers.CharField(max_length=50, required=False)
    sort_order = serializers.IntegerField(required=False)
    is_active = serializers.BooleanField(required=False)


class FloorOutputSerializer(serializers.ModelSerializer):
    chamber_name = serializers.CharField(source='chamber.name', read_only=True)
    facility_id = serializers.IntegerField(source='chamber.facility_id', read_only=True)

    class Meta:
        model = Floor
        fields = [
            'id',
            'chamber_id',
            'chamber_name',
            'facility_id',
            'name',
            'code',
            'sort_order',
            'is_active',
            'created_at',
            'updated_at'
        ]


class FloorInputSerializer(serializers.Serializer):
    facility_id = serializers.IntegerField(required=False, allow_null=True, default=None)
    chamber_id = serializers.IntegerField()
    name = serializers.CharField(max_length=50)
    sort_order = serializers.IntegerField(default=0, required=False)
    is_active = serializers.BooleanField(default=True, required=False)


class FloorUpdateInputSerializer(serializers.Serializer):
    chamber_id = serializers.IntegerField(required=False)
    name = serializers.CharField(max_length=50, required=False)
    sort_order = serializers.IntegerField(required=False)
    is_active = serializers.BooleanField(required=False)


class BlockOutputSerializer(serializers.ModelSerializer):
    floor_name = serializers.CharField(source='floor.name', read_only=True)
    chamber_id = serializers.IntegerField(source='floor.chamber_id', read_only=True)
    chamber_name = serializers.CharField(source='floor.chamber.name', read_only=True)
    facility_id = serializers.IntegerField(source='floor.chamber.facility_id', read_only=True)

    class Meta:
        model = Block
        fields = [
            'id',
            'floor_id',
            'floor_name',
            'chamber_id',
            'chamber_name',
            'facility_id',
            'name',
            'code',
            'sort_order',
            'capacity_bags',
            'is_active',
            'created_at',
            'updated_at'
        ]


class BlockInputSerializer(serializers.Serializer):
    facility_id = serializers.IntegerField(required=False, allow_null=True, default=None)
    chamber_id = serializers.IntegerField(required=False, allow_null=True, default=None)
    floor_id = serializers.IntegerField()
    name = serializers.CharField(max_length=50)
    sort_order = serializers.IntegerField(default=0, required=False)
    capacity_bags = serializers.IntegerField(required=False, allow_null=True, default=None)
    is_active = serializers.BooleanField(default=True, required=False)


class BlockUpdateInputSerializer(serializers.Serializer):
    floor_id = serializers.IntegerField(required=False)
    name = serializers.CharField(max_length=50, required=False)
    sort_order = serializers.IntegerField(required=False)
    capacity_bags = serializers.IntegerField(required=False, allow_null=True)
    is_active = serializers.BooleanField(required=False)

