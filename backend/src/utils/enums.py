from enum import Enum


class Provider(str, Enum):
    GITHUB = "github"
    GOOGLE = "google"
    VK = "vk"
    TELEGRAM = "telegram"

__all__ = ["Provider"]