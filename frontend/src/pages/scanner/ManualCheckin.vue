<template>
  <section class="manual">
    <h1 class="title">Manual Check-in</h1>
    <input v-model="query" placeholder="Name, email, or reference" @keyup.enter="search" />
    <button class="btn" @click="search">Search</button>
    <ul class="results">
      <li v-for="r in rows" :key="r.name">
        <div>
          <strong>{{ r.attendee_name }}</strong>
          <span>{{ r.attendee_email }} · {{ r.ticket_title }} · {{ r.payment_status }}</span>
          <span>{{ r.checked_in ? "Already checked in" : "Not checked in" }}</span>
        </div>
        <button class="btn small" :disabled="r.checked_in" @click="checkin(r.name)">Check in</button>
      </li>
    </ul>
    <p v-if="message">{{ message }}</p>
    <router-link to="/scanner">Back to scanner</router-link>
  </section>
</template>

<script setup>
import { ref } from "vue"
import { api } from "@/services/api"

const query = ref("")
const rows = ref([])
const message = ref("")

async function search() {
  const res = await api("event_management.api.checkin.search_registration", { query: query.value })
  rows.value = res.data || []
}

async function checkin(name) {
  const res = await api("event_management.api.checkin.checkin_by_registration", { registration: name })
  message.value = `${res.code}: ${res.message || ""}`
  await search()
}
</script>

<style scoped>
.title { font-family: var(--em-serif); font-size: 2rem; }
input { width: 100%; padding: .8rem; border-radius: 8px; border: 1px solid var(--em-line); margin: .75rem 0; }
.btn { background: var(--em-accent); color: #fff; border: 0; border-radius: 8px; padding: .7rem 1rem; cursor: pointer; }
.btn.small { padding: .5rem .75rem; }
.results { list-style: none; padding: 0; display: grid; gap: .75rem; margin-top: 1rem; }
.results li { display: flex; justify-content: space-between; gap: 1rem; padding: .75rem 0; border-bottom: 1px solid var(--em-line); }
.results span { display: block; opacity: .65; font-size: .85rem; }
</style>
