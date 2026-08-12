<template>
  <section>
    <h1 class="title">Organizer Dashboard</h1>
    <label class="filter">
      Event
      <select v-model="event" @change="load">
        <option value="">All events</option>
        <option v-for="e in events" :key="e.name" :value="e.name">{{ e.event_name }}</option>
      </select>
    </label>

    <div v-if="loading" class="muted">Loading dashboard…</div>

    <div v-if="metrics" class="kpis">
      <div v-for="(val, key) in metrics.kpis" :key="key" class="kpi">
        <span>{{ labelize(key) }}</span>
        <strong>{{ formatValue(key, val) }}</strong>
      </div>
    </div>

    <div v-if="metrics" class="charts">
      <div class="chart-block">
        <h2>Registration trend</h2>
        <ul>
          <li v-for="row in metrics.charts.registration_trend" :key="'r'+row.day">
            <span>{{ row.day }}</span>
            <b>{{ row.count }}</b>
            <i :style="{ width: barWidth(row.count, maxReg) }"></i>
          </li>
        </ul>
      </div>
      <div class="chart-block">
        <h2>Ticket distribution</h2>
        <ul>
          <li v-for="row in metrics.charts.ticket_type_distribution" :key="row.ticket_type">
            <span>{{ row.ticket_type }}</span>
            <b>{{ row.count }}</b>
            <i :style="{ width: barWidth(row.count, maxTicket) }"></i>
          </li>
        </ul>
      </div>
      <div class="chart-block">
        <h2>Attendance</h2>
        <ul>
          <li v-for="row in metrics.charts.attendance" :key="row.label">
            <span>{{ row.label }}</span>
            <b>{{ row.count }}</b>
            <i :style="{ width: barWidth(row.count, maxAtt) }"></i>
          </li>
        </ul>
      </div>
      <div class="chart-block">
        <h2>Revenue trend</h2>
        <ul>
          <li v-for="row in metrics.charts.revenue_trend" :key="'v'+row.day">
            <span>{{ row.day }}</span>
            <b>{{ Number(row.revenue || 0).toFixed(0) }}</b>
            <i :style="{ width: barWidth(row.revenue, maxRev) }"></i>
          </li>
        </ul>
      </div>
    </div>

    <button class="btn" :disabled="exporting" @click="exportCsv">{{ exporting ? "Exporting…" : "Export Attendees" }}</button>
    <p v-if="error" class="error">{{ error }}</p>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from "vue"
import { api } from "@/services/api"

const event = ref("")
const events = ref([])
const metrics = ref(null)
const loading = ref(true)
const error = ref("")
const exporting = ref(false)

function labelize(key) {
  return key.replaceAll("_", " ")
}
function formatValue(key, val) {
  if (key === "revenue") return Number(val || 0).toFixed(2)
  if (key === "attendance_percentage") return `${val}%`
  return val
}
function barWidth(value, max) {
  const pct = max ? Math.max(6, Math.round((Number(value || 0) / max) * 100)) : 6
  return `${pct}%`
}

const maxReg = computed(() => Math.max(1, ...(metrics.value?.charts?.registration_trend || []).map((r) => Number(r.count || 0))))
const maxTicket = computed(() => Math.max(1, ...(metrics.value?.charts?.ticket_type_distribution || []).map((r) => Number(r.count || 0))))
const maxAtt = computed(() => Math.max(1, ...(metrics.value?.charts?.attendance || []).map((r) => Number(r.count || 0))))
const maxRev = computed(() => Math.max(1, ...(metrics.value?.charts?.revenue_trend || []).map((r) => Number(r.revenue || 0))))

async function load() {
  error.value = ""
  try {
    const res = await api("event_management.api.organizer.dashboard_metrics", {
      event: event.value || undefined,
    })
    metrics.value = res.data
  } catch (e) {
    error.value = e.message || "Could not load dashboard. Login as Organizer or Administrator."
    metrics.value = null
  }
}

async function exportCsv() {
  exporting.value = true
  try {
    window.location.href = `/api/method/event_management.api.organizer.export_attendees?event=${encodeURIComponent(event.value || "")}`
  } finally {
    exporting.value = false
  }
}

onMounted(async () => {
  loading.value = true
  error.value = ""
  try {
    const list = await api("event_management.api.attendee.list_upcoming_events", { limit: 100 })
    events.value = list?.data || []
    await load()
  } catch (e) {
    error.value = e.message || "Could not load dashboard."
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.title { font-family: var(--em-serif); font-size: 2rem; }
.filter { display: inline-flex; gap: .5rem; align-items: center; margin: .75rem 0 1rem; }
.kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: .75rem; margin: 1rem 0; }
.kpi { padding: .9rem; border-bottom: 1px solid var(--em-line); display: grid; gap: .35rem; }
.kpi span { opacity: .65; font-size: .8rem; text-transform: uppercase; letter-spacing: .04em; }
.kpi strong { font-size: 1.4rem; font-family: var(--em-serif); }
.charts { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 1rem; margin: 1.25rem 0; }
.chart-block h2 { font-size: 1rem; margin: 0 0 .5rem; font-family: var(--em-serif); }
.chart-block ul { list-style: none; padding: 0; margin: 0; display: grid; gap: .45rem; }
.chart-block li { position: relative; display: flex; justify-content: space-between; gap: .5rem; padding: .35rem 0; }
.chart-block li i {
  position: absolute; left: 0; bottom: 0; height: 3px; background: var(--em-accent); opacity: .55; border-radius: 2px;
}
.btn { background: var(--em-accent); color: #fff; border: 0; border-radius: 8px; padding: .7rem 1rem; cursor: pointer; }
.btn:disabled { opacity: .55; cursor: not-allowed; }
select { padding: .4rem; }
.error { color: #9b1c1c; margin-top: 1rem; }
.muted { opacity: .75; margin: 1rem 0; }
</style>
