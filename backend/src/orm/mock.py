import asyncio
import random
from datetime import datetime, timedelta, timezone
from typing import List, Dict

from tortoise import Tortoise
from tortoise.exceptions import IntegrityError
from tortoise.transactions import in_transaction

from orm.models import (
    User, Source, UserSource, RowData, Cluster, Article,
    UserArticleState, Topic, ClusterTopic, UserTopicPref,
    SourceKind, SourceStatus, RawContentType, Language, TopicKind
)
from orm.db import init_db

DEFAULT_SOURCES = [
    # kind, domain, status, parser_profile
    (SourceKind.RSS,  "www.reuters.com",   SourceStatus.ACTIVE,     "generic_rss"),
    (SourceKind.RSS,  "www.bbc.com",       SourceStatus.ACTIVE,     "generic_rss"),
    (SourceKind.RSS,  "habr.com",          SourceStatus.ACTIVE,     "generic_rss"),
    (SourceKind.TELEGRAM, "www.rbc.ru",        SourceStatus.VALIDATING, "rbc_html"),
    (SourceKind.RSS,  "www.theverge.com",  SourceStatus.ACTIVE,     "generic_rss"),
    (SourceKind.JSONFEED, "api.meduza.io", SourceStatus.ACTIVE,     "jsonfeed_default"),
]

RANDOM_TITLES = [
    "ИИ меняет индустрию", "Рынки растут на фоне отчётов", "Исследователи представили новый метод",
    "Крупная сделка на технологическом рынке", "Учёные улучшили точность модели", "Проблемы цепочек поставок"
]

RANDOM_SUMM = [
    "Короткое резюме событий дня.", "Подробности в материале по ссылке.",
    "Аналитики ожидают продолжения тренда.", "Эксперты призвали к осторожности."
]

# ----------------- УТИЛИТЫ -----------------
def utc_now() -> datetime:
    return datetime.now(timezone.utc)

def rand_dt_within(days: int = 7) -> datetime:
    return utc_now() - timedelta(days=random.randint(0, days),
                                 hours=random.randint(0, 23),
                                 minutes=random.randint(0, 59))

def pick_topics(n: int) -> List[TopicKind]:
    all_topics = list(TopicKind)
    random.shuffle(all_topics)
    return all_topics[:n]


async def seed_topics() -> Dict[TopicKind, int]:
    print("→ Topics …")
    ids: Dict[TopicKind, int] = {}
    for tk in TopicKind:
        topic, _ = await Topic.get_or_create(code=tk, defaults={"title": tk.value.capitalize()})
        ids[tk] = topic.id
    return ids

async def seed_sources() -> Dict[str, int]:
    print("→ Sources …")
    ids: Dict[str, int] = {}
    for kind, domain, status, profile in DEFAULT_SOURCES:
        src, _ = await Source.get_or_create(
            kind=kind, domain=domain,
            defaults={
                "status": status,
                "parser_profile": profile,
                "parse_overrides": None
            }
        )
        ids[domain] = src.id
    return ids

async def seed_user(phone: str) -> int:
    print("→ User …")
    user, _ = await User.get_or_create(phone=phone, defaults={"name": "Test User"})
    return user.id

async def seed_user_sources(user_id: int, source_ids: List[int]):
    print("→ UserSource …")
    objs = []
    rank = 0
    for sid in source_ids:
        objs.append(UserSource(user_id=user_id, source_id=sid, is_enabled=True, poll_interval_sec=900, rank=rank))
        rank += 1
    try:
        await UserSource.bulk_create(objs, ignore_conflicts=True)
    except IntegrityError:
        pass

async def seed_clusters(n_clusters: int) -> List[int]:
    print(f"→ Clusters x{n_clusters} …")
    cluster_ids: List[int] = []
    for i in range(n_clusters):
        title = f"{random.choice(RANDOM_TITLES)} #{i+1}"
        cl = await Cluster.create(
            title=title,
            summary=random.choice(RANDOM_SUMM),
            top_image=None,
            first_published_at=rand_dt_within(5),
            language=Language.RU,
            weight=random.randint(1, 100)
        )
        cluster_ids.append(cl.id)
    return cluster_ids

