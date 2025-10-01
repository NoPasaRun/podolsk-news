from enum import StrEnum


class SourceKind(StrEnum):
    RSS = "rss"
    HTML = "html"
    JSONFEED = "jsonfeed"
    TELEGRAM = "telegram"


class SourceStatus(StrEnum):
    ACTIVE = "active"
    VALIDATING = "validating"
    ERROR = "error"


class Language(StrEnum):
    AUTO = "auto"
    RU = "ru"
    EN = "en"
    DE = "de"


class TopicKind(StrEnum):
    POLITICS = "politics"
    BUSINESS = "business"
    TECH = "tech"
    SCIENCE = "science"
    HEALTH = "health"
    SPORTS = "sports"
    ENTERTAINMENT = "entertainment"
    WORLD = "world"
    CULTURE = "culture"
    EDUCATION = "education"
    TRAVEL = "travel"
    AUTO = "auto"
    FINANCE = "finance"
    REAL_ESTATE = "real_estate"
    CRIME = "crime"
    WAR = "war"
    LOCALE = "local"


__all__ = ["SourceKind", "SourceStatus", "RawContentType", "Language", "TopicKind"]