import React, { useMemo, useState } from "react";


export default function PrettyImage({
  src,
  alt = "",
  caption,
  className = "",
  ratio = 16 / 9, // число: ширина/высота. Пример: 1 (квадрат), 4/3, 21/9
  fit = "cover", // 'cover' | 'contain'
  radius = "2xl", // 'none' | 'sm' | 'md' | 'lg' | 'xl' | '2xl' | '3xl' | 'full'
  shadow = true,
  bordered = false,
  zoomOnHover = true,
  lightbox = false,
  overlayGradient = true,
  loading = "lazy", // 'lazy' | 'eager'
  blurUp = true,
  badge,
}) {
  const [loaded, setLoaded] = useState(false);
  const [failed, setFailed] = useState(false);
  const [open, setOpen] = useState(false);

  const radiusClass = useMemo(() => {
    const map = {
      none: "rounded-none",
      sm: "rounded-sm",
      md: "rounded-md",
      lg: "rounded-lg",
      xl: "rounded-xl",
      "2xl": "rounded-2xl",
      "3xl": "rounded-3xl",
      full: "rounded-full",
    };
    return map[radius] ?? "rounded-2xl";
  }, [radius]);

  const wrapperClasses = [
    "group relative overflow-hidden",
    radiusClass,
    shadow ? "shadow-lg dark:shadow-black/40" : "",
    bordered ? "ring-1 ring-black/10 dark:ring-white/10" : "",
    className,
  ]
    .filter(Boolean)
    .join(" ");

  // Паддинг для сохранения аспекта до загрузки
  const padTop = useMemo(() => `${100 / ratio}%`, [ratio]);

  const imgClasses = [
    "absolute inset-0 h-full w-full object-" + fit,
    "transition-transform duration-500",
    zoomOnHover ? "group-hover:scale-[1.04] group-hover:rotate-[0.15deg]" : "",
    blurUp && !loaded ? "scale-[1.02] blur-sm brightness-90" : "",
    "opacity-0",
    loaded ? "opacity-100 transition-opacity duration-300" : "",
  ]
    .filter(Boolean)
    .join(" ");

  const showLightbox = lightbox && !failed;

  return (
    <figure className={wrapperClasses} style={{ paddingTop: padTop }}>
      {/* Скелетон */}
      {!loaded && !failed && (
        <div className="absolute inset-0 animate-pulse bg-neutral-200 dark:bg-neutral-800" />
      )}

      {/* Бейдж в углу (опция) */}
      {badge && (
        <span className="absolute left-3 top-3 z-20 select-none rounded-full bg-black/70 px-2 py-1 text-xs font-medium text-white backdrop-blur-md dark:bg-white/15">
          {badge}
        </span>
      )}

      {/* Само изображение */}
      {!failed ? (
        <img
          src={src}
          alt={alt}
          loading={loading}
          className={imgClasses}
          onLoad={() => setLoaded(true)}
          onError={() => setFailed(true)}
          style={{ willChange: zoomOnHover ? "transform" : undefined }}
          onClick={() => (showLightbox ? setOpen(true) : null)}
        />
      ) : (
        <Fallback alt={alt} />
      )}

      {/* Подпись с градиентом */}
      {caption && (
        <figcaption className="pointer-events-none absolute inset-x-0 bottom-0 z-10">
          <div
            className={[
              overlayGradient ? "bg-gradient-to-t from-black/70 via-black/10 to-transparent" : "",
              "p-3 text-sm text-white drop-shadow-md",
            ]
              .filter(Boolean)
              .join(" ")}
          >
            <span className="select-text">{caption}</span>
          </div>
        </figcaption>
      )}

      {/* Лайтбокс */}
      {showLightbox && open && (
        <Lightbox src={src} alt={alt} onClose={() => setOpen(false)} />)
      }
    </figure>
  );
}

function Lightbox({ src, alt, onClose }) {
  return (
    <div
      className="fixed inset-0 z-[999] flex items-center justify-center bg-black/80 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      onClick={onClose}
      onKeyDown={(e) => e.key === "Escape" && onClose()}
      tabIndex={-1}
    >
      <button
        className="absolute right-4 top-4 rounded-full bg-white/10 px-3 py-1 text-white backdrop-blur-md hover:bg-white/20 focus:outline-none"
        onClick={(e) => {
          e.stopPropagation();
          onClose();
        }}
      >
        ✕
      </button>
      <img
        src={src}
        alt={alt}
        className="max-h-[90vh] max-w-[92vw] select-none rounded-xl object-contain shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      />
    </div>
  );
}

function Fallback({ alt }) {
  return (
    <div className="absolute inset-0 grid place-items-center bg-neutral-100 text-neutral-500 dark:bg-neutral-900 dark:text-neutral-400">
      <div className="flex items-center gap-3">
        <svg
          width="28"
          height="28"
          viewBox="0 0 24 24"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          aria-hidden
        >
          <path
            d="M3 5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5Z"
            className="stroke-current"
            strokeWidth="1.5"
          />
          <path
            d="M21 14l-3.5-3.5a2 2 0 0 0-2.83 0L7 18"
            className="stroke-current"
            strokeWidth="1.5"
          />
          <circle cx="9" cy="9" r="1.5" className="fill-current" />
        </svg>
        <span className="text-sm">Не удалось загрузить изображение{alt ? `: ${alt}` : ""}</span>
      </div>
    </div>
  );
}
