from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
DROP FUNCTION IF EXISTS upsert_article_with_cluster;
create function upsert_article_with_cluster(p_source_id integer, p_url text, p_title text, p_published_at timestamp with time zone, p_summary text DEFAULT NULL::text, p_image text DEFAULT NULL::text, p_language text DEFAULT 'russian'::text, p_created_at timestamp with time zone DEFAULT now(), p_recency interval DEFAULT '14 days'::interval, p_w_trgm double precision DEFAULT 0.75, p_w_ft double precision DEFAULT 0.25, p_min_trgm double precision DEFAULT 0.35, p_min_ts double precision DEFAULT 0.05, p_min_score double precision DEFAULT 0.42, p_min_candidates integer DEFAULT 2)
    returns TABLE(out_cluster_id integer, out_article_id integer, out_score double precision, out_matched boolean, out_created_new boolean)
    language plpgsql
as
$$
DECLARE
  v_text       text := coalesce(p_title,'') || ' ' || coalesce(p_summary,'');
  v_best_id    integer;
  v_best_scr   double precision;
  v_new_clid   integer;
  v_art_id     integer;
  v_matched    boolean := false;
  v_created    boolean := false;
  v_cand_count integer := 0;
BEGIN
  -- снизим порог похожести для similarity()
  PERFORM set_config('pg_trgm.similarity_threshold','0.25', true);

  WITH cand AS (
    SELECT
      n.cluster_id::integer AS cl_id,
      GREATEST(
        similarity(n.title, p_title),
        similarity(n.summary, p_summary)
      ) AS s_trgm,
      ts_rank_cd(
        to_tsvector(p_language::regconfig, coalesce(n.title,'') || ' ' || coalesce(n.summary,'')),
        plainto_tsquery(p_language::regconfig, v_text)
      ) AS s_ts_raw
    FROM article n
    WHERE n.created_at >= p_created_at - p_recency
  ),
  agg AS (
    SELECT cl_id, MAX(s_trgm) AS s_trgm, MAX(s_ts_raw) AS s_ts_raw
    FROM cand
    GROUP BY cl_id
  ),
  stats AS (
    SELECT
      COUNT(*) AS cand_count,
      MAX(s_ts_raw) AS max_ts
    FROM agg
  ),
  norm AS (
    SELECT
      a.cl_id,
      a.s_trgm,
      a.s_ts_raw,
      s.cand_count,
      CASE
        WHEN s.cand_count >= p_min_candidates AND s.max_ts > 0
          THEN a.s_ts_raw / s.max_ts     -- нормализуем только если кандидатов >= 2
        ELSE 0
      END AS s_ts_norm
    FROM agg a CROSS JOIN stats s
  ),
  filtered AS (                     -- отбрасываем заведомо слабые матчи
    SELECT *
    FROM norm
    WHERE (s_trgm >= p_min_trgm OR s_ts_raw >= p_min_ts)
  ),
  scored AS (
    SELECT
      cl_id,
      (p_w_trgm * s_trgm + p_w_ft * s_ts_norm) AS score
    FROM filtered
  )
  SELECT
    (SELECT cand_count FROM (SELECT DISTINCT cand_count FROM norm) AS t LIMIT 1),
    cl_id, score
  INTO v_cand_count, v_best_id, v_best_scr
  FROM scored
  ORDER BY score DESC
  LIMIT 1;

  -- выбрать кластер или создать новый
  IF v_best_id IS NULL OR v_best_scr IS NULL OR v_best_scr < p_min_score THEN
    INSERT INTO cluster (first_published_at, language, weight)
    VALUES (COALESCE(p_published_at, p_created_at), p_language, 0)
    RETURNING id INTO v_new_clid;
    v_matched := false;
    v_created := true;
  ELSE
    v_new_clid := v_best_id;
    v_matched := true;
    v_created := false;
  END IF;

  -- вставка/апдейт статьи
  INSERT INTO article (source_id, cluster_id, url, image, title, summary, published_at)
  VALUES (p_source_id, v_new_clid, p_url, p_image, p_title, p_summary, p_published_at)
  ON CONFLICT (source_id, url) DO UPDATE
    SET cluster_id   = EXCLUDED.cluster_id,
        image        = COALESCE(EXCLUDED.image, article.image),
        title        = EXCLUDED.title,
        summary      = EXCLUDED.summary,
        published_at = EXCLUDED.published_at
  RETURNING id INTO v_art_id;

  RETURN QUERY
  SELECT
    v_new_clid::integer,
    v_art_id::integer,
    COALESCE(v_best_scr, 0)::double precision,
    v_matched,
    v_created;
