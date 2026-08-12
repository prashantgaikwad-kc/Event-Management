<template>
  <div class="em-app min-h-screen">
    <header class="em-header">
      <router-link to="/events" class="em-brand">Event Management</router-link>
      <nav class="em-nav">
        <router-link to="/events">Events</router-link>
        <router-link to="/my-registrations">My Registrations</router-link>
        <router-link to="/organizer/dashboard">Organizer</router-link>
        <router-link to="/scanner">Scanner</router-link>
      </nav>
    </header>
    <main class="em-main">
      <router-view />
    </main>
  </div>
</template>

<script setup>
</script>

<style>
@import url("https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=Fraunces:opsz,wght@9..144,500;700&display=swap");

:root {
  --em-ink: #1a2332;
  --em-paper: #f7f3ee;
  --em-accent: #0f6e56;
  --em-accent-2: #c45c26;
  --em-line: rgba(26, 35, 50, 0.12);
  --em-serif: "Fraunces", "Source Serif 4", Georgia, serif;
  --em-sans: "DM Sans", "Segoe UI", sans-serif;
}

.em-app {
  background:
    radial-gradient(1200px 600px at 10% -10%, rgba(15, 110, 86, 0.12), transparent 60%),
    radial-gradient(900px 500px at 100% 0%, rgba(196, 92, 38, 0.10), transparent 55%),
    linear-gradient(180deg, #fbf8f4 0%, var(--em-paper) 40%, #efe8df 100%);
  color: var(--em-ink);
  font-family: var(--em-sans);
}
.em-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  padding: 1rem 1.5rem;
  border-bottom: 1px solid var(--em-line);
  backdrop-filter: blur(8px);
  position: sticky;
  top: 0;
  z-index: 10;
}
.em-brand {
  font-family: var(--em-serif);
  font-size: 1.35rem;
  font-weight: 700;
  color: var(--em-ink);
  text-decoration: none;
}
.em-nav {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
}
.em-nav a {
  color: var(--em-ink);
  text-decoration: none;
  opacity: 0.75;
  font-size: 0.95rem;
}
.em-nav a.router-link-active {
  opacity: 1;
  color: var(--em-accent);
  font-weight: 600;
}
.em-main {
  max-width: 1100px;
  margin: 0 auto;
  padding: 1.5rem;
  min-height: 40vh;
}
.em-loading {
  opacity: 0.75;
  padding: 1rem 0;
}
</style>
