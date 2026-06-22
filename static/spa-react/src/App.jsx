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
    events.forEach((event) => {
      if (event.category) set.add(event.category)
    })
    return Array.from(set)
  }, [events])

  const filteredEvents = useMemo(() => {
    const lowerQuery = query.toLowerCase().trim()
    return events.filter((event) => {
      const matchesQuery =
        !lowerQuery ||
        [event.title, event.location, event.category].some((value) =>
          String(value || '')
            .toLowerCase()
            .includes(lowerQuery)
        )
      const matchesCategory =
        activeCategory === 'Все' || event.category === activeCategory
      return matchesQuery && matchesCategory
    })
  }, [events, query, activeCategory])

  const openEvent = (eventId) => {
    window.location.href = `/event/${eventId}`
  }

  return (
    <div className="page-shell">
      {/* ── Header ── */}
      <header className="page-header">
        <div className="brand">
          <div className="brand-icon">🎫</div>
          <div className="brand-name">SC-TICKETS</div>
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
          <span className="admin-badge">ADMIN</span>
        </div>
      </header>

      {/* ── Content ── */}
      {activeTab === 'afisha' ? (
        <main className="afisha-page">
          {/* Search + filters */}
          <section className="search-row">
            <div className="search-input-wrap">
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

          {/* Cards */}
          <section className="cards-grid">
            {filteredEvents.length > 0 ? (
              filteredEvents.map((event) => {
                const sold = event.sold || 0
                const capacity = event.capacity || 1
                const percent = Math.round((sold / capacity) * 100)
                const available = capacity - sold
                const hasCover = !!event.cover_url

                return (
                  <article key={event.id} className="event-card">
                    <div
                      className="event-cover"
                      style={
                        hasCover
                          ? { backgroundImage: `url(${event.cover_url})` }
                          : undefined
                      }
                    >
                      {!hasCover && (
                        <span className="event-cover-placeholder">
                          600 × 400
                        </span>
                      )}
                      {event.category && (
                        <span className="event-label">{event.category}</span>
                      )}
                    </div>

                    <div className="event-body">
                      <h2>{event.title}</h2>
                      <div className="event-meta-row">
                        <span className="event-meta-item">
                          <span className="meta-icon">📅</span>
                          {event.date}
                        </span>
                        <span className="event-meta-item">
                          <span className="meta-icon">📍</span>
                          {event.location || 'Не указано'}
                        </span>
                      </div>
                      <div className="event-progress-row">
                        <span className="event-progress-text">
                          Занято {percent}%
                        </span>
                        <span className="event-available">
                          {available} мест осталось
                        </span>
                      </div>
                      <div className="progress-bar">
                        <div
                          className="progress-fill"
                          style={{ width: `${Math.min(percent, 100)}%` }}
                        />
                      </div>
                      <button
                        type="button"
                        className="event-action"
                        disabled={available <= 0}
                        onClick={() => openEvent(event.id)}
                      >
                        <span className="action-icon">🎟</span>
                        {available <= 0 ? 'мест нет' : 'получить билет'}
                      </button>
                    </div>
                  </article>
                )
              })
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
