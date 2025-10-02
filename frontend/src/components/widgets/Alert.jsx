import {useRef, useEffect} from "react";
import { AnimatePresence, motion } from "framer-motion";


const tone = (variant = "default") => {
  switch (variant) {
    case "info":
      return {
        panel: "bg-white dark:bg-neutral-900 border-black/5 dark:border-white/10",
        title: "text-gray-900 dark:text-gray-100",
        desc: "text-gray-600 dark:text-gray-300",
        iconWrap: "bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300",
        ghostBtn:
          "border-gray-200 bg-white text-gray-700 hover:bg-gray-50 dark:border-neutral-700 dark:bg-neutral-900 dark:text-neutral-200 dark:hover:bg-neutral-800",
        primaryBtn:
          "bg-blue-600 text-white hover:bg-blue-500 focus-visible:ring-2 focus-visible:ring-blue-300 dark:focus-visible:ring-blue-600",
      };
    case "success":
      return {
        panel: "bg-white dark:bg-neutral-900 border-black/5 dark:border-white/10",
        title: "text-gray-900 dark:text-gray-100",
        desc: "text-gray-600 dark:text-gray-300",
        iconWrap: "bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300",
        ghostBtn:
          "border-gray-200 bg-white text-gray-700 hover:bg-gray-50 dark:border-neutral-700 dark:bg-neutral-900 dark:text-neutral-200 dark:hover:bg-neutral-800",
        primaryBtn:
          "bg-green-600 text-white hover:bg-green-500 focus-visible:ring-2 focus-visible:ring-green-300 dark:focus-visible:ring-green-600",
      };
    case "warning":
      return {
        panel: "bg-white dark:bg-neutral-900 border-black/5 dark:border-white/10",
        title: "text-gray-900 dark:text-gray-100",
        desc: "text-gray-600 dark:text-gray-300",
        iconWrap: "bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300",
        ghostBtn:
          "border-gray-200 bg-white text-gray-700 hover:bg-gray-50 dark:border-neutral-700 dark:bg-neutral-900 dark:text-neutral-200 dark:hover:bg-neutral-800",
        primaryBtn:
          "bg-amber-600 text-white hover:bg-amber-500 focus-visible:ring-2 focus-visible:ring-amber-300 dark:focus-visible:ring-amber-600",
      };
    case "destructive":
      return {
        panel: "bg-white dark:bg-neutral-900 border-black/5 dark:border-white/10",
        title: "text-gray-900 dark:text-gray-100",
        desc: "text-gray-600 dark:text-gray-300",
        iconWrap: "bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300",
        ghostBtn:
          "border-gray-200 bg-white text-gray-700 hover:bg-gray-50 dark:border-neutral-700 dark:bg-neutral-900 dark:text-neutral-200 dark:hover:bg-neutral-800",
        primaryBtn:
          "bg-red-600 text-white hover:bg-red-500 focus-visible:ring-2 focus-visible:ring-red-300 dark:focus-visible:ring-red-600",
      };
    default:
      return {
        panel: "bg-white dark:bg-neutral-900 border-black/5 dark:border-white/10",
        title: "text-gray-900 dark:text-gray-100",
        desc: "text-gray-600 dark:text-gray-300",
        iconWrap: "bg-gray-100 dark:bg-neutral-800 text-gray-700 dark:text-neutral-200",
        ghostBtn:
          "border-gray-200 bg-gray-50 text-gray-700 hover:bg-gray-100 dark:border-neutral-700 dark:bg-neutral-800 dark:text-neutral-200 dark:hover:bg-neutral-700",
        primaryBtn:
          "bg-gray-900 text-white hover:bg-black focus-visible:ring-2 focus-visible:ring-gray-300 dark:bg-white dark:text-black dark:hover:bg-neutral-200 dark:focus-visible:ring-neutral-600",
      };
  }
};

