<template>
  <section>
    <h1 class="title">Upcoming Events</h1>
    <p class="sub">Browse published events and register.</p>
    <div v-if="loading" class="muted">Loading…</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else-if="!events.length" class="empty">
      <p>No upcoming events right now.</p>
    </div>
    <ul v-else class="event-list">
      <li v-for="event in events" :key="event.name" class="event-item">
        <router-link :to="`/events/${event.slug}`" class="event-row">
          <div>
            <h2>{{ event.event_name }}</h2>
            <p>{{ event.short_description }}</p>
            <p class="meta">{{ formatDate(event.event_start) }} · {{ event.venue_name || event.city }}</p>
          </div>
          <span class="chev">→</span>
        </router-link>
      </li>
    </ul>
  </section>
</template>

<script setup>
import { onMounted, ref } from "vue"
import { api } from "@/services/api"

const events = ref([])
const loading = ref(true)
const error = ref("")

function formatDate(v) {
  if (!v) return ""
  return new Date(v).toLocaleString()
}

onMounted(async () => {
  try {
    const res = await api("event_management.api.attendee.list_upcoming_events")
    events.value = Array.isArray(res?.data) ? res.data : []
  } catch (e) {
    error.value = e.message || "Failed to load events"
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.title { font-family: var(--em-serif); font-size: 2rem; margin: 0 0 .35rem; }
.sub { opacity: .75; margin-bottom: 1.5rem; }
.event-list { list-style: none; padding: 0; margin: 0; display: grid; gap: .75rem; }
.event-item { border: 1px solid var(--em-line); border-radius: 12px; overflow: hidden; background: rgba(255,255,255,.55); }
.event-row {
  display: flex; justify-content: space-between; align-items: center; gap: 1rem;
  padding: 1rem 1.1rem; text-decoration: none; color: var(--em-ink);
  transition: background .2s ease, transform .2s ease;
}
.chev { color: var(--em-accent); font-size: 1.25rem; font-weight: 700; }
.event-row:hover { background: rgba(15,110,86,.06); transform: translateX(2px); }
.event-row h2 { margin: 0 0 .25rem; font-size: 1.2rem; font-family: var(--em-serif); }
.meta { opacity: .65; font-size: .9rem; }
.muted, .error, .empty { opacity: .85; }
.hint { opacity: .7; }
.error { color: #9b1c1c; }
</style>
