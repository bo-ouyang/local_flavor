from django.db import models


class LocalUser(models.Model):
    openid = models.CharField(max_length=64, unique=True, db_index=True)
    phone = models.CharField(max_length=20, unique=True, null=True, blank=True, db_index=True)
    password_hash = models.CharField(max_length=128, null=True, blank=True)
    nickname = models.CharField(max_length=64, null=True, blank=True)
    avatar = models.CharField(max_length=255, null=True, blank=True)
    is_verified = models.BooleanField(default=False)

    region_code = models.CharField(max_length=20, null=True, blank=True, db_index=True)
    province = models.CharField(max_length=64, null=True, blank=True)
    city = models.CharField(max_length=64, null=True, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    last_region_update = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "users"
        indexes = [
            models.Index(fields=["province", "city"]),
            models.Index(fields=["created_at"]),
        ]

    @property
    def is_authenticated(self):
        """Allow LocalUser to participate in DRF authentication and throttling."""
        return True

    @property
    def is_anonymous(self):
        return False


class AuthSession(models.Model):
    user = models.ForeignKey(
        LocalUser,
        on_delete=models.CASCADE,
        related_name="auth_sessions",
    )
    access_token_hash = models.CharField(max_length=64, unique=True)
    access_expires_at = models.DateTimeField(db_index=True)
    refresh_expires_at = models.DateTimeField(db_index=True)
    revoked_at = models.DateTimeField(null=True, blank=True, db_index=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    device_label = models.CharField(max_length=120, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "auth_sessions"
        indexes = [
            models.Index(fields=["user", "revoked_at", "-created_at"]),
        ]


class AuthRefreshToken(models.Model):
    session = models.ForeignKey(
        AuthSession,
        on_delete=models.CASCADE,
        related_name="refresh_credentials",
    )
    token_hash = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField(db_index=True)
    used_at = models.DateTimeField(null=True, blank=True, db_index=True)
    successor = models.OneToOneField(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="predecessor",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "auth_refresh_tokens"
        indexes = [
            models.Index(fields=["session", "used_at", "-created_at"]),
        ]


class Region(models.Model):
    code = models.CharField(max_length=20, unique=True, db_index=True)
    name = models.CharField(max_length=64, db_index=True)
    level = models.IntegerField()
    parent = models.ForeignKey(
        "self",
        to_field="code",
        db_column="parent_code",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="children",
    )

    class Meta:
        db_table = "regions"
        indexes = [
            models.Index(fields=["parent", "level"]),
        ]


class UserPreferenceSnapshot(models.Model):
    user = models.OneToOneField(LocalUser, on_delete=models.CASCADE, related_name="preference_snapshot")
    flavor_vector = models.JSONField(default=list)
    category_weights = models.JSONField(default=dict)
    region_weights = models.JSONField(default=dict)
    exchange_completed_count = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_preference_snapshots"
