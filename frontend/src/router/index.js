import { createRouter, createWebHistory } from "vue-router"
import EventList from "@/pages/events/EventList.vue"
import EventDetail from "@/pages/events/EventDetail.vue"
import MyRegistrations from "@/pages/registration/MyRegistrations.vue"
import RegistrationDetail from "@/pages/registration/RegistrationDetail.vue"
import MyTicket from "@/pages/ticket/MyTicket.vue"
import Dashboard from "@/pages/organizer/Dashboard.vue"
import Scanner from "@/pages/scanner/Scanner.vue"
import ManualCheckin from "@/pages/scanner/ManualCheckin.vue"

const routes = [
  { path: "/", redirect: "/events" },
  { path: "/events", name: "Events", component: EventList },
  { path: "/events/:slug", name: "EventDetail", component: EventDetail, props: true },
  {
    path: "/my-registrations",
    alias: "/my_registrations",
    name: "MyRegistrations",
    component: MyRegistrations,
  },
  {
    path: "/my-registrations/:id",
    name: "RegistrationDetail",
    component: RegistrationDetail,
    props: true,
  },
  { path: "/my-ticket/:id", name: "MyTicket", component: MyTicket, props: true },
  { path: "/organizer/dashboard", name: "OrganizerDashboard", component: Dashboard },
  { path: "/scanner", name: "Scanner", component: Scanner },
  { path: "/scanner/manual", name: "ManualCheckin", component: ManualCheckin },
]

const router = createRouter({
  history: createWebHistory("/em"),
  routes,
})

export default router
