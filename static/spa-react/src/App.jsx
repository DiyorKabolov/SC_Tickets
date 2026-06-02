import React, { useEffect, useMemo, useState } from 'react'

const TABS = [
  { id: 'afisha', title: 'Афиша' },
  { id: 'details', title: 'Описание события' },
  { id: 'tickets', title: 'Мои билеты' },
  { id: 'profile', title: 'Личный кабинет' },
]

const FORMAT_OPTIONS = ['Все', 'Кино', 'Лекции', 'Балы']

export default function App() {
  const [events, setEvents] = useState([])
  const [query, setQuery] = useState('')
  const [activeTab, setActiveTab] = useState('afisha')
  const [activeCategory, setActiveCategory] = useState('Все')

  useEffect(() => {
    fetch('/api/events')
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => setEvents(data?.events || []))
      .catch(() => setEvents([]))
  }, [])

  const categories = useMemo(() => {
    const set = new Set(FORMAT_OPTIONS)
    events.forEach((event) => set.add(event.category || 'Без категории'))
    return Array.from(set)
  }, [events])

  const filteredEvents = useMemo(() => {
    const lowerQuery = query.toLowerCase().trim()
    return events.filter((event) => {
      const matchesQuery =
        !lowerQuery ||
        [event.title, event.location, event.category]
          .some((value) => String(value || '').toLowerCase().includes(lowerQuery))
      const matchesCategory =
        activeCategory === 'Все' ||
        (event.category || 'Без категории') === activeCategory
      return matchesQuery && matchesCategory
    })
  }, [events, query, activeCategory])

  const fallbackCover = '/static/design/page1_img1.jpeg'

  return (
    <div className="page-shell">
      <header className="page-header">
        <div className="brand">
          <div className="brand-mark">SC</div>
          <div>
            <div className="brand-name">SC-TICKETS</div>
            <div className="brand-meta">Лиловая афиша</div>
          </div>
        </div>

        <nav className="page-nav">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              type="button"
              className={activeTab === tab.id ? 'tab-button active' : 'tab-button'}
              onClick={() => setActiveTab(tab.id)}
            >
              {tab.title}
            </button>
          ))}
        </nav>

        <div className="header-actions">
          <span className="user-name">Диёр</span>
          <button type="button" className="admin-button">ADMIN</button>
        </div>
      </header>

      {activeTab === 'afisha' ? (
        <main className="afisha-page">
          <section className="search-row">
            <div className="search-input">
              <span className="search-icon">🔍</span>
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Поиск событий, мест, артистов..."
              />
            </div>

            <div className="format-panel">
              <span className="format-label">ФОРМАТ:</span>
              <div className="format-pills">
                {categories.map((category) => (
                  <button
                    key={category}
                    type="button"
                    className={
                      category === activeCategory ? 'format-pill active' : 'format-pill'
                    }
                    onClick={() => setActiveCategory(category)}
                  >
                    {category}
                  </button>
                ))}
              </div>
            </div>
          </section>

          <section className="cards-grid">
            {filteredEvents.length > 0 ? (
              filteredEvents.map((event) => (
                <article key={event.id} className="event-card">
                  <div
                    className="event-cover"
                    style={{
                      backgroundImage: `linear-gradient(180deg, rgba(18, 8, 33, 0.2), rgba(18, 8, 33, 0.9)), url(${event.cover_url || fallbackCover})`,
                    }}
                  >
                    <span className="event-label">
                      {(event.category || 'Без категории').toUpperCase()}
                    </span>
                  </div>
                  <div className="event-body">
                    <h2>{event.title}</h2>
                    <div className="event-meta-row">
                      <span className="event-meta-item">📅 {event.date}</span>
                      <span className="event-meta-item">📍 {event.location || 'Не указано'}</span>
                    </div>
                    <div className="event-progress-row">
                      <span className="event-progress-text">Занято {event.percent}%</span>
                      <span className="event-available">{event.available} мест осталось</span>
                    </div>
                    <div className="progress-bar">
                      <div className="progress-fill" style={{ width: `${event.percent}%` }} />
                    </div>
                    <button type="button" className="event-action">Получить билет</button>
                  </div>
                </article>
              ))
            ) : (
              <div className="empty-state">
                События не найдены. Измените запрос или выберите другую категорию.
              </div>
            )}
          </section>
        </main>
      ) : (
        <main className="placeholder-page">
          <h2>{TABS.find((tab) => tab.id === activeTab)?.title}</h2>
          <p>Эта вкладка пока в разработке — для демонстрации доступна только «Афиша».</p>
        </main>
      )}
    </div>
  )
}
