export default function Time ({ iso })  {
  const date = new Date(iso);

  // Опции форматирования
  const options = {
    day: "numeric",
    month: "long",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "UTC"
  };

  const formatted = new Intl.DateTimeFormat("ru-RU", options).format(date);

  return (
    <time
      dateTime={iso}
      className="px-2 py-1 rounded-md font-medium
                 bg-gray-200 text-gray-800
                 dark:bg-gray-700 dark:text-gray-100"
    >
      {formatted}
    </time>
  );
};