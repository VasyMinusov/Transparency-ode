// Разворачиваемый текст: длинные фрагменты с кнопкой «развернуть/свернуть».
import { useState } from "react";

export default function Expandable({ text, limit = 320 }: { text: string; limit?: number }) {
  const [open, setOpen] = useState(false);
  if (!text || text.length <= limit) return <>{text}</>;
  return (
    <span>
      {open ? text : `${text.slice(0, limit)}… `}
      <button className="link small-link" onClick={() => setOpen((v) => !v)}>
        {open ? "свернуть" : "развернуть"}
      </button>
    </span>
  );
}
