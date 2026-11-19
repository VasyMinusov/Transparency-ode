// Подобранные статьи НПА для сигнала: релевантность, конспект, ссылка на источник.
import { useState } from "react";
import type { ArticleMatch } from "../data/types";

export default function LegalArticles({ articles }: { articles: ArticleMatch[] }) {
  const [open, setOpen] = useState(false);
  if (!articles?.length) return null;
  return (
    <div className="legal-articles">
      <button className="link small-link" onClick={() => setOpen((v) => !v)}>
        {open ? "▾" : "▸"} Подобранные статьи НПА ({articles.length})
      </button>
      {open && (
        <div className="articles-list">
          {articles.map((a) => (
            <div className="article-card" key={a.id}>
              <div className="article-head">
                <b>{a.act}, {a.article} «{a.title}»</b>
                <span className="mono muted small">релевантность {(a.score * 100).toFixed(0)}%</span>
              </div>
              <p className="muted small">{a.excerpt}</p>
              <p className="muted small">Полный текст: publication.pravo.gov.ru</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
