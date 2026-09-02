from django.contrib.auth.models import User
from django.db import models

PROJECT_COLORS = [
    '#e53935', '#d81b60', '#8e24aa', '#5e35b1', '#3949ab',
    '#1e88e5', '#039be5', '#00acc1', '#00897b', '#43a047',
    '#7cb342', '#c0ca33', '#fdd835', '#ffb300', '#fb8c00',
    '#f4511e', '#ec407a', '#ab47bc', '#7e57c2', '#5c6bc0',
    '#42a5f5', '#29b6f6', '#26c6da', '#26a69a', '#66bb6a',
    '#9ccc65', '#d4e157', '#ffee58', '#ffca28', '#ffa726',
    '#ff7043', '#ff1744', '#aa00ff', '#6200ea',
    '#2962ff', '#0091ea', '#00b8d4', '#00bfa5', '#64dd17',
    '#aeea00', '#ffd600', '#ffab00', '#ff6d00',
]


ROLES = [
    ('RD', 'RD'),
    ('FE', 'FE'),
    ('QA', 'QA'),
    ('UI', 'UI'),
    ('PM', 'PM'),
    ('DevOps', 'DevOps'),
]


class Project(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='projects', blank=True)
    name = models.CharField(max_length=200, db_index=True)
    description = models.TextField(blank=True)
    color = models.CharField(max_length=7, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(fields=['owner', 'name'], name='unique_project_per_user'),
        ]

    def save(self, *args, **kwargs):
        if not self.color:
            from .services import ProjectService
            self.color = ProjectService.pick_color()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Holiday(models.Model):
    date = models.DateField(unique=True)
    name = models.CharField(max_length=50)
    is_off_day = models.BooleanField(default=True)

    class Meta:
        ordering = ['date']

    def __str__(self):
        return f'{self.date} {self.name}'


class Assignment(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assignments', blank=True)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='assignments',
        db_index=True,
    )
    role = models.CharField(max_length=50, choices=ROLES, blank=True, db_index=True)
    assignee = models.CharField(max_length=100, blank=True, db_index=True)
    title = models.CharField(max_length=200)
    start_date = models.DateField(db_index=True)
    end_date = models.DateField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['start_date']

    def __str__(self):
        return f'{self.title} ({self.start_date})'
