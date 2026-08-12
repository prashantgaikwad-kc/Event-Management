<template>
  <section v-if="ticket" class="ticket">
    <h1 class="title">{{ ticket.event_name }}</h1>
    <p>{{ ticket.attendee_name }}</p>
    <p>{{ formatDate(ticket.event_start) }} · {{ ticket.venue_name }}</p>
    <p>{{ ticket.ticket_title }}</p>
    <p class="ref">{{ ticket.registration_reference }}</p>
    <img v-if="ticket.qr_image_base64" :src="`data:image/png;base64,${ticket.qr_image_base64}`" alt="Ticket QR" />
    <div class="actions">
      <a v-if="ticket.pdf_url" class="btn" :href="ticket.pdf_url" target="_blank" rel="noopener">Download PDF</a>
      <router-link class="btn ghost" to="/my-registrations">Back to registrations</router-link>
    </div>
  </section>
  <p v-else class="muted">Loading ticket…</p>
</template>

<script setup>
import { onMounted, ref } from "vue"
import { api } from "@/services/api"

const props = defineProps({ id: String })
const ticket = ref(null)

function formatDate(v) {
  return v ? new Date(v).toLocaleString() : ""
}

onMounted(async () => {
  const res = await api("event_management.api.attendee.get_my_ticket", { registration: props.id })
  ticket.value = res.data
})
</script>

<style scoped>
.ticket { text-align: center; padding: 1rem; }
.title { font-family: var(--em-serif); font-size: 2rem; }
.ref { letter-spacing: .08em; opacity: .7; }
img { width: min(280px, 80vw); margin: 1.25rem auto; display: block; }
.actions { display: flex; gap: .75rem; justify-content: center; flex-wrap: wrap; margin-top: 1.25rem; }
.btn {
  background: var(--em-accent); color: #fff; text-decoration: none; border: 0;
  padding: .7rem 1rem; border-radius: 8px; font-weight: 600;
}
.btn.ghost { background: transparent; color: var(--em-ink); border: 1px solid var(--em-line); }
.muted { opacity: .75; text-align: center; }
</style>
