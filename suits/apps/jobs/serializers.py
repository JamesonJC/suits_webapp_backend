from rest_framework import serializers
from .models import Task

class TaskSerializer(serializers.ModelSerializer):
    case_title    = serializers.CharField(source='case.title', read_only=True, default=None)
    assigned_name = serializers.SerializerMethodField(read_only=True)

    def get_assigned_name(self, obj):
        u = obj.assigned_to
        if not u: return None
        return f'{u.first_name} {u.last_name}'.strip() or u.username

    class Meta:
        model  = Task
        fields = ['id','title','description','due_date','status','priority','category',
                  'law_firm','case','case_title','assigned_to','assigned_name','created_at','updated_at']
        read_only_fields = ('law_firm','tenant','case_title','assigned_name','created_at','updated_at')

    def validate_title(self, value):
        if not value or not str(value).strip():
            raise serializers.ValidationError('Task title is required.')
        return str(value).strip()