export default function Alert({
  open,
  onClose,
  title,
  description,
  icon,
  actions,
  closeOnOverlay = true,
  className = "",
  variant = "default",
}) {
  const panelRef = useRef(null);
  const t = tone(variant);

  // Close on Escape
  useEffect(() => {
    if (!open) return;
    const onKey = (e) => {
      if (e.key === "Escape") {
        e.preventDefault();
        onClose?.();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  // Lock page scroll while open
  useEffect(() => {
    if (!open) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prev;
    };
  }, [open]);

  // Focus first focusable inside on open
  useEffect(() => {
    if (!open) return;
    const id = window.setTimeout(() => {
      const first = panelRef.current?.querySelector(
        "button, [href], input, select, textarea, [tabindex]:not([tabindex='-1'])"
      );
      first?.focus();
    }, 10);
    return () => window.clearTimeout(id);
  }, [open]);

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          key="overlay"
          aria-hidden={!open}
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        >
          {/* Overlay */}
          <div
            className="absolute inset-0 bg-black/50 dark:bg-black/60 backdrop-blur-sm"
            onClick={() => {
              if (closeOnOverlay) onClose?.();
            }}
          />

          {/* Panel */}
          <motion.div
            role="alertdialog"
            aria-modal="true"
            aria-labelledby={title ? "alert-title" : undefined}
            aria-describedby={description ? "alert-desc" : undefined}
            ref={panelRef}
            tabIndex={-1}
            className={
              "relative z-10 w-full max-w-md rounded-2xl border p-5 shadow-2xl outline-none " +
              t.panel +
              (className ? ` ${className}` : "")
            }
            initial={{ y: 8, opacity: 0, scale: 0.98 }}
            animate={{ y: 0, opacity: 1, scale: 1 }}
            exit={{ y: 8, opacity: 0, scale: 0.98 }}
            transition={{ type: "spring", stiffness: 400, damping: 30, mass: 0.5 }}
          >
            <div className="flex items-start gap-3">
              {(icon || variant !== "default") && (
                <div className={"mt-1 flex h-10 w-10 items-center justify-center rounded-xl " + t.iconWrap}>
                  {icon ?? (
                    // Default icon per variant
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="h-6 w-6" aria-hidden>
                      {variant === "destructive" ? (
                        <path fillRule="evenodd" d="M12 2.25a9.75 9.75 0 1 0 0 19.5 9.75 9.75 0 0 0 0-19.5Zm.75 5.25a.75.75 0 0 0-1.5 0v6a.75.75 0 0 0 1.5 0v-6Zm0 9a.75.75 0 1 0-1.5 0 .75.75 0 0 0 1.5 0Z" clipRule="evenodd" />
                      ) : variant === "warning" ? (
                        <path fillRule="evenodd" d="M10.883 1.142a1.5 1.5 0 0 1 2.234 0l9.5 10.5A1.5 1.5 0 0 1 21.5 14H2.5a1.5 1.5 0 0 1-1.117-2.358l9.5-10.5Z" clipRule="evenodd" />
                      ) : variant === "success" ? (
                        <path fillRule="evenodd" d="M12 2.25a9.75 9.75 0 1 0 0 19.5 9.75 9.75 0 0 0 0-19.5Zm4.28 7.97a.75.75 0 0 0-1.06-1.06l-3.97 3.97-1.47-1.47a.75.75 0 1 0-1.06 1.06l2 2a.75.75 0 0 0 1.06 0l4.5-4.5Z" clipRule="evenodd" />
                      ) : (
                        <path fillRule="evenodd" d="M12 2.25a9.75 9.75 0 1 0 0 19.5 9.75 9.75 0 0 0 0-19.5Zm.75 5.25a.75.75 0 0 0-1.5 0v6a.75.75 0 0 0 1.5 0v-6Zm0 9a.75.75 0 1 0-1.5 0 .75.75 0 0 0 1.5 0Z" clipRule="evenodd" />
                      )}
                    </svg>
                  )}
                </div>
              )}

              <div className="flex-1">
                {title && (
                  <h2 id="alert-title" className={"text-lg font-semibold " + t.title}>
                    {title}
                  </h2>
                )}
                {description && (
                  <p id="alert-desc" className={"mt-1 text-sm leading-6 " + t.desc}>
                    {description}
                  </p>
                )}

                <div className="mt-4 flex flex-wrap items-center gap-2">
                  {actions ?? (
                    <button
                      onClick={onClose}
                      className={
                        "inline-flex min-w-[96px] items-center justify-center rounded-xl px-4 py-2 text-sm font-medium focus-visible:outline-none " +
                        t.primaryBtn
                      }
                    >
                      Ок
                    </button>
                  )}
                </div>
              </div>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}