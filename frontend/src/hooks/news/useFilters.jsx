// hooks/useFilters.js
import {useCallback, useEffect, useMemo, useState} from "react";

function useDebounce(value, delay = 400) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const id = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(id);
  }, [value, delay]);
  return debounced;
}

function getInitialFromLocation() {
  const sp = new URLSearchParams(window.location.search);
  const topic_ids = sp.getAll("topic_ids").map(Number).filter(n => !Number.isNaN(n));

  return {
    topic_ids,
    language: sp.get("language") || null,
    q: sp.get("q") || "",
    since: sp.get("since") || "",
    until: sp.get("until") || "",
    bookmarkOnly: Boolean(Number(sp.get("bookmarkOnly"))),
    max_articles_per_cluster: Number(sp.get("max_articles_per_cluster")) || 10,
    order_in_cluster: sp.get("order_in_cluster") === "date_asc" ? "date_asc" : "date_desc",
    sort: sp.get("sort") === "weight" ? "weight" : "recent",
    limit: (() => {
      const v = Number(sp.get("limit"));
      if (!v) return 20;
      return Math.min(Math.max(v, 1), 100);
    })(),
  };
}

export function useFilters() {
  const initial = useMemo(getInitialFromLocation, []);
  const [topicIds, setTopicIds] = useState(initial.topic_ids);
  const [language, setLanguage] = useState(initial.language);
  const [q, setQ] = useState(initial.q);
  const [since, setSince] = useState(initial.since);
  const [until, setUntil] = useState(initial.until);
  const [maxPerCluster, setMaxPerCluster] = useState(initial.max_articles_per_cluster);
  const [orderInCluster, setOrderInCluster] = useState(initial.order_in_cluster);
  const [sort, setSort] = useState(initial.sort);
  const [limit, setLimit] = useState(initial.limit);
  const [bookmarkOnly, setBookmarkOnly] = useState(initial.bookmarkOnly);

  const qDebounced = useDebounce(q, 500);

  const searchParams = useMemo(() => {
    const sp = new URLSearchParams();

    if (topicIds?.length) for (const id of topicIds) sp.append("topic_ids", String(id));
    if (language) sp.set("language", language);
    if (qDebounced && qDebounced.trim().length >= 2) sp.set("q", qDebounced.trim());
    if (since) sp.set("since", since);
    if (until) sp.set("until", until);

    sp.set("max_articles_per_cluster", String(maxPerCluster));
    sp.set("order_in_cluster", orderInCluster);
    sp.set("sort", sort);
    sp.set("limit", String(limit));
    sp.set("bookmarkOnly", String(Number(bookmarkOnly)))

    return sp;
  }, [topicIds, language, qDebounced, since, until, maxPerCluster, orderInCluster, sort, limit, bookmarkOnly]);

  const filters = useMemo(() => {
    const s = searchParams.toString();
    return s ? `?${s}` : "";
  }, [searchParams]);

  useEffect(() => {
    const url = filters ? `${location.pathname}${filters}` : location.pathname;
    window.history.replaceState(null, "", url);
  }, [filters]);

  const reset = useCallback(() => {
    setTopicIds([]);
    setLanguage(null);
    setQ("");
    setSince("");
    setUntil("");
    setMaxPerCluster(10);
    setOrderInCluster("date_desc");
    setSort("recent");
    setLimit(20);
    setBookmarkOnly(false);
  }, []);

  return {
    filters,
    state: { topicIds, language, q, since, until, orderInCluster, sort, bookmarkOnly },
    set: { setTopicIds, setLanguage, setQ, setSince, setUntil, setOrderInCluster, setSort, setBookmarkOnly },
    reset,
  };
}