END
$$;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
DROP FUNCTION IF EXISTS upsert_article_with_cluster;
CREATE OR REPLACE FUNCTION upsert_article_with_cluster(
    p_source_id     integer,
    p_url           text,
    p_title         text,
    p_published_at  timestamptz,
    p_summary       text DEFAULT NULL,
    p_image         text DEFAULT NULL,
    p_language      text DEFAULT 'auto',

    -- подбор кластера
    p_created_at    timestamptz DEFAULT now(),
    p_recency       interval    DEFAULT '14 days',
    p_w_trgm        double precision DEFAULT 0.75,
    p_w_ft          double precision DEFAULT 0.25,

    -- пороги и анти-залипание
    p_min_trgm      double precision DEFAULT 0.35,  -- абсолютный минимум для trigram
    p_min_ts        double precision DEFAULT 0.05,  -- абсолютный минимум для ts_rank_cd
    p_min_score     double precision DEFAULT 0.42,  -- общий порог решения
    p_min_candidates integer        DEFAULT 2       -- включать ts-нормализацию только когда >=2 кандидатов
)
RETURNS TABLE (
    out_cluster_id  integer,
    out_article_id  integer,
    out_score       double precision,
    out_matched     boolean,
    out_created_new boolean
)
LANGUAGE plpgsql
AS $$
DECLARE
  v_text       text := coalesce(p_title,'') || ' ' || coalesce(p_summary,'');
  v_best_id    integer;
  v_best_scr   double precision;
  v_new_clid   integer;
  v_art_id     integer;
  v_matched    boolean := false;
  v_created    boolean := false;
  v_cand_count integer := 0;
BEGIN
  -- снизим порог похожести для similarity()
  PERFORM set_config('pg_trgm.similarity_threshold','0.25', true);

  WITH cand AS (
    SELECT
      n.cluster_id::integer AS cl_id,
      GREATEST(
        similarity(n.title, p_title),
        similarity(n.summary, p_summary)
      ) AS s_trgm,
      ts_rank_cd(
        to_tsvector('russian', coalesce(n.title,'') || ' ' || coalesce(n.summary,'')),
        plainto_tsquery('russian', v_text)
      ) AS s_ts_raw
    FROM article n
    WHERE n.created_at >= p_created_at - p_recency
  ),
  agg AS (
    SELECT cl_id, MAX(s_trgm) AS s_trgm, MAX(s_ts_raw) AS s_ts_raw
    FROM cand
    GROUP BY cl_id
  ),
  stats AS (
    SELECT
      COUNT(*) AS cand_count,
      MAX(s_ts_raw) AS max_ts
    FROM agg
  ),
  norm AS (
    SELECT
      a.cl_id,
      a.s_trgm,
      a.s_ts_raw,
      s.cand_count,
      CASE
        WHEN s.cand_count >= p_min_candidates AND s.max_ts > 0
          THEN a.s_ts_raw / s.max_ts     -- нормализуем только если кандидатов >= 2
        ELSE 0
      END AS s_ts_norm
    FROM agg a CROSS JOIN stats s
  ),
  filtered AS (                     -- отбрасываем заведомо слабые матчи
    SELECT *
    FROM norm
    WHERE (s_trgm >= p_min_trgm OR s_ts_raw >= p_min_ts)
  ),
  scored AS (
    SELECT
      cl_id,
      (p_w_trgm * s_trgm + p_w_ft * s_ts_norm) AS score
    FROM filtered
  )
  SELECT
    (SELECT cand_count FROM (SELECT DISTINCT cand_count FROM norm) AS t LIMIT 1),
    cl_id, score
  INTO v_cand_count, v_best_id, v_best_scr
  FROM scored
  ORDER BY score DESC
  LIMIT 1;

  -- выбрать кластер или создать новый
  IF v_best_id IS NULL OR v_best_scr IS NULL OR v_best_scr < p_min_score THEN
    INSERT INTO cluster (first_published_at, language, weight)
    VALUES (COALESCE(p_published_at, p_created_at), p_language, 0)
    RETURNING id INTO v_new_clid;
    v_matched := false;
    v_created := true;
  ELSE
    v_new_clid := v_best_id;
    v_matched := true;
    v_created := false;
  END IF;

  -- вставка/апдейт статьи
  INSERT INTO article (source_id, cluster_id, url, image, title, summary, published_at, language)
  VALUES (p_source_id, v_new_clid, p_url, p_image, p_title, p_summary, p_published_at, p_language)
  ON CONFLICT (source_id, url) DO UPDATE
    SET cluster_id   = EXCLUDED.cluster_id,
        image        = COALESCE(EXCLUDED.image, article.image),
        title        = EXCLUDED.title,
        summary      = EXCLUDED.summary,
        published_at = EXCLUDED.published_at,
        language     = EXCLUDED.language
  RETURNING id INTO v_art_id;

  RETURN QUERY
  SELECT
    v_new_clid::integer,
    v_art_id::integer,
    COALESCE(v_best_scr, 0)::double precision,
    v_matched,
    v_created;
END
$$;
"""

