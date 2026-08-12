<template>
  <section v-if="event">
    <p class="eyebrow">{{ event.city || "Event" }}</p>
    <h1 class="title">{{ event.event_name }}</h1>
    <p class="meta">{{ formatDate(event.event_start) }} · {{ event.venue_name }}</p>
    <div class="desc" v-html="event.description || event.short_description"></div>

    <h2>Tickets</h2>
    <div class="options">
      <label v-for="t in event.ticket_types" :key="t.name" class="option">
        <input type="radio" :value="t.name" v-model="ticketType" :disabled="!t.available" />
        <span>
          <strong>{{ t.title }}</strong>
          — {{ formatMoney(t.price) }}
          <em>{{ t.available ? `${t.available_count} left` : "Sold out" }}</em>
        </span>
      </label>
    </div>

    <h2 v-if="event.addons?.length">Add-ons</h2>
    <div class="options">
      <label v-for="a in event.addons" :key="a.name" class="option">
        <input type="checkbox" :value="a.name" v-model="addons" :disabled="!a.available" />
        <span>
          <strong>{{ a.title }}</strong>
          — {{ formatMoney(a.price) }}
          <em>{{ a.available ? "Available" : "Out of stock" }}</em>
        </span>
      </label>
    </div>

    <button class="cta" :disabled="!ticketType || submitting" @click="register">
      {{ submitting ? "Registering…" : "Register" }}
    </button>
    <p v-if="message" class="msg">{{ message }}</p>
  </section>
  <p v-else-if="error" class="error">{{ error }}</p>
  <p v-else class="muted">Loading…</p>
</template>

<script setup>
import { onMounted, ref } from "vue"
import { useRouter } from "vue-router"
import { api } from "@/services/api"

const props = defineProps({ slug: String })
const router = useRouter()
const event = ref(null)
const ticketType = ref("")
const addons = ref([])
const submitting = ref(false)
const message = ref("")
const error = ref("")

function formatDate(v) {
  return v ? new Date(v).toLocaleString() : ""
}
function formatMoney(v) {
  return new Intl.NumberFormat(undefined, { style: "currency", currency: event.value?.currency || "INR" }).format(v || 0)
}

onMounted(async () => {
  try {
    const res = await api("event_management.api.attendee.get_event", { slug: props.slug })
    event.value = res.data
  } catch (e) {
    error.value = e.message || "Event not found"
  }
})

async function register() {
  submitting.value = true
  message.value = ""
  try {
    const res = await api("event_management.api.attendee.create_registration", {
      event: event.value.name,
      ticket_type: ticketType.value,
      addon_ids: addons.value,
    })
    message.value = res.message || "Registered"
    if (res.data?.registration) {
      router.push(`/my-registrations/${res.data.registration}`)
    }
  } catch (e) {
    const text = e.message || "Registration failed"
    message.value = text
    if (/login|permission|not permitted/i.test(text)) {
      window.location.href = `/login?redirect-to=/em/events/${props.slug}`
    }
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.eyebrow { text-transform: uppercase; letter-spacing: .08em; font-size: .75rem; opacity: .6; }
.title { font-family: var(--em-serif); font-size: 2.2rem; margin: .2rem 0 .4rem; }
.meta { opacity: .7; margin-bottom: 1rem; }
.options { display: grid; gap: .6rem; margin: .75rem 0 1.25rem; }
.option { display: flex; gap: .6rem; align-items: flex-start; }
.option em { opacity: .55; font-style: normal; margin-left: .35rem; }
.cta {
  background: var(--em-accent); color: white; border: 0; border-radius: 8px;
  padding: .85rem 1.4rem; font-weight: 600; cursor: pointer;
}
.cta:disabled { opacity: .5; cursor: not-allowed; }
.msg, .error, .muted { margin-top: 1rem; }
.error { color: #9b1c1c; }
</style>
