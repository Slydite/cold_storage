from rest_framework import serializers
from .models import Floor, Chamber


class FloorOutputSerializer(serializers.ModelSerializer):
    class Meta:
        model = Floor
        fields = [
            'id',
            'facility_id',
            'name',
            'sort_order',
            'is_active',
            'created_at',
            'updated_at'
        ]


class FloorInputSerializer(serializers.Serializer):
    facility_id = serializers.IntegerField()
    name = serializers.CharField(max_length=50)
    sort_order = serializers.IntegerField(default=0, required=False)
    is_active = serializers.BooleanField(default=True, required=False)


class FloorUpdateInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=50, required=False)
    sort_order = serializers.IntegerField(required=False)
    is_active = serializers.BooleanField(required=False)


class ChamberOutputSerializer(serializers.ModelSerializer):
    floor_name = serializers.CharField(source='floor.name', read_only=True)
    facility_id = serializers.IntegerField(source='floor.facility_id', read_only=True)

    class Meta:
        model = Chamber
        fields = [
            'id',
            'floor_id',
            'floor_name',
            'facility_id',
            'name',
            'sort_order',
            'capacity_bags',
            'is_active',
            'created_at',
            'updated_at'
        ]


class ChamberInputSerializer(serializers.Serializer):
    facility_id = serializers.IntegerField()
    floor_id = serializers.IntegerField()
    name = serializers.CharField(max_length=50)
    sort_order = serializers.IntegerField(default=0, required=False)
    capacity_bags = serializers.IntegerField(required=False, allow_null=True, default=None)
    is_active = serializers.BooleanField(default=True, required=False)


class ChamberUpdateInputSerializer(serializers.Serializer):
    floor_id = serializers.IntegerField(required=False)
    name = serializers.CharField(max_length=50, required=False)
    sort_order = serializers.IntegerField(required=False)
    capacity_bags = serializers.IntegerField(required=False, allow_null=True)
    is_active = serializers.BooleanField(required=False)
