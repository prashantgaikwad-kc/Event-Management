<template>
  <section>
    <h1 class="title">My Registrations</h1>
    <div v-if="loading" class="muted">Loading…</div>
    <div v-else-if="error" class="error">
      <p>{{ error }}</p>
      <a class="btn" href="/login?redirect-to=/em/my-registrations">Login to continue</a>
    </div>
    <div v-else-if="!rows.length" class="empty">
      <p>No registrations yet.</p>
      <router-link class="btn" to="/events">Browse events</router-link>
    </div>
    <ul v-else class="list">
      <li v-for="r in rows" :key="r.name">
        <router-link :to="`/my-registrations/${r.name}`">
          <strong>{{ r.event_name }}</strong>
          <span>{{ r.registration_reference }} · {{ r.status }} · {{ r.ticket_title }}</span>
        </router-link>
      </li>
    </ul>
  </section>
</template>

<script setup>
import { onMounted, ref } from "vue"
import { api } from "@/services/api"

const rows = ref([])
const loading = ref(true)
const error = ref("")

onMounted(async () => {
  try {
    const res = await api("event_management.api.attendee.list_my_registrations")
    rows.value = res.data || []
  } catch (e) {
    error.value = e.message || "Could not load registrations. Please login first."
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.title { font-family: var(--em-serif); font-size: 2rem; }
.list { list-style: none; padding: 0; display: grid; gap: .75rem; }
.list a { display: grid; gap: .2rem; text-decoration: none; color: inherit; padding: .85rem 0; border-bottom: 1px solid var(--em-line); }
.list span { opacity: .65; font-size: .9rem; }
.empty, .error { margin-top: 1rem; }
.hint { opacity: .7; max-width: 36rem; }
.btn {
  display: inline-block; margin-top: .75rem; background: var(--em-accent); color: #fff;
  text-decoration: none; padding: .7rem 1rem; border-radius: 8px; font-weight: 600;
}
.error { color: #9b1c1c; }
</style>
