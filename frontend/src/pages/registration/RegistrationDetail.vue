<template>
  <section v-if="reg">
    <h1 class="title">{{ reg.event.event_name }}</h1>
    <p>{{ reg.registration_reference }} · {{ reg.status }}</p>
    <p>Ticket: {{ reg.ticket_title }}</p>
    <p>Total: {{ reg.grand_total }} · Payment: {{ reg.payment_status }}</p>
    <p>Check-in: {{ reg.checked_in ? `Yes (${reg.checked_in_at})` : "No" }}</p>

    <div v-if="reg.status === 'Pending Payment'" class="notice">
      <p>Complete payment to receive your ticket.</p>
      <button class="btn" :disabled="paying" @click="payNow">
        {{ paying ? "Processing…" : "Pay Now" }}
      </button>
    </div>

    <div class="actions">
      <router-link v-if="reg.status === 'Confirmed'" class="btn" :to="`/my-ticket/${reg.name}`">
        View Ticket
      </router-link>
      <button
        v-if="reg.status === 'Confirmed' && reg.event.allow_cancellation"
        class="btn ghost"
        @click="cancel"
      >
        Cancel
      </button>
    </div>
    <p v-if="message" class="message">{{ message }}</p>
  </section>
  <p v-else-if="error" class="error">{{ error }}</p>
  <p v-else class="muted">Loading…</p>
</template>

<script setup>
import { onMounted, ref } from "vue"
import { api } from "@/services/api"

const props = defineProps({ id: String })
const reg = ref(null)
const message = ref("")
const error = ref("")
const paying = ref(false)

async function refresh() {
  const res = await api("event_management.api.attendee.get_my_registration", { registration: props.id })
  reg.value = res.data
}

onMounted(async () => {
  try {
    await refresh()
  } catch (e) {
    error.value = e.message || "Registration not found"
  }
})

async function payNow() {
  paying.value = true
  message.value = ""
  try {
    await api("event_management.api.payment.verify_payment", {
      registration: props.id,
      payload: {
        payment_id: `pay_${Date.now()}`,
        order_id: reg.value?.payment_reference || reg.value?.name,
        signature: "dev",
      },
    })
    message.value = "Payment confirmed."
    await refresh()
  } catch (e) {
    message.value = e.message || "Payment failed"
  } finally {
    paying.value = false
  }
}

async function cancel() {
  const res = await api("event_management.api.attendee.cancel_registration", { registration: props.id })
  message.value = res.message || "Cancelled"
  await refresh()
}
</script>

<style scoped>
.title { font-family: var(--em-serif); font-size: 2rem; }
.notice {
  margin: 1rem 0;
  padding: 1rem;
  border: 1px solid var(--em-line);
  border-radius: 10px;
}
.actions { display: flex; gap: .75rem; margin-top: 1rem; flex-wrap: wrap; }
.btn {
  background: var(--em-accent); color: #fff; text-decoration: none; border: 0;
  padding: .7rem 1rem; border-radius: 8px; font-weight: 600; cursor: pointer;
}
.btn.ghost { background: transparent; color: var(--em-ink); border: 1px solid var(--em-line); }
.btn:disabled { opacity: .55; cursor: not-allowed; }
.message { margin-top: 1rem; }
.error { color: #9b1c1c; }
.muted { opacity: .75; }
</style>