async def seed_articles_for_sources(
    source_ids: Dict[str, int],
    cluster_ids: List[int],
    per_source: int
) -> List[int]:
    print(f"→ Articles (≈{per_source} на источник) …")
    article_ids: List[int] = []
    for domain, sid in source_ids.items():
        for i in range(per_source):
            # распределяем кластеры равномерно
            cluster_id = cluster_ids[(i + sid) % len(cluster_ids)]
            title = f"{random.choice(RANDOM_TITLES)} — {domain} — {i+1}"
            url = f"https://{domain}/news/{sid}/{i+1}"
            try:
                art, created = await Article.get_or_create(
                    source_id=sid,
                    url=url,
                    defaults={
                        "cluster_id": cluster_id,
                        "url_canon": url,
                        "title": title,
                        "summary": random.choice(RANDOM_SUMM),
                        "content_html": "<p>Demo content</p>",
                        "published_at": rand_dt_within(3),
                        "language": Language.RU,
                        "content_fingerprint": None
                    }
                )
                article_ids.append(art.id)
            except IntegrityError:
                # уникальный (source, url) уже есть
                pass
    return article_ids

async def seed_rowdata_for_articles():
    print("→ RowData (сэмплы) …")
    # Берем последние 50 статей и добавляем по ним один снапшот
    arts = await Article.all().order_by("-id").limit(50)
    objs = []
    for a in arts:
        objs.append(RowData(
            source_id=a.source_id,
            url_original=a.url,
            url_canon=a.url_canon,
            raw_content="<html><body>cached snapshot</body></html>",
            raw_content_type=RawContentType.HTML,
            raw_hash=f"hash:{a.source_id}:{a.id}",
        ))
    if objs:
        try:
            await RowData.bulk_create(objs, ignore_conflicts=True)
        except IntegrityError:
            pass

async def seed_cluster_topics(cluster_ids: List[int], topic_map: Dict[TopicKind, int]):
    print("→ ClusterTopic …")
    topics = list(topic_map.items())
    objs = []
    for cid in cluster_ids:
        # 1–2 темы на кластер
        picks = random.sample(topics, k=min(2, len(topics)))
        for idx, (tk, tid) in enumerate(picks):
            objs.append(ClusterTopic(cluster_id=cid, topic_id=tid, score=0.6 - idx * 0.1, primary=(idx == 0)))
    if objs:
        try:
            await ClusterTopic.bulk_create(objs, ignore_conflicts=True)
        except IntegrityError:
            pass

async def seed_user_prefs(user_id: int, topic_map: Dict[TopicKind, int], source_ids: Dict[str, int]):
    print("→ User prefs (topics & sources) …")
    # Темы — выберем 4
    chosen_topics = pick_topics(4)
    topic_objs = [UserTopicPref(user_id=user_id, topic_id=topic_map[tk], weight=random.randint(1, 5))
                  for tk in chosen_topics]
    try:
        await UserTopicPref.bulk_create(topic_objs, ignore_conflicts=True)
    except IntegrityError:
        pass

    # Источники — первые 3
    src_ids = list(source_ids.values())[:3]
    await seed_user_sources(user_id, src_ids)

async def seed_user_article_states(user_id: int):
    print("→ UserArticleState (прочитано/в закладках) …")
    # Берём 10 последних кластеров — 5 прочитано, 3 в закладках
    clusters = await Cluster.all().order_by("-first_published_at").limit(10)
    objs = []
    for i, cl in enumerate(clusters):
        read = i < 5
        bookmarked = i in (1, 4, 7)
        objs.append(UserArticleState(user_id=user_id, cluster_id=cl.id, read=read, bookmarked=bookmarked))
    if objs:
        try:
            await UserArticleState.bulk_create(objs, ignore_conflicts=True)
        except IntegrityError:
            pass

# ----------------- ГЛАВНАЯ ПРОЦЕДУРА -----------------
async def main():
    import argparse
    parser = argparse.ArgumentParser(description="Seed DB for news project (Tortoise ORM).")
    parser.add_argument("--user-phone", default="+70000000000", help="Телефон тестового пользователя")
    parser.add_argument("--clusters", type=int, default=12, help="Сколько создать кластеров")
    parser.add_argument("--articles-per-source", type=int, default=8, help="Сколько статей на источник создать")
    args = parser.parse_args()

    await init_db(generate_schemas=False)
    try:
        async with in_transaction():
            topic_map = await seed_topics()
            source_ids = await seed_sources()
            user_id = await seed_user(args.user_phone)

            cluster_ids = await seed_clusters(args.clusters)
            await seed_cluster_topics(cluster_ids, topic_map)

            await seed_articles_for_sources(source_ids, cluster_ids, args.articles_per_source)
            await seed_rowdata_for_articles()

            await seed_user_prefs(user_id, topic_map, source_ids)
            await seed_user_article_states(user_id)

        print("✅ Seed OK")
    finally:
        await Tortoise.close_connections()

if __name__ == "__main__":
    asyncio.run(main())
