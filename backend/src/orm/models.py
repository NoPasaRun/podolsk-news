from datetime import datetime, timezone

from tortoise import fields
from tortoise.indexes import Index
from tortoise.models import Model

from settings import settings
from utils.enums import SourceKind, SourceStatus, Language, TopicKind


class User(Model):
    id = fields.IntField(pk=True)
    phone = fields.CharField(max_length=32, unique=True, null=True)
    phone_verified_at = fields.DatetimeField(null=True)
    name = fields.CharField(max_length=255, null=True)
    avatar = fields.CharField(max_length=512, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    async def source_ids(self):
        return [r.source_id for r in await UserSource.filter(user_id=self.id).all()]


class PhoneOTP(Model):
    id = fields.IntField(pk=True)
    phone = fields.CharField(max_length=32, index=True)
    code_hash = fields.CharField(max_length=128)
    expires_at = fields.DatetimeField()
    attempts = fields.IntField(default=0)
    last_sent_at: datetime = fields.DatetimeField(null=True)

    @property
    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) > self.expires_at

    @property
    def can_resend(self) -> bool:
        if not self.last_sent_at:
            return True
        delta = (datetime.now(timezone.utc) - self.last_sent_at).total_seconds()
        return delta >= settings.otp.resend_sec

    class Meta:
        table = "phone_otps"
        indexes = (("phone",),)


class Source(Model):
    """
    kind задаёт тип источника (rss/html/jsonfeed/telegram).
    parser_profile выбирает стратегию парсинга.
    parse_overrides — ручные селекторы/правила для конкретного домена.
    """
    id = fields.IntField(pk=True)
    kind = fields.CharEnumField(SourceKind, max_length=16)
    domain = fields.TextField()
    status = fields.CharEnumField(SourceStatus, max_length=16, default=SourceStatus.VALIDATING)
    is_default = fields.BooleanField(default=False)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        unique_together = (("kind", "domain"),)


class UserSource(Model):
    """
    Подключение источника пользователем.
    rank — приоритет этого источника.
    """
    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField("models.User", related_name="user_sources", on_delete=fields.CASCADE)
    source = fields.ForeignKeyField("models.Source", related_name="user_sources", on_delete=fields.CASCADE)
    poll_interval_sec = fields.IntField(default=900)
    rank = fields.IntField(default=0)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        unique_together = (("user", "source"),)


class Cluster(Model):
    """
    Инфоповод = группа похожих статей.
    summary — краткий анонс/описание.
    weight — «популярность» (кол-во источников, свежесть, клики).
    """
    id = fields.IntField(pk=True)
    title = fields.TextField()
    summary = fields.TextField(null=True)
    top_image = fields.TextField(null=True)
    first_published_at = fields.DatetimeField(index=True)
    last_updated_at = fields.DatetimeField(auto_now=True, index=True)
    language = fields.CharEnumField(Language, max_length=8, default=Language.AUTO)
    weight = fields.IntField(default=0)

    class Meta:
        indexes = [
            Index(fields=("first_published_at",)),
            Index(fields=("last_updated_at",)),
            Index(fields=("weight",)),
        ]


class Article(Model):
    """
    Нормализованный документ для выдачи.
    content_html — очищенный текст/HTML.
    content_fingerprint — simhash/minhash для дедупа.
    """
    id = fields.IntField(pk=True)
    source = fields.ForeignKeyField("models.Source", related_name="articles", on_delete=fields.CASCADE)
    cluster = fields.ForeignKeyField("models.Cluster", related_name="articles", on_delete=fields.CASCADE)
    url = fields.TextField()
    title = fields.TextField()
    summary = fields.TextField(null=True)
    published_at = fields.DatetimeField(index=True)
    language = fields.CharEnumField(Language, max_length=8, default=Language.AUTO)
    content_fingerprint = fields.CharField(max_length=64, null=True, index=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        indexes = [
            Index(fields=("cluster_id", "published_at")),
            Index(fields=("source_id", "published_at"))
        ]
        unique_together = (("source", "url"),)


class UserArticleState(Model):
    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField("models.User", related_name="article_states", on_delete=fields.CASCADE)
    cluster = fields.ForeignKeyField("models.Cluster", related_name="user_states", on_delete=fields.CASCADE)
    read = fields.BooleanField(default=False)
    bookmarked = fields.BooleanField(default=False)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        unique_together = (("user", "cluster"),)


class Topic(Model):
    id = fields.IntField(pk=True)
    code = fields.CharEnumField(TopicKind, max_length=32, unique=True)
    title = fields.CharField(max_length=128)
    created_at = fields.DatetimeField(auto_now_add=True)


class ClusterTopic(Model):
    """M2M с весом/уверенностью классификатора"""
    id = fields.IntField(pk=True)
    cluster = fields.ForeignKeyField("models.Cluster", related_name="cluster_topics", on_delete=fields.CASCADE)
    topic = fields.ForeignKeyField("models.Topic", related_name="cluster_topics", on_delete=fields.CASCADE)
    score = fields.FloatField(default=0.0)
    primary = fields.BooleanField(default=False)

    class Meta:
        unique_together = (("cluster", "topic"),)


class UserTopicPref(Model):
    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField("models.User", related_name="topic_prefs", on_delete=fields.CASCADE)
    topic = fields.ForeignKeyField("models.Topic", related_name="user_prefs", on_delete=fields.CASCADE)
    weight = fields.IntField(default=0)

    class Meta:
        unique_together = (("user","topic"),)
