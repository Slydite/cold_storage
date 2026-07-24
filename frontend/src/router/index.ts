import { createRouter, createWebHistory } from 'vue-router'
import DashboardView from '../views/DashboardView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'dashboard',
      component: DashboardView,
      meta: { title: 'Dashboard', subtitle: "Good evening, Admin 👋 Here's what's happening in your cold storage today." }
    },
    {
      path: '/grn',
      name: 'grn',
      component: () => import('../views/GrnView.vue'),
      meta: { title: 'GRN / Inward', subtitle: 'List of all inward (GRN) records & goods receipts.' }
    },
    {
      path: '/delivery',
      name: 'delivery',
      component: () => import('../views/DeliveryView.vue'),
      meta: { title: 'Delivery / Outward', subtitle: 'Manage outward goods dispatch and delivery challans.' }
    },
    {
      path: '/inventory',
      name: 'inventory',
      component: () => import('../views/InventoryView.vue'),
      meta: { title: 'Inventory / Lots', subtitle: 'View and manage lot-wise stock ledger and chambers.' }
    },
    {
      path: '/billing',
      name: 'billing',
      component: () => import('../views/BillingView.vue'),
      meta: { title: 'Billing & Rent', subtitle: 'Rent calculation engine and billing history.' }
    },
    {
      path: '/invoicing',
      name: 'invoicing',
      component: () => import('../views/InvoicingView.vue'),
      meta: { title: 'Invoicing', subtitle: 'Generate and track customer GST tax invoices.' }
    },
    {
      path: '/parties',
      name: 'parties',
      component: () => import('../views/PartiesView.vue'),
      meta: { title: 'Parties', subtitle: 'Customer and supplier directory management.' }
    },
    {
      path: '/reports',
      name: 'reports',
      component: () => import('../views/ReportsView.vue'),
      meta: { title: 'Reports & Analytics', subtitle: 'Stock occupancy, revenue, and audit reports.' }
    },
    {
      path: '/settings',
      name: 'settings',
      component: () => import('../views/SettingsView.vue'),
      meta: { title: 'Settings', subtitle: 'Facility configuration, units, and preference settings.' }
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('../views/LoginView.vue'),
      meta: { public: true, title: 'Sign in', subtitle: '' }
    }
  ]
})

router.beforeEach(async (to) => {
  const { useAuthStore } = await import('../stores/auth')
  const authStore = useAuthStore()

  if (!authStore.authChecked) {
    await authStore.fetchCurrentUser()
  }

  const isPublic = Boolean(to.meta.public)
  const isAuthenticated = authStore.isAuthenticated

  if (!isPublic && !isAuthenticated) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }

  if (to.name === 'login' && isAuthenticated) {
    return '/'
  }
})

export default router
