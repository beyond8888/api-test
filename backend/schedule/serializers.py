from django.db import transaction
from django.db.models import Q
from rest_framework import serializers

from .models import Assignment, Project


class AssignmentInlineSerializer(serializers.ModelSerializer):
    class Meta:
        model = Assignment
        fields = ['id', 'role', 'assignee', 'start_date', 'end_date']


class ProjectSerializer(serializers.ModelSerializer):
    assignments = AssignmentInlineSerializer(many=True, required=False)

    class Meta:
        model = Project
        fields = ['id', 'name', 'description', 'color', 'assignments', 'created_at']

    @transaction.atomic
    def create(self, validated_data):
        assignments_data = validated_data.pop('assignments', [])
        project = Project.objects.create(**validated_data)
        request = self.context.get('request')
        owner = getattr(request, 'user', None) if request else None
        for a in assignments_data:
            Assignment.objects.create(project=project, owner=owner, title=project.name, **a)
        return project

    @transaction.atomic
    def update(self, instance, validated_data):
        assignments_data = validated_data.pop('assignments', None)
        instance.name = validated_data.get('name', instance.name)
        instance.description = validated_data.get('description', instance.description)
        if 'color' in validated_data:
            instance.color = validated_data['color']
        instance.save()

        # Diff-update assignments to preserve ids and avoid unnecessary deletes.
        if assignments_data is not None:
            existing = {a.id: a for a in instance.assignments.all()}
            incoming_ids = set()
            for a in assignments_data:
                a_id = a.get('id')
                if a_id and a_id in existing:
                    assignment = existing[a_id]
                    for attr, value in a.items():
                        if attr == 'id':
                            continue
                        setattr(assignment, attr, value)
                    assignment.title = instance.name
                    assignment.save()
                    incoming_ids.add(a_id)
                else:
                    new_a = Assignment.objects.create(
                        project=instance,
                        owner=instance.owner,
                        title=instance.name,
                        **{k: v for k, v in a.items() if k != 'id'},
                    )
                    incoming_ids.add(new_a.id)

            # Remove assignments that are no longer present.
            instance.assignments.exclude(id__in=incoming_ids).delete()

        return instance


class AssignmentSerializer(serializers.ModelSerializer):
    project = serializers.PrimaryKeyRelatedField(
        queryset=Project.objects.all()
    )

    class Meta:
        model = Assignment
        fields = [
            'id', 'project', 'title', 'start_date', 'end_date',
            'role', 'assignee', 'created_at',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if user and getattr(user, 'is_authenticated', False):
            # Restrict project choices to the current user's own projects so an
            # attacker cannot attach an assignment to another user's project.
            instance = getattr(self, 'instance', None)
            current_project_id = getattr(instance, 'project_id', None)
            if current_project_id:
                self.fields['project'].queryset = Project.objects.filter(
                    Q(owner=user) | Q(id=current_project_id)
                )
            else:
                self.fields['project'].queryset = Project.objects.filter(owner=user)


class HolidayQuerySerializer(serializers.Serializer):
    """Query param validation for GET /holidays/."""
    year = serializers.IntegerField(min_value=2000, max_value=2100, required=True)


class AssigneeQuerySerializer(serializers.Serializer):
    """Query param validation for GET /assignees/."""
    project_id = serializers.IntegerField(required=False)
    role = serializers.CharField(required=False, allow_blank=True